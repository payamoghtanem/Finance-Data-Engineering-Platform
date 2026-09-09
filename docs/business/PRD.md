# Product Requirements Document (PRD)

**What this document answers:** given the "why" in `BRD.md`, what can a user actually do with this product, and in what priority order do we build it?
**How it differs from its neighbors:** this describes user-visible capability and experience. It does not specify database schemas (`../technical/data-model.md`) or exact system behavior per scenario (`../requirements/FRD.md`) — it specifies what the *user* sees and can do.

## 1. Personas

| Persona | Goal | Primary surface |
|---|---|---|
| **Analyst (Ana)** | Explore and chart macro/market/crypto indicators without writing ingestion code | Dashboard (Metabase/Superset) |
| **Developer (Dev)** | Build an application or notebook against a stable, documented API | REST API (`../technical/api-design.md`) |
| **Researcher (Rae)** | Reproduce a historical analysis exactly, including the data vintage that existed at the time | API with vintage/point-in-time parameters |
| **Platform Operator (Omar)** | Keep pipelines healthy, investigate failures, add new sources | Orchestrator UI (Dagster/Airflow), observability dashboards (Grafana) |
| **Scoped AI Agent** | Help Ana/Dev/Rae find the right dataset, draft a query, or explain a quality issue | Agent chat surface, constrained per `../ai-agent/agentic-ai-design.md` |

## 2. User journeys

### 2.1 Ana wants Eurozone inflation vs. US inflation, aligned

1. Ana searches the data catalog for "inflation" and finds two Gold-layer indicators: `hicp_eurozone_yoy` and `cpi_us_yoy`, each showing source, unit, seasonal-adjustment status, and last-updated timestamp.
2. Ana adds both to a dashboard chart; the platform aligns them on `period_end` automatically because both conform to the canonical `fact_economic_observation` schema.
3. Ana exports the chart's underlying data as CSV, with full source attribution embedded.

### 2.2 Dev wants BTC daily OHLCV for the last 90 days via API

1. Dev reads the OpenAPI spec at `../technical/api-design.md`, authenticates with an API key, and calls `GET /v1/instruments/crypto/BTC/ohlcv?interval=1d&limit=90`.
2. The response includes `observed_at`, OHLCV fields, `source_id`, and a `data_quality_status` flag per record.
3. If the source was rate-limited that day, Dev sees an explicit gap marker rather than a silently interpolated or missing value.

### 2.3 Rae wants exactly what "GDP growth" looked like on a specific past date (point-in-time)

1. Rae calls the API with a `as_of` parameter (e.g., `as_of=2024-03-01`).
2. The platform returns the **vintage** of the GDP figure that was published as of that date — not today's revised figure — because `vintage_date` is tracked as a first-class field (see `../00-glossary.md` — Look-ahead Bias).

### 2.4 Omar investigates a failed ingestion run

1. Omar opens the orchestrator UI and sees the failed `ingestion_run` row with its error, retry count, and a link to the raw request/response that failed.
2. Omar checks the Grafana dashboard for the affected connector's recent freshness/latency trend.
3. Omar either fixes the connector and replays the run (idempotent — no duplicate records result) or, if the source itself is down, acknowledges the incident per the runbook.

### 2.5 Ana asks the AI agent "why does this dataset look wrong?"

1. Ana asks the agent about a suspicious spike in a chart.
2. The agent retrieves the relevant `data_quality_result` and `ingestion_run` records (read-only) and explains, e.g., "this data point failed the outlier-detection rule and is flagged, not confirmed" — citing its source and confidence, never asserting certainty it doesn't have.
3. If Ana asks the agent to "fix" or "remove" the data point, the agent explains it cannot take write actions and describes the human-operated path to do so (see `../ai-agent/agentic-ai-design.md`).

## 3. Product capabilities (prioritized, MoSCoW)

### Must have (MVP)

- **Dataset catalog & search** — browse/search datasets by domain, source, and freshness; each entry shows trust tier, license, and last-updated time.
- **Canonical query API** — a documented, versioned REST API over Gold-layer tables (`../technical/api-design.md`).
- **Point-in-time / vintage queries** for economic indicators.
- **Dashboards** for the MVP's priority domains (macro, crypto) built on standardized Gold models.
- **Data-quality visibility** — every dataset/record exposes a pass/fail/flagged quality status, not just a value.
- **Operational visibility** — an operator can see job status, freshness, and failures without reading logs by hand.

### Should have (Team-ready phase)

- **Alerting** on freshness SLO breach or repeated ingestion failure.
- **Role-based access control** for API keys/dashboard users.
- **Lineage view** — trace a Gold value back through Silver/Bronze to the exact raw file.
- **Scoped AI agent** for dataset discovery, query drafting, and quality explanation (read-only).

### Could have (Cloud-native phase)

- **Self-service dataset onboarding** for a new domain owner to propose a new connector against the platform's contract template.
- **Multi-region serving** for latency-sensitive dashboard use.
- **Cost/usage dashboard** per API consumer.

### Won't have (any phase, by design)

- Trade execution or brokerage integration.
- Personalized investment advice generation.
- Unrestricted/autonomous AI agent write access.
- Real-time (sub-minute) equity ticks without an explicit, paid, licensed data agreement.

## 4. Product-level acceptance criteria (representative)

- **AC-P1**: A user can find any Gold-layer dataset from the catalog search in under 3 clicks/queries, and see its trust tier and license before using it.
- **AC-P2**: A point-in-time query for any economic indicator returns the vintage that existed as of the requested date, verified against at least one known historical revision case (e.g., a documented GDP restatement).
- **AC-P3**: Every dashboard chart cites its underlying source(s) and last-updated timestamp visibly, not only on hover.
- **AC-P4**: An ingestion failure becomes visible to the operator (dashboard/alert) within the latency target defined in `../requirements/NFR.md`, without the operator needing to read raw logs.
- **AC-P5**: The AI agent never returns a data value without stating its source and timestamp, and never performs a write action regardless of how it is asked (verified by the adversarial-agent test suite referenced in `../ai-agent/agentic-ai-design.md`).

## 5. Traceability

Every capability above maps to functional requirements in `../requirements/FRD.md` and to at least one BRD goal in `BRD.md` §4 (Value proposition). See `../requirements/traceability-matrix.md` for the full mapping table — do not restate that mapping here.
