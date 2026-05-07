from __future__ import annotations

from datetime import datetime

from bson import ObjectId

from app.infrastructure.db.main import DBManager
from app.models.db.crypto import EncryptedBlob
from app.models.db.emails import Emails
from app.models.db.gmail_account import GmailAccount
from app.models.db.user import Users
from app.models.db.utils import utc_now


class UserStore:
    def __init__(self, db_manager: DBManager) -> None:
        self._db = db_manager.document_db

    async def get_by_id(self, user_id: ObjectId | str) -> Users | None:
        if isinstance(user_id, ObjectId):
            object_id = user_id
        else:
            try:
                object_id = ObjectId(user_id)
            except Exception:
                return None
        return await self._db.find_one(Users, {"_id": object_id})

    async def get_by_email(self, email: str) -> Users | None:
        return await self._db.find_one(Users, {"email": email})

    async def create(self, user: Users) -> ObjectId:
        return await self._db.insert_one(Users, user)

    async def mark_deleted(self, user_id: ObjectId | str) -> bool:
        object_id = user_id if isinstance(user_id, ObjectId) else ObjectId(user_id)
        updated = await self._db.update_one(
            Users,
            {"_id": object_id},
            {"$set": {"status": "deleted", "updated_at": utc_now()}},
        )
        return updated > 0


class GmailAccountStore:
    def __init__(self, db_manager: DBManager) -> None:
        self._db = db_manager.document_db

    async def get_by_email(self, gmail_address: str) -> GmailAccount | None:
        return await self._db.find_one(GmailAccount, {"gmail_address": gmail_address})

    async def get_by_user_id(self, user_id: ObjectId | str) -> GmailAccount | None:
        object_id = user_id if isinstance(user_id, ObjectId) else ObjectId(user_id)
        return await self._db.find_one(GmailAccount, {"user_id": object_id})

    async def create(self, account: GmailAccount) -> ObjectId:
        return await self._db.insert_one(GmailAccount, account)

    async def update_tokens(
        self,
        account_id: ObjectId | str,
        access_token: EncryptedBlob | None,
        access_expires_at: datetime | None,
        refresh_token: EncryptedBlob | None = None,
    ) -> None:
        object_id = account_id if isinstance(account_id, ObjectId) else ObjectId(account_id)
        update: dict[str, object] = {"updated_at": utc_now()}
        if access_token is not None:
            update["access_token"] = access_token
        if refresh_token is not None:
            update["refresh_token"] = refresh_token
        if access_expires_at is not None:
            update["access_token_expires_at"] = access_expires_at
        await self._db.update_one(
            GmailAccount,
            {"_id": object_id},
            {"$set": update},
        )

    async def update_watch(
        self,
        account_id: ObjectId | str,
        history_id: str | None,
        watch_expiration: datetime | None,
    ) -> None:
        object_id = account_id if isinstance(account_id, ObjectId) else ObjectId(account_id)
        update = {"updated_at": utc_now()}
        if history_id is not None:
            update["history_id"] = history_id
        if watch_expiration is not None:
            update["watch_expiration"] = watch_expiration
        await self._db.update_one(
            GmailAccount,
            {"_id": object_id},
            {"$set": update},
        )


class EmailStore:
    def __init__(self, db_manager: DBManager) -> None:
        self._db = db_manager.document_db

    async def upsert_email(self, email: Emails) -> str:
        existing = await self._db.find_one(
            Emails, {"gmail_message_id": email.gmail_message_id}
        )
        payload = email.model_dump(by_alias=True, exclude_none=True)
        payload["updated_at"] = utc_now()
        if existing is None:
            payload["created_at"] = email.created_at
            inserted_id = await self._db.insert_one(
                Emails, Emails.model_validate(payload)
            )
            return str(inserted_id)

        await self._db.update_one(
            Emails,
            {"_id": existing.id},
            {"$set": payload},
        )
        return str(existing.id)

    async def list_by_user(
        self, user_id: ObjectId | str, limit: int, offset: int
    ) -> list[Emails]:
        object_id = user_id if isinstance(user_id, ObjectId) else ObjectId(user_id)
        return await self._db.find_many(
            Emails,
            {"user_id": object_id},
            limit=limit,
            skip=offset,
        )
