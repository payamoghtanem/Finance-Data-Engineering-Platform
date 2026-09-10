"""Unit tests for IngestionRunRecorder (US-02-005, FR-OPS-001)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from src.common.ingestion_run import IngestionRunRecorder


@pytest.fixture
def recorder() -> IngestionRunRecorder:
    return IngestionRunRecorder(db_path=":memory:")


class TestRecordSuccess:
    def test_record_returns_matching_run(self, recorder: IngestionRunRecorder) -> None:
        started = datetime(2026, 9, 10, 12, 0, 0, tzinfo=UTC)
        finished = started + timedelta(seconds=3)
        run = recorder.record(
            dataset_id="fred_cpiaucsl",
            connector_version="0.1.0",
            started_at=started,
            finished_at=finished,
            status="success",
            request_hash="abc123",
            retry_count=0,
            raw_storage_path="raw/fred/CPIAUCSL/date=2026-09-10/abc.json",
        )
        assert run.dataset_id == "fred_cpiaucsl"
        assert run.status == "success"
        assert run.retry_count == 0
        assert run.error is None
        assert run.duration_seconds == pytest.approx(3.0)

    def test_get_round_trips_a_recorded_run(self, recorder: IngestionRunRecorder) -> None:
        started = datetime(2026, 9, 10, 12, 0, 0, tzinfo=UTC)
        written = recorder.record(
            dataset_id="fred_cpiaucsl",
            connector_version="0.1.0",
            started_at=started,
            finished_at=started + timedelta(seconds=1),
            status="success",
            request_hash="abc123",
            retry_count=0,
            raw_storage_path="raw/fred/CPIAUCSL/date=2026-09-10/abc.json",
        )
        looked_up = recorder.get(written.run_id)
        assert looked_up == written

    def test_started_at_and_finished_at_round_trip_as_utc(
        self, recorder: IngestionRunRecorder
    ) -> None:
        started = datetime(2026, 9, 10, 12, 0, 0, tzinfo=UTC)
        written = recorder.record(
            dataset_id="fred_cpiaucsl",
            connector_version="0.1.0",
            started_at=started,
            finished_at=started,
            status="success",
            request_hash="abc123",
            retry_count=0,
        )
        fetched = recorder.get(written.run_id)
        assert fetched is not None
        assert fetched.started_at.tzinfo is not None
        assert fetched.started_at == started


class TestRecordFailure:
    def test_failed_run_preserves_error_and_retry_count(
        self, recorder: IngestionRunRecorder
    ) -> None:
        started = datetime(2026, 9, 10, 12, 0, 0, tzinfo=UTC)
        run = recorder.record(
            dataset_id="fred_cpiaucsl",
            connector_version="0.1.0",
            started_at=started,
            finished_at=started + timedelta(seconds=10),
            status="failed",
            request_hash="abc123",
            retry_count=3,
            raw_storage_path=None,
            error="Failed to fetch CPIAUCSL after 3 retries",
        )
        assert run.status == "failed"
        assert run.retry_count == 3
        assert run.raw_storage_path is None
        assert "3 retries" in (run.error or "")


class TestEveryRunIsItsOwnRow:
    """Unlike Raw/Bronze, ingestion_run is not content-addressed: every
    execution is its own audit-log entry, even with identical inputs."""

    def test_two_identical_records_get_distinct_run_ids(
        self, recorder: IngestionRunRecorder
    ) -> None:
        started = datetime(2026, 9, 10, 12, 0, 0, tzinfo=UTC)
        kwargs = {
            "dataset_id": "fred_cpiaucsl",
            "connector_version": "0.1.0",
            "started_at": started,
            "finished_at": started,
            "status": "success",
            "request_hash": "abc123",
            "retry_count": 0,
        }
        first = recorder.record(**kwargs)
        second = recorder.record(**kwargs)
        assert first.run_id != second.run_id

    def test_list_for_dataset_returns_all_runs_oldest_first(
        self, recorder: IngestionRunRecorder
    ) -> None:
        t0 = datetime(2026, 9, 10, 12, 0, 0, tzinfo=UTC)
        for i in range(3):
            recorder.record(
                dataset_id="fred_cpiaucsl",
                connector_version="0.1.0",
                started_at=t0 + timedelta(hours=i),
                finished_at=t0 + timedelta(hours=i, seconds=1),
                status="success",
                request_hash="abc123",
                retry_count=0,
            )
        runs = recorder.list_for_dataset("fred_cpiaucsl")
        assert len(runs) == 3
        assert [r.started_at for r in runs] == sorted(r.started_at for r in runs)

    def test_list_for_dataset_ignores_other_datasets(self, recorder: IngestionRunRecorder) -> None:
        started = datetime(2026, 9, 10, 12, 0, 0, tzinfo=UTC)
        recorder.record(
            dataset_id="fred_cpiaucsl",
            connector_version="0.1.0",
            started_at=started,
            finished_at=started,
            status="success",
            request_hash="abc123",
            retry_count=0,
        )
        recorder.record(
            dataset_id="worldbank_gdp",
            connector_version="0.1.0",
            started_at=started,
            finished_at=started,
            status="success",
            request_hash="def456",
            retry_count=0,
        )
        assert len(recorder.list_for_dataset("fred_cpiaucsl")) == 1
