from __future__ import annotations

import base64

import pytest

from app.infrastructure.security.crypto import CryptoManager
from app.infrastructure.security.session import SessionManager


def make_crypto(key_byte: bytes = b"0") -> CryptoManager:
    raw = base64.urlsafe_b64encode(key_byte * 32).decode("ascii")
    return CryptoManager.from_secret(raw, "v1")


def test_crypto_roundtrip():
    crypto = make_crypto()
    blob = crypto.encrypt_str("refresh-token-secret")
    assert blob.key_id == "v1"
    assert crypto.decrypt_str(blob) == "refresh-token-secret"


def test_crypto_wrong_master_key_fails():
    blob = make_crypto(b"0").encrypt_str("secret")
    with pytest.raises(Exception):
        make_crypto(b"1").decrypt_str(blob)


def test_session_roundtrip():
    manager = SessionManager(secret=b"top-secret", ttl_seconds=3600)
    token = manager.create_session("user-123")
    assert manager.verify_session(token) == "user-123"


def test_session_tampered_token_rejected():
    manager = SessionManager(secret=b"top-secret", ttl_seconds=3600)
    token = manager.create_session("user-123")
    payload, signature = token.split(".", 1)
    assert manager.verify_session(payload + "x." + signature) is None
    assert manager.verify_session("garbage") is None


def test_session_wrong_secret_rejected():
    token = SessionManager(secret=b"a", ttl_seconds=3600).create_session("user-123")
    assert SessionManager(secret=b"b", ttl_seconds=3600).verify_session(token) is None


def test_session_expired_rejected():
    manager = SessionManager(secret=b"top-secret", ttl_seconds=-10)
    token = manager.create_session("user-123")
    assert manager.verify_session(token) is None
