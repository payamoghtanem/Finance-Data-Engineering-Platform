# Architecture Reference & Decisions Document (ARD)

**What this document answers:** what structural patterns and non-negotiable principles govern this system, and why?
**How it differs from its neighbors:** this is principles and patterns, at the level that should survive almost any single technology swap. `solution-design-document.md` shows the concrete instantiation; `decisions/*.md` records the individually consequential choices in full.

## 1. Mental model

Every dataset in this platform moves through the same pipeline shape:

```
Source → Ingest → Raw Storage → Validate → Transform → Serve → Observe & Govern
```

No dataset skips a stage. A "quick" connector that writes straight into a serving table without passing through immutable raw storage and validation is an architecture violation, not a shortcut.

## 2. Non-negotiable architecture principles

These are repeated in the root `CLAUDE.md` because they must be visible to anyone — human or agent — writing code anywhere in this system.

### 2.1 Data provenance

Every record must be traceable to: source, retrieval timestamp, API/file version, the exact request made, and the code version that processed it. Without this, "why does this number look different from last week" has no answer.

### 2.2 Immutable raw data

Store the original API response or downloaded file exactly as received — headers, URL, retrieval time, checksum included. If a transformation turns out to be wrong, the fix is to reprocess from raw, never to patch a downstream table by hand.

### 2.3 Separation of concerns

Ingestion, raw storage, validation, transformation/modeling, serving, observability, and any user interface are separate services or modules. A single script that does "fetch, clean, and write to the dashboard table" in one file is exactly the anti-pattern this principle forbids — it cannot be tested, retried, or reasoned about in isolation.

### 2.4 Data contracts

Before a pipeline runs against a dataset, its format, meaning, keys, units, update cadence, valid ranges, and schema-change policy must be written down and versioned (see the sample in `../technical/data-model.md` and the data-quality rules in `../requirements/NFR.md`). A pipeline built against an undocumented, implicit schema is technical debt from the moment it's written.

### 2.5 Idempotency

Re-running a job must never create duplicate records or an inconsistent result. Example primary key for a market bar: `source + instrument_id + interval + observed_at`. This is what makes retries and backfills safe.

### 2.6 Data quality as code

Validation is not a manual or eyeball step — it is versioned test code that runs in CI and inside the pipeline itself, blocking bad data from advancing to the next layer (see `../requirements/NFR.md` for the required control types: schema validation, completeness, uniqueness, freshness, range, consistency, referential integrity, reconciliation, outlier detection, semantic validation).

### 2.7 Secure by default

No API key, password, or token is ever committed to Git, baked into a Docker image, hard-coded in a notebook, or placed in a shared/general config file. Local development uses a git-ignored `.env` file only; later phases use a secrets manager (HashiCorp Vault or a cloud provider's secret manager) — see ADR-0004.

### 2.8 Avoid vendor lock-in

Store data in open formats (Parquet columnar files, Apache Iceberg table format) so the compute engine or cloud provider can change later without a full data migration. This is what makes the "start on a laptop, move to cloud later" promise credible rather than aspirational.

## 3. Layered reference architecture

```
[Official / Licensed Data Sources]
          |
          v
[Source Connectors / Ingestion Workers]   REST API | SDMX | CSV | XBRL | WebSocket (where permitted)
          |
          v
[Event Notification]                       (in-process in MVP; a real broker from Phase 2 — see ADR-0002)
          |
          +----------------------+
          |                      |
          v                      v
[Raw Object Storage]       [Validation / Quarantine]
 MinIO (local) / S3-compatible (cloud)     schema + quality failures → DLQ
          |
          v
[Bronze Tables]  Iceberg + Parquet — parsed raw, minimally changed
          |
          v
[Transform / Standardize]   Python + dbt Core (+ Spark/Flink only when volume genuinely requires it)
          |
          v
[Silver Tables]  Canonical, conformed model — shared units, codes, keys across sources
          |
          v
[Gold Tables / Data Products / KPIs]
          |
     +----+-----+-----------+
     |          |           |
     v          v           v
 [Trino/DuckDB] [PostgreSQL] [API / Dashboard]
  SQL analytics   serving       FastAPI / Metabase
          |
          v
[Catalog + Lineage + Quality + Observability]
 Data dictionary (Git-based in MVP; OpenMetadata later) + Great Expectations/Soda + OpenTelemetry + Prometheus + Grafana
```

Full column-level detail for every layer: `../technical/data-model.md`. Full endpoint detail for the serving layer: `../technical/api-design.md`.

## 4. Architecture patterns in use, and why

### 4.1 Event-Driven Architecture (EDD as an architecture pattern, not just a dev methodology)

A producer publishes an event; independently deployable consumers react. This decouples "a new file arrived" from "process the file," which in turn decouples "processing finished" from "tell the dashboard to refresh." It's the natural fit for financial/economic data because that data is inherently a stream of time-stamped events, and because pipeline failures/delays need to be *announced*, not just logged. Full event catalog: `../technical/event-schema.md`; methodology-level reasoning: `../methodology/edd-sdd-tdd.md`.

**MVP-phase note:** the event *shape* (schemas, event types) is defined from day one; the event *transport* is an in-process function call or a lightweight local queue in Phase 1, and only becomes Apache Kafka in Phase 2+ once there are enough independent connectors and consumers to justify a real broker (see ADR-0002). Designing the event contracts early and swapping only the transport later is what avoids a rewrite.

### 4.2 Medallion Architecture (Bronze / Silver / Gold)

See `../00-glossary.md` for the definition. Chosen because it gives an explicit, auditable answer to "which version of this data can I trust for what" — Bronze for forensic/reprocessing needs, Silver for cross-source analysis, Gold for fast, standardized consumption — rather than one undifferentiated "the tables" layer where trust level is implicit and inconsistent.

### 4.3 Lakehouse, not pure Data Warehouse, not full Data Mesh

- **Why not a pure Data Warehouse (e.g., committing to Snowflake/BigQuery from day one):** warehouses are excellent for structured, governed, Gold-layer serving, but expensive and rigid for holding large volumes of raw/semi-structured historical data the platform must keep forever for reprocessing. See ADR-0001 for the full comparison.
- **Why not a full Data Mesh:** Data Mesh is an *organizational* model (domain teams independently owning "data products," backed by shared self-service platform infrastructure) more than a technology choice. It pays off when multiple independent teams each own a data domain. For a single owner or small team, a **Central Lakehouse with clear per-domain ownership boundaries** captures the useful parts of Data Mesh thinking (explicit ownership, data-as-product discipline, documented contracts) without the organizational overhead of a mesh with no separate teams to mesh together. Revisit this decision if/when multiple independent teams actually join the project — see ADR-0001.
- **Why Lakehouse wins for this project specifically:** object storage (MinIO locally, S3-compatible in the cloud) is cheap and suits large historical volumes; Parquet is a columnar format suited to analytics; Apache Iceberg adds table semantics — snapshots, schema evolution, time travel — on top of that cheap storage; Trino or DuckDB can run SQL analytics directly against Iceberg without first loading everything into an expensive proprietary warehouse; PostgreSQL is reserved for metadata, users, job state, watchlists, and low-latency API reads — never for the full historical OHLCV volume.

## 5. Tool-selection table (why, and explicitly why not)

| Need | Chosen tool | Why | When NOT to reach for it |
|---|---|---|---|
| Containerization | Docker | Reproducible local runs and CI | Not a substitute for orchestration at real scale |
| Cloud-native orchestration | Kubernetes | Elastic scaling, self-healing, a standard deployment target | Unnecessary complexity for a single-operator MVP — defer to Phase 3 |
| Ingestion event broker | Apache Kafka | Pub/sub, replay, independent scaling of producers/consumers | Not needed to poll a handful of daily APIs — defer until there are enough independent connectors/consumers to justify it (ADR-0002) |
| Workflow orchestration | Dagster (or Apache Airflow) | Scheduling, dependency graphs, retries, backfills, run visibility | Kafka is not a substitute for this — they solve different problems |
| Lightweight processing | Python + Polars/Pandas | Fast connector/transform development | Not suited to very large or continuous streaming volumes |
| Heavy/streaming processing | Apache Spark or Apache Flink | Distributed batch or stream processing | Adds operational cost and complexity from day one — introduce only when volume actually requires it |
| Analytical transforms | dbt Core | Versioned, tested, documented SQL transforms | Not ideal for complex JSON/XBRL parsing — use Python for that |
| Data lake storage | MinIO (dev) / S3-compatible (cloud) | Standard object-storage API; separates compute from storage | Insufficient alone for low-latency query serving |
| Table format | Apache Iceberg + Parquet | Snapshots, schema evolution, multi-engine support | Overkill for a genuinely tiny project — plain CSV/SQLite may suffice for a toy prototype |
| SQL federation / analytics engine | Trino (cloud/team) or DuckDB (laptop/MVP) | SQL directly over Iceberg/Parquet without a separate warehouse | DuckDB alone doesn't serve concurrent multi-user production load — Trino for that |
| Serving database | PostgreSQL | Metadata, users, job state, fast API reads | Never for full historical OHLCV volume |
| Data quality | Great Expectations or Soda Core | Versioned, CI-executed quality tests | Does not replace understanding the economic/financial meaning of the data — tests check the rules a human still has to define correctly |
| Data catalog | Git-based data dictionary (MVP) → OpenMetadata (Phase 2+) | Ownership, lineage, discovery | Full OpenMetadata is unnecessary operational overhead for a solo MVP |
| API | FastAPI | OpenAPI-native, fast to develop, strong Python ecosystem | Never expose it publicly without auth and rate limiting |
| BI / dashboards | Metabase or Apache Superset | Fast, user-friendly dashboards over Gold models | Must query Gold, standardized models — never bypass modeling and hit Bronze/Silver directly |
| Identity & access | Keycloak + RBAC (Phase 2+) | Standard identity, roles, token-based access | Likely overkill for a single local user in Phase 1 |
| Secrets | HashiCorp Vault or a cloud secrets manager (Phase 2+) | Removes secrets from code, enables rotation | `.env` files are fine, but Phase-1-only, and must stay out of Git |
| Observability | OpenTelemetry + Prometheus + Grafana | Standard traces, metrics, logs, alerting | Log files alone are not sufficient for production operation |
| CI/CD & delivery | GitHub Actions (+ Argo CD in Phase 3) | Auditable, automated build/test/deploy | Argo CD/GitOps is unnecessary for a simple local environment |
| Infrastructure as Code | OpenTofu or Terraform (Phase 3) | Repeatable, reviewed infrastructure changes | Never hand-edit production cloud infrastructure directly |

## 6. Relationship to requirements and technical documents

- `../requirements/FRD.md` and `../requirements/NFR.md` state *what* the system must do and *how well*; nothing there may silently assume an architecture choice not documented here.
- `../technical/data-model.md`, `../technical/api-design.md`, and `../technical/event-schema.md` go one level more concrete than this document — schema DDL, endpoint contracts, and event payloads respectively.
- Any decision consequential and hard-to-reverse enough to need a full argument (with rejected alternatives) is recorded as an ADR in `decisions/`, not inline here.
