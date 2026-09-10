"""Raw (Bronze-input) object storage.

Implements the immutable-raw-data requirement of FR-ING-001 and architecture
principle 2 in docs/architecture/ARD.md: the *original* bytes returned by a
source are persisted, untouched, before anything parses them.

Storage is content-addressed: the object key contains the SHA-256 of the exact
payload bytes. Writing the same payload twice therefore resolves to the same
key and is a no-op, which is what makes the raw layer idempotent (FR-ING-001).

Two `RawStorage` implementations exist behind the same protocol, so a caller
never changes when swapping one for the other:

- `LocalRawStorage` — filesystem-backed, used where a bucket isn't available.
- `S3RawStorage` — the MinIO/S3 backend (EPIC-03, US-03-001), the one the
  Phase 1 `docker-compose.yml` `minio` service is actually for.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

import boto3
from botocore.exceptions import ClientError


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


class S3RawStorage:
    """S3/MinIO-backed `RawStorage` — the Phase 1 production backend.

    Content-addressed the same way as `LocalRawStorage`: `put` checks for the
    object's existence before writing, so storing an already-present key is a
    no-op rather than a duplicate write (the idempotency half of FR-ING-001).

    The `boto3` client is injected so tests run against a mocked S3 (moto),
    never a live network call, per docs/engineering/test-strategy.md §2.
    """

    def __init__(
        self,
        bucket: str,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        client: Any | None = None,
    ) -> None:
        self.bucket = bucket
        self._client: Any = client or boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )

    def ensure_bucket(self) -> None:
        """Create the bucket if it does not already exist. Safe to call every startup."""
        try:
            self._client.head_bucket(Bucket=self.bucket)
        except ClientError:
            self._client.create_bucket(Bucket=self.bucket)

    def put(self, key: str, payload: bytes) -> str:
        if self.exists(key):
            # Content-addressed: identical key means identical bytes already stored.
            return key
        try:
            self._client.put_object(Bucket=self.bucket, Key=key, Body=payload)
        except ClientError as exc:
            raise RawStorageError(
                f"Could not write raw payload to s3://{self.bucket}/{key}: {exc}"
            ) from exc
        return key

    def exists(self, key: str) -> bool:
        try:
            self._client.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "")
            if error_code in ("404", "NoSuchKey", "NotFound"):
                return False
            raise RawStorageError(f"Could not check s3://{self.bucket}/{key}: {exc}") from exc

    def get(self, key: str) -> bytes:
        try:
            response = self._client.get_object(Bucket=self.bucket, Key=key)
            return bytes(response["Body"].read())
        except ClientError as exc:
            raise RawStorageError(
                f"Could not read raw payload at s3://{self.bucket}/{key}: {exc}"
            ) from exc

    @classmethod
    def from_config(cls, minio_config: Any) -> S3RawStorage:
        """Build from a `MinIOConfig` (src/common/config.py)."""
        return cls(
            bucket=minio_config.raw_bucket,
            endpoint_url=minio_config.endpoint,
            access_key=minio_config.access_key,
            secret_key=minio_config.secret_key,
        )
