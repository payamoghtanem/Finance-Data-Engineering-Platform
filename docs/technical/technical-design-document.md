# Technical Design Document (TDD)

**What this document answers:** at implementation-detail level, how are modules organized, what is the exact retry/backoff and DLQ algorithm, what does the repo layout and local `docker-compose` look like, and what does the CI/CD pipeline do?
**How it differs from its neighbors:** `data-model.md` says what a table looks like; `api-design.md` says what an endpoint looks like; this document is where those become buildable — module boundaries, algorithms, repo structure, and deployment mechanics.

## 1. Repository layout (target, once implementation begins)

```
.
├── docs/                       # This documentation set (already present)
├── src/
│   ├── connectors/             # One package per data source
│   │   ├── fred/
│   │   ├── worldbank/
│   │   ├── eurostat/
│   │   ├── sec_edgar/
│   │   └── coingecko/
│   ├── validation/             # Schema + data-quality rule engine (FR-QUAL-xxx)
│   ├── bronze/                  # Loads a raw object into Bronze with full lineage (NFR-GOV-002)
│   ├── transform/               # dbt project (Silver→Gold models)
│   │   └── dbt_project/
│   ├── serving/
│   │   ├── api/                # FastAPI app implementing api-design.md
│   │   └── agent/               # Scoped AI agent implementing ai-agent/agentic-ai-design.md
│   ├── events/                  # Event envelope + emit/consume helpers (event-schema.md)
│   └── common/                  # Shared types, config loading, logging
├── pipelines/
│   └── dagster_project/         # Orchestration: schedules, sensors, asset definitions
├── infra/
│   ├── docker-compose.yml       # Phase 1 local stack
│   ├── k8s/                     # Phase 3 manifests/Helm charts
│   └── terraform/               # Phase 3 IaC (OpenTofu/Terraform, per ARD tool table)
├── tests/
│   ├── unit/
│   ├── integration/
│   └── data_quality/            # Great Expectations / Soda Core suites
└── .github/workflows/           # CI/CD (see §5)
```

Each `src/connectors/<name>/` package must contain, per NFR-MAINT-001: `README.md` (owner, purpose), `contract.yaml` (data contract per `../architecture/solution-design-document.md` §4), `connector.py`, and `tests/`.

## 2. Module boundaries (enforcing `../architecture/ARD.md` §2.3)

| Module | Responsibility | Must NOT do |
|---|---|---|
| `connectors/*` | Fetch from one external source, write raw response to Raw Storage, emit `raw_data.received` | Parse business meaning, write to Silver/Gold, know about other connectors |
| `events/` | The event envelope and the Phase 1 in-process transport (`EventBus`, EPIC-06, ADR-0002) — `publish`/`subscribe`, isolating one subscriber's failure from others and from the publisher | Contain business logic; know what a specific event *means* to its consumers |
| `validation/` (EPIC-04) | Check schema + data contract + quality rules against a batch of already-parsed records, emit `raw_data.validated` or `raw_data.quarantined` (§2c) | Fetch data itself, transform/rename fields for business meaning, parse a source's raw payload into record shape (that's a connector's job) |
| `bronze/` | Load one raw object into Bronze with lineage back to it (`raw_object_key`, `source_id`, `retrieved_at`, `code_version`), emit `bronze_data.written`. Reads only from `RawStorage` — never re-fetches from the source (ARD §2.2) | Parse business fields into typed/canonical columns (that's `transform/`'s job, FR-MODEL-001), fetch data itself |
| `transform/` (dbt, EPIC-05) | Silver→Gold SQL transforms, canonical conformance (§2d) | Perform network I/O, manage scheduling, write back to Bronze |
| `serving/api` | Expose Gold data per `api-design.md`, enforce auth/rate limits | Perform transformation logic, write to any table |
| `serving/agent` | Read-only retrieval + natural-language response per `ai-agent/agentic-ai-design.md` | Any write, delete, schema, or backfill action |
| `pipelines/dagster_project` (EPIC-07) | Scheduling, dependency graph, retries, backfills, run visibility (§2e) | Contain business/transform logic itself — it orchestrates other modules, it doesn't replace them |

### 2a. Bronze storage shape (`bronze/`, EPIC-03)

Bronze mirrors Raw's content plus lineage — it does **not** parse business
fields into typed columns; that conformance step is `transform/`'s job
(FR-MODEL-001, EPIC-05), not this module's. One row per raw object:

| Column | Notes |
|---|---|
| `bronze_id` | Deterministic hash of `raw_object_key` — makes a re-load of the same raw object a no-op, not a duplicate |
| `source_id`, `dataset_id` | Denormalized from the ingestion run for query convenience |
| `raw_object_key` | The exact `RawStorage` key this row was loaded from |
| `raw_sha256` | Recomputed from the bytes at load time and compared against the key's own hash suffix — catches silent corruption between write and read |
| `retrieved_at`, `code_version` | Copied from provenance, not re-derived |
| `ingested_at` | When *this* Bronze row was written (distinct from `retrieved_at`, per the time-field discipline in `data-model.md` §5) |
| `payload` | The raw JSON, untouched, as text |

Phase 1 storage: a local DuckDB file (`bronze_store/bronze.duckdb`) — DuckDB is
already the Phase 1 query engine per `../roadmap/mvp-plan.md` §2, so this adds
no new infrastructure. It becomes an Iceberg table per `data-model.md` §1 when
the platform moves off a single laptop; nothing above this storage detail
changes when that swap happens.

### 2b. `ingestion_run` storage (US-02-005)

Every connector run — success or failure — writes exactly one row via
`src/common/ingestion_run.py`, matching the `ingestion_run` schema in
`data-model.md` §4. Unlike Raw/Bronze, this table is **not** content-addressed:
each execution is its own audit-log entry, even one that (because the data
layer is idempotent) writes nothing new downstream.

Phase 1 storage is a separate local DuckDB file
(`ops_store/ingestion_runs.duckdb`), for the same zero-extra-infrastructure
reason as Bronze's. `ingestion_run` and `data_quality_result` are operational
metadata rather than data-lake content, so their more likely production home
is PostgreSQL (`PlatformConfig.database` already exists for this) once
multiple connectors write concurrently — revisit when EPIC-07/08 need that.

### 2c. Validation rule engine (`validation/`, EPIC-04)

`src/validation/rules.py` implements the nine FR-QUAL-001..009 rules from
`../requirements/FRD.md` §2 as pure functions: given a batch of records
already shaped to a dataset's `contract.yaml` field names, plus the loaded
`DataContract` (`src/validation/contract.py`, parsed from the connector's
`contract.yaml` at runtime — not a second hand-copied schema), each returns
one `RuleResult` (`PASSED` / `FAILED` / `FLAGGED` / `SKIPPED`).

`FLAGGED` is a distinct outcome from `FAILED`, per FR-QUAL-008's own text:
a flagged batch ("statistically extreme" but not yet confirmed invalid)
still gets published, not quarantined — that distinction is enforced in
`ValidationEngine.validate()` (`src/validation/engine.py`), which runs all
nine rules and publishes `raw_data.validated` or `raw_data.quarantined`
(this module's documented role in `event-schema.md` §2) based only on
whether any rule `FAILED`.

Four rules need context this engine has no independent way to obtain yet,
and are honestly `SKIPPED` rather than faking a pass when it's absent:

| Rule | Needs | Who would supply it |
|---|---|---|
| FR-QUAL-002 (completeness) | an expected-record calendar | a scheduler that knows the dataset's cadence (EPIC-07) |
| FR-QUAL-004 (freshness) | `max_lag`, because `freshness_slo` is free text, not a parseable schedule | whatever turns the SLO text into a duration (EPIC-07) |
| FR-QUAL-006 (referential integrity) | known dimension-table keys | Silver/Gold dimension tables (EPIC-05) |
| FR-QUAL-007 (reconciliation) | the source's own count/checksum | a periodic reconciliation job (EPIC-07) |

`ValidationEngine` is not, as of EPIC-04, wired as a live consumer of
`raw_data.received` — that requires a source-specific parser turning a
connector's raw bytes into the contract's record shape (e.g. FRED's
`{"date": ..., "value": ...}` observations into
`observed_at`/`value`/`source_id`/...), which doesn't exist for any
connector yet. What exists now is the rule engine itself, callable directly
once such a parser lands.

### 2d. Silver/Gold dbt project (`src/transform/dbt_project/`, EPIC-05)

A real `dbt-duckdb` project — no new infrastructure, per the same reasoning
as Bronze and `ingestion_run` (§2a/§2b): DuckDB is already the Phase 1 query
engine. It reads Bronze **in place** via dbt-duckdb's `attach` feature
(`profiles.yml` attaches `bronze_store/bronze.duckdb` read-only, aliased
`bronze_db`) rather than copying Bronze data anywhere — `transform/` conforms
what `bronze/` already wrote, it never re-fetches from a source and never
writes back to Bronze (module boundary table, §2).

**Silver** — `models/silver/fact_economic_observation.sql` parses Bronze's
untouched raw JSON payload in place (DuckDB's `json_each`/`json_extract` over
`decode(payload)`; the payload is stored as `BLOB`, and DuckDB's `BLOB::VARCHAR`
cast does *not* UTF-8 decode it — `decode()` does) and conforms it to the
canonical shape in `data-model.md`. `seeds/seed_dataset_indicator_map.csv` is
what makes this source-agnostic: it routes a connector's raw `dataset_id` to
a canonical `indicator_id`/`geo_code`, so a second source conforms by adding a
mapping row and a parsing branch, not by changing the table's shape.

**Gold** — `models/gold/fact_economic_kpi.sql` computes month-over-month and
year-over-year % change exactly once (FR-MODEL-003), reading only from the
Silver model above; no dashboard or API handler is permitted to recompute this
logic itself.

**Time fields (FR-MODEL-002)** — `period`/`period_start`/`period_end` are
computed once in the Silver model from the source's own date, never derived
again downstream; `vintage_date` is FRED's `realtime_start` (the date a
revision became the known value — standard ALFRED/FRED vintage semantics);
`retrieved_at` is copied from Bronze's own `retrieved_at`; `processed_at` is
the dbt run's own `run_started_at`, distinct from `retrieved_at` by
construction; `published_at` is left `NULL` for FRED rather than faked as a
copy of `vintage_date` — FRED's per-observation JSON does not expose a
publication timestamp distinct from it. A singular dbt test
(`tests/assert_fact_economic_observation_time_fields_distinct.sql`) fails the
build if `period_start` ever equals `period_end`, or if `processed_at`
precedes `retrieved_at` — either would mean two of these fields got aliased
together instead of independently populated.

**Honest scope limits**: only FRED feeds this today — Eurostat doesn't exist
yet (EPIC-14). Nothing invokes `dbt build` automatically; it's a manual step
(`src/transform/dbt_project/README.md`) until EPIC-07 (Dagster) schedules it.
Proven against real data: a synthetic FRED payload run through the actual
`BronzeWriter` into a real Bronze row, then `dbt build` end-to-end, including
a second, later "revision" of the same period to confirm `vintage_date`
keeps both rows distinct in Silver while Gold's KPI model correctly picks the
latest vintage per period — not just written and assumed correct.

### 2e. Dagster orchestration (`pipelines/dagster_project/`, EPIC-07)

Three assets wire the existing modules into one scheduled pipeline, in
dependency order — this module contains no fetch/storage/transform logic of
its own, per its module boundary above:

| Asset | Calls | Notes |
|---|---|---|
| `fred_cpi_raw` | `FREDConnector.run_ingestion` (via `FREDIngestionResource`) | Has a Dagster-level `RetryPolicy` (2 retries, exponential backoff) layered *above* the connector's own per-HTTP-call retry — one covers a single transient response, the other covers the whole materialization failing for any reason. Re-running is safe: raw storage is content-addressed and `ingestion_run` records every attempt regardless (US-02-005). |
| `fred_cpi_bronze` | `BronzeWriter.write` (via `BronzeResource`) | Depends on `fred_cpi_raw`'s output (object key, checksum, retrieved-at). |
| `silver_gold_conformance` | `dbt build` (subprocess, same invocation as `scripts/verify_epic05_acceptance.py`) | Depends on `fred_cpi_bronze`. This is what makes `dbt build` automatic instead of the manual step `transform/dbt_project/README.md` describes (EPIC-05's own documented gap). |

**Schedule** (`fred_cpi_daily_schedule`, `schedules.py`): a daily cron
targeting a job that runs all three assets in order. **Defaults to
`STOPPED`** — it would fetch from a real external API with a real credential
on every fire, which must not start just because `Definitions` loaded; an
operator enables it deliberately from the Dagster UI. The cron cadence is
illustrative (daily, not release-calendar-aware) — FRED's own
`freshness_slo` is "typically mid-month," and a daily poll is deliberately
over-frequent rather than under, since a no-op re-fetch of unchanged data is
cheap (content-addressed raw storage, idempotent Bronze write).

**Run visibility** (FR-OPS-001) comes from Dagster's own UI (`dagster dev`)
once these `Definitions` are loaded — status, duration, and a failure's
stack trace/logs are visible per run, satisfying the requirement for the
orchestrated pipeline specifically. A dedicated cross-cutting operator
dashboard (Grafana, EPIC-08) is still separate, not built.

**Honest scope limit**: US-07-001's acceptance criterion is "≥95% unattended
success, measured over ≥3 consecutive days" (NFR-AVAIL-002) — that is a
measurement of real elapsed operation, not something a build or test run can
produce. What's proven here is the mechanism: `tests/unit/test_dagster_pipeline.py`
materializes the fetch→Bronze chain end-to-end against fake resources (no
live network/S3), and CI's `dagster-pipeline` job runs `dagster definitions
validate` to catch a structural wiring mistake (a bad dependency, an
unloadable resource) before merge. The 3-day success-rate metric itself is
measured once an operator turns the schedule on.

A `from __future__ import annotations` import is deliberately absent from
`assets.py` (unlike every other module in this repo): Dagster's `@asset`
decorator validates the `context` parameter's type by identity against
`AssetExecutionContext`, and PEP 563's postponed evaluation breaks that
check — confirmed empirically while building this, not a style choice.

## 3. Retry / backoff algorithm (implements FR-ING-001 etc.)

```python
# Pseudocode — the authoritative behavioral spec is FR-ING-001 in ../requirements/FRD.md
MAX_RETRIES = 3
BASE_DELAY_SECONDS = 2

def fetch_with_retry(request_fn):
    for attempt in range(MAX_RETRIES + 1):
        try:
            response = request_fn()
            return response
        except TransientError as e:
            if attempt == MAX_RETRIES:
                raise IngestionFailed(cause=e, retries=attempt)
            delay = BASE_DELAY_SECONDS * (2 ** attempt)  # exponential backoff: 2s, 4s, 8s
            sleep(delay)
        except PermanentError as e:
            # Do not retry on 4xx (except 429) — these will not succeed on retry
            raise IngestionFailed(cause=e, retries=attempt)
```

- `TransientError`: network timeout, connection reset, 5xx, or 429 (rate limited — respects `Retry-After` if present, overriding the exponential schedule).
- `PermanentError`: 4xx other than 429 (e.g., malformed request, auth failure) — retrying would not help and wastes rate-limit budget.
- Every attempt (success or failure) is recorded on the `ingestion_run` row (`data-model.md`), satisfying NFR-AUDIT-001.

## 4. Idempotent write pattern (implements ARD §2.5)

Silver/Gold writes use `MERGE`/upsert semantics keyed on each table's documented primary key (`data-model.md`), never blind `INSERT`. Example (Iceberg SQL via Trino/DuckDB):

```sql
MERGE INTO silver.fact_market_ohlcv AS target
USING staging.fact_market_ohlcv_batch AS source
ON  target.source_id = source.source_id
AND target.instrument_id = source.instrument_id
AND target.interval = source.interval
AND target.observed_at = source.observed_at
WHEN MATCHED THEN UPDATE SET
    open = source.open, high = source.high, low = source.low,
    close = source.close, volume = source.volume,
    data_quality_status = source.data_quality_status
WHEN NOT MATCHED THEN INSERT (*)
```

Re-running the same ingestion run produces the same final state — no duplicates, satisfying FR-QUAL-003.

## 5. CI/CD pipeline design (GitHub Actions, Phase 1–2; add Argo CD in Phase 3 per ARD tool table)

1. **Lint & static checks**: Python (ruff/mypy-equivalent), SQL (dbt's own linting), YAML schema checks on data contracts.
2. **Secret scanning**: block any commit introducing a credential pattern (enforces NFR-SEC-003).
3. **Unit tests**: `tests/unit/` — connectors' parsing logic, validation rule logic, API request/response shape.
4. **Data contract validation**: every `contract.yaml` under `src/connectors/*` is schema-validated against the contract template in `../architecture/solution-design-document.md` §4.
5. **Integration tests**: `tests/integration/` — spin up the Phase 1 `docker-compose` stack, run a connector against a recorded/mocked response, assert Bronze/Silver/Gold rows land correctly and idempotently.
6. **Data quality suite**: `tests/data_quality/` — Great Expectations/Soda Core suites implementing FR-QUAL-001..009 against sample data.
7. **Build & (Phase 2+) publish** container images.
8. **Deploy** (Phase 2+): GitOps trigger via Argo CD watching the `infra/k8s` manifests.

A pull request cannot merge unless steps 1–6 pass — this is the mechanical enforcement of `../architecture/ARD.md` §2.6 (Data Quality as Code) and the TDD leg of `../methodology/edd-sdd-tdd.md`.

## 6. Phase 1 local stack (`infra/docker-compose.yml`, conceptual)

```yaml
services:
  postgres:        # metadata, job state, API cache — see data-model.md
  minio:            # raw object storage + Bronze/Silver/Gold Iceberg data
  dagster:          # orchestration — schedules, sensors, run visibility
  dbt:              # Bronze→Silver→Gold transforms (invoked by dagster, not standalone long-running)
  duckdb:           # embedded, invoked by API/dashboard processes — no separate service typically needed
  metabase:         # dashboards over Gold models
  api:              # FastAPI serving service (api-design.md)
  prometheus:       # metrics scraping
  grafana:          # dashboards over Prometheus (operational, distinct from Metabase's business dashboards)
```

No Kafka, no Kubernetes, no Keycloak, no Vault in this file for Phase 1 — see ADR-0002 and ADR-0004 for why, and `../roadmap/mvp-plan.md` for when each is added.

## 7. Error handling and DLQ implementation

A quarantined record (from `validation/`) is written to a `dlq` Iceberg table with columns: `event_id`, `original_payload_reference`, `failure_reason`, `quarantined_at`, `dataset_id`. A replay tool (invoked manually by the operator, or later by the agent's human-approved workflow) re-emits `raw_data.received` for a DLQ entry after the underlying issue is fixed — reprocessing is idempotent per §4 above, satisfying FR-OPS-003.

## 8. Relationship to other documents

- Module boundaries here enforce the separation-of-concerns principle in `../architecture/ARD.md` §2.3.
- The retry/backoff and idempotency algorithms here are the concrete implementation of FR-ING-001 and NFR-RTO-002 in `../requirements/`.
- The CI/CD steps here are how `../methodology/edd-sdd-tdd.md`'s TDD leg is mechanically enforced, not just followed by convention.
- The Phase 1 stack here must match `../roadmap/mvp-plan.md`'s Phase 1 tool list exactly — if they disagree, that's a defect (see `../roadmap/CLAUDE.md`).
