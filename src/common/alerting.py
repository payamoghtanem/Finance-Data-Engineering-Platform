"""Alert detection (FR-OPS-002, NFR-FRESH-003, EPIC-08).

Pure functions deciding WHEN an alert condition exists, reading only from
`IngestionRunRecorder`/`DataQualityResultRecorder` history -- no network, no
Prometheus, no Grafana. Delivery in Phase 1 is a structured JSON ERROR-level
log line (docs/engineering/engineering-standards.md §5's own contract:
"ERROR = human action needed") -- the one alert-delivery mechanism this
project's own docs actually specify. No design doc names a Prometheus/Grafana
alert channel for Phase 1; building one would mean inventing infra the docs
never committed to. See STATUS.md's EPIC-08 entry for the full reasoning.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from src.common.data_quality_result import DataQualityResult
from src.common.ingestion_run import IngestionRun
from src.common.logging_config import setup_logging

_logger = setup_logging(__name__)


@dataclass(frozen=True)
class AlertEvent:
    """One FR-OPS-002 alert condition."""

    alert_type: str
    dataset_id: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)


def detect_consecutive_failures(
    runs: Sequence[IngestionRun], *, threshold: int = 2
) -> AlertEvent | None:
    """FR-OPS-002: "a repeated ingestion failure (>= 2 consecutive failures
    for the same connector)".

    `runs` must already be ordered oldest-first --
    `IngestionRunRecorder.list_for_dataset`'s own contract. This function
    trusts that order rather than re-sorting: silently re-sorting a
    caller's mistake would hide a real bug instead of surfacing it.
    """
    if not runs:
        return None
    dataset_id = runs[-1].dataset_id
    consecutive = 0
    for run in reversed(runs):
        if run.status != "failed":
            break
        consecutive += 1
    if consecutive < threshold:
        return None
    return AlertEvent(
        alert_type="consecutive_failures",
        dataset_id=dataset_id,
        message=f"{consecutive} consecutive ingestion failures for {dataset_id}",
        details={
            "consecutive_failures": consecutive,
            "latest_run_id": runs[-1].run_id,
            "latest_error": runs[-1].error,
        },
    )


def detect_freshness_breach(
    latest_run: IngestionRun | None,
    *,
    max_lag: timedelta,
    now: datetime | None = None,
) -> AlertEvent | None:
    """FR-OPS-002 / NFR-FRESH-003: alert when a dataset's latest successful
    ingestion is older than its freshness SLO allows (detection-to-alert
    latency target: < 1 hour, NFR-FRESH-003 -- met by construction, since
    this is a synchronous check with no queueing of its own).

    Like `src/validation/rules.py::check_freshness`, this does not parse a
    contract's `freshness_slo` free text into a schedule -- pass `max_lag`
    (that SLO already translated to a maximum age) explicitly.
    """
    now = now or datetime.now(UTC)
    if latest_run is None:
        return AlertEvent(
            alert_type="freshness_breach",
            dataset_id="unknown",
            message="No ingestion run exists to evaluate freshness against",
        )
    if latest_run.status != "success":
        return AlertEvent(
            alert_type="freshness_breach",
            dataset_id=latest_run.dataset_id,
            message=f"Latest run for {latest_run.dataset_id} did not succeed; no fresh data",
            details={"latest_run_id": latest_run.run_id, "latest_status": latest_run.status},
        )
    lag = now - latest_run.finished_at
    if lag <= max_lag:
        return None
    return AlertEvent(
        alert_type="freshness_breach",
        dataset_id=latest_run.dataset_id,
        message=(
            f"Latest successful run for {latest_run.dataset_id} is {lag} old, "
            f"exceeding max_lag {max_lag}"
        ),
        details={
            "latest_run_id": latest_run.run_id,
            "lag_seconds": lag.total_seconds(),
            "max_lag_seconds": max_lag.total_seconds(),
        },
    )


def detect_blocking_quality_failure(
    results: Sequence[DataQualityResult],
) -> AlertEvent | None:
    """FR-OPS-002: "a data-quality blocking-test failure"."""
    failing = [result for result in results if result.status == "fail"]
    if not failing:
        return None
    table_name = failing[0].table_name
    return AlertEvent(
        alert_type="data_quality_blocking_failure",
        dataset_id=table_name,
        message=f"{len(failing)} blocking data-quality test(s) failing for {table_name}",
        details={"failing_test_ids": [result.test_id for result in failing]},
    )


def emit_alert(alert: AlertEvent) -> None:
    """Deliver one alert as a structured JSON ERROR-level log line."""
    _logger.error(
        alert.message,
        extra={"alert_type": alert.alert_type, "dataset_id": alert.dataset_id, **alert.details},
    )
