import uuid
from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models import Document, User
from app.api.deps import get_current_user
from app.storage.s3 import upload_file
from app.core.exceptions import ValidationException
from app.core.logging import log

router = APIRouter()

ALLOWED_TYPES = ["application/pdf"]
MAX_SIZE_MB   = 50
MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024


@router.post("/")
async def upload_pdf(
    file    : UploadFile = File(...),
    db      : AsyncSession = Depends(get_db),
    user    : User         = Depends(get_current_user),
):
    # ── Validate file type ────────────────────────────────────
    if file.content_type not in ALLOWED_TYPES:
        raise ValidationException("Only PDF files are allowed")

    if not file.filename.endswith(".pdf"):
        raise ValidationException("File must have .pdf extension")

    # ── Read file ─────────────────────────────────────────────
    file_bytes = await file.read()

    # ── Validate file size ────────────────────────────────────
    if len(file_bytes) > MAX_SIZE_BYTES:
        raise ValidationException(f"File too large. Max size is {MAX_SIZE_MB}MB")

    if len(file_bytes) == 0:
        raise ValidationException("File is empty")

    # ── Upload to MinIO ───────────────────────────────────────
    s3_key = f"pdfs/{user.id}/{uuid.uuid4()}.pdf"
    upload_file(file_bytes, s3_key)

    # ── Save to DB ────────────────────────────────────────────
    doc = Document(
        user_id  = user.id,
        filename = file.filename,
        s3_key   = s3_key,
        status   = "pending",
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    
    from app.workers.celery_app import celery_app
    celery_app.send_task("tasks.extract_text", args=[doc.id])

    log.info("pdf_uploaded",
        doc_id   = doc.id,
        user_id  = user.id,
        filename = file.filename,
        size_bytes = len(file_bytes),
    )

    return {
        "doc_id"  : doc.id,
        "filename": doc.filename,
        "status"  : doc.status,
        "message" : "PDF uploaded successfully. Processing will start shortly.",
    }


@router.get("/documents")
async def list_documents(
    db  : AsyncSession = Depends(get_db),
    user: User         = Depends(get_current_user),
):
    """Returns all documents uploaded by the current user"""
    from sqlalchemy import select
    result = await db.execute(
        select(Document)
        .where(Document.user_id == user.id)
        .order_by(Document.created_at.desc())
    )
    docs = result.scalars().all()

    return {
        "documents": [
            {
                "doc_id"    : d.id,
                "filename"  : d.filename,
                "status"    : d.status,
                "created_at": str(d.created_at),
            }
            for d in docs
        ]
    }