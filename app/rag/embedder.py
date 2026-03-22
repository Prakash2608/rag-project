import ollama
from app.core.config import settings
from app.core.logging import log


def get_embedding(text: str) -> list[float]:
    """Get embedding vector for a text string"""
    result = ollama.embeddings(
        model  = settings.OLLAMA_EMBED_MODEL,
        prompt = text,
    )
    return result["embedding"]