"""Outbound processing-complete webhooks.

Deliberately synchronous (httpx.Client) so the Celery worker can call this
directly, and deliberately loud: every attempt writes a ``webhook_deliveries``
row and every failure goes through ``logger.error``. This is the opposite of
the email path in ``notifications.py``, which swallows errors on purpose.
"""
import json
import logging
import time
from datetime import datetime, timezone
from typing import Optional, Tuple

import httpx
from sqlalchemy.orm import Session

from .models import WebhookDelivery

logger = logging.getLogger(__name__)

WEBHOOK_TIMEOUT_SECONDS = 8.0
RETRY_DELAY_SECONDS = 5.0
MAX_RESPONSE_TEXT = 2000


def add_webhook_delivery(
    db: Session,
    *,
    user_id,
    document_id: Optional[str],
    webhook_url: str,
    status_code: Optional[int],
    payload: Optional[str],
    response_text: Optional[str],
    error: Optional[str],
    success: bool,
) -> None:
    """Insert one delivery-attempt row and commit it immediately.

    Committed on its own so the audit row survives the caller's later
    ``rollback()``/``raise`` on the task failure path. Never raises: a broken
    audit write must not take down document processing.
    """
    try:
        db.add(
            WebhookDelivery(
                user_id=user_id,
                document_id=document_id,
                webhook_url=webhook_url[:512],
                status_code=status_code,
                payload=payload,
                response_text=response_text[:MAX_RESPONSE_TEXT] if response_text else None,
                error=error,
                success=success,
            )
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error(
            "Failed to record webhook delivery for document %s to %s: %s",
            document_id,
            webhook_url,
            exc,
        )


def _post_once(webhook_url: str, payload: dict) -> Tuple[bool, Optional[int], Optional[str], Optional[str]]:
    """Return (success, status_code, response_text, error) for a single POST."""
    try:
        with httpx.Client(timeout=WEBHOOK_TIMEOUT_SECONDS) as client:
            response = client.post(webhook_url, json=payload)
        ok = 200 <= response.status_code < 300
        return (
            ok,
            response.status_code,
            response.text,
            None if ok else f"HTTP {response.status_code}",
        )
    except Exception as exc:
        return False, None, None, f"{type(exc).__name__}: {exc}"


def deliver_webhook(
    db: Session,
    user_pref,
    document_id: str,
    status: str,
    filename: str,
    confidence: Optional[int],
) -> Tuple[bool, Optional[int]]:
    """POST the processing-complete payload, with one retry after ~5s.

    Records a ``webhook_deliveries`` row for *every* attempt and returns
    ``(success, status_code_of_last_attempt)``. Returns ``(False, None)``
    without any HTTP call when no webhook URL is configured.
    """
    webhook_url = (getattr(user_pref, "webhook_url", None) or "").strip()
    if not webhook_url:
        return False, None

    # Read before the loop: add_webhook_delivery() commits between attempts,
    # which would otherwise expire user_pref and force a refresh SELECT.
    user_id = user_pref.user_id

    payload = {
        "document_id": str(document_id),
        "status": status,
        "filename": filename,
        "confidence_score": confidence,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    payload_json = json.dumps(payload)

    status_code: Optional[int] = None
    for attempt in (1, 2):
        success, status_code, response_text, error = _post_once(webhook_url, payload)

        add_webhook_delivery(
            db,
            user_id=user_id,
            document_id=str(document_id),
            webhook_url=webhook_url,
            status_code=status_code,
            payload=payload_json,
            response_text=response_text,
            error=error,
            success=success,
        )

        if success:
            if attempt > 1:
                logger.info(
                    "Webhook delivered for document %s to %s on attempt %d",
                    document_id,
                    webhook_url,
                    attempt,
                )
            return True, status_code

        logger.error(
            "Webhook attempt %d/2 failed for document %s to %s: %s",
            attempt,
            document_id,
            webhook_url,
            error,
        )

        if attempt == 1:
            time.sleep(RETRY_DELAY_SECONDS)

    logger.error(
        "Webhook delivery permanently failed for document %s to %s after 2 attempts "
        "(last status_code=%s). See webhook_deliveries table.",
        document_id,
        webhook_url,
        status_code,
    )
    return False, status_code
