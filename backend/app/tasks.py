import logging
import uuid
from celery import Celery
from celery.exceptions import Retry
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from .config import get_settings
from .models import Document, DocumentStatus, Notification
from .ocr import extract_text
from .ai_service import summarize_text, extract_structured_data, compute_confidence_score
from .notifications import send_processing_complete_email
from .webhooks import deliver_webhook

logger = logging.getLogger(__name__)

settings = get_settings()

celery_app = Celery(
    "tasks",
    broker=settings.redis_url,
    backend=settings.redis_url,
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

sync_engine = create_engine(settings.sync_database_url, pool_pre_ping=True)
SyncSession = sessionmaker(bind=sync_engine)


def get_sync_db() -> Session:
    return SyncSession()


def _fire_webhook(db: Session, notif, document_id: str, status: str, filename: str, confidence) -> None:
    """Best-effort webhook delivery. Never raises — document state wins."""
    if not notif or not notif.webhook_url:
        return
    try:
        deliver_webhook(
            db,
            notif,
            document_id=document_id,
            status=status,
            filename=filename,
            confidence=confidence,
        )
    except Exception as exc:
        logger.error(
            "Unexpected error delivering webhook for document %s: %s",
            document_id,
            exc,
            exc_info=True,
        )


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def process_document(self, document_id: str) -> dict:
    db = get_sync_db()
    try:
        doc = db.query(Document).filter(Document.id == uuid.UUID(document_id)).first()
        if not doc:
            return {"error": "Document not found"}

        doc.status = DocumentStatus.processing
        db.commit()

        file_path = f"{settings.upload_dir}/{doc.filename}"

        try:
            ocr_text = extract_text(file_path, doc.file_type)
        except Exception as exc:
            doc.status = DocumentStatus.failed
            doc.error_message = f"OCR failed: {str(exc)}"
            db.commit()
            raise self.retry(exc=exc)

        try:
            summary = summarize_text(ocr_text)
            extracted = extract_structured_data(ocr_text)
            confidence = compute_confidence_score(extracted)
        except Exception as exc:
            doc.status = DocumentStatus.failed
            doc.error_message = f"AI processing failed: {str(exc)}"
            db.commit()
            raise self.retry(exc=exc)

        doc.ocr_text = ocr_text
        doc.ai_summary = summary
        doc.extracted_data = extracted
        doc.confidence_score = confidence

        if confidence is not None and confidence < settings.confidence_threshold:
            doc.status = DocumentStatus.needs_review
            doc.needs_review = True
        else:
            doc.status = DocumentStatus.completed
            doc.needs_review = False
        final_status = doc.status.value
        db.commit()

        notif = db.query(Notification).filter(Notification.user_id == doc.user_id).first()
        if notif and notif.email_enabled and notif.email_address:
            try:
                send_processing_complete_email(
                    notif.email_address,
                    doc.original_name,
                    final_status,
                )
            except Exception:
                pass

        _fire_webhook(db, notif, document_id, final_status, doc.original_name, confidence)

        return {
            "status": final_status,
            "document_id": document_id,
            "confidence_score": confidence,
        }

    except Exception as exc:
        db.rollback()
        doc = db.query(Document).filter(Document.id == uuid.UUID(document_id)).first()
        if doc and doc.status != DocumentStatus.failed:
            doc.status = DocumentStatus.failed
            doc.error_message = str(exc)
            db.commit()

        notif = db.query(Notification).filter(Notification.user_id == doc.user_id).first() if doc else None
        if notif and notif.email_enabled and notif.email_address:
            try:
                send_processing_complete_email(
                    notif.email_address,
                    doc.original_name if doc else "Unknown",
                    "failed",
                )
            except Exception:
                pass

        # A Retry is not a completion — Celery will run this task again, so
        # firing the webhook here would POST once per attempt. Only the final
        # attempt (which re-raises the original exception) notifies.
        if not isinstance(exc, Retry):
            _fire_webhook(
                db,
                notif,
                document_id,
                "failed",
                doc.original_name if doc else "Unknown",
                doc.confidence_score if doc else None,
            )

        raise
    finally:
        db.close()
