from __future__ import annotations

import logging

from app.infrastructure.vectorstore.providers import QdrantVectorStore, VectorStore

logger = logging.getLogger(__name__)


async def build_vector_store(
    *, url: str, api_key: str | None, collection: str, dim: int
) -> VectorStore | None:
    """Build the vector store and ensure its collection. Returns None (logged) if
    Qdrant is unreachable, so the rest of the app runs without semantic memory."""
    store = QdrantVectorStore(url=url, api_key=api_key, collection=collection)
    try:
        await store.ensure_collection(dim)
    except Exception:
        logger.exception(
            "build_vector_store: Qdrant unreachable at %s; semantic memory disabled", url
        )
        return None
    logger.info("Semantic memory enabled (Qdrant %s, collection %s)", url, collection)
    return store
