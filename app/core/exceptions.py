import structlog
from fastapi import Request
from fastapi.responses import JSONResponse

log = structlog.get_logger()


# ── Custom Exception Classes ──────────────────────────────────

class RAGException(Exception):
    """Base exception for all RAG errors"""
    def __init__(self, message: str, status_code: int = 500):
        self.message     = message
        self.status_code = status_code
        super().__init__(message)


class AuthException(RAGException):
    """Wrong credentials, expired token, not logged in"""
    def __init__(self, message: str = "Not authenticated"):
        super().__init__(message, status_code=401)


class PermissionException(RAGException):
    """Logged in but not allowed to do this"""
    def __init__(self, message: str = "Permission denied"):
        super().__init__(message, status_code=403)


class NotFoundException(RAGException):
    """Document, user, or resource not found"""
    def __init__(self, message: str = "Not found"):
        super().__init__(message, status_code=404)


class ValidationException(RAGException):
    """Bad input from user"""
    def __init__(self, message: str = "Validation error"):
        super().__init__(message, status_code=422)


class LLMException(RAGException):
    """Groq / Ollama / OpenAI call failed"""
    def __init__(self, message: str = "LLM call failed"):
        super().__init__(message, status_code=502)


class StorageException(RAGException):
    """S3 / MinIO upload or download failed"""
    def __init__(self, message: str = "Storage error"):
        super().__init__(message, status_code=502)


# ── FastAPI Global Handlers ───────────────────────────────────

async def rag_exception_handler(request: Request, exc: RAGException):
    log.error(
        "rag_exception",
        path=str(request.url),
        method=request.method,
        status_code=exc.status_code,
        error=exc.message,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )


async def unhandled_exception_handler(request: Request, exc: Exception):
    log.error(
        "unhandled_exception",
        path=str(request.url),
        method=request.method,
        error=str(exc),
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )