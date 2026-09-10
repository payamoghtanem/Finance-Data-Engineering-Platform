"""Dead-letter queue (DLQ) recorder.

Implements the `dlq` operational table from docs/technical/data-model.md §4 —
FR-OPS-003's "any failed or quarantined run must be replayable from the DLQ
without manual data surgery." This module only makes a dead-lettered event
durable and queryable; wiring it to `EventBus` (both a subscriber handler
raising, and a `raw_data.quarantined` event itself) and replaying an entry
back onto the bus is `src/events/dlq.py`'s job, not this one's — same
layering as `ingestion_run.py` (recording) vs. the alerting/asset-check
modules that read it.

Note on table format: `docs/technical/technical-design-document.md` §7
originally described this as an "Iceberg table." That was never true of its
two sibling operational tables (`ingestion_run`, `data_quality_result`, both
plain DuckDB tables per data-model.md §4) and ADR-0003's Iceberg choice is
explicitly scoped to Bronze/Silver/Gold tables only — corrected in the same
change that built this module.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import duckdb

DLQStatus = Literal["pending", "replayed"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS dlq (
    event_id           VARCHAR PRIMARY KEY,
    event_type         VARCHAR NOT NULL,
    producer           VARCHAR NOT NULL,
    dataset_id         VARCHAR NOT NULL,
    correlation_id     VARCHAR,
    payload_reference  VARCHAR,
    metadata           VARCHAR,
    failure_reason     VARCHAR NOT NULL,
    quarantined_at     TIMESTAMP NOT NULL,
    status             VARCHAR NOT NULL,
    replayed_at        TIMESTAMP
)
"""


def _to_naive_utc(value: datetime) -> datetime:
    """Same reasoning as ingestion_run.py / data_quality_result.py: DuckDB's
    plain TIMESTAMP column is timezone-naive, and TIMESTAMPTZ needs an
    optional `pytz` dependency this project doesn't otherwise use.
    """
    if value.tzinfo is None:
        raise ValueError("Naive datetime given where a timezone-aware one is required")
    return value.astimezone(UTC).replace(tzinfo=None)


def _to_aware_utc(value: datetime | None) -> datetime | None:
    """Reattach UTC tzinfo to a naive datetime read back from storage."""
    return None if value is None else value.replace(tzinfo=UTC)


@dataclass(frozen=True)
class DLQEntry:
    """One `dlq` row: a dead-lettered event plus why it landed here."""

    event_id: str
    event_type: str
    producer: str
    dataset_id: str
    correlation_id: str | None
    payload_reference: str | None
    metadata: dict[str, Any]
    failure_reason: str
    quarantined_at: datetime
    status: str
    replayed_at: datetime | None


class DLQRecorder:
    """Records dead-lettered events and tracks their replay state.

    Args:
        db_path: Path to the DuckDB file. `:memory:` is valid for tests.
            Same Phase-1 storage reasoning as `IngestionRunRecorder` /
            `DataQualityResultRecorder`: zero extra infrastructure now,
            PostgreSQL once multiple writers need it concurrently.
    """

    def __init__(self, db_path: str | Path = "ops_store/dlq.duckdb") -> None:
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
        event_id: str,
        event_type: str,
        producer: str,
        dataset_id: str,
        failure_reason: str,
        correlation_id: str | None = None,
        payload_reference: str | None = None,
        metadata: dict[str, Any] | None = None,
        quarantined_at: datetime | None = None,
    ) -> DLQEntry:
        """Record one dead-lettered event as `pending`.

        Idempotent on `event_id`: recording the same event twice (e.g. two
        subscribers both raising for one publish) never creates a second row
        or overwrites the first failure's context — the first recording
        wins, and this always returns the entry actually stored.
        """
        if quarantined_at is None:
            quarantined_at = datetime.now(UTC)
        self._conn.execute(
            """
            INSERT INTO dlq VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', NULL)
            ON CONFLICT (event_id) DO NOTHING
            """,
            [
                event_id,
                event_type,
                producer,
                dataset_id,
                correlation_id,
                payload_reference,
                json.dumps(metadata or {}),
                failure_reason,
                _to_naive_utc(quarantined_at),
            ],
        )
        entry = self.get(event_id)
        if entry is None:
            raise RuntimeError(
                f"dlq row for event_id {event_id!r} vanished immediately after insert"
            )
        return entry

    def mark_replayed(self, event_id: str, replayed_at: datetime | None = None) -> DLQEntry | None:
        """Transition `event_id` from `pending` to `replayed`.

        Idempotent: a second call on an already-replayed entry updates
        nothing (the `WHERE status = 'pending'` guard matches zero rows) and
        simply returns the entry as it already stood — `replayed_at` is not
        overwritten by a repeated call.
        """
        if replayed_at is None:
            replayed_at = datetime.now(UTC)
        self._conn.execute(
            "UPDATE dlq SET status = 'replayed', replayed_at = ? "
            "WHERE event_id = ? AND status = 'pending'",
            [_to_naive_utc(replayed_at), event_id],
        )
        return self.get(event_id)

    def get(self, event_id: str) -> DLQEntry | None:
        row = self._conn.execute(
            "SELECT event_id, event_type, producer, dataset_id, correlation_id, "
            "payload_reference, metadata, failure_reason, quarantined_at, status, "
            "replayed_at FROM dlq WHERE event_id = ?",
            [event_id],
        ).fetchone()
        return self._row_to_entry(row) if row is not None else None

    def list_pending(self) -> list[DLQEntry]:
        """Every entry still awaiting replay, oldest first."""
        rows = self._conn.execute(
            "SELECT event_id, event_type, producer, dataset_id, correlation_id, "
            "payload_reference, metadata, failure_reason, quarantined_at, status, "
            "replayed_at FROM dlq WHERE status = 'pending' ORDER BY quarantined_at"
        ).fetchall()
        return [self._row_to_entry(row) for row in rows]

    @staticmethod
    def _row_to_entry(row: Any) -> DLQEntry:
        return DLQEntry(
            event_id=row[0],
            event_type=row[1],
            producer=row[2],
            dataset_id=row[3],
            correlation_id=row[4],
            payload_reference=row[5],
            metadata=json.loads(row[6]) if row[6] else {},
            failure_reason=row[7],
            quarantined_at=_to_aware_utc(row[8]),  # type: ignore[arg-type]
            status=row[9],
            replayed_at=_to_aware_utc(row[10]),
        )
