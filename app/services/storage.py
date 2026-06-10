from __future__ import annotations

from datetime import datetime

from bson import ObjectId

from app.infrastructure.db.main import DBManager
from app.models.db.crypto import EncryptedBlob
from app.models.db.emails import Emails, EmailProcessingStatus
from app.models.db.gmail_account import GmailAccount
from app.models.db.user import Users
from app.models.db.utils import utc_now


class UserStore:
    def __init__(self, db_manager: DBManager) -> None:
        self._db = db_manager.document_db

    async def get_by_id(self, user_id: ObjectId) -> Users | None:
        return await self._db.find_one(Users, {"_id": user_id})

    async def get_by_email(self, email: str) -> Users | None:
        return await self._db.find_one(Users, {"email": email})

    async def get_by_google_sub(self, google_sub: str) -> Users | None:
        return await self._db.find_one(Users, {"google_sub": google_sub})

    async def create(self, user: Users) -> ObjectId:
        return await self._db.insert_one(Users, user)

    async def update_google_identity(
        self,
        user_id: ObjectId,
        *,
        google_sub: str,
        display_name: str | None = None,
        picture_url: str | None = None,
    ) -> None:
        update: dict[str, object] = {
            "google_sub": google_sub,
            "updated_at": utc_now(),
        }
        if display_name is not None:
            update["display_name"] = display_name
        if picture_url is not None:
            update["picture_url"] = picture_url
        await self._db.update_one(Users, {"_id": user_id}, {"$set": update})

    async def mark_deleted(self, user_id: ObjectId) -> bool:
        updated = await self._db.update_one(
            Users,
            {"_id": user_id},
            {"$set": {"status": "deleted", "updated_at": utc_now()}},
        )
        return updated > 0


class GmailAccountStore:
    def __init__(self, db_manager: DBManager) -> None:
        self._db = db_manager.document_db

    async def get_by_email(self, gmail_address: str) -> GmailAccount | None:
        return await self._db.find_one(GmailAccount, {"gmail_address": gmail_address})

    async def get_by_user_id(self, user_id: ObjectId) -> GmailAccount | None:
        return await self._db.find_one(GmailAccount, {"user_id": user_id})

    async def create(self, account: GmailAccount) -> ObjectId:
        return await self._db.insert_one(GmailAccount, account)

    async def update_tokens(
        self,
        account_id: ObjectId,
        access_token: EncryptedBlob | None,
        access_expires_at: datetime | None,
        refresh_token: EncryptedBlob | None = None,
    ) -> None:
        update: dict[str, object] = {"updated_at": utc_now()}
        if access_token is not None:
            update["access_token"] = access_token.model_dump(by_alias=True)
        if refresh_token is not None:
            update["refresh_token"] = refresh_token.model_dump(by_alias=True)
        if access_expires_at is not None:
            update["access_token_expires_at"] = access_expires_at
        await self._db.update_one(
            GmailAccount,
            {"_id": account_id},
            {"$set": update},
        )

    async def find_expiring(self, before: datetime, limit: int = 100) -> list[GmailAccount]:
        return await self._db.find_many(
            GmailAccount,
            {
                "status": "active",
                "watch_expiration": {"$lt": before},
            },
            limit=limit,
        )

    async def update_watch(
        self,
        account_id: ObjectId,
        history_id: str | None,
        watch_expiration: datetime | None,
    ) -> None:
        update = {"updated_at": utc_now()}
        if history_id is not None:
            update["history_id"] = history_id
        if watch_expiration is not None:
            update["watch_expiration"] = watch_expiration
        await self._db.update_one(
            GmailAccount,
            {"_id": account_id},
            {"$set": update},
        )


class EmailStore:
    def __init__(self, db_manager: DBManager) -> None:
        self._db = db_manager.document_db

    async def get_by_id(self, email_id: ObjectId) -> Emails | None:
        return await self._db.find_one(Emails, {"_id": email_id})

    async def update_card_fields(
        self,
        email_id: ObjectId,
        *,
        processing_status: EmailProcessingStatus | None = None,
        card_text: str | None = None,
        card_background_url: str | None = None,
        card_audio_url: str | None = None,
        last_error: str | None = None,
    ) -> None:
        update: dict[str, object] = {"updated_at": utc_now()}
        if processing_status is not None:
            update["processing_status"] = processing_status.value
        if card_text is not None:
            update["card_text"] = card_text
        if card_background_url is not None:
            update["card_background_url"] = card_background_url
        if card_audio_url is not None:
            update["card_audio_url"] = card_audio_url
        if last_error is not None:
            update["last_error"] = last_error
        await self._db.update_one(
            Emails,
            {"_id": email_id},
            {"$set": update},
        )

    async def upsert_email(self, email: Emails) -> tuple[ObjectId, bool]:
        """Insert or refresh an email row. Returns (id, is_new).

        Existing rows only get their message-content fields refreshed; card
        fields and queue state are left untouched so duplicate Pub/Sub
        notifications don't reset finished cards.
        """
        existing = await self._db.find_one(
            Emails, {"gmail_message_id": email.gmail_message_id}
        )
        if existing is None:
            payload = email.model_dump(by_alias=True, exclude_none=True)
            payload["updated_at"] = utc_now()
            payload["created_at"] = email.created_at
            inserted_id = await self._db.insert_one(
                Emails, Emails.model_validate(payload)
            )
            oid = ObjectId(inserted_id) if not isinstance(inserted_id, ObjectId) else inserted_id
            return oid, True

        content_fields = (
            "thread_id", "subject", "from_email", "snippet", "body", "received_at"
        )
        payload = email.model_dump(include=set(content_fields), exclude_none=True)
        payload["updated_at"] = utc_now()
        await self._db.update_one(
            Emails,
            {"_id": existing.id},
            {"$set": payload},
        )
        return existing.id, False

    async def list_by_user(
        self, user_id: ObjectId, limit: int, offset: int
    ) -> list[Emails]:
        return await self._db.find_many(
            Emails,
            {"user_id": user_id},
            limit=limit,
            skip=offset,
            sort=[("received_at", -1), ("created_at", -1)],
        )

    async def claim_next_pending(self) -> Emails | None:
        """Atomically claim the oldest pending email for processing."""
        now = utc_now()
        return await self._db.find_one_and_update(
            Emails,
            {"processing_status": EmailProcessingStatus.PENDING.value},
            {
                "$set": {
                    "processing_status": EmailProcessingStatus.PROCESSING.value,
                    "claimed_at": now,
                    "updated_at": now,
                },
                "$inc": {"attempts": 1},
            },
            sort=[("created_at", 1)],
        )

    async def requeue(self, email_id: ObjectId) -> None:
        await self._db.update_one(
            Emails,
            {"_id": email_id},
            {
                "$set": {
                    "processing_status": EmailProcessingStatus.PENDING.value,
                    "claimed_at": None,
                    "last_error": None,
                    "updated_at": utc_now(),
                }
            },
        )

    async def reset_stale_processing(self, claimed_before: datetime) -> int:
        """Requeue emails stuck in PROCESSING past their lease (e.g. after a crash)."""
        reset = 0
        while True:
            stale = await self._db.find_one_and_update(
                Emails,
                {
                    "processing_status": EmailProcessingStatus.PROCESSING.value,
                    "$or": [
                        {"claimed_at": {"$lt": claimed_before}},
                        {"claimed_at": None},
                    ],
                },
                {
                    "$set": {
                        "processing_status": EmailProcessingStatus.PENDING.value,
                        "claimed_at": None,
                        "updated_at": utc_now(),
                    }
                },
            )
            if stale is None:
                return reset
            reset += 1
