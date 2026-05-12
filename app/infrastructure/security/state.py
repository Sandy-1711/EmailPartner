from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class OAuthStateManager:
    secret: bytes
    ttl_seconds: int

    def create_state(self, payload: dict[str, Any] | None = None) -> str:
        full_payload: dict[str, Any] = dict(payload or {})
        full_payload.setdefault("nonce", secrets.token_urlsafe(16))
        full_payload["iat"] = int(time.time())
        payload_bytes = json.dumps(full_payload, separators=(",", ":")).encode("utf-8")
        payload_b64 = base64.urlsafe_b64encode(payload_bytes).decode("ascii").rstrip("=")
        signature = hmac.new(self.secret, payload_b64.encode("ascii"), hashlib.sha256).digest()
        signature_b64 = base64.urlsafe_b64encode(signature).decode("ascii").rstrip("=")
        return f"{payload_b64}.{signature_b64}"

    def verify_state_payload(self, state: str) -> dict[str, Any] | None:
        try:
            payload_b64, signature_b64 = state.split(".", 1)
        except ValueError:
            return None

        expected_sig = hmac.new(
            self.secret, payload_b64.encode("ascii"), hashlib.sha256
        ).digest()
        expected_b64 = base64.urlsafe_b64encode(expected_sig).decode("ascii").rstrip("=")
        if not hmac.compare_digest(signature_b64, expected_b64):
            return None

        try:
            payload_json = base64.urlsafe_b64decode(_pad_base64(payload_b64))
            payload = json.loads(payload_json)
        except (ValueError, json.JSONDecodeError):
            return None

        issued_at = int(payload.get("iat", 0))
        if issued_at <= 0 or (issued_at + self.ttl_seconds) < int(time.time()):
            return None

        return payload


def _pad_base64(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return f"{value}{padding}".encode("ascii")
