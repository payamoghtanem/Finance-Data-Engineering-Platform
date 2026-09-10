# `transform/dbt_project`

Bronze → Silver → Gold conformance (EPIC-05). Implements FR-MODEL-001 (canonical
shape), FR-MODEL-002 (six distinct time fields), FR-MODEL-003 (KPI logic defined
once). See `../../../docs/technical/technical-design-document.md` §2d for the
full design and `../../../docs/technical/data-model.md` for the target schema.

## What this reads and writes

- **Reads** Bronze in place via dbt-duckdb's `attach` (see `profiles.yml`) —
  never re-fetches from a source, never writes back to Bronze.
- **Writes** `models/silver/fact_economic_observation.sql` and
  `models/gold/fact_economic_kpi.sql` into its own local DuckDB file
  (`transform_store/transform.duckdb` by default).

## Honest scope note

Only FRED feeds this today (`seeds/seed_dataset_indicator_map.csv` has one
row). The shape is source-agnostic by design — Eurostat (EPIC-14) conforms by
adding a mapping row and a parsing branch to the Silver model, not by changing
the table shape. Nothing here is wired to run automatically yet: invoking it
is a manual step until EPIC-07 (Dagster) schedules it.

## Running it locally

From the repository root, with `dbt-core` and `dbt-duckdb` installed
(`pip install -e ".[dev,transform]"` — see `pyproject.toml`) and at least one
real Bronze row already written by `src/bronze/writer.py` (a live connector
run, or `python scripts/seed_bronze_fixture.py` for a synthetic one):

```bash
mkdir -p transform_store   # dbt-duckdb doesn't create the output file's parent dir itself
export DBT_PROFILES_DIR="$(pwd)/src/transform/dbt_project"
dbt build --project-dir src/transform/dbt_project   # seeds + models + tests, in dependency order
```

Run it with `--project-dir` from the repository root rather than `cd`-ing into
`src/transform/dbt_project` first: `profiles.yml`'s default paths
(`transform_store/transform.duckdb`, `bronze_store/bronze.duckdb`) are relative
to the current working directory, and repo root is where `bronze_store/`
actually lives (the same default `BronzeWriter` uses). Override
`DBT_DUCKDB_PATH` / `DBT_BRONZE_DB_PATH` to point at a different Bronze file
(e.g. a test fixture) regardless of working directory.

## The CI check

`.github/workflows/ci.yml`'s `dbt-transform` job doesn't just run `dbt build`
once — it runs `scripts/verify_epic05_acceptance.py`, which seeds a fixture,
builds, re-runs against identical data to prove no duplication (US-02-004),
then seeds a later revision of the same period and proves it lands as a new,
independently queryable `vintage_date` row with Gold's KPI model correctly
picking the latest one (US-02-006). Run it locally the same way CI does:

```bash
python scripts/verify_epic05_acceptance.py
```
