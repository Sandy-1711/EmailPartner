from __future__ import annotations

import base64
import os
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.models.db.crypto import EncryptedBlob


@dataclass(frozen=True)
class CryptoManager:
    master_key: bytes
    key_id: str

    @staticmethod
    def _decode_key(raw: str) -> bytes:
        key = base64.urlsafe_b64decode(raw)
        if len(key) != 32:
            raise ValueError("ENCRYPTION_MASTER_KEY must be 32 bytes after base64 decoding")
        return key

    @classmethod
    def from_secret(cls, raw_key: str, key_id: str) -> CryptoManager:
        return cls(master_key=cls._decode_key(raw_key), key_id=key_id)

    def encrypt_str(self, value: str) -> EncryptedBlob:
        data_key = os.urandom(32)
        data_nonce = os.urandom(12)
        key_nonce = os.urandom(12)

        data_ciphertext = AESGCM(data_key).encrypt(data_nonce, value.encode("utf-8"), None)
        key_ciphertext = AESGCM(self.master_key).encrypt(key_nonce, data_key, None)

        return EncryptedBlob(
            key_id=self.key_id,
            nonce=base64.urlsafe_b64encode(data_nonce).decode("ascii"),
            ciphertext=base64.urlsafe_b64encode(data_ciphertext).decode("ascii"),
            key_nonce=base64.urlsafe_b64encode(key_nonce).decode("ascii"),
            key_ciphertext=base64.urlsafe_b64encode(key_ciphertext).decode("ascii"),
        )

    def decrypt_str(self, blob: EncryptedBlob) -> str:
        data_nonce = base64.urlsafe_b64decode(blob.nonce)
        data_ciphertext = base64.urlsafe_b64decode(blob.ciphertext)
        key_nonce = base64.urlsafe_b64decode(blob.key_nonce)
        key_ciphertext = base64.urlsafe_b64decode(blob.key_ciphertext)

        data_key = AESGCM(self.master_key).decrypt(key_nonce, key_ciphertext, None)
        plaintext = AESGCM(data_key).decrypt(data_nonce, data_ciphertext, None)
        return plaintext.decode("utf-8")
