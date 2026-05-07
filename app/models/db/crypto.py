from __future__ import annotations

from typing import Literal

from app.config import ConfigModels


class EncryptedBlob(ConfigModels.EmailPartnerDBConfig):
    alg: Literal["AESGCM"] = "AESGCM"
    key_id: str
    nonce: str
    ciphertext: str
    key_nonce: str
    key_ciphertext: str
    version: int = 1
