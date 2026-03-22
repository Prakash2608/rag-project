from qdrant_client import QdrantClient
from app.core.config import settings
from app.core.logging import log


def get_qdrant_client() -> QdrantClient:
    return QdrantClient(
        host = settings.QDRANT_HOST,
        port = settings.QDRANT_PORT,
    )


def search_chunks(query_vector: list[float], limit: int = 5) -> list:
    """Search for similar chunks in Qdrant"""
    client  = get_qdrant_client()
    results = client.search(
        collection_name = "documents",
        query_vector    = query_vector,
        limit           = limit,
        with_payload    = True,
    )
    return results