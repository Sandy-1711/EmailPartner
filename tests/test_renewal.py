from __future__ import annotations

import httpx
import pytest
from bson import ObjectId

from app.infrastructure.google.oauth import is_invalid_grant
from app.infrastructure.security.crypto import CryptoManager
from app.models.db.gmail_account import GmailAccount, GmailAccountStatus
from app.models.db.utils import utc_now
from app.services.storage import GmailAccountStore
from app.services.watch.renewal import WatchRenewalService

pytestmark = pytest.mark.anyio


def _http_error(status: int, body: dict | None = None) -> httpx.HTTPStatusError:
    req = httpx.Request("POST", "https://oauth2.googleapis.com/token")
    resp = httpx.Response(status, json=body or {}, request=req)
    return httpx.HTTPStatusError("boom", request=req, response=resp)


def test_is_invalid_grant_only_matches_revoked_grant():
    assert is_invalid_grant(_http_error(400, {"error": "invalid_grant"})) is True
    assert is_invalid_grant(_http_error(400, {"error": "invalid_scope"})) is False
    assert is_invalid_grant(_http_error(500)) is False
    assert is_invalid_grant(RuntimeError("nope")) is False


async def test_renew_disables_account_on_invalid_grant(db_manager, app_settings):
    crypto = CryptoManager.from_secret(
        app_settings.encryption_master_key.get_secret_value(),
        app_settings.encryption_key_id,
    )
    account = GmailAccount(
        user_id=ObjectId(),
        gmail_address="revoked@example.com",
        refresh_token=crypto.encrypt_str("stale-refresh"),
        watch_expiration=utc_now(),  # within the renewal threshold -> picked up
    )
    await db_manager.document_db.insert_one(GmailAccount, account)

    # the token endpoint rejects the refresh: access was revoked
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": "invalid_grant"}, request=request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    service = WatchRenewalService(db_manager, client, crypto, app_settings)

    renewed = await service.renew_expiring()
    await client.aclose()

    assert renewed == 0
    refreshed = await GmailAccountStore(db_manager).get_by_email("revoked@example.com")
    assert refreshed is not None
    assert refreshed.status == GmailAccountStatus.DISABLED
