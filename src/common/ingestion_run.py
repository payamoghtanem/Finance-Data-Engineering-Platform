"""Ingestion run recorder.

Implements the `ingestion_run` operational table from
docs/technical/data-model.md §4 — the "every run, including failures,
produces a record with status, duration, connector version, and a request
hash" half of FR-ING-001 / FR-OPS-001 (US-02-005).

Recording the row is this module's job. Surfacing it on an operator
dashboard, or alerting on repeated failures, is EPIC-08's job — this module
only makes the data exist for that to read later.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import duckdb

RunStatus = Literal["success", "failed", "partial", "quarantined"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS ingestion_run (
    run_id             VARCHAR PRIMARY KEY,
    dataset_id         VARCHAR NOT NULL,
    connector_version  VARCHAR NOT NULL,
    started_at         TIMESTAMP NOT NULL,
    finished_at        TIMESTAMP NOT NULL,
    status             VARCHAR NOT NULL,
    request_hash       VARCHAR NOT NULL,
    retry_count        INTEGER NOT NULL,
    raw_storage_path   VARCHAR,
    error              VARCHAR
)
"""


def _to_naive_utc(value: datetime) -> datetime:
    """Convert to UTC and drop tzinfo, for storage.

    Same reasoning as src/bronze/writer.py: DuckDB's plain TIMESTAMP column
    is timezone-naive, and TIMESTAMPTZ needs an optional `pytz` dependency
    this project doesn't otherwise use.
    """
    if value.tzinfo is None:
        raise ValueError("Naive datetime given where a timezone-aware one is required")
    return value.astimezone(UTC).replace(tzinfo=None)


def _to_aware_utc(value: datetime) -> datetime:
    """Reattach UTC tzinfo to a naive datetime read back from storage."""
    return value.replace(tzinfo=UTC)


@dataclass(frozen=True)
class IngestionRun:
    """One `ingestion_run` row. `status` is one of `RunStatus`'s values."""

    run_id: str
    dataset_id: str
    connector_version: str
    started_at: datetime
    finished_at: datetime
    status: str
    request_hash: str
    retry_count: int
    raw_storage_path: str | None
    error: str | None

    @property
    def duration_seconds(self) -> float:
        return (self.finished_at - self.started_at).total_seconds()


class IngestionRunRecorder:
    """Records one row per ingestion attempt, success or failure.

    Args:
        db_path: Path to the DuckDB file. `:memory:` is valid for tests.
            Phase 1 storage note: `ingestion_run` is operational metadata, and
            the eventual production home for it is likely PostgreSQL
            (`PlatformConfig.database` already exists for this) once multiple
            connectors write concurrently. DuckDB is used here for the same
            reason it was chosen for Bronze (docs/technical/
            technical-design-document.md §2a): zero extra infrastructure,
            already the Phase 1 query engine, trivially testable without a
            live service. Revisit when EPIC-07/08 need concurrent writers.
    """

    def __init__(self, db_path: str | Path = "ops_store/ingestion_runs.duckdb") -> None:
        self.db_path = str(db_path)
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn: Any = duckdb.connect(self.db_path)
        self._conn.execute(_SCHEMA)

    def close(self) -> None:
        self._conn.close()

    def record(
        self,
        *,
        dataset_id: str,
        connector_version: str,
        started_at: datetime,
        finished_at: datetime,
        status: RunStatus,
        request_hash: str,
        retry_count: int,
        raw_storage_path: str | None = None,
        error: str | None = None,
    ) -> IngestionRun:
        """Record one completed attempt (success or failure — never skipped).

        A fresh `run_id` every call, always: unlike Bronze/Raw, this is not
        content-addressed — every execution is its own audit-log entry, even
        one that (because the data layer is idempotent) writes nothing new.
        """
        run_id = str(uuid.uuid4())
        self._conn.execute(
            "INSERT INTO ingestion_run VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                run_id,
                dataset_id,
                connector_version,
                _to_naive_utc(started_at),
                _to_naive_utc(finished_at),
                status,
                request_hash,
                retry_count,
                raw_storage_path,
                error,
            ],
        )
        return IngestionRun(
            run_id=run_id,
            dataset_id=dataset_id,
            connector_version=connector_version,
            started_at=started_at,
            finished_at=finished_at,
            status=status,
            request_hash=request_hash,
            retry_count=retry_count,
            raw_storage_path=raw_storage_path,
            error=error,
        )

    def get(self, run_id: str) -> IngestionRun | None:
        row = self._conn.execute(
            "SELECT run_id, dataset_id, connector_version, started_at, finished_at, "
            "status, request_hash, retry_count, raw_storage_path, error "
            "FROM ingestion_run WHERE run_id = ?",
            [run_id],
        ).fetchone()
        return self._row_to_run(row) if row is not None else None

    def list_for_dataset(self, dataset_id: str) -> list[IngestionRun]:
        """All runs for a dataset, oldest first — e.g. for the FR-OPS-002
        '≥2 consecutive failures' alerting rule once EPIC-08 consumes this."""
        rows = self._conn.execute(
            "SELECT run_id, dataset_id, connector_version, started_at, finished_at, "
            "status, request_hash, retry_count, raw_storage_path, error "
            "FROM ingestion_run WHERE dataset_id = ? ORDER BY started_at",
            [dataset_id],
        ).fetchall()
        return [self._row_to_run(row) for row in rows]

    @staticmethod
    def _row_to_run(row: Any) -> IngestionRun:
        return IngestionRun(
            run_id=row[0],
            dataset_id=row[1],
            connector_version=row[2],
            started_at=_to_aware_utc(row[3]),
            finished_at=_to_aware_utc(row[4]),
            status=row[5],
            request_hash=row[6],
            retry_count=row[7],
            raw_storage_path=row[8],
            error=row[9],
        )
