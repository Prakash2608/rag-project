import io
from app.workers.celery_app import celery_app
from app.core.logging import log


# ── Task 1: Extract text from PDF ────────────────────────────

@celery_app.task(
    bind       = True,
    max_retries= 3,
    name       = "tasks.extract_text",
)
def extract_text(self, doc_id: str):
    """Downloads PDF from MinIO and extracts raw text"""
    try:
        log.info("extract_started", doc_id=doc_id)

        # import here to avoid circular imports
        from app.storage.s3 import download_file
        from app.db.models import Document

        # update status to extracting
        _update_doc_status(doc_id, "extracting")

        # download PDF from MinIO
        s3_key     = _get_doc_s3_key(doc_id)
        file_bytes = download_file(s3_key)

        # extract text using pdfplumber
        import pdfplumber
        text = ""
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"

        if not text.strip():
            raise ValueError("No text could be extracted from PDF")

        log.info("extract_done",
            doc_id    = doc_id,
            chars     = len(text),
            pages     = len(pdfplumber.open(io.BytesIO(file_bytes)).pages),
        )

        # update status and chain to next task
        _update_doc_status(doc_id, "extracted")

        # pass to next task
        chunk_text.delay(doc_id, text)

    except Exception as exc:
        log.error("extract_failed", doc_id=doc_id, error=str(exc))
        _update_doc_status(doc_id, "failed")
        raise self.retry(exc=exc, countdown=60)


# ── Task 2: Chunk the text ────────────────────────────────────

@celery_app.task(
    bind        = True,
    max_retries = 3,
    name        = "tasks.chunk_text",
)
def chunk_text(self, doc_id: str, text: str):
    try:
        log.info("chunk_started", doc_id=doc_id, text_length=len(text))

        from langchain_text_splitters import RecursiveCharacterTextSplitter

        splitter = RecursiveCharacterTextSplitter(
            chunk_size    = 1500,  # was 512 — bigger = more complete context
            chunk_overlap = 200,   # was 64  — more overlap = no lost context
            separators    = ["\n\n", "\n", ". ", " ", ""],
        )

        chunks = splitter.split_text(text)

        if not chunks:
            raise ValueError("No chunks produced from text")

        log.info("chunk_done",
            doc_id         = doc_id,
            num_chunks     = len(chunks),
            avg_chunk_size = sum(len(c) for c in chunks) // len(chunks),
        )

        _update_doc_status(doc_id, "chunked")
        embed_chunks.delay(doc_id, chunks)

    except Exception as exc:
        log.error("chunk_failed", doc_id=doc_id, error=str(exc))
        _update_doc_status(doc_id, "failed")
        raise self.retry(exc=exc, countdown=60)


# ── Task 3: Embed chunks and store in Qdrant ─────────────────

@celery_app.task(
    bind       = True,
    max_retries= 3,
    name       = "tasks.embed_chunks",
)
def embed_chunks(self, doc_id: str, chunks: list[str]):
    """Embeds each chunk and stores vectors in Qdrant"""
    try:
        log.info("embed_started", doc_id=doc_id, num_chunks=len(chunks))

        import ollama
        from qdrant_client import QdrantClient
        from qdrant_client.models import PointStruct, VectorParams, Distance
        from app.core.config import settings

        qdrant = QdrantClient(
            host = settings.QDRANT_HOST,
            port = settings.QDRANT_PORT,
        )

        collection_name = "documents"

        # create collection if not exists
        existing = [c.name for c in qdrant.get_collections().collections]
        if collection_name not in existing:
            # get embedding dimension first
            sample = ollama.embeddings(
                model  = settings.OLLAMA_EMBED_MODEL,
                prompt = "test",
            )
            dim = len(sample["embedding"])

            qdrant.create_collection(
                collection_name = collection_name,
                vectors_config  = VectorParams(
                    size     = dim,
                    distance = Distance.COSINE,
                ),
            )
            log.info("qdrant_collection_created",
                collection = collection_name,
                dimensions = dim,
            )

        # embed each chunk and store
        points = []
        for i, chunk in enumerate(chunks):
            result    = ollama.embeddings(
                model  = settings.OLLAMA_EMBED_MODEL,
                prompt = chunk,
            )
            vector = result["embedding"]

            points.append(PointStruct(
                id      = abs(hash(f"{doc_id}_{i}")) % (2**63),
                vector  = vector,
                payload = {
                    "doc_id" : doc_id,
                    "chunk"  : chunk,
                    "index"  : i,
                },
            ))

        # upsert all points
        qdrant.upsert(
            collection_name = collection_name,
            points          = points,
        )

        log.info("embed_done",
            doc_id     = doc_id,
            num_vectors= len(points),
        )

        _update_doc_status(doc_id, "ready")

    except Exception as exc:
        log.error("embed_failed", doc_id=doc_id, error=str(exc))
        _update_doc_status(doc_id, "failed")
        raise self.retry(exc=exc, countdown=60)


# ── Helper functions ──────────────────────────────────────────

def _get_doc_s3_key(doc_id: str) -> str:
    """Gets s3_key for a document from DB synchronously"""
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session
    from app.db.models import Document
    from app.core.config import settings

    # use sync engine for celery workers
    sync_url = settings.DATABASE_URL.replace(
        "postgresql+asyncpg", "postgresql+psycopg2"
    )
    engine = create_engine(sync_url)
    with Session(engine) as session:
        result = session.execute(
            select(Document).where(Document.id == doc_id)
        )
        doc = result.scalar_one_or_none()
        if not doc:
            raise ValueError(f"Document {doc_id} not found")
        return doc.s3_key


def _update_doc_status(doc_id: str, status: str):
    """Updates document status in DB synchronously"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app.db.models import Document
    from app.core.config import settings

    sync_url = settings.DATABASE_URL.replace(
        "postgresql+asyncpg", "postgresql+psycopg2"
    )
    engine = create_engine(sync_url)
    with Session(engine) as session:
        doc = session.get(Document, doc_id)
        if doc:
            doc.status = status
            session.commit()
            log.info("doc_status_updated", doc_id=doc_id, status=status)