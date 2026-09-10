# User Stories

**What this document answers:** what is the next individually assignable unit of work, who is it for, and how do we know it is done?
**How it differs from its neighbors:** `epics.md` is the coarse breakdown and ordering; this file is the assignable detail. The binding behavioural spec is always the `FR-xxx` in `../requirements/FRD.md` — a story's acceptance criteria summarise that FR, they do not replace it.

Story ID format: `US-<epic number>-<sequence>`. Personas (Ana, Dev, Rae, Omar) are
defined in `../business/PRD.md` §2; "Operator" is the person running the platform.

Phase 1 epics are decomposed in full below because they are next. Phase 2–3 epics
are intentionally left at epic granularity until their phase is closer — decomposing
them now would produce stories that are stale before anyone reads them.

---

## EPIC-01 — Repository & environment scaffolding

| ID | Story | Acceptance criteria | Source |
|---|---|---|---|
| US-01-001 | As an Operator, I want the `src/`/`pipelines/`/`infra/`/`tests/` tree created exactly as specified, so future code has an unambiguous home. | Tree matches `../technical/technical-design-document.md` §1 exactly; each package has `__init__.py`; CI asserts the layout. | NFR-MAINT-001 |
| US-01-002 | As a Developer, I want dependency and tooling config committed, so every contributor and agent gets an identical environment. | `pyproject.toml` pins Python + deps; lint/format/type-check all run from one command; documented in `CONTRIBUTING.md`. | NFR-MAINT-001 |
| US-01-003 | As an Operator, I want secret scanning and a `.gitignore` before any credential exists, so no key can ever reach history. | `.env` ignored; pre-commit secret scan active; CI fails on detected secret; `.env.example` committed with placeholder values only. | NFR-SEC-003 |
| US-01-004 | As an Operator, I want the Phase 1 `docker-compose.yml` to stand up the full local stack. | All nine services from `../roadmap/mvp-plan.md` §2 start; healthchecks pass; documented teardown. | NFR-COST-001 |

## EPIC-02 — FRED connector (reference implementation)

| ID | Story | Acceptance criteria | Source |
|---|---|---|---|
| US-02-001 | As an Operator, I want a registered `dim_source` row and data contract for FRED before any fetch runs. | `contract.yaml` validates against the §4 schema; `dim_source` row has `license_url`, `terms_version`, `redistribution_allowed`, `trust_tier`; CI blocks a connector with no contract. | FR-ING-006 |
| US-02-002 | As Ana, I want CPI (`CPIAUCSL`) fetched on a daily schedule so I can chart inflation without manual downloads. | Scheduled trigger fires; response persisted to Raw **before** parsing, with SHA-256 + `retrieved_at`. | FR-ING-001 |
| US-02-003 | As an Operator, I want transient failures retried with exponential backoff, so a blip does not fail a run. | 5xx/timeout/reset retried ≤ 3 times with backoff per TDD §3; 4xx **not** retried; final failure marks the run failed and emits an event. | FR-ING-001 |
| US-02-004 | As an Operator, I want re-running a day's job to be a no-op, so backfills can't double-count. | Running the same day twice yields identical row counts in `fact_economic_observation`; upsert key per contract; verified by an automated test. | FR-ING-001 |
| US-02-005 | As an Operator, I want every run recorded in `ingestion_run`, so I can audit what happened. | Status, duration, connector version, request hash written for every run including failures. | FR-OPS-001 |
| US-02-006 | As Rae, I want series metadata changes tracked over time, so revisions are diffable. | A changed series definition produces a new vintage row rather than overwriting; prior vintage remains queryable. | FR-ING-001 |

## EPIC-03 — Raw & Bronze storage with provenance

| ID | Story | Acceptance criteria | Source |
|---|---|---|---|
| US-03-001 | As an Auditor, I want every raw payload stored immutably with its checksum. | Object written once to MinIO, write-once path convention, SHA-256 stored alongside; mutation attempt fails. | NFR-AUDIT-001 |
| US-03-002 | As an Auditor, I want any Bronze row traceable to the exact raw file that produced it. | Bronze carries `raw_object_key`, `source_id`, `retrieved_at`, `code_version`; lineage test proves round-trip. | NFR-GOV-002 |
| US-03-003 | As an Operator, I want reprocessing to read from Raw, never re-fetch from the source. | A full Bronze rebuild runs with the network disabled. | ARD §2.2 |

## EPIC-04 — Data-quality rule engine

| ID | Story | Acceptance criteria | Source |
|---|---|---|---|
| US-04-001 | As an Operator, I want structurally invalid records quarantined, never coerced. | Type/schema mismatch → quarantine + `raw_data.quarantined` event; nothing reaches Silver. | FR-QUAL-001 |
| US-04-002 | As Ana, I want missing expected observations flagged, not shown as zero. | Gap in a defined cadence raises a completeness failure; aggregates exclude rather than zero-fill. | FR-QUAL-002 |
| US-04-003 | As an Operator, I want duplicates rejected or upserted per contract, never double-counted. | Contract-declared PK enforced; duplicate handling matches declared behaviour. | FR-QUAL-003 |
| US-04-004 | As an Operator, I want a freshness breach to raise an alert. | Latest timestamp vs contract SLO evaluated each run; breach emits alert within NFR-FRESH-003. | FR-QUAL-004, FR-OPS-002 |
| US-04-005 | As an Analyst, I want impossible values rejected. | Negative price/volume rejected; OHLCV satisfies `low ≤ open,close ≤ high`. | FR-QUAL-005 |
| US-04-006 | As an Operator, I want facts with unresolvable foreign keys rejected. | Fact whose `instrument_id`/`indicator_id` has no dimension row fails validation. | FR-QUAL-006 |
| US-04-007 | As an Auditor, I want periodic reconciliation against the source. | Sampled counts/checksums compared on a schedule; mismatch raises an incident. | FR-QUAL-007 |
| US-04-008 | As an Analyst, I want extreme moves flagged for review, not silently dropped. | Outlier flagged with a status distinguishing `flagged` from `confirmed_invalid`; row still stored. | FR-QUAL-008 |
| US-04-009 | As Ana, I want indicators missing unit/base/adjustment metadata blocked from Gold. | Semantic validation fails a CPI series lacking base year or seasonal-adjustment flag. | FR-QUAL-009 |

## EPIC-05 — Canonical Silver/Gold modelling

| ID | Story | Acceptance criteria | Source |
|---|---|---|---|
| US-05-001 | As Ana, I want FRED and Eurostat rows queryable through one shape. | Both populate `fact_economic_observation` canonical fields; a single query returns both. | FR-MODEL-001 |
| US-05-002 | As Rae, I want the six timestamp types kept distinct, so I can avoid look-ahead bias. | `observed_at`/`period_start`/`period_end`, `published_at`, `retrieved_at`, `processed_at`, `vintage_date` all present and separately populated; a test asserts none is derived from another. | FR-MODEL-002 |
| US-05-003 | As Ana, I want KPI logic defined once in dbt, so two charts can't disagree. | YoY/MoM defined in a single versioned dbt model; no dashboard-level recomputation; lineage documented. | FR-MODEL-003 |

## EPIC-06 / EPIC-09 — Events, DLQ and replay

| ID | Story | Acceptance criteria | Source |
|---|---|---|---|
| US-06-001 | As an Operator, I want each stage to advance only on a validated event. | Silver consumes `raw_data.validated` only; a bare "script ran" signal cannot advance the flow. | ADR-0002 |
| US-09-001 | As an Operator, I want every failure routed to a DLQ — never silently dropped. | All nine event types have a declared DLQ policy; a forced failure lands in DLQ with full context. | FR-OPS-003 |
| US-09-002 | As an Operator, I want to replay from the DLQ without manual data surgery. | Replay is one command, idempotent, and produces no duplicates. | FR-OPS-003 |

## EPIC-07 / EPIC-08 / EPIC-10 — Orchestration, observability, dashboard

| ID | Story | Acceptance criteria | Source |
|---|---|---|---|
| US-07-001 | As an Operator, I want schedules and sensors defined in Dagster with ≥95% unattended success. | Measured over ≥ 3 consecutive days per the Phase 1 exit criteria. | NFR-AVAIL-002 |
| US-08-001 | As an Operator, I want every run visible with status, duration, and a failure link. | Dashboard lists runs; failures link to the raw request/response and error. | FR-OPS-001 |
| US-08-002 | As an Operator, I want alerts on freshness breach and repeated failure. | Alert fires on SLO breach or ≥2 consecutive connector failures, within < 1 hour. | FR-OPS-002 |
| US-10-001 | As Ana, I want a dashboard reading Gold only, returning in under 5 seconds. | Metabase queries Gold (never Bronze/Silver); p50 < 5s. | NFR-PERF-001 |

---

## Phase 2–3

Decompose `EPIC-11` … `EPIC-24` into stories when their phase is entered, per
`../roadmap/mvp-plan.md`. Do not decompose early — the design will have moved.
