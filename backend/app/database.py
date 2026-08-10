from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from .config import get_settings

settings = get_settings()

engine_kwargs: dict = {"echo": False, "pool_pre_ping": True}
if settings.database_url.startswith("sqlite"):
    # SQLite (aiosqlite) uses NullPool — pool sizing kwargs are invalid.
    pass
else:
    engine_kwargs.update(pool_size=10, max_overflow=20)

engine = create_async_engine(settings.database_url, **engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
