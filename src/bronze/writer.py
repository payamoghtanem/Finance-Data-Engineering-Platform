"""Bronze writer.

Loads a payload already persisted by a `RawStorage` implementation into the
Bronze layer, carrying full lineage back to that raw object. See
docs/technical/technical-design-document.md §2a for the storage shape and the
rationale for keeping Bronze source-shaped rather than typed/canonical.

This module reads only from `RawStorage.get()` — it never performs network
I/O, so a full Bronze rebuild can run with the network disabled (US-03-003,
ARD principle 2).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb

from src.common.raw_storage import RawStorage, RawStorageError


class BronzeWriteError(Exception):
    """Raised when a raw object cannot be loaded into Bronze."""


def _bronze_id(raw_object_key: str) -> str:
    """Deterministic id for a raw object key.

    Reloading the same raw object always yields the same `bronze_id`, which is
    what makes `BronzeWriter.write` idempotent rather than a duplicate insert.
    """
    return hashlib.sha256(raw_object_key.encode("utf-8")).hexdigest()


def _to_naive_utc(value: datetime) -> datetime:
    """Convert to UTC and drop tzinfo, for storage.

    DuckDB's plain TIMESTAMP column is timezone-naive; TIMESTAMPTZ requires an
    optional `pytz` dependency this project doesn't otherwise need. Converting
    explicitly at the storage boundary (here and in `_to_aware_utc`) keeps
    every value unambiguously UTC without adding that dependency.
    """
    if value.tzinfo is None:
        raise ValueError("Naive datetime given where a timezone-aware one is required")
    return value.astimezone(UTC).replace(tzinfo=None)


def _to_aware_utc(value: datetime) -> datetime:
    """Reattach UTC tzinfo to a naive datetime read back from storage."""
    return value.replace(tzinfo=UTC)


@dataclass(frozen=True)
class BronzeRecord:
    """One Bronze row: a raw object plus its lineage."""

    bronze_id: str
    source_id: str
    dataset_id: str
    raw_object_key: str
    raw_sha256: str
    retrieved_at: datetime
    code_version: str
    ingested_at: datetime
    payload: bytes


_SCHEMA = """
CREATE TABLE IF NOT EXISTS bronze_raw_records (
    bronze_id      VARCHAR PRIMARY KEY,
    source_id      VARCHAR NOT NULL,
    dataset_id     VARCHAR NOT NULL,
    raw_object_key VARCHAR NOT NULL,
    raw_sha256     VARCHAR NOT NULL,
    retrieved_at   TIMESTAMP NOT NULL,
    code_version   VARCHAR NOT NULL,
    ingested_at    TIMESTAMP NOT NULL,
    payload        BLOB NOT NULL
)
"""


class BronzeWriter:
    """Loads raw objects into the Bronze table, with lineage.

    Args:
        raw_storage: Where the original payloads live. Never fetched from the
            network — only ever read via `raw_storage.get()`.
        db_path: Path to the DuckDB file backing Bronze in Phase 1. `:memory:`
            is a valid value for tests.
    """

    def __init__(
        self, raw_storage: RawStorage, db_path: str | Path = "bronze_store/bronze.duckdb"
    ) -> None:
        self.raw_storage = raw_storage
        self.db_path = str(db_path)
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn: Any = duckdb.connect(self.db_path)
        self._conn.execute(_SCHEMA)

    def close(self) -> None:
        self._conn.close()

    def write(
        self,
        *,
        source_id: str,
        dataset_id: str,
        raw_object_key: str,
        raw_sha256: str,
        retrieved_at: datetime,
        code_version: str,
    ) -> BronzeRecord:
        """Load one raw object into Bronze.

        Idempotent: writing the same `raw_object_key` twice returns the
        existing row rather than inserting a duplicate (US-03-002's lineage
        guarantee only holds if there is exactly one Bronze row per raw
        object).
        """
        bronze_id = _bronze_id(raw_object_key)

        existing = self._get(bronze_id)
        if existing is not None:
            return existing

        try:
            payload = self.raw_storage.get(raw_object_key)
        except RawStorageError as exc:
            raise BronzeWriteError(f"Could not read raw object {raw_object_key}: {exc}") from exc

        actual_sha256 = hashlib.sha256(payload).hexdigest()
        if actual_sha256 != raw_sha256:
            # The bytes we just read don't match the checksum we were told to
            # expect. Silently loading corrupted data would poison every
            # downstream layer's provenance (NFR-AUDIT-001) — fail loudly instead.
            raise BronzeWriteError(
                f"Checksum mismatch for {raw_object_key}: expected {raw_sha256}, got {actual_sha256}"
            )

        ingested_at = datetime.now(UTC)
        self._conn.execute(
            "INSERT INTO bronze_raw_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                bronze_id,
                source_id,
                dataset_id,
                raw_object_key,
                actual_sha256,
                _to_naive_utc(retrieved_at),
                code_version,
                _to_naive_utc(ingested_at),
                payload,
            ],
        )

        return BronzeRecord(
            bronze_id=bronze_id,
            source_id=source_id,
            dataset_id=dataset_id,
            raw_object_key=raw_object_key,
            raw_sha256=actual_sha256,
            retrieved_at=retrieved_at,
            code_version=code_version,
            ingested_at=ingested_at,
            payload=payload,
        )

    def _get(self, bronze_id: str) -> BronzeRecord | None:
        row = self._conn.execute(
            "SELECT bronze_id, source_id, dataset_id, raw_object_key, raw_sha256, "
            "retrieved_at, code_version, ingested_at, payload "
            "FROM bronze_raw_records WHERE bronze_id = ?",
            [bronze_id],
        ).fetchone()
        if row is None:
            return None
        return BronzeRecord(
            bronze_id=row[0],
            source_id=row[1],
            dataset_id=row[2],
            raw_object_key=row[3],
            raw_sha256=row[4],
            retrieved_at=_to_aware_utc(row[5]),
            code_version=row[6],
            ingested_at=_to_aware_utc(row[7]),
            payload=bytes(row[8]),
        )

    def get_by_raw_object_key(self, raw_object_key: str) -> BronzeRecord | None:
        """Look up the Bronze row for a raw object, for lineage verification."""
        return self._get(_bronze_id(raw_object_key))
