# CLAUDE.md — `docs/technical/`

## Purpose

The implementation-detail layer — the last stop before actual code. Four documents:

- **`technical-design-document.md`** — module/service boundaries, the ingestion retry/backoff algorithm, dead-letter-queue (DLQ) design, repository layout for the eventual codebase, the local `docker-compose` shape for the MVP, and the CI/CD pipeline design.
- **`data-model.md`** — the complete schema: every dimension and fact table (`dim_source`, `dim_dataset`, `dim_instrument`, `dim_indicator`, `fact_market_ohlcv`, `fact_economic_observation`, `fact_trade_observation`, `fact_crypto_market`, `ingestion_run`, `data_quality_result`), with columns, types, keys, and the Bronze/Silver/Gold layer each table belongs to.
- **`api-design.md`** — the serving API contract: every endpoint, method, request/response shape, auth requirement, and rate limit, in an OpenAPI-compatible style.
- **`event-schema.md`** — every event type in the platform's event-driven flow, its envelope fields, producer, consumer(s), and DLQ policy.

## This is where future code must match exactly

Once implementation begins, `src/`, `pipelines/`, and `infra/` (not yet created) must match what's documented here. If an implementer needs to deviate — a column needs a different type, an endpoint needs an extra parameter — **the correct order is: update the doc, then write the code**, in the same change. Code that silently diverges from `data-model.md` or `api-design.md` is a bug in the code, not evidence the doc was wrong (unless the doc is provably wrong — then fix the doc explicitly, with a comment on why).

## How this relates to the rest of `docs/`

- This folder is downstream of `../architecture/`: architecture says "Lakehouse, Bronze/Silver/Gold, Iceberg tables"; this folder says exactly which columns exist in which Silver table.
- This folder is downstream of `../requirements/FRD.md`: every `FR-ING-xxx` requirement should be satisfiable by something concretely specified here (an endpoint, a table, an event).
- Data types and units used here (e.g., `decimal(20,8)` for prices, UTC timestamps) must be consistent with `../requirements/NFR.md` precision/latency targets and `../data-sources/catalog.md` source semantics (e.g., a source's native currency/unit).

## Current status

- **This folder:** Stable — data model, API, event schema, and TDD complete.
- No code implements these yet. `src/` lands in EPIC-01; this folder is what it must match.

**Live project state is in `/STATUS.md`, not here** — it records what is done, in
progress, and next. Do not duplicate that state into this file; it will drift.
