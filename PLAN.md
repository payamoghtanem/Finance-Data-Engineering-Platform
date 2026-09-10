# Project Plan (English) — Finance & Economic Data Engineering Platform Documentation Set

> This is the English, repository-tracked version of the design plan. An earlier Persian/Farsi planning pass covered the same ground conversationally; this document supersedes it as the source of truth going forward, and everything below is written natively in English rather than translated line-by-line.

## Context

Two source materials informed this plan:

1. A detailed technical design note covering: the data platform mental model (`Source → Ingest → Raw Storage → Validate → Transform → Serve → Observe & Govern`), eight non-negotiable architecture principles, a Bronze/Silver/Gold Lakehouse reference architecture, a tool-selection table with explicit "why / why not" reasoning, a three-phase rollout (Local MVP → Team-ready → Cloud-native Production), a canonical dimensional/fact data model, the six distinct timestamp types needed to avoid look-ahead bias, required data-quality controls, a sample data contract, the combined EDD+SDD+TDD methodology with a sample event flow, the full list of required requirements/design documents with sample FR/NFR entries, an architecture question checklist, a risk/control table, a safe Agentic-AI design (read-only, allow-listed, audited), and a ten-step practical learning roadmap.
2. A 36-page catalog of verified, official, or trusted financial/economic/trade/crypto/energy data sources, organized by country (Germany, UK, China, Japan, USA, India, Russia, Canada), each with ~80–120 sources ranked by reliability tier (official statistical/regulatory bodies → exchanges → rating agencies → credible financial media → analytics platforms → crypto/energy specialists).

The repository (`payamoghtanem/Finance-Data-Engineering-Platform`, branch `Claude-Code-Agent`) started essentially empty. This plan turns both source materials into a durable, English-language, git-tracked documentation set that:

- Reads as real BRD / PRD / ARD / FRD / NFR / SRS / Solution Design Document / Technical Design Document artifacts — not a paraphrase of the source notes.
- Is **traceable**: every functional requirement links back to a business goal; every architecture decision is recorded as an ADR with rejected alternatives; every document states what question it answers and how it differs from its neighbors.
- Is **navigable by both humans and LLM agents**, via a distributed network of `CLAUDE.md` context files (one per major folder) plus a root `CLAUDE.md` — so an agent given a narrow task (e.g., "update the FRD") can orient itself from the nearest `CLAUDE.md` without re-reading the entire repository.
- Ships as a **pull request** against `main`, not just commits pushed silently to a feature branch, so it goes through normal review.

## Scope of this change

In scope:
- Full documentation set listed in the Document Index below, as real files under `docs/`.
- Repository scaffolding: folder structure that mirrors how the eventual codebase (`src/`, `pipelines/`, `infra/`) will be organized, described in advance so future code has a home to land in.
- Distributed `CLAUDE.md` files: one at repo root, one per top-level `docs/` subfolder.
- This `PLAN.md` file itself, and `README.md` as the human entry point.
- A single PR from `Claude-Code-Agent` into `main`.

Out of scope for this change (explicitly deferred to later phases per the roadmap):
- Any runtime code (connectors, pipelines, API server, dashboards).
- Actual cloud infrastructure or IaC.
- CI/CD pipeline definitions (the design for them is documented; the YAML itself is a later phase).

## Document index and what each one must contain

| # | File | Purpose | Primary source material |
|---|---|---|---|
| 1 | `docs/00-glossary.md` | Canonical English term list, one definition per term, referenced everywhere else | Both |
| 2 | `docs/01-executive-summary-and-recommendation.md` | Honest verdict on the idea, the "you can't have free + cloud-native + production-ready simultaneously" reality check, recommended path | Design note |
| 3 | `docs/business/BRD.md` | Vision, problem statement, stakeholders, value proposition, out-of-scope, product KPIs, business risks | Design note |
| 4 | `docs/business/PRD.md` | Personas, user journeys, product capabilities, MoSCoW prioritization, acceptance criteria at product level | Design note |
| 5 | `docs/architecture/ARD.md` | Layered reference architecture, architecture principles, patterns (Event-Driven, Medallion, Lakehouse vs. Warehouse vs. Data Mesh with rationale), tool-selection table | Design note |
| 6 | `docs/architecture/solution-design-document.md` | End-to-end data flow diagram, technology choices with rejected alternatives, phased deployment | Design note |
| 7 | `docs/architecture/decisions/ADR-*.md` | Individual architecture decision records (Lakehouse vs. Warehouse, defer Kafka in MVP, Iceberg vs. Delta Lake, etc.) | Design note |
| 8 | `docs/requirements/FRD.md` | Precise functional requirements per data domain, Given/When/Then style, FR-ING-xxx / FR-QUAL-xxx / FR-API-xxx | Design note |
| 9 | `docs/requirements/NFR.md` | Measurable non-functional targets: availability, freshness, performance, security, RPO/RTO, maintainability, auditability | Design note |
| 10 | `docs/requirements/SRS.md` | Single traceable reference per ISO/IEC/IEEE 29148 structure, tying BRD→PRD→FRD→NFR together | Both |
| 11 | `docs/requirements/traceability-matrix.md` | Requirement-to-goal traceability table | Both |
| 12 | `docs/technical/technical-design-document.md` | Implementation detail: module boundaries, retry/backoff algorithm, DLQ design, repo layout, docker-compose | Design note |
| 13 | `docs/technical/data-model.md` | Full schema: `dim_source`, `dim_dataset`, `dim_instrument`, `dim_indicator`, `fact_market_ohlcv`, `fact_economic_observation`, `fact_trade_observation`, `fact_crypto_market`, `ingestion_run`, `data_quality_result` | Design note |
| 14 | `docs/technical/api-design.md` | Serving API contract (FastAPI/OpenAPI style) | Design note |
| 15 | `docs/technical/event-schema.md` | Event envelope, event types, producers/consumers, DLQ policy | Design note |
| 16 | `docs/data-sources/catalog.md` | Structured catalog of free/official sources: global priority sources (FRED, World Bank, Eurostat/SDMX, SEC EDGAR, CoinGecko) plus the country-by-country catalog condensed from the SSOT PDF, mapped to `dim_source` fields | PDF catalog |
| 17 | `docs/ai-agent/agentic-ai-design.md` | Agent role, RAG scope, tool allow-list, audit logging, human-approval loop, Coordinator/Implementor/Verifier pattern | Design note |
| 18 | `docs/methodology/edd-sdd-tdd.md` | How Event-Driven, Spec-Driven, and Test-Driven Development combine on this project, with the full sample event flow | Design note |
| 19 | `docs/learning-guide/system-design-guide.md` | Standalone teaching document: design criteria, topics to consider, constraints/risks, the architecture-question checklist with rationale, where to find trustworthy answers, tool/framework trade-offs | Design note |
| 20 | `docs/roadmap/mvp-plan.md` | Three-phase rollout with exit criteria per phase, laptop-first MVP stack | Design note |

Plus: root `CLAUDE.md`, `docs/CLAUDE.md`, and one `CLAUDE.md` per subfolder in the table above (business/, architecture/, requirements/, technical/, data-sources/, ai-agent/, methodology/, learning-guide/, roadmap/).

## Sequencing

1. Repository scaffolding + root `CLAUDE.md` / `README.md` / `PLAN.md` (this file).
2. Per-folder `CLAUDE.md` files.
3. `docs/00-glossary.md` and `docs/01-executive-summary-and-recommendation.md`.
4. Business layer: BRD, PRD.
5. Architecture layer: ARD, Solution Design Document, ADRs.
6. Requirements layer: FRD, NFR, SRS, traceability matrix.
7. Technical layer: Technical Design Document, data model, API design, event schema.
8. Data source catalog, Agentic AI design, methodology doc, learning guide, roadmap.
9. Commit, push to `Claude-Code-Agent`, open PR against `main`.

## Status

> **Superseded.** This plan covered the Phase-0 documentation effort, which is
> **complete**. It is kept as the historical record of that scope and sequencing.
>
> **Live project state now lives in [`STATUS.md`](STATUS.md)** — what is done, what is
> in progress, what to do next, and which decisions are blocking.
>
> The earlier version of this section delegated status to "the session's task list."
> That was a defect: session task lists are ephemeral, so project state did not survive
> the session that created it. `STATUS.md` exists to fix exactly that.

## Verification

- Every document required by the design note's own document taxonomy (BRD/PRD/FRD/NFR/SRS/SDD/TDD/ARD/ADR) has a real counterpart file.
- `docs/data-sources/catalog.md` covers all eight countries from the source PDF and maps to `dim_source` columns.
- `docs/requirements/traceability-matrix.md` has a row for every FR-xxx in the FRD.
- `docs/learning-guide/system-design-guide.md` is readable on its own, without requiring the other documents.
- `git log` shows a clean commit on `Claude-Code-Agent`, pushed, with an open PR against `main`.
