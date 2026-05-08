import uuid
from celery import Celery
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from .config import get_settings
from .models import Document, DocumentStatus, Notification
from .ocr import extract_text
from .ai_service import summarize_text, extract_structured_data
from .notifications import send_processing_complete_email

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
        except Exception as exc:
            doc.status = DocumentStatus.failed
            doc.error_message = f"AI processing failed: {str(exc)}"
            db.commit()
            raise self.retry(exc=exc)

        doc.ocr_text = ocr_text
        doc.ai_summary = summary
        doc.extracted_data = extracted
        doc.status = DocumentStatus.completed
        db.commit()

        notif = db.query(Notification).filter(Notification.user_id == doc.user_id).first()
        if notif and notif.email_enabled and notif.email_address:
            try:
                send_processing_complete_email(
                    notif.email_address,
                    doc.original_name,
                    "completed",
                )
            except Exception:
                pass

        return {"status": "completed", "document_id": document_id}

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

        raise
    finally:
        db.close()
