from __future__ import annotations

import asyncio
from pathlib import Path


class LocalBlobStorage:
    def __init__(self, root_dir: Path | str, public_base_url: str) -> None:
        self._root = Path(root_dir)
        self._public_base_url = public_base_url.rstrip("/")
        self._root.mkdir(parents=True, exist_ok=True)

    async def put(self, key: str, data: bytes, mime: str) -> str:
        del mime  # not needed on disk; content-type comes from the file extension
        safe_key = key.lstrip("/\\")
        path = self._root / safe_key
        path.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(path.write_bytes, data)
        return f"{self._public_base_url}/{safe_key.replace(chr(92), '/')}"
