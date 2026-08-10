"""Per-user LLM provider settings — backs the "AI Provider" section of Settings.

Stores provider, base URL and model name; the API key is encrypted at rest
(Fernet, see crypto_utils.py) and is never returned by the API — only
`has_api_key` is exposed. An absent `api_key` in a PUT keeps the stored key;
an explicit empty string clears it.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .auth import get_current_user
from .crypto_utils import encrypt_secret
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
        }
    return {
        "provider": row.provider,
        "base_url": row.base_url,
        "model": row.model,
        "has_api_key": bool(row.api_key_encrypted),
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
