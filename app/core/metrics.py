import time
import structlog
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime, timezone

logger = structlog.get_logger(__name__)


# ── Data Classes ──────────────────────────────────────────────────────────────

@dataclass
class QueryMetrics:
    """Metrics captured for a single RAG query."""
    question: str
    user_id: Optional[int] = None

    # Timing
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None

    # Cache
    exact_cache_hit: bool = False
    semantic_cache_hit: bool = False
    semantic_similarity_score: Optional[float] = None

    # Retrieval
    chunks_retrieved: int = 0
    retrieval_score_avg: Optional[float] = None

    # LLM
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None

    # Result
    success: bool = False
    error: Optional[str] = None

    @property
    def total_tokens(self) -> Optional[int]:
        if self.prompt_tokens is not None and self.completion_tokens is not None:
            return self.prompt_tokens + self.completion_tokens
        return None

    @property
    def response_time_ms(self) -> Optional[float]:
        if self.end_time is not None:
            return round((self.end_time - self.start_time) * 1000, 2)
        return None

    @property
    def cache_hit(self) -> bool:
        return self.exact_cache_hit or self.semantic_cache_hit

    def finish(self, success: bool = True, error: Optional[str] = None):
        """Mark the query as complete."""
        self.end_time = time.time()
        self.success = success
        self.error = error


@dataclass
class DocumentMetrics:
    """Metrics captured during document ingestion."""
    document_id: int
    filename: str

    # Timing
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None

    # Processing
    total_chunks: int = 0
    embedded_chunks: int = 0
    failed_chunks: int = 0
    file_size_bytes: Optional[int] = None

    # Result
    success: bool = False
    error: Optional[str] = None

    @property
    def response_time_ms(self) -> Optional[float]:
        if self.end_time is not None:
            return round((self.end_time - self.start_time) * 1000, 2)
        return None

    @property
    def embedding_success_rate(self) -> Optional[float]:
        if self.total_chunks > 0:
            return round(self.embedded_chunks / self.total_chunks * 100, 2)
        return None

    def finish(self, success: bool = True, error: Optional[str] = None):
        """Mark ingestion as complete."""
        self.end_time = time.time()
        self.success = success
        self.error = error


# ── Metrics Logger ────────────────────────────────────────────────────────────

class MetricsLogger:
    """
    Logs metrics to structlog and optionally persists to the
    llm_traces table in PostgreSQL via the db session.
    """

    def log_query(self, metrics: QueryMetrics) -> None:
        """Log query metrics to structlog."""
        log_data = {
            "event": "query_metrics",
            "question_length": len(metrics.question),
            "user_id": metrics.user_id,
            "response_time_ms": metrics.response_time_ms,
            "cache_hit": metrics.cache_hit,
            "exact_cache_hit": metrics.exact_cache_hit,
            "semantic_cache_hit": metrics.semantic_cache_hit,
            "semantic_similarity": metrics.semantic_similarity_score,
            "chunks_retrieved": metrics.chunks_retrieved,
            "llm_provider": metrics.llm_provider,
            "llm_model": metrics.llm_model,
            "prompt_tokens": metrics.prompt_tokens,
            "completion_tokens": metrics.completion_tokens,
            "total_tokens": metrics.total_tokens,
            "success": metrics.success,
            "error": metrics.error,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if metrics.success:
            logger.info("query completed", **log_data)
        else:
            logger.error("query failed", **log_data)

    def log_document(self, metrics: DocumentMetrics) -> None:
        """Log document ingestion metrics to structlog."""
        log_data = {
            "event": "document_metrics",
            "document_id": metrics.document_id,
            "filename": metrics.filename,
            "file_size_bytes": metrics.file_size_bytes,
            "response_time_ms": metrics.response_time_ms,
            "total_chunks": metrics.total_chunks,
            "embedded_chunks": metrics.embedded_chunks,
            "failed_chunks": metrics.failed_chunks,
            "embedding_success_rate": metrics.embedding_success_rate,
            "success": metrics.success,
            "error": metrics.error,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if metrics.success:
            logger.info("document ingested", **log_data)
        else:
            logger.error("document ingestion failed", **log_data)


# ── Singleton ─────────────────────────────────────────────────────────────────

metrics_logger = MetricsLogger()


# ── Usage Example ─────────────────────────────────────────────────────────────
#
# In your RAG query handler:
#
#   from app.core.metrics import QueryMetrics, metrics_logger
#
#   m = QueryMetrics(question=question, user_id=user.id)
#   try:
#       m.exact_cache_hit = cache_result is not None
#       m.chunks_retrieved = len(chunks)
#       m.llm_provider = "groq"
#       m.prompt_tokens = token_usage.prompt_tokens
#       m.completion_tokens = token_usage.completion_tokens
#       m.finish(success=True)
#   except Exception as e:
#       m.finish(success=False, error=str(e))
#       raise
#   finally:
#       metrics_logger.log_query(m)
#
# In your Celery document processor:
#
#   from app.core.metrics import DocumentMetrics, metrics_logger
#
#   m = DocumentMetrics(document_id=doc_id, filename=filename)
#   try:
#       m.total_chunks = len(chunks)
#       m.embedded_chunks = successful_embeds
#       m.file_size_bytes = file_size
#       m.finish(success=True)
#   except Exception as e:
#       m.finish(success=False, error=str(e))
#       raise
#   finally:
#       metrics_logger.log_document(m)