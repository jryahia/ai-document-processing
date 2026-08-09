import enum
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, BigInteger, Boolean, DateTime,
    ForeignKey, Enum as SAEnum, Text, func
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
import uuid
from .database import Base


class DocumentStatus(str, enum.Enum):
    uploaded = "uploaded"
    processing = "processing"
    completed = "completed"
    failed = "failed"
    needs_review = "needs_review"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    documents = relationship("Document", back_populates="user", lazy="select")
    notification = relationship("Notification", back_populates="user", uselist=False, lazy="select")


class Document(Base):
    """
    MIGRATION NOTE (no alembic in this project — main.py's lifespan calls
    ``Base.metadata.create_all``, which only creates *missing* tables and never
    alters existing ones). A fresh database picks up the columns below
    automatically; an existing PostgreSQL deployment must be updated by hand
    before deploying this version, or the worker will fail on commit:

        ALTER TABLE documents ADD COLUMN confidence_score INTEGER;
        ALTER TABLE documents ADD COLUMN needs_review BOOLEAN NOT NULL DEFAULT FALSE;
        ALTER TYPE documentstatus ADD VALUE 'needs_review';

    The third statement is required as well: ``SAEnum(DocumentStatus)`` maps to a
    native PostgreSQL enum type named ``documentstatus``, and create_all will not
    add the new member to it.
    """

    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(512), nullable=False)
    original_name = Column(String(512), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    file_type = Column(String(64), nullable=False)
    status = Column(SAEnum(DocumentStatus), nullable=False, default=DocumentStatus.uploaded)
    ocr_text = Column(Text, nullable=True)
    ai_summary = Column(Text, nullable=True)
    extracted_data = Column(JSONB, nullable=True)
    confidence_score = Column(Integer, nullable=True)
    needs_review = Column(Boolean, nullable=False, default=False, server_default="false")
    error_message = Column(Text, nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="documents")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    email_enabled = Column(Boolean, nullable=False, default=False)
    email_address = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="notification")
