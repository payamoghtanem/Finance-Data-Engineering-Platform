# `pipelines/dagster_project`

Orchestration (EPIC-07). Wires the existing connector, Bronze, and dbt
modules into one scheduled pipeline — see
`../../docs/technical/technical-design-document.md` §2e for the full design.

## What this does and doesn't do

- **Does**: define assets (`fred_cpi_raw` → `fred_cpi_bronze` →
  `silver_gold_conformance`), a job wiring them together, a daily schedule,
  and a Dagster-level retry policy on the fetch step.
- **Doesn't**: fetch, parse, store, or transform anything itself — every
  asset calls an existing class (`FREDConnector`, `BronzeWriter`, `dbt
  build`) via a thin resource in `resources.py`. If you're looking for
  business logic, it isn't here by design (`technical-design-document.md`
  §2's module boundary table).

## Running it locally

From the repository root, with the `orchestration` extra installed
(`pip install -e ".[dev,orchestration]"`) and the environment variables
`FREDConnector`/`BronzeWriter` need (`POSTGRES_PASSWORD`,
`MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `FRED_API_KEY` — see
`src/common/config.py`):

```bash
dagster dev -f pipelines/dagster_project/definitions.py
```

Open the printed URL for the Dagster UI — this is what gives the pipeline
real run visibility (FR-OPS-001): status, duration, and a failure's
logs/stack trace per run.

**The daily schedule defaults to STOPPED.** It fetches from a real external
API with a real credential on every fire, so it must not start just because
these `Definitions` loaded — enable it deliberately from the UI's Schedules
tab (or `dagster schedule start fred_cpi_daily_schedule` once the daemon is
running).

## Testing

`tests/unit/test_dagster_pipeline.py` proves the asset graph's wiring
(dependencies, resources, retry policy, schedule config) using fake
resources that never touch the network, S3, or DuckDB — `FREDConnector`'s
and `BronzeWriter`'s own logic is already covered by their own test suites.
Run it the same way as every other unit test:

```bash
pytest tests/unit/test_dagster_pipeline.py
```

CI additionally runs `dagster definitions validate` (the `dagster-pipeline`
job) as a structural check that catches a wiring mistake plain unit tests
might miss — a bad resource key, an unresolvable dependency.

## Known gaps

- `infra/docker-compose.yml`'s `dagster` service references a
  `Dockerfile.dagster` that doesn't exist yet — untested in this session (no
  Docker daemon available), tracked honestly rather than guessed at.
- The daily schedule's cron cadence is illustrative, not release-calendar
  aware (see `schedules.py`'s comment).
- US-07-001's "≥95% success over ≥3 consecutive days" is a measurement of
  real elapsed operation once the schedule is enabled — not something this
  code or its tests can produce on their own.
