"""FastAPI application entry point."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import engine, Base
from .auth import router as auth_router
from .upload import router as upload_router
from .notifications import router as notifications_router
from .llm_settings import router as llm_settings_router
from .config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="AI Document Processing",
    version="1.0.0",
    lifespan=lifespan,
)

# Explicit, configurable allowed origins (never "*" with credentials).
cors_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# auth_router already declares prefix="/api/auth" — don't double it.
app.include_router(auth_router, tags=["auth"])
app.include_router(upload_router, prefix="/api/documents", tags=["documents"])
app.include_router(notifications_router, prefix="/api/notifications", tags=["notifications"])
app.include_router(llm_settings_router, tags=["llm-settings"])


@app.get("/api/health")
async def health():
    return {"status": "healthy", "service": "ai-document-processing"}
