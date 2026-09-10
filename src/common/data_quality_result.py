"""Data-quality result recorder.

Implements the `data_quality_result` operational table from
docs/technical/data-model.md §4 — one row per quality rule evaluated against
one table, for one run. This is what makes FR-OPS-001's "every ... validation
run must be visible" concrete: `src/validation/` runs the FR-QUAL-xxx rules
and returns a `ValidationReport` (EPIC-04), but nothing persists that report
anywhere queryable yet. This module is that home; wiring `ValidationEngine`
to actually call it is follow-on work, tracked in STATUS.md rather than done
here (EPIC-08's job is giving the data a place to live, not rewiring EPIC-04).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import duckdb

QualityResultStatus = Literal["pass", "fail", "warn"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS data_quality_result (
    test_id      VARCHAR NOT NULL,
    table_name   VARCHAR NOT NULL,
    run_id       VARCHAR NOT NULL,
    status       VARCHAR NOT NULL,
    failed_rows  INTEGER NOT NULL,
    evaluated_at TIMESTAMP NOT NULL,
    PRIMARY KEY (test_id, table_name)
)
"""


def _to_naive_utc(value: datetime) -> datetime:
    """Same reasoning as ingestion_run.py / bronze/writer.py: DuckDB's plain
    TIMESTAMP column is timezone-naive, and TIMESTAMPTZ needs an optional
    `pytz` dependency this project doesn't otherwise use.
    """
    if value.tzinfo is None:
        raise ValueError("Naive datetime given where a timezone-aware one is required")
    return value.astimezone(UTC).replace(tzinfo=None)


def _to_aware_utc(value: datetime) -> datetime:
    """Reattach UTC tzinfo to a naive datetime read back from storage."""
    return value.replace(tzinfo=UTC)


@dataclass(frozen=True)
class DataQualityResult:
    """One `data_quality_result` row. `status` is one of `QualityResultStatus`'s values."""

    test_id: str
    table_name: str
    run_id: str
    status: str
    failed_rows: int
    evaluated_at: datetime


class DataQualityResultRecorder:
    """Records the outcome of one quality rule against one table, per run.

    Args:
        db_path: Path to the DuckDB file. `:memory:` is valid for tests.
            Same Phase-1 storage reasoning as `IngestionRunRecorder`
            (docs/technical/technical-design-document.md §2b): zero extra
            infrastructure now, PostgreSQL once multiple writers need it
            concurrently.
    """

    def __init__(self, db_path: str | Path = "ops_store/data_quality_results.duckdb") -> None:
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
        test_id: str,
        table_name: str,
        run_id: str,
        status: QualityResultStatus,
        failed_rows: int,
        evaluated_at: datetime | None = None,
    ) -> DataQualityResult:
        """Record one rule's outcome, overwriting a prior result for the same
        `(test_id, table_name)` -- the primary key holds the *latest*
        evaluation of a given rule against a given table, not a full history
        (the run_id/evaluated_at fields tell you when that last evaluation
        happened; per-run history is `ingestion_run`'s job, not this one's).
        """
        if evaluated_at is None:
            evaluated_at = datetime.now(UTC)
        self._conn.execute(
            """
            INSERT INTO data_quality_result VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (test_id, table_name) DO UPDATE SET
                run_id = excluded.run_id,
                status = excluded.status,
                failed_rows = excluded.failed_rows,
                evaluated_at = excluded.evaluated_at
            """,
            [
                test_id,
                table_name,
                run_id,
                status,
                failed_rows,
                _to_naive_utc(evaluated_at),
            ],
        )
        return DataQualityResult(
            test_id=test_id,
            table_name=table_name,
            run_id=run_id,
            status=status,
            failed_rows=failed_rows,
            evaluated_at=evaluated_at,
        )

    def get(self, test_id: str, table_name: str) -> DataQualityResult | None:
        row = self._conn.execute(
            "SELECT test_id, table_name, run_id, status, failed_rows, evaluated_at "
            "FROM data_quality_result WHERE test_id = ? AND table_name = ?",
            [test_id, table_name],
        ).fetchone()
        return self._row_to_result(row) if row is not None else None

    def list_for_table(self, table_name: str) -> list[DataQualityResult]:
        """Every rule's latest outcome for one table, ordered by test_id --
        e.g. for FR-OPS-002's "data-quality blocking-test failure" alert rule.
        """
        rows = self._conn.execute(
            "SELECT test_id, table_name, run_id, status, failed_rows, evaluated_at "
            "FROM data_quality_result WHERE table_name = ? ORDER BY test_id",
            [table_name],
        ).fetchall()
        return [self._row_to_result(row) for row in rows]

    @staticmethod
    def _row_to_result(row: Any) -> DataQualityResult:
        return DataQualityResult(
            test_id=row[0],
            table_name=row[1],
            run_id=row[2],
            status=row[3],
            failed_rows=row[4],
            evaluated_at=_to_aware_utc(row[5]),
        )
