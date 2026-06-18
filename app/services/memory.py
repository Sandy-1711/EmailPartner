from __future__ import annotations

import logging

from bson import ObjectId

from app.infrastructure.db.main import DBManager
from app.infrastructure.embeddings.providers import EmbeddingProvider
from app.infrastructure.vectorstore.providers import VectorRecord, VectorStore
from app.models.db.emails import Emails
from app.services.storage import EmailStore

logger = logging.getLogger(__name__)

_MAX_DOC_CHARS = 8000


class EmailMemory:
    """Semantic memory over the user's emails: embed on ingest, retrieve by
    meaning. The vector store holds one point per email (payload filtered by
    user); the email bodies stay in Mongo and are joined back on search."""

    def __init__(
        self,
        db_manager: DBManager,
        embedder: EmbeddingProvider,
        vector_store: VectorStore,
    ) -> None:
        self._emails = EmailStore(db_manager)
        self._embedder = embedder
        self._vector_store = vector_store

    @staticmethod
    def _document(email: Emails) -> str:
        parts = [email.subject, email.from_email, email.body or email.snippet]
        return "\n".join(p for p in parts if p)[:_MAX_DOC_CHARS]

    async def index(self, email: Emails, *, tone: str | None = None) -> None:
        text = self._document(email)
        if not text.strip():
            return
        [vector] = await self._embedder.embed([text])
        payload = {
            "user_id": str(email.user_id),
            "sender": email.from_email,
            "subject": email.subject,
            "tone": tone or email.card_tone,
            "received_at": email.received_at.isoformat() if email.received_at else None,
        }
        await self._vector_store.upsert(
            [VectorRecord(id=str(email.id), vector=vector, payload=payload)]
        )

    async def search(self, user_id: ObjectId, query: str, limit: int = 10) -> list[Emails]:
        [vector] = await self._embedder.embed([query])
        hits = await self._vector_store.search(vector, user_id=str(user_id), limit=limit)
        results: list[Emails] = []
        for hit in hits:
            try:
                email = await self._emails.get_by_id(ObjectId(hit.id))
            except Exception:
                continue
            if email is not None:
                results.append(email)
        return results
