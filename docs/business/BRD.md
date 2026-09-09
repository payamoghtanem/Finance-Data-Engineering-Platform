# Business Requirements Document (BRD)

**What this document answers:** why must this platform exist, for whom, and what business value and risk does it carry?
**How it differs from its neighbors:** this is the only document in the repository that never mentions a specific technology. If you find yourself writing "PostgreSQL" or "Kafka" here, that sentence belongs in `../architecture/ARD.md` or `../technical/`.

## 1. Business problem

Analysts, independent researchers, developers, and product managers who want to reason about financial markets, macroeconomic conditions, trade flows, or crypto assets today face a fragmented, unreliable, and unauditable process:

- Data is scattered across dozens of APIs, spreadsheets, PDFs, and web pages, each with its own format, units, and update cadence.
- There is no shared record of *where* a number came from, *when* it was retrieved, or *which version* of it was used in a given analysis — so results are not reproducible, and revisions (e.g., a restated GDP figure) silently corrupt historical analysis (look-ahead bias).
- Manually re-fetching and re-cleaning the same data for every new question wastes time that should go to analysis.
- There is no single place to check whether a dataset is even legally usable (license, redistribution terms) before someone builds on it.

## 2. Vision

Build a trustworthy, reusable, auditable data system — not a folder of fetch scripts — that turns official and clearly licensed financial, economic, trade, and crypto data into a clean, documented, queryable set of data products, accessible via API and dashboard, and safely assistable by a tightly scoped AI agent.

## 3. Stakeholders

| Stakeholder | Interest |
|---|---|
| **Analyst** | Wants fast, trustworthy answers to market/economic questions without hand-collecting data |
| **Developer** | Wants a stable, documented API/data model to build applications against |
| **Researcher** | Needs reproducibility: the same query against the same vintage must always return the same answer |
| **Product manager / decision-maker** | Wants a defensible, auditable source for numbers used in decisions |
| **Platform operator** (the project owner, initially) | Needs the system to be maintainable solo, on a laptop, without a team or budget at first |
| **AI Agent (scoped)** | A constrained, read-only consumer of the catalog and quality results — see `../ai-agent/agentic-ai-design.md` — not a stakeholder with unrestricted interests |

## 4. Value proposition

- **Eliminates manual data collection** by centralizing ingestion behind data contracts and scheduled, monitored pipelines.
- **Makes analysis reproducible** by preserving immutable raw data and distinguishing observation time from publication time from retrieval time from revision (vintage) — see `../00-glossary.md`.
- **Makes provenance provable**: every number can be traced back to its raw source file, retrieval timestamp, and the exact code version that processed it.
- **Provides one API** instead of N inconsistent ones, with a canonical data model shared across all sources.
- **Reduces legal/compliance risk** by gating every ingested dataset on an explicit license check before it becomes a "data product."

## 5. Out of scope

This platform explicitly does **not**:

- Execute trades or connect to any brokerage/exchange trading API.
- Provide personalized investment advice or recommendations.
- Guarantee real-time equity market data without a paid, licensed data agreement — real-time exchange data is a licensing and cost problem this platform does not solve for free.
- Act as a system of record for regulatory/compliance reporting (it is an analytical platform, not a regulated financial system of record).
- Grant the AI agent any write, delete, schema-change, or trade-execution capability under any circumstance (see `../ai-agent/agentic-ai-design.md`).

## 6. Product-level KPIs

| KPI | Target (MVP) | Why it matters |
|---|---|---|
| Ingestion job success rate | ≥ 99% over a rolling 30 days | Reliability is the entire value proposition |
| Freshness SLO adherence | ≥ 95% of scheduled datasets meet their documented freshness target | Stale data silently corrupts decisions |
| Data-quality test pass rate | 100% of blocking tests must pass before data reaches Silver/Gold | Bad data must never reach consumers |
| Mean time to detect a broken pipeline | < 1 hour (via alerting, not manual discovery) | Detection speed limits the blast radius of bad data |
| Datasets with complete metadata (license, trust tier, contract) | 100% of datasets exposed as "data products" | Legal risk and reproducibility both depend on this |
| Recovery time for a failed ingestion run | < 4 hours (matches RTO in `../requirements/NFR.md`) | Bounds how long a source outage can degrade the platform |

## 7. Business risks

| Risk | Business impact | Owning mitigation |
|---|---|---|
| A free-tier data source changes terms, rate limits, or shuts down | Pipeline breakage, possible gap in historical continuity | `../architecture/ARD.md` (adapter layer, contract tests), `../data-sources/catalog.md` (never single-source a critical KPI without a fallback noted) |
| Using data without a clear redistribution license | Legal exposure, forced takedown of a data product | `../data-sources/catalog.md` license-registry rule; enforced in `../requirements/FRD.md` |
| Silent data quality degradation | Wrong conclusions drawn by users or the AI agent | `../requirements/NFR.md` data-quality NFRs; `../technical/data-model.md` `data_quality_result` table |
| Cloud cost growth outpacing value delivered | Project becomes financially unsustainable before it proves its value | Phased rollout in `../roadmap/mvp-plan.md` — cloud spend is deferred until Phase 3, and is explicitly budgeted before it begins |
| Over-engineering (building Phase-3 infrastructure before Phase-1 value is proven) | Wasted effort, delayed time-to-value, abandoned project | ADR discipline (`../architecture/decisions/`) and the phase-exit criteria in `../roadmap/mvp-plan.md` |
| AI agent hallucination or scope creep | Wrong or unauthorized action taken on the user's behalf | `../ai-agent/agentic-ai-design.md` — read-only by default, audited, human-approved for anything consequential |

## 8. Success definition

The BRD is satisfied when: (a) the MVP defined in `../roadmap/mvp-plan.md` runs unattended on a laptop and consistently meets the KPIs above for at least one full data domain end-to-end; and (b) every dataset exposed to a user or the AI agent carries provable provenance, a passing quality record, and a resolved license status.
