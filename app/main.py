import sentry_sdk
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.exceptions import (
    RAGException,
    rag_exception_handler,
    unhandled_exception_handler,
)
from app.api.routes import auth, upload, query, admin
from app.storage.s3 import ensure_bucket_exists

setup_logging()

if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.APP_ENV,
    )

# ── Lifespan — replaces @app.on_event ────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # runs on startup
    ensure_bucket_exists()
    yield
    # runs on shutdown (add cleanup here if needed)

# ── App ───────────────────────────────────────────────────────
app = FastAPI(
    title    = "RAG API",
    version  = "1.0.0",
    docs_url = "/docs",
    redoc_url= "/redoc",
    lifespan = lifespan,      # ← pass lifespan here
)

# ── CORS ──────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Exception handlers ────────────────────────────────────────
app.add_exception_handler(RAGException, rag_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

# ── Routers ───────────────────────────────────────────────────
app.include_router(auth.router,   prefix="/auth",   tags=["auth"])
app.include_router(upload.router, prefix="/upload", tags=["upload"])
app.include_router(query.router,  prefix="/query",  tags=["query"])
app.include_router(admin.router,  prefix="/admin",  tags=["admin"])

# ── Health check ──────────────────────────────────────────────
@app.get("/health")
async def health():
    return {
        "status" : "ok",
        "env"    : settings.APP_ENV,
        "version": "1.0.0",
    }