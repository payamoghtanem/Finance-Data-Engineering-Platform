# Glossary

**What this document answers:** what does each recurring term in this repository mean, precisely, so every other document can use it without redefining it.
**How it differs from its neighbors:** every other document assumes these definitions; this is the only place they're defined.

Terms are grouped by theme. Each entry: **Term (alternate form)** — definition, and where it matters most.

## Data platform fundamentals

- **Data Architecture** — the discipline of documenting an organization's data assets, mapping how data flows through its systems, and producing a plan for managing that data (hardware, software, network, storage method, and logical access pattern). See `architecture/ARD.md`.
- **Data Platform** — the deployed substrate that realizes a data architecture: the repository and processing home for all of an organization's data.
- **Data Engineering** — designing and implementing scalable, efficient data architectures, and building/maintaining the pipelines that move and transform data through them.
- **Data Pipeline** — an automated sequence of steps that moves data from a source, through processing stages, to a destination.
- **Lakehouse** — an architecture combining a data lake's cheap, open, columnar object storage with a data warehouse's table semantics (ACID transactions, schema enforcement, time travel), via a table format such as Apache Iceberg.
- **Medallion Architecture (Bronze / Silver / Gold)** — a layered data-quality model: **Bronze** holds parsed raw data with minimal changes; **Silver** holds cleaned, standardized, conformed data across sources; **Gold** holds business-ready aggregates, KPIs, and data products. See `technical/data-model.md`.
- **Data Mesh** — an organizational model where domain-owning teams publish data as self-service "data products," backed by shared platform infrastructure for catalog, discovery, and observability. Contrasted with a **Central Lakehouse** (a single team/platform owns ingestion→serving with clear per-domain ownership) — this project uses the latter; see ADR-0001.
- **Data Product** — a dataset (or API) that is treated as a product: documented, owned, quality-tested, versioned, and discoverable — not just "a table that happens to exist."

## Provenance, time, and trust

- **Data Provenance** — the recorded chain of where a piece of data came from, when, via which API/version, and by which code version — enabling audit and reproduction.
- **Immutable Raw Data** — the original API response or downloaded file, stored unmodified, so any transformation can be redone from scratch if it was wrong.
- **Idempotency** — the property that re-running the same job produces the same result with no duplicates — critical for safe retries and backfills.
- **Look-ahead Bias** — an analytical error caused by using information that would not actually have been available at the historical point in time being analyzed (e.g., using a revised GDP figure in a "what did the market know on that date" analysis). Prevented by keeping `observed_at`, `published_at`, `retrieved_at`, and `vintage_date` distinct — see `technical/data-model.md`.
- **Vintage / Vintage Date** — the specific revision of a data point as it existed at a specific point in time; economic statistics are frequently revised, so "GDP for Q1" can have multiple vintages.
- **Trust Tier** — this project's classification of a data source's reliability, from *Official/Regulatory* (highest) through *Licensed Commercial*, *Reputable Media/Analytics*, down to *Community/Unofficial* (lowest, prototyping-only). See `data-sources/catalog.md`.
- **SSOT (Single Source of Truth)** — for any given fact, the one authoritative source designated to resolve disagreements between other sources.

## Data contracts and quality

- **Data Contract** — a versioned, machine-checkable specification of a dataset's schema, semantics, primary key, valid ranges, freshness SLO, and schema-change policy, agreed before a pipeline is built against it.
- **Schema Evolution** — the ability of a table format (e.g., Iceberg) to accommodate schema changes (added/renamed/removed columns) without rewriting all historical data.
- **Data Quality as Code** — expressing data validation rules (completeness, uniqueness, freshness, range, referential integrity, reconciliation) as versioned, CI-executed tests rather than manual spot checks.
- **Dead-Letter Queue (DLQ)** — a holding location for events/records that fail processing, so they are inspectable and reprocessable rather than silently dropped.
- **Freshness / Freshness SLO** — how current a dataset is relative to its source's own publication schedule, expressed as a measurable service-level objective (e.g., "available by 22:00 CET on trading days").
- **Reconciliation** — comparing record counts/checksums against the source to detect silent data loss or unauthorized modification.

## Architecture and methodology

- **Event-Driven Development (EDD)** — an architecture/development style where system behavior is organized around discrete events (e.g., `raw_data.received`) with independent, decoupled producers and consumers.
- **Spec-Driven Development (SDD)** — a methodology where a structured, behavior-first specification is written *before* any code, and treated as an executable contract that (increasingly, with AI coding agents) code is generated from and kept in sync with. Three maturity levels: **Spec-First** (spec guides one task), **Spec-Anchored** (spec is maintained after the task, for future evolution), **Spec-as-Source** (the spec is the actual source of truth; humans edit only the spec, never the generated code directly).
- **Test-Driven Development (TDD)** — writing tests before the implementation code that must satisfy them.
- **Architectural Drift** — the gradual divergence between documented design and actual implementation when documentation is passive rather than enforced; SDD counters this by making the spec executable/enforced rather than descriptive-only.
- **Adversarial Agent Pattern** — an AI-development pattern where a separate **Verifier** agent checks an **Implementor** agent's output against the spec, instead of trusting the implementor to self-certify; a **Coordinator** splits the spec into sub-tasks for implementors.
- **Architecture Decision Record (ADR)** — a short, permanent, append-only document recording one significant architecture decision: context, decision, rejected alternatives, consequences.

## Data domains (this project's scope)

- **Macroeconomics** — country/region-level indicators: GDP, CPI, unemployment rate, interest rates.
- **Equity Market** — OHLCV price data, indices, company fundamentals, dividends.
- **Fixed Income & Rates** — bond yields, interbank rates, yield curves.
- **Trade** — imports, exports, tariffs, trading partners, commodities.
- **Cryptoassets** — price, volume, supply, market capitalization of digital assets.
- **Corporate Filings** — regulatory disclosures such as 10-K/10-Q and XBRL-tagged financial statements.
- **OHLCV** — Open, High, Low, Close, Volume — the standard bar/candle representation of price/volume over an interval.

## Time fields (see `technical/data-model.md` for full usage)

- **`observed_at`** — when the market event or measurement actually occurred.
- **`period_start` / `period_end`** — the period an economic indicator covers.
- **`published_at`** — when the source officially released the data.
- **`retrieved_at`** — when this platform's ingestion pulled the data.
- **`processed_at`** — when the pipeline transformed the data.
- **`vintage_date`** — the revision/version date of the data point.

## Governance and security

- **RBAC (Role-Based Access Control)** — granting permissions based on a user's assigned role rather than per-user configuration.
- **Secret** — any credential (API key, password, token) that must never be committed to source control, container images, or shared config; managed via a secrets manager (e.g., HashiCorp Vault) in later phases, `.env` files (git-ignored) only in local development.
- **RPO (Recovery Point Objective)** — the maximum acceptable amount of data loss, measured in time, after an incident.
- **RTO (Recovery Time Objective)** — the maximum acceptable time to restore service after an incident.
- **Audit Log** — an immutable record of who/what did what, when, used both for security review and for explaining any AI agent's actions.

## Requirements-document acronyms

| Acronym | Full name | What it answers |
|---|---|---|
| BRD | Business Requirements Document | Why does this exist, for whom? |
| PRD | Product Requirements Document | What can a user do? |
| FRD | Functional Requirements Document | What must the system do, exactly? |
| NFR / NFRD | Non-Functional Requirement(s) (Document) | How well must it do it (speed, security, availability, scale)? |
| SRS | Software Requirements Specification | The single traceable reference tying the above together |
| ARD | Architecture Reference & Decisions Document | What structural patterns and principles govern the system, and what was decided at the architecture level? |
| ADR | Architecture Decision Record | One specific decision: what, why, alternatives, consequences |
| SDD (doc) | Solution Design Document | Why this architecture, these components, this data flow? — *not* to be confused with SDD (methodology) = Spec-Driven Development, used elsewhere in this repo; context disambiguates |
| TDD (doc) | Technical Design Document | Implementation detail: schemas, APIs, algorithms, deployment — *not* to be confused with TDD (methodology) = Test-Driven Development |
| Runbook | Operational Playbook | What do we do during an incident, a delay, or a secret leak? |
