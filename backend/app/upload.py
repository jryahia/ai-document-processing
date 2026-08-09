"""File upload, document listing, detail, search, delete."""
import os
import uuid
from typing import Optional

import magic
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import FileResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete as sa_delete
from sqlalchemy.orm import selectinload

from .database import get_db
from .models import User, Document, DocumentStatus
from .auth import get_current_user
from .schemas import (
    DocumentOut,
    DocumentListOut,
    PaginatedDocuments,
    BatchUploadItem,
    BatchUploadResponse,
)
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


def validate_file(contents: bytes) -> tuple[Optional[str], Optional[str]]:
    """Validate raw upload bytes. Returns (ext, None) on accept, (None, error) on reject."""
    if len(contents) > MAX_FILE_SIZE:
        return None, "File exceeds 20MB limit"

    # Detect MIME type from content
    mime_type = magic.from_buffer(contents, mime=True)
    ext = ALLOWED_MIME_TYPES.get(mime_type)
    if not ext:
        return None, f"Unsupported file type: {mime_type}. Allowed: PDF, PNG, JPG"

    return ext, None


def _store_file(contents: bytes, ext: str, original_name: Optional[str], user_id) -> Document:
    """Write validated bytes to the upload dir and build the (uncommitted) Document row."""
    upload_dir = settings.upload_dir or "uploads"
    os.makedirs(upload_dir, exist_ok=True)

    file_id = str(uuid.uuid4())
    filename = f"{file_id}.{ext}"
    filepath = os.path.join(upload_dir, filename)

    with open(filepath, "wb") as f:
        f.write(contents)

    return Document(
        id=uuid.UUID(file_id),
        user_id=user_id,
        filename=filename,
        original_name=original_name or filename,
        file_size=len(contents),
        file_type=ext,
        status=DocumentStatus.uploaded,
    )


@router.post("/upload", response_model=DocumentOut)
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contents = await file.read()
    ext, error = validate_file(contents)
    if error:
        raise HTTPException(status_code=400, detail=error)

    doc = _store_file(contents, ext, file.filename, current_user.id)
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # Trigger async processing
    process_document.delay(str(doc.id))

    return DocumentOut.model_validate(doc)


@router.post("/upload/batch", response_model=BatchUploadResponse)
async def upload_documents_batch(
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload several files at once. Invalid files are rejected individually;
    valid files are still stored and queued (partial success)."""
    results: list[BatchUploadItem] = []
    queued: list[str] = []

    for file in files:
        name = file.filename or "unnamed"
        contents = await file.read()
        ext, error = validate_file(contents)
        if error:
            results.append(
                BatchUploadItem(filename=name, status="rejected", error=error)
            )
            continue

        doc = _store_file(contents, ext, file.filename, current_user.id)
        db.add(doc)
        queued.append(str(doc.id))
        results.append(
            BatchUploadItem(filename=name, document_id=doc.id, status="accepted")
        )

    if queued:
        await db.commit()
        # Queue only after commit so the worker can see the rows.
        for doc_id in queued:
            process_document.delay(doc_id)

    accepted = sum(1 for r in results if r.status == "accepted")
    return BatchUploadResponse(
        results=results,
        accepted=accepted,
        rejected=len(results) - accepted,
    )


@router.get("", response_model=PaginatedDocuments)
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

    pages = max(1, (total + per_page - 1) // per_page)
    return PaginatedDocuments(
        items=[DocumentListOut.model_validate(d) for d in docs],
        total=total,
        page=page,
        page_size=per_page,
        pages=pages,
    )


@router.get("/search", response_model=PaginatedDocuments)
async def search_documents_endpoint(
    q: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    docs, total = await search_fn(db, current_user.id, q, page, per_page)
    pages = max(1, (total + per_page - 1) // per_page)
    return PaginatedDocuments(
        items=[DocumentListOut.model_validate(d) for d in docs],
        total=total,
        page=page,
        page_size=per_page,
        pages=pages,
    )


@router.get("/{doc_id}", response_model=DocumentOut)
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

    return DocumentOut.model_validate(doc)


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
