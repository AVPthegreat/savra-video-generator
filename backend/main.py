"""FastAPI entrypoint for Savra Video Generator v1.5 Production API."""

from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from backend.auth.router import router as auth_router
from backend.api.v1.user_router import router as user_router
from backend.api.v1.admin_router import router as admin_router
from backend.core.config import get_settings
from backend.db.database import create_all_tables, SessionLocal
from backend.db import crud

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Modern lifespan handler replacing deprecated on_event."""
    settings = get_settings()
    # Database initialization is now handled exclusively by Alembic migrations.
    logger.info("Application lifespan started.")

    # Ensure the admin user always exists (idempotent seed)
    try:
        from scripts.seed_admin import seed_admin
        seed_admin()
    except Exception as e:
        logger.warning("seed_admin failed (non-fatal): %s", e)

    if settings.recover_stale_jobs_on_startup:
        db = SessionLocal()
        try:
            crud.recover_incomplete_jobs(
                db,
                reason="Job lost due to service restart/crash",
            )
        finally:
            db.close()
    yield

app = FastAPI(
    title="Savra Video Generator Production API", 
    version="1.5.0", 
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

_settings = get_settings()

# Allowed origins for CORS
_allowed_origins = [
    origin.strip() for origin in _settings.allowed_origins.split(",") if origin.strip()
]

# When allow_credentials=True, 'allow_origins' cannot be ["*"].
# We must explicitly list the development and production origins.
if "*" in _allowed_origins or not _allowed_origins:
    _allowed_origins = [
        "http://localhost:5173", 
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

logger.info(f"CORS Allowed Origins: {_allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True, # Required for HttpOnly Cookies
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Attach a unique request ID for distributed tracing."""
    request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex[:16])
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

# ── ROUTERS (API v1) ─────────────────────────────────────────────────────────
app.include_router(auth_router, prefix="/api/v1")
app.include_router(user_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")


@app.get("/healthz")
def healthz():
    return {"status": "ok", "version": "1.5.0"}


def _renderer_root() -> Path:
    return Path(__file__).resolve().parent.parent / "renderer"


@app.get("/api/artifacts/{path:path}")
async def serve_artifacts(path: str):
    """Serve artifacts from local disk (dev) or redirect to GCS (prod)."""
    settings = get_settings()
    if settings.app_env.lower() == "production" and settings.gcs_bucket_name:
        return RedirectResponse(f"https://storage.googleapis.com/{settings.gcs_bucket_name}/{path.lstrip('/')}")
    
    local_path = _renderer_root() / "public" / path
    if local_path.exists() and local_path.is_file():
        return FileResponse(local_path)
    
    raise HTTPException(status_code=404, detail="Artifact not found")

# Mount local artifacts for middleware if needed
if (_renderer_root() / "public").exists():
    app.mount("/local-artifacts", StaticFiles(directory=str(_renderer_root() / "public")), name="local-artifacts")

# Optional: Serve a minimal landing page if the backend is visited directly
index_path = Path(__file__).resolve().parent / "static" / "index.html"
if index_path.exists():
    @app.get("/", response_class=FileResponse)
    async def root():
        return FileResponse(index_path)
