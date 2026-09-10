"""Raw (Bronze-input) object storage.

Implements the immutable-raw-data requirement of FR-ING-001 and architecture
principle 2 in docs/architecture/ARD.md: the *original* bytes returned by a
source are persisted, untouched, before anything parses them.

Storage is content-addressed: the object key contains the SHA-256 of the exact
payload bytes. Writing the same payload twice therefore resolves to the same
key and is a no-op, which is what makes the raw layer idempotent (FR-ING-001).

Phase 1 uses a local filesystem backend. The MinIO/S3 backend lands in EPIC-03
behind the same `RawStorage` protocol, so no caller changes when it arrives.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Protocol


class RawStorageError(Exception):
    """Raised when a raw payload cannot be persisted."""


def compute_sha256(payload: bytes) -> str:
    """Return the hex SHA-256 of the exact bytes given."""
    return hashlib.sha256(payload).hexdigest()


def build_object_key(source: str, dataset: str, retrieved_at: datetime, sha256: str) -> str:
    """Build the content-addressed key for a raw payload.

    The date partition makes retention and listing practical; the hash suffix is
    what makes the write idempotent.
    """
    date_part = retrieved_at.strftime("%Y-%m-%d")
    return f"raw/{source}/{dataset}/date={date_part}/{sha256}.json"


class RawStorage(Protocol):
    """Write-once storage for original source payloads."""

    def put(self, key: str, payload: bytes) -> str:
        """Persist `payload` at `key` and return the key actually written.

        Implementations MUST be write-once: if `key` already exists with the
        same content the call is a no-op. They MUST NOT modify the payload.
        """
        ...

    def exists(self, key: str) -> bool:
        """Return True if `key` is already stored."""
        ...

    def get(self, key: str) -> bytes:
        """Return the exact bytes previously stored at `key`."""
        ...


class LocalRawStorage:
    """Filesystem-backed `RawStorage` for the Phase 1 local MVP.

    Not a stub: it really writes, and a caller can read back the identical
    bytes. That is what lets provenance (NFR-AUDIT-001) actually hold in Phase 1.
    """

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def _path(self, key: str) -> Path:
        return self.root / key

    def put(self, key: str, payload: bytes) -> str:
        path = self._path(key)
        if path.exists():
            # Content-addressed: identical key means identical bytes. Re-running
            # the same ingestion is a no-op rather than a duplicate write.
            return key
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            # Write to a temp file then rename, so a crash cannot leave a
            # half-written object that looks complete.
            tmp = path.with_suffix(path.suffix + ".partial")
            tmp.write_bytes(payload)
            tmp.replace(path)
        except OSError as exc:
            raise RawStorageError(f"Could not write raw payload to {path}: {exc}") from exc
        return key

    def exists(self, key: str) -> bool:
        return self._path(key).exists()

    def get(self, key: str) -> bytes:
        try:
            return self._path(key).read_bytes()
        except OSError as exc:
            raise RawStorageError(f"Could not read raw payload at {key}: {exc}") from exc
