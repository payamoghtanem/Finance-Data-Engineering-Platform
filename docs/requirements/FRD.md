# Functional Requirements Document (FRD)

**What this document answers:** exactly what must the system do, in each scenario, for each data domain?
**How it differs from its neighbors:** requirements here are behavioral and testable ("the system must retry 3 times with exponential backoff"), never architectural ("the system uses Kafka" belongs in `../architecture/`) and never implementation-level ("using Python's `tenacity` library" belongs in `../technical/technical-design-document.md`).

Requirement IDs follow the pattern `FR-<AREA>-<NNN>`. Areas: `ING` (ingestion), `QUAL` (data quality), `MODEL` (transformation/modeling), `API` (serving), `AGENT` (AI agent behavior — cross-referenced with `../ai-agent/agentic-ai-design.md`), `OPS` (operations/observability).

## 1. Ingestion requirements

### FR-ING-001: Ingest CPI from FRED

- **Given** a scheduled daily trigger for the `fred_cpi` connector,
  **When** the connector runs,
  **Then** the system must fetch the configured FRED series (e.g., `CPIAUCSL`) via the FRED API.
- The raw API response must be stored in Raw Object Storage with a SHA-256 checksum and retrieval timestamp before any parsing occurs.
- If the API returns a transient error (5xx, timeout, connection reset), the system must retry up to 3 times with exponential backoff before marking the run failed.
- If the response violates the registered data contract or schema, the record must **not** advance to Bronze/Silver — it must be quarantined and routed to the dead-letter queue (DLQ).
- Every run must produce an `ingestion_run` record (status, duration, connector version, request hash) and be visible on the operational dashboard.
- The pipeline must be idempotent: re-running the same day's job must not create duplicate `fact_economic_observation` rows.
- Any change to the series definition or its metadata must be tracked and diffable over time (vintage awareness).

### FR-ING-002: Ingest global development indicators from World Bank

- The system must fetch specified indicators from the World Bank Indicators API on a scheduled cadence (no API key required, per `../data-sources/catalog.md`).
- The system must respect the source's pagination and must not assume a single response contains the full result set.
- Same raw-storage, retry, contract-validation, idempotency, and run-recording behavior as FR-ING-001 applies.

### FR-ING-003: Ingest Eurozone statistics from Eurostat (SDMX)

- The system must fetch specified datasets via Eurostat's SDMX 2.1/3.0 API.
- The system must correctly resolve SDMX dimension codes (geography, unit, seasonal adjustment, frequency) into the canonical Silver-layer fields — an unresolved/unknown code must fail validation rather than being silently dropped or guessed.
- Same raw-storage, retry, contract-validation, idempotency, and run-recording behavior as FR-ING-001 applies.

### FR-ING-004: Ingest company filings from SEC EDGAR

- The system must fetch filings/XBRL financial statement data via `data.sec.gov`, respecting SEC's fair-access request-rate policy (including a compliant User-Agent identifying the platform, per SEC's published requirements).
- The system must preserve the filing's accession number, form type, and filing date as part of provenance.
- Same raw-storage, retry, contract-validation, idempotency, and run-recording behavior as FR-ING-001 applies.

### FR-ING-005: Ingest crypto market data from CoinGecko

- The system must fetch price, volume, market cap, and supply data via CoinGecko's free/demo tier.
- The system must track and respect the demo tier's rate limits and its 365-day historical data ceiling, exposing a data-availability flag to consumers rather than silently truncating history.
- Same raw-storage, retry, contract-validation, idempotency, and run-recording behavior as FR-ING-001 applies.

### FR-ING-006: New connector onboarding

- Any new data source connector must have, before its first production run: a registered `dim_source` entry (license, trust tier), a data contract (`../architecture/solution-design-document.md` §4 format), and passing contract/unit tests — enforced by CI, not by reviewer memory.

## 2. Data quality requirements

### FR-QUAL-001: Schema validation

The system must reject (quarantine, not silently coerce) any raw record whose structure or types do not match the registered contract (e.g., a price field containing non-numeric text).

### FR-QUAL-002: Completeness

For any actively tracked instrument/indicator with a defined cadence, the system must detect and flag a missing expected record (e.g., no trading-day OHLCV row) rather than presenting a gap as "zero" or omitting it silently from aggregates.

### FR-QUAL-003: Uniqueness

The system must enforce the primary key defined in each dataset's contract (e.g., `source + instrument_id + interval + observed_at` for OHLCV) and reject/upsert duplicates according to the contract's declared behavior — never silently double-count.

### FR-QUAL-004: Freshness

The system must compare each dataset's latest available timestamp against its contract's freshness SLO and raise an alert (see FR-OPS-002) when it is breached.

### FR-QUAL-005: Range and consistency

The system must reject records with impossible values (e.g., negative price or volume) and enforce cross-field consistency rules (e.g., `low ≤ open ≤ high`, `low ≤ close ≤ high` for OHLCV).

### FR-QUAL-006: Referential integrity

The system must reject any fact record whose foreign key (e.g., `instrument_id`) does not resolve to an existing dimension row.

### FR-QUAL-007: Reconciliation

The system must periodically compare record counts and/or checksums for a sample of ingested datasets against the source, to detect silent data loss or unexpected modification.

### FR-QUAL-008: Outlier detection

The system must flag (not silently accept or silently drop) statistically extreme changes (e.g., a >1000% single-interval price move) for human or agent review, distinguishing "flagged" from "confirmed invalid."

### FR-QUAL-009: Semantic validation

For economic indicators, the system must validate that unit, index base, and seasonal-adjustment metadata are present and internally consistent before a value is published to Gold — a CPI series missing its base year or adjustment flag must not reach a dashboard.

## 3. Transformation / modeling requirements

### FR-MODEL-001: Canonical conformance

Every Silver-layer record must populate the shared canonical fields for its domain (see `../technical/data-model.md`) regardless of source — a Eurostat HICP row and a FRED CPI row must both be queryable through the same `fact_economic_observation` shape.

### FR-MODEL-002: Time field discipline

Every fact record must distinguish `observed_at`/`period_start`/`period_end`, `published_at`, `retrieved_at`, `processed_at`, and (where applicable) `vintage_date` as separate fields — collapsing these into a single "date" field is a defect, not a simplification.

### FR-MODEL-003: Gold KPI definitions are versioned

Any KPI computation logic (e.g., "year-over-year % change") must be defined once, in version-controlled transformation code (dbt models), and never recomputed ad hoc per dashboard — this is what FR-P3 in the PRD (chart source consistency) depends on.

## 4. Serving / API requirements

### FR-API-001: Documented, versioned API

The system must expose Gold-layer data through a versioned (`/v1/...`), OpenAPI-documented REST API — see `../technical/api-design.md` for the full contract.

### FR-API-002: Point-in-time queries

For any indicator with tracked vintages, the API must support an `as_of` parameter that returns the vintage that existed as of the requested date, not the latest revision, unless the latest revision is explicitly requested.

### FR-API-003: Authentication and rate limiting

Every API endpoint beyond a minimal public health check must require an API key and enforce a rate limit; the system must never expose an unauthenticated, unlimited data endpoint (this directly enforces `../architecture/ARD.md` §2.7 at the API layer).

### FR-API-004: Quality status surfaced to consumers

Every API response returning a data value must include that value's data-quality status (e.g., `ok`, `flagged`, `estimated`) — never a bare number with no quality context.

## 5. AI agent requirements (cross-reference `../ai-agent/agentic-ai-design.md`)

### FR-AGENT-001: Read-only retrieval only

The agent's tools may only read from the catalog, data dictionary, runbooks, data contracts, and quality-test results. No tool available to the agent may write, delete, alter schema, or trigger a backfill.

### FR-AGENT-002: Mandatory attribution

Every agent response that cites a data value must include its source, timestamp, and any known quality flag or limitation.

### FR-AGENT-003: Escalation, not silent refusal or silent action

If a user asks the agent to perform a write-class action, the agent must explain that this requires human action and describe the correct human-operated path — it must neither silently ignore the request nor find a workaround tool to perform it anyway.

## 6. Operations requirements

### FR-OPS-001: Run visibility

Every ingestion, transformation, and validation run must be visible in the operator dashboard with status, duration, and (on failure) a link to the relevant raw request/response and error detail.

### FR-OPS-002: Alerting

A freshness SLO breach, a repeated ingestion failure (≥ 2 consecutive failures for the same connector), or a data-quality blocking-test failure must trigger an alert to the operator within the latency defined in `NFR.md`.

### FR-OPS-003: Safe replay

Any failed or quarantined run must be replayable from the DLQ without manual data surgery, and replay must be idempotent (see FR-ING-001).

## 7. Traceability

Every FR-xxx above must have a corresponding row in `traceability-matrix.md` linking it to a BRD/PRD goal. Do not add a requirement here without adding that row in the same change.
