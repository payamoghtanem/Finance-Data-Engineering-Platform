# No `from __future__ import annotations` here -- same reasoning as
# assets.py: Dagster's context-parameter type validation breaks under PEP
# 563's postponed evaluation, confirmed empirically for @asset and assumed
# (not re-verified) to apply the same way to @asset_check's context param,
# since both share the same underlying op-definition machinery.
"""Asset checks: FR-OPS-002 alerting wired into the real pipeline (EPIC-08).

Each check reads `ingestion_run` history after `fred_cpi_raw` materializes
and evaluates one FR-OPS-002 alert condition (`src/common/alerting.py`). A
failing check is visible in the Dagster UI per-run (FR-OPS-001) and triggers
the structured-log alert (`emit_alert`) in the same step.
"""

from datetime import timedelta

from dagster import AssetCheckExecutionContext, AssetCheckResult, AssetCheckSeverity, asset_check
from src.common.alerting import (
    AlertEvent,
    detect_consecutive_failures,
    detect_freshness_breach,
    emit_alert,
)

from pipelines.dagster_project.assets import fred_cpi_raw
from pipelines.dagster_project.resources import IngestionRunHistoryResource

_DATASET_ID = "fred_cpiaucsl"

# How long fred_cpiaucsl may go without a successful ingestion before this
# check fires. A Phase 1 default, not derived from the FRED contract's own
# freshness_slo (free text, not machine-parseable -- same reasoning as
# src/validation/rules.py::check_freshness). Generous relative to the daily
# schedule in schedules.py so one missed/delayed run doesn't alert; tune
# once real operational data exists (see STATUS.md's EPIC-08 entry).
_DEFAULT_MAX_LAG = timedelta(hours=48)


def _result_for(alert: AlertEvent | None) -> AssetCheckResult:
    if alert is None:
        return AssetCheckResult(passed=True, metadata={"dataset_id": _DATASET_ID})
    emit_alert(alert)
    return AssetCheckResult(
        passed=False,
        severity=AssetCheckSeverity.ERROR,
        description=alert.message,
        metadata={key: str(value) for key, value in alert.details.items()},
    )


@asset_check(
    asset=fred_cpi_raw,
    description="FR-OPS-002: alert on >= 2 consecutive ingestion failures.",
)
def fred_cpi_consecutive_failures_check(
    context: AssetCheckExecutionContext,
    ingestion_run_history: IngestionRunHistoryResource,
) -> AssetCheckResult:
    runs = ingestion_run_history.list_for_dataset(_DATASET_ID)
    return _result_for(detect_consecutive_failures(runs, threshold=2))


@asset_check(
    asset=fred_cpi_raw,
    description="FR-OPS-002 / NFR-FRESH-003: alert when the dataset goes stale.",
)
def fred_cpi_freshness_check(
    context: AssetCheckExecutionContext,
    ingestion_run_history: IngestionRunHistoryResource,
) -> AssetCheckResult:
    runs = ingestion_run_history.list_for_dataset(_DATASET_ID)
    latest_run = runs[-1] if runs else None
    return _result_for(detect_freshness_breach(latest_run, max_lag=_DEFAULT_MAX_LAG))
