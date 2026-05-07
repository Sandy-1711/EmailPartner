from __future__ import annotations

from pymongo import IndexModel

from app.infrastructure.db.mongo import MongoDBManager


async def ensure_indexes(db: MongoDBManager) -> None:
    users = db.get_collection("users")
    gmail_accounts = db.get_collection("gmail_accounts")
    emails = db.get_collection("emails")

    await users.create_indexes([IndexModel([("email", 1)], unique=True)])
    await gmail_accounts.create_indexes(
        [
            IndexModel([("gmail_address", 1)], unique=True),
            IndexModel([("user_id", 1)]),
        ]
    )
    await emails.create_indexes(
        [
            IndexModel([("gmail_message_id", 1)], unique=True),
            IndexModel([("user_id", 1), ("created_at", -1)]),
        ]
    )
