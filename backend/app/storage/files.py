"""Encrypted files on a local volume, behind a small interface (ADR 0002, ADR 0005).

Files are named by a random storage key, never by their original name. A write goes to a
temporary file that is renamed when complete, so a failed upload leaves nothing half-written.
"""

import os
import re
import time
from datetime import timedelta
from pathlib import Path

_KEY = re.compile(r"^[0-9a-f]{32}$")


class LocalStorage:
    def __init__(self, root: Path) -> None:
        self.root = root

    def _path(self, storage_key: str) -> Path:
        if not _KEY.match(storage_key):  # never a path supplied by a user
            raise ValueError("invalid storage key")
        return self.root / storage_key[:2] / storage_key

    def write(self, storage_key: str, data: bytes) -> None:
        path = self._path(storage_key)
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        temporary = path.with_suffix(".part")
        with open(temporary, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        temporary.replace(path)

    def read(self, storage_key: str) -> bytes:
        return self._path(storage_key).read_bytes()

    def delete(self, storage_key: str) -> None:
        self._path(storage_key).unlink(missing_ok=True)

    def exists(self, storage_key: str) -> bool:
        return self._path(storage_key).exists()

    def keys(self, older_than: timedelta = timedelta(0)) -> set[str]:
        """Stored keys whose file is at least `older_than` old (for removing orphans)."""
        if not self.root.exists():
            return set()
        limit = time.time() - older_than.total_seconds()
        return {
            p.name
            for p in self.root.glob("*/*")
            if _KEY.match(p.name) and p.stat().st_mtime <= limit
        }
