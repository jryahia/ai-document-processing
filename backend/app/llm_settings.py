"""Per-user LLM provider settings — backs the "AI Provider" section of Settings.

Stores provider, base URL and model name; the API key is encrypted at rest
(Fernet, see crypto_utils.py) and is never returned by the API — only
`has_api_key` is exposed. An absent `api_key` in a PUT keeps the stored key;
an explicit empty string clears it. The last "Test Connection" result is also
persisted here so the UI can show it without re-testing on every load.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from openai import OpenAI, OpenAIError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .auth import get_current_user
from .crypto_utils import decrypt_secret, encrypt_secret
from .database import get_db
from .models import LLMSettings, User

router = APIRouter(prefix="/api/llm-settings", tags=["llm-settings"])

# Sensible defaults per provider (frontend mirrors these for the dropdown UX).
PROVIDER_PRESETS: dict[str, dict[str, str]] = {
    "openai": {"base_url": "https://api.openai.com/v1", "model": "gpt-4o-mini"},
    "deepseek": {"base_url": "https://api.deepseek.com", "model": "deepseek-chat"},
    "openrouter": {"base_url": "https://openrouter.ai/api/v1", "model": "openai/gpt-4o-mini"},
    "groq": {"base_url": "https://api.groq.com/openai/v1", "model": "llama-3.1-8b-instant"},
    "custom": {"base_url": "", "model": ""},
}
VALID_PROVIDERS = set(PROVIDER_PRESETS)

DEFAULT_PROVIDER = "openai"


async def _load(db: AsyncSession, user_id) -> LLMSettings | None:
    result = await db.execute(select(LLMSettings).where(LLMSettings.user_id == user_id))
    return result.scalar_one_or_none()


def _to_payload(row: LLMSettings | None) -> dict:
    preset = PROVIDER_PRESETS.get(row.provider if row else DEFAULT_PROVIDER, PROVIDER_PRESETS[DEFAULT_PROVIDER])
    if row is None:
        return {
            "provider": DEFAULT_PROVIDER,
            "base_url": preset["base_url"],
            "model": preset["model"],
            "has_api_key": False,
            "last_test_status": None,
            "last_test_message": None,
            "last_test_at": None,
        }
    return {
        "provider": row.provider,
        "base_url": row.base_url,
        "model": row.model,
        "has_api_key": bool(row.api_key_encrypted),
        "last_test_status": row.last_test_status,
        "last_test_message": row.last_test_message,
        "last_test_at": row.last_test_at.isoformat() if row.last_test_at else None,
    }


@router.get("")
async def get_llm_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _to_payload(await _load(db, current_user.id))


@router.put("")
async def update_llm_settings(
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    provider = (data.get("provider") or DEFAULT_PROVIDER).strip().lower()
    if provider not in VALID_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown provider '{provider}'. Valid: {sorted(VALID_PROVIDERS)}")

    base_url = (data.get("base_url") or "").strip()
    model = (data.get("model") or "").strip()

    if provider != "custom":
        preset = PROVIDER_PRESETS[provider]
        if not base_url:
            base_url = preset["base_url"]
        if not model:
            model = preset["model"]
    else:
        if not base_url:
            raise HTTPException(status_code=400, detail="base_url is required for the custom provider")
        if not model:
            raise HTTPException(status_code=400, detail="model is required for the custom provider")

    if len(base_url) > 512:
        raise HTTPException(status_code=400, detail="base_url must be 512 characters or fewer")
    if len(model) > 128:
        raise HTTPException(status_code=400, detail="model must be 128 characters or fewer")
    if not base_url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="base_url must start with http:// or https://")

    row = await _load(db, current_user.id)
    if row is None:
        row = LLMSettings(user_id=current_user.id)
        db.add(row)

    row.provider = provider
    row.base_url = base_url
    row.model = model

    if "api_key" in data:
        api_key = (data.get("api_key") or "").strip()
        if api_key:
            row.api_key_encrypted = encrypt_secret(api_key)
        else:
            row.api_key_encrypted = None  # explicit empty string clears the key

    await db.commit()
    await db.refresh(row)
    return _to_payload(row)


@router.post("/test")
async def test_llm_connection(
    data: dict | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Make a minimal real completion call to the provider.

    Body (optional) may carry unsaved config: {provider, base_url, model,
    api_key}. Values not provided fall back to the saved config; an absent
    api_key falls back to the saved (decrypted) key. A provided api_key is
    used for the test only and is NOT stored. The result is persisted on the
    LLMSettings row (when one exists) so the UI can show it on page load.
    """
    data = data or {}
    row = await _load(db, current_user.id)
    saved = _to_payload(row)

    provider = (data.get("provider") or saved["provider"]).strip().lower()
    if provider not in VALID_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown provider '{provider}'. Valid: {sorted(VALID_PROVIDERS)}")

    base_url = (data.get("base_url") or saved["base_url"]).strip()
    model = (data.get("model") or saved["model"]).strip()
    if not base_url or not model:
        raise HTTPException(status_code=400, detail="base_url and model are required (fill the form or save first)")

    api_key = (data.get("api_key") or "").strip()
    if not api_key and row and row.api_key_encrypted:
        api_key = decrypt_secret(row.api_key_encrypted)

    now = datetime.now(timezone.utc)

    def persist(status: str, message: str):
        # Persist only when a settings row exists (no row = never saved).
        if row is None:
            return
        row.last_test_status = status
        row.last_test_message = message
        row.last_test_at = now

    if not api_key:
        msg = "No API key configured for this provider. Add a key and save, or type one to test."
        persist("failed", msg)
        await db.commit()
        return {
            "success": False,
            "provider": provider,
            "model": model,
            "message": msg,
            "tested_at": now.isoformat(),
        }

    try:
        client = OpenAI(api_key=api_key, base_url=base_url, timeout=15.0)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Reply with exactly: OK"}],
            max_tokens=5,
            temperature=0,
        )
        content = (response.choices[0].message.content or "").strip()
        msg = f"Connected — {provider} · {model} responded" + (f" (\"{content[:40]}\")" if content else "")
        persist("ok", msg)
        await db.commit()
        return {
            "success": True,
            "provider": provider,
            "model": model,
            "message": msg,
            "tested_at": now.isoformat(),
        }
    except OpenAIError as exc:
        msg = f"Failed — {type(exc).__name__}: {str(exc)[:300]}"
        persist("failed", msg)
        await db.commit()
        return {
            "success": False,
            "provider": provider,
            "model": model,
            "message": msg,
            "tested_at": now.isoformat(),
        }
    except Exception as exc:  # defensive — never crash the endpoint
        msg = f"Failed — {type(exc).__name__}: {str(exc)[:300]}"
        persist("failed", msg)
        await db.commit()
        return {
            "success": False,
            "provider": provider,
            "model": model,
            "message": msg,
            "tested_at": now.isoformat(),
        }
