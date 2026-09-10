"""Schedule wiring for EPIC-07 (US-07-001, US-02-002).

Defaults to STOPPED: this schedule fetches from a real external API using a
real credential on every fire, which must not silently start running just
because a Dagster instance loaded these `Definitions`. An operator turns it
on deliberately from the Dagster UI (this is exactly the kind of write-class
action `docs/ai-agent/agentic-ai-design.md` reserves for a human, never the
platform's own agent).
"""

from __future__ import annotations

from dagster import DefaultScheduleStatus, ScheduleDefinition, define_asset_job

from pipelines.dagster_project.assets import fred_cpi_bronze, fred_cpi_raw, silver_gold_conformance

fred_cpi_ingestion_job = define_asset_job(
    "fred_cpi_ingestion_job",
    selection=[fred_cpi_raw, fred_cpi_bronze, silver_gold_conformance],
    description=(
        "Fetch FRED CPI, load Bronze, conform to Silver/Gold -- one run of the full pipeline."
    ),
)

# Illustrative Phase 1 cadence, not release-calendar-aware: FRED's own
# freshness_slo (src/connectors/fred/contract.yaml) is "available by 08:30
# America/New_York on release days (typically mid-month)" -- a daily poll is
# deliberately over-frequent rather than under, since content-addressed raw
# storage and Bronze's idempotent write make a no-op re-fetch cheap and
# harmless. A release-calendar-aware sensor is a reasonable future upgrade,
# not required for US-02-002/US-07-001's own acceptance criteria.
fred_cpi_daily_schedule = ScheduleDefinition(
    job=fred_cpi_ingestion_job,
    cron_schedule="0 13 * * *",
    default_status=DefaultScheduleStatus.STOPPED,
)
