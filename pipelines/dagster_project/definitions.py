"""Dagster entry point.

Run the local UI (FR-OPS-001's run visibility) from the repository root:

    dagster dev -f pipelines/dagster_project/definitions.py

Repository root matters: `BronzeResource`/`FREDIngestionResource` and the
`silver_gold_conformance` asset all use paths (`bronze_store/`,
`transform_store/`, `src/transform/dbt_project`) relative to the current
working directory, matching every other local-dev entry point in this repo
(`src/transform/dbt_project/README.md`, `scripts/verify_epic05_acceptance.py`).
"""

from __future__ import annotations

from dagster import Definitions

from pipelines.dagster_project.asset_checks import (
    fred_cpi_consecutive_failures_check,
    fred_cpi_freshness_check,
)
from pipelines.dagster_project.assets import fred_cpi_bronze, fred_cpi_raw, silver_gold_conformance
from pipelines.dagster_project.resources import (
    BronzeResource,
    FREDIngestionResource,
    IngestionRunHistoryResource,
)
from pipelines.dagster_project.schedules import fred_cpi_daily_schedule, fred_cpi_ingestion_job

defs = Definitions(
    assets=[fred_cpi_raw, fred_cpi_bronze, silver_gold_conformance],
    asset_checks=[fred_cpi_consecutive_failures_check, fred_cpi_freshness_check],
    jobs=[fred_cpi_ingestion_job],
    schedules=[fred_cpi_daily_schedule],
    resources={
        "fred_ingestion": FREDIngestionResource(),
        "bronze": BronzeResource(),
        "ingestion_run_history": IngestionRunHistoryResource(),
    },
)
