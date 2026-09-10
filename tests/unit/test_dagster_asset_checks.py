"""Tests for pipelines/dagster_project/asset_checks.py (FR-OPS-002, EPIC-08).

Fake IngestionRunHistoryResource -- never touches DuckDB -- proves the
check's decision logic and its wiring into the Dagster asset graph. The
underlying alert-detection logic itself is covered by test_alerting.py.
"""

import logging
from datetime import UTC, datetime, timedelta

from dagster import build_asset_check_context
from pipelines.dagster_project.asset_checks import (
    fred_cpi_consecutive_failures_check,
    fred_cpi_freshness_check,
)
from pipelines.dagster_project.definitions import defs
from src.common.ingestion_run import IngestionRun

_T0 = datetime(2026, 9, 10, 12, 0, 0, tzinfo=UTC)


def _run(*, status: str, hours_offset: int = 0, run_id: str = "run-1") -> IngestionRun:
    started = _T0 + timedelta(hours=hours_offset)
    return IngestionRun(
        run_id=run_id,
        dataset_id="fred_cpiaucsl",
        connector_version="0.1.0",
        started_at=started,
        finished_at=started + timedelta(seconds=1),
        status=status,
        request_hash="abc123",
        retry_count=0,
        raw_storage_path=None,
        error=None,
    )


class _FakeHistory:
    """Not a ConfigurableResource subclass on purpose: these tests call the
    check functions directly (plain Python argument passing, no Dagster
    resource-config resolution), and a `list[IngestionRun]` field isn't a
    type Dagster's pydantic-based resource config can represent."""

    def __init__(self, runs: list[IngestionRun]) -> None:
        self._runs = runs

    def list_for_dataset(self, dataset_id: str) -> list[IngestionRun]:
        return list(self._runs)


class TestConsecutiveFailuresCheck:
    def test_passes_with_no_failure_streak(self) -> None:
        history = _FakeHistory(runs=[_run(status="success")])
        result = fred_cpi_consecutive_failures_check(build_asset_check_context(), history)
        assert result.passed

    def test_fails_at_two_consecutive_failures(self, caplog) -> None:
        history = _FakeHistory(
            runs=[
                _run(status="failed", hours_offset=0, run_id="run-1"),
                _run(status="failed", hours_offset=1, run_id="run-2"),
            ]
        )
        with caplog.at_level(logging.ERROR, logger="src.common.alerting"):
            result = fred_cpi_consecutive_failures_check(build_asset_check_context(), history)
        assert not result.passed
        assert len(caplog.records) == 1
        assert caplog.records[0].alert_type == "consecutive_failures"  # type: ignore[attr-defined]


class TestFreshnessCheck:
    def test_passes_when_recent(self) -> None:
        recent_run = _run(status="success", hours_offset=0)
        history = _FakeHistory(runs=[recent_run])
        # build_asset_check_context() doesn't let us inject "now" -- the
        # check uses the module's default (a generous 48h max_lag), and a
        # freshly-built run finishes effectively "now", so it passes.
        result = fred_cpi_freshness_check(build_asset_check_context(), history)
        assert result.passed

    def test_fails_with_no_runs_at_all(self, caplog) -> None:
        history = _FakeHistory(runs=[])
        with caplog.at_level(logging.ERROR, logger="src.common.alerting"):
            result = fred_cpi_freshness_check(build_asset_check_context(), history)
        assert not result.passed
        assert len(caplog.records) == 1
        assert caplog.records[0].alert_type == "freshness_breach"  # type: ignore[attr-defined]


class TestDefinitionsIncludeChecks:
    def test_asset_checks_are_registered(self) -> None:
        check_names = {check.check_key.name for check in defs.asset_checks or []}
        assert "fred_cpi_consecutive_failures_check" in check_names
        assert "fred_cpi_freshness_check" in check_names
