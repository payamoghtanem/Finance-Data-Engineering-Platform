"""Tests for pipelines/dagster_project/ (EPIC-07, US-07-001/US-02-002).

Proves the asset graph's *wiring* (dependencies, resources, retry policy,
schedule config) -- not FREDConnector's or BronzeWriter's own fetch/storage
logic, which is already covered by test_fred_connector.py and
test_bronze_writer.py. Fake resources here never touch the network, S3, or
DuckDB.
"""

from __future__ import annotations

from typing import Any

from dagster import AssetKey, Backoff, DefaultScheduleStatus, build_asset_context, materialize
from pipelines.dagster_project.assets import fred_cpi_bronze, fred_cpi_raw, silver_gold_conformance
from pipelines.dagster_project.definitions import defs
from pipelines.dagster_project.resources import BronzeResource, FREDIngestionResource
from pipelines.dagster_project.schedules import fred_cpi_daily_schedule, fred_cpi_ingestion_job


class _FakeFREDIngestionResource(FREDIngestionResource):
    def run_ingestion(self) -> dict[str, Any]:
        return {
            "status": "success",
            "series_id": self.series_id,
            "dataset_id": f"fred_{self.series_id.lower()}",
            "correlation_id": "corr-test",
            "retrieved_at": "2024-02-01T09:00:00+00:00",
            "object_key": "raw/fred/CPIAUCSL/fake.json",
            "sha256": "abc123",
            "observation_count": 3,
            "run_id": "run-test",
        }


class _FakeBronzeResource(BronzeResource):
    def write_bronze(self, **kwargs: Any) -> dict[str, Any]:
        return {"bronze_id": "bronze-fake", "raw_object_key": kwargs["raw_object_key"]}


class TestAssetWiring:
    def test_fred_cpi_raw_calls_the_resource(self) -> None:
        context = build_asset_context()
        result = fred_cpi_raw(context, _FakeFREDIngestionResource())
        assert result["object_key"] == "raw/fred/CPIAUCSL/fake.json"
        assert result["dataset_id"] == "fred_cpiaucsl"

    def test_fred_cpi_bronze_passes_upstream_fields_through(self) -> None:
        context = build_asset_context()
        raw_result = fred_cpi_raw(context, _FakeFREDIngestionResource())
        bronze_result = fred_cpi_bronze(context, raw_result, _FakeBronzeResource())
        assert bronze_result["bronze_id"] == "bronze-fake"
        assert bronze_result["raw_object_key"] == raw_result["object_key"]

    def test_silver_gold_conformance_depends_on_bronze(self) -> None:
        assert silver_gold_conformance.asset_deps == {
            AssetKey(["silver_gold_conformance"]): {AssetKey(["fred_cpi_bronze"])}
        }


class TestFullAssetGraph:
    def test_materializes_fetch_and_bronze_end_to_end(self) -> None:
        # silver_gold_conformance is excluded: it shells out to a real `dbt`
        # binary, which isn't installed in every environment that runs this
        # test (it lives behind the separate `transform` extra) -- covered
        # end-to-end instead by CI's dbt-transform job / verify_epic05_acceptance.py.
        result = materialize(
            [fred_cpi_raw, fred_cpi_bronze],
            resources={
                "fred_ingestion": _FakeFREDIngestionResource(),
                "bronze": _FakeBronzeResource(),
            },
        )
        assert result.success


class TestRetryPolicy:
    def test_fred_cpi_raw_has_a_dagster_level_retry_policy(self) -> None:
        # Layered above FREDConnector's own per-HTTP-call retry -- see
        # assets.py's docstring for why this isn't redundant.
        policy = fred_cpi_raw.op.retry_policy
        assert policy is not None
        assert policy.max_retries == 2
        assert policy.backoff is Backoff.EXPONENTIAL


class TestSchedule:
    def test_defaults_to_stopped(self) -> None:
        # Must never auto-fetch from a real external API just because
        # Definitions loaded -- an operator turns this on deliberately.
        assert fred_cpi_daily_schedule.default_status is DefaultScheduleStatus.STOPPED

    def test_targets_the_full_pipeline_job(self) -> None:
        assert fred_cpi_daily_schedule.job_name == fred_cpi_ingestion_job.name


class TestJobSelection:
    def test_includes_all_three_pipeline_stages(self) -> None:
        assert set(fred_cpi_ingestion_job.selection.selected_keys) == {
            AssetKey(["fred_cpi_raw"]),
            AssetKey(["fred_cpi_bronze"]),
            AssetKey(["silver_gold_conformance"]),
        }


class TestDefinitionsLoad:
    def test_definitions_object_is_loadable(self) -> None:
        assert defs is not None
