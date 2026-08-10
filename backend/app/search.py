"""PostgreSQL full-text search for documents (falls back to ILIKE on non-PG)."""
from uuid import UUID

from sqlalchemy import select, func, or_, exc as sa_exc
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Document


async def search_documents(
    db: AsyncSession,
    user_id: UUID,
    query: str,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[Document], int]:
    like_pattern = f"%{query}%"
    ilike_filter = or_(
        Document.ocr_text.ilike(like_pattern),
        Document.ai_summary.ilike(like_pattern),
        Document.original_name.ilike(like_pattern),
    )

    # Try PostgreSQL full-text search first (unsupported on SQLite — falls back below)
    try:
        ts_query = func.plainto_tsquery("english", query)
        ts_vector = func.to_tsvector("english", Document.ocr_text + " " + func.coalesce(Document.ai_summary, ""))

        count_query = (
            select(func.count())
            .select_from(Document)
            .where(
                Document.user_id == user_id,
                Document.deleted_at.is_(None),
                ts_vector.op("@@")(ts_query),
            )
        )
        total = (await db.execute(count_query)).scalar() or 0

        if total > 0:
            query = (
                select(Document)
                .where(
                    Document.user_id == user_id,
                    Document.deleted_at.is_(None),
                    ts_vector.op("@@")(ts_query),
                )
                .order_by(func.ts_rank(ts_vector, ts_query).desc())
                .offset((page - 1) * per_page)
                .limit(per_page)
            )
            result = await db.execute(query)
            return list(result.scalars().all()), total
    except sa_exc.SQLAlchemyError:
        # Full-text search unavailable (e.g. SQLite) — use ILIKE fallback.
        pass

    # Fallback to ILIKE
    query = (
        select(Document)
        .where(
            Document.user_id == user_id,
            Document.deleted_at.is_(None),
            ilike_filter,
        )
        .order_by(Document.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    count_query = (
        select(func.count())
        .select_from(Document)
        .where(
            Document.user_id == user_id,
            Document.deleted_at.is_(None),
            ilike_filter,
        )
    )
    total = (await db.execute(count_query)).scalar() or 0

    result = await db.execute(query)
    docs = list(result.scalars().all())
    return docs, total
