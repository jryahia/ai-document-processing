"""Email notifications and notification preferences."""
import asyncio
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import get_settings
from .database import get_db
from .models import User, Notification
from .auth import get_current_user

settings = get_settings()
router = APIRouter()


async def send_email(to_address: str, subject: str, body_html: str) -> None:
    if not settings.smtp_user or not settings.smtp_password:
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = to_address
    msg.attach(MIMEText(body_html, "html"))

    await aiosmtplib.send(
        msg,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_user,
        password=settings.smtp_password,
        start_tls=True,
    )


def send_processing_complete_email(to_address: str, document_name: str, status: str) -> None:
    status_color = "#22c55e" if status == "completed" else "#ef4444"
    status_label = "Successfully Processed" if status == "completed" else "Processing Failed"
    body = f"""
    <html><body style="font-family: sans-serif; background: #0f172a; color: #e2e8f0; padding: 32px;">
      <div style="max-width: 560px; margin: 0 auto; background: #1e293b; border-radius: 12px; padding: 32px;">
        <h1 style="color: #7c3aed; margin-top: 0;">DocProcess AI</h1>
        <p>Your document <strong>{document_name}</strong> has been processed.</p>
        <div style="background: #0f172a; border-radius: 8px; padding: 16px; margin: 16px 0;">
          <span style="color: {status_color}; font-weight: bold; font-size: 18px;">
            ● {status_label}
          </span>
        </div>
        <p style="color: #94a3b8; font-size: 14px;">
          Log in to your dashboard to view the extracted data and AI summary.
        </p>
      </div>
    </body></html>
    """
    try:
        loop = asyncio.new_event_loop()
        loop.run_until_complete(send_email(to_address, f"Document Processed: {document_name}", body))
        loop.close()
    except Exception:
        pass


@router.get("")
async def get_notifications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Notification).where(Notification.user_id == current_user.id)
    )
    notif = result.scalar_one_or_none()
    if not notif:
        return {"email_enabled": False, "email_address": "", "webhook_url": ""}
    return {
        "email_enabled": notif.email_enabled,
        "email_address": notif.email_address or "",
        "webhook_url": notif.webhook_url or "",
    }


@router.put("")
async def update_notifications(
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    email_enabled = data.get("email_enabled", False)
    email_address = data.get("email_address", "")

    result = await db.execute(
        select(Notification).where(Notification.user_id == current_user.id)
    )
    notif = result.scalar_one_or_none()

    # Absent key leaves the stored value alone; an explicit empty string clears it.
    webhook_url = data.get("webhook_url", notif.webhook_url if notif else "")
    webhook_url = (webhook_url or "").strip()
    if webhook_url:
        if len(webhook_url) > 512:
            raise HTTPException(status_code=400, detail="webhook_url must be 512 characters or fewer")
        if not webhook_url.startswith(("http://", "https://")):
            raise HTTPException(status_code=400, detail="webhook_url must start with http:// or https://")

    if not notif:
        notif = Notification(
            user_id=current_user.id,
            email_enabled=email_enabled,
            email_address=email_address,
            webhook_url=webhook_url or None,
        )
        db.add(notif)
    else:
        notif.email_enabled = email_enabled
        notif.email_address = email_address
        notif.webhook_url = webhook_url or None

    await db.commit()
    return {
        "email_enabled": email_enabled,
        "email_address": email_address,
        "webhook_url": webhook_url,
    }
