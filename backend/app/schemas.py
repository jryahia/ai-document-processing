from datetime import datetime
from typing import Any, Literal, Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field
from .models import DocumentStatus


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str = Field(min_length=1, max_length=255)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: UUID
    email: str
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class DocumentOut(BaseModel):
    id: UUID
    filename: str
    original_name: str
    file_size: int
    file_type: str
    status: DocumentStatus
    ocr_text: Optional[str] = None
    ai_summary: Optional[str] = None
    extracted_data: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentListOut(BaseModel):
    id: UUID
    original_name: str
    file_size: int
    file_type: str
    status: DocumentStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaginatedDocuments(BaseModel):
    items: list[DocumentListOut]
    total: int
    page: int
    page_size: int
    pages: int


class BatchUploadItem(BaseModel):
    """Per-file outcome of a batch upload. `document_id`/`error` are mutually exclusive."""
    filename: str
    document_id: Optional[UUID] = None
    status: Literal["accepted", "rejected"]
    error: Optional[str] = None


class BatchUploadResponse(BaseModel):
    results: list[BatchUploadItem]
    accepted: int
    rejected: int


class NotificationSettings(BaseModel):
    email_enabled: bool
    email_address: Optional[EmailStr] = None


class NotificationOut(BaseModel):
    email_enabled: bool
    email_address: Optional[str] = None

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None


class SearchResult(BaseModel):
    items: list[DocumentListOut]
    total: int
    query: str


class DashboardStats(BaseModel):
    total: int
    completed: int
    processing: int
    failed: int
    uploaded: int
    recent: list[DocumentListOut]
