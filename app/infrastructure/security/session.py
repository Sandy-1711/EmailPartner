from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class SessionManager:
    secret: bytes
    ttl_seconds: int

    def create_session(self, user_id: str) -> str:
        payload = {"sub": user_id, "iat": int(time.time())}
        payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        payload_b64 = base64.urlsafe_b64encode(payload_bytes).decode("ascii").rstrip("=")
        signature = hmac.new(self.secret, payload_b64.encode("ascii"), hashlib.sha256).digest()
        signature_b64 = base64.urlsafe_b64encode(signature).decode("ascii").rstrip("=")
        return f"{payload_b64}.{signature_b64}"

    def verify_session(self, token: str) -> str | None:
        try:
            payload_b64, signature_b64 = token.split(".", 1)
        except ValueError:
            return None

        expected = hmac.new(
            self.secret, payload_b64.encode("ascii"), hashlib.sha256
        ).digest()
        expected_b64 = base64.urlsafe_b64encode(expected).decode("ascii").rstrip("=")
        if not hmac.compare_digest(signature_b64, expected_b64):
            return None

        try:
            padded = payload_b64 + "=" * (-len(payload_b64) % 4)
            payload = json.loads(base64.urlsafe_b64decode(padded))
        except (ValueError, json.JSONDecodeError):
            return None

        issued_at = int(payload.get("iat", 0))
        if issued_at <= 0 or (issued_at + self.ttl_seconds) < int(time.time()):
            return None

        sub = str(payload.get("sub", ""))
        return sub or None
