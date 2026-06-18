from __future__ import annotations

import pytest
from bson import ObjectId

from app.services.storage import DeviceTokenStore

pytestmark = pytest.mark.anyio


async def test_register_then_list(db_manager):
    store = DeviceTokenStore(db_manager)
    user = ObjectId()

    await store.register(user, "tok-a", "android")
    await store.register(user, "tok-b", "android")

    assert sorted(await store.list_tokens(user)) == ["tok-a", "tok-b"]


async def test_register_same_token_is_idempotent_and_rebinds_owner(db_manager):
    store = DeviceTokenStore(db_manager)
    user1, user2 = ObjectId(), ObjectId()

    await store.register(user1, "tok", "android")
    await store.register(user2, "tok", "android")  # device re-signed-in as user2

    assert await store.list_tokens(user1) == []
    assert await store.list_tokens(user2) == ["tok"]


async def test_delete_removes_token(db_manager):
    store = DeviceTokenStore(db_manager)
    user = ObjectId()
    await store.register(user, "tok", "android")

    await store.delete("tok")

    assert await store.list_tokens(user) == []
