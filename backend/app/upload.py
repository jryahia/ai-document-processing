"""File upload, document listing, detail, search, delete."""
import os
import uuid
import magic
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import FileResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete as sa_delete
from sqlalchemy.orm import selectinload

from .database import get_db
from .models import User, Document, DocumentStatus
from .auth import get_current_user
from .schemas import DocumentResponse, DocumentListResponse, PaginationMeta
from .tasks import process_document
from .config import get_settings
from .search import search_documents as search_fn
from .reports import generate_document_report

router = APIRouter()
settings = get_settings()

ALLOWED_MIME_TYPES = {
    "application/pdf": "pdf",
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
}

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File exceeds 20MB limit")

    # Detect MIME type from content
    mime_type = magic.from_buffer(contents, mime=True)
    ext = ALLOWED_MIME_TYPES.get(mime_type)
    if not ext:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {mime_type}. Allowed: PDF, PNG, JPG",
        )

    upload_dir = settings.upload_dir or "uploads"
    os.makedirs(upload_dir, exist_ok=True)

    file_id = str(uuid.uuid4())
    filename = f"{file_id}.{ext}"
    filepath = os.path.join(upload_dir, filename)

    with open(filepath, "wb") as f:
        f.write(contents)

    doc = Document(
        id=uuid.UUID(file_id),
        user_id=current_user.id,
        filename=filename,
        original_name=file.filename or filename,
        file_size=len(contents),
        file_type=ext,
        status=DocumentStatus.uploaded,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # Trigger async processing
    process_document.delay(str(doc.id))

    return DocumentResponse.from_orm(doc)


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        select(Document)
        .where(Document.user_id == current_user.id, Document.deleted_at.is_(None))
        .order_by(Document.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(query)
    docs = result.scalars().all()

    count_query = select(func.count()).select_from(Document).where(
        Document.user_id == current_user.id, Document.deleted_at.is_(None)
    )
    total = (await db.execute(count_query)).scalar()

    return DocumentListResponse(
        items=[DocumentResponse.from_orm(d) for d in docs],
        pagination=PaginationMeta(page=page, per_page=per_page, total=total),
    )


@router.get("/search", response_model=DocumentListResponse)
async def search_documents_endpoint(
    q: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    docs, total = await search_fn(db, current_user.id, q, page, per_page)
    return DocumentListResponse(
        items=[DocumentResponse.from_orm(d) for d in docs],
        pagination=PaginationMeta(page=page, per_page=per_page, total=total),
    )


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        uid = uuid.UUID(doc_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID")

    result = await db.execute(
        select(Document).where(
            Document.id == uid,
            Document.user_id == current_user.id,
            Document.deleted_at.is_(None),
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentResponse.from_orm(doc)


@router.get("/{doc_id}/download")
async def download_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        uid = uuid.UUID(doc_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID")

    result = await db.execute(
        select(Document).where(
            Document.id == uid,
            Document.user_id == current_user.id,
            Document.deleted_at.is_(None),
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    filepath = os.path.join(settings.upload_dir or "uploads", doc.filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found on disk")

    return FileResponse(
        filepath,
        filename=doc.original_name,
        media_type="application/octet-stream",
    )


@router.get("/{doc_id}/report")
async def get_report(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        uid = uuid.UUID(doc_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID")

    result = await db.execute(
        select(Document).where(
            Document.id == uid,
            Document.user_id == current_user.id,
            Document.deleted_at.is_(None),
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.status.value != "completed":
        raise HTTPException(status_code=400, detail="Document not yet processed")

    pdf_buf = await generate_document_report(doc)
    return Response(
        content=pdf_buf.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{doc.original_name.split(".")[0]}_report.pdf"'},
    )


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        uid = uuid.UUID(doc_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID")

    result = await db.execute(
        select(Document).where(
            Document.id == uid,
            Document.user_id == current_user.id,
            Document.deleted_at.is_(None),
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    from datetime import datetime, timezone
    doc.deleted_at = datetime.now(timezone.utc)
    await db.commit()

    return {"message": "Document deleted", "id": doc_id}
