"""Dagster assets: schedule -> fetch -> Bronze -> Silver/Gold (EPIC-07).

This module wires EXISTING components together (`FREDConnector`,
`BronzeWriter`, the dbt project) -- it contains no fetch/storage/transform
logic of its own, per the `pipelines/` module boundary
(technical-design-document.md §2: "it orchestrates other modules, it doesn't
replace them").
"""

# No `from __future__ import annotations` here (unlike every other module in
# this repo): Dagster's `@asset` decorator validates the `context` parameter's
# type by identity against `AssetExecutionContext`, and PEP 563's postponed
# (string) evaluation breaks that check -- confirmed empirically, not a
# guess. See https://github.com/dagster-io/dagster (op_definition.py's
# `_validate_context_type_hint`).

import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from dagster import AssetExecutionContext, Backoff, RetryPolicy, asset

from pipelines.dagster_project.resources import BronzeResource, FREDIngestionResource

_DBT_PROJECT_DIR = str(Path(__file__).resolve().parents[2] / "src" / "transform" / "dbt_project")


@asset(
    retry_policy=RetryPolicy(max_retries=2, delay=30, backoff=Backoff.EXPONENTIAL),
    description="Fetch FRED CPI, persist raw bytes immutably (FR-ING-001).",
)
def fred_cpi_raw(
    context: AssetExecutionContext, fred_ingestion: FREDIngestionResource
) -> dict[str, Any]:
    """Fetch one FRED CPI ingestion run.

    The `retry_policy` here is a *second*, Dagster-level retry layered above
    `FREDConnector.fetch_series_raw`'s own per-HTTP-call retry (3 attempts,
    exponential backoff): the connector's retry covers one transient
    response, this covers the entire materialization failing for any reason
    (a process crash, an exception past the connector's own retry budget).
    Re-running is safe either way -- raw storage is content-addressed
    (identical payload -> no-op write) and `ingestion_run` records every
    attempt regardless (US-02-005).
    """
    result = fred_ingestion.run_ingestion()
    context.add_output_metadata(
        {
            "object_key": result["object_key"],
            "sha256": result["sha256"],
            "run_id": result["run_id"],
            "observation_count": result["observation_count"],
        }
    )
    return result


@asset(description="Load the raw FRED response into Bronze with lineage (US-03-002).")
def fred_cpi_bronze(
    context: AssetExecutionContext, fred_cpi_raw: dict[str, Any], bronze: BronzeResource
) -> dict[str, Any]:
    record = bronze.write_bronze(
        source_id="fred",
        dataset_id=fred_cpi_raw["dataset_id"],
        raw_object_key=fred_cpi_raw["object_key"],
        raw_sha256=fred_cpi_raw["sha256"],
        retrieved_at=datetime.fromisoformat(fred_cpi_raw["retrieved_at"]),
    )
    context.add_output_metadata({"bronze_id": record["bronze_id"]})
    return record


@asset(deps=[fred_cpi_bronze], description="Conform Bronze into Silver/Gold via dbt (EPIC-05).")
def silver_gold_conformance(context: AssetExecutionContext) -> None:
    """Invoke `dbt build` -- the manual step `transform/dbt_project/README.md`
    describes is now this asset's job, not an operator's.
    """
    dbt_executable = shutil.which("dbt")
    if dbt_executable is None:
        raise RuntimeError("dbt is not on PATH -- install the 'transform' extra (pyproject.toml)")
    Path("transform_store").mkdir(parents=True, exist_ok=True)
    # Fixed argv built from this module's own constant, never external input.
    subprocess.run(  # noqa: S603
        [
            dbt_executable,
            "build",
            "--project-dir",
            _DBT_PROJECT_DIR,
            "--profiles-dir",
            _DBT_PROJECT_DIR,
        ],
        check=True,
    )
    context.add_output_metadata({"dbt_project_dir": _DBT_PROJECT_DIR})
