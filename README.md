# Finance & Economic Data Engineering Platform

A free-to-start, cloud-ready, modular, secure, and **agentic-AI-assisted** data engineering platform for financial, economic, trade, and crypto data — designed to run as a single-laptop MVP first and scale into a cloud-native production system without a ground-up rewrite.

This repository currently holds the **requirements, architecture, and design documentation** for the platform (Phase 0 of the roadmap — see [`docs/roadmap/mvp-plan.md`](docs/roadmap/mvp-plan.md)). Implementation code will land in subsequent phases under `src/`, `pipelines/`, `infra/`, etc., following the design frozen here.

## Why this project exists

Investors, analysts, researchers, developers, and (tightly scoped) AI agents currently have to hand-stitch together dozens of financial/economic APIs, spreadsheets, and scraped pages to answer basic questions ("what is Eurozone HICP inflation this quarter?", "what is BTC's 30-day realized volatility?", "what did SEC filings say about Company X's Q2 net income?"). This is slow, error-prone, unauditable, and impossible to reproduce.

This platform's job is to be a **trustworthy data system**, not a pile of fetch scripts: pull from official or licensed sources, keep an immutable raw copy, prove quality and provenance, conform to a canonical model, and serve it securely, observably, and reproducibly — to humans and to a supervised AI agent alike.

See [`docs/01-executive-summary-and-recommendation.md`](docs/01-executive-summary-and-recommendation.md) for the full recommendation, including the one hard truth this project must accept up front: **"fully free" + "cloud-native" + "enterprise production-ready" cannot all be true simultaneously on day one.** The roadmap resolves that tension by growing in three deliberate phases instead of promising all three at once.

## How this repository is organized

```
.
├── CLAUDE.md                     # Root agent/LLM context file — read this first if you are an AI agent
├── STATUS.md                     # LIVE STATE — what's done, in progress, and next
├── README.md                     # This file — human-facing entry point
├── PLAN.md                       # Phase-0 design plan (historical record)
├── CONTRIBUTING.md               # Order of work, local setup, PR rules
├── SECURITY.md                   # Secrets posture and vulnerability reporting
├── scripts/                      # Doc-link and traceability checks (run by CI)
├── .github/                      # CI workflows, issue + PR templates
├── .claude/                      # Agent harness config: permissions + slash commands
└── docs/
    ├── CLAUDE.md                 # Context for the docs/ tree as a whole
    ├── 00-glossary.md            # Shared terminology used across every document
    ├── 01-executive-summary-and-recommendation.md
    ├── business/                 # BRD, PRD — why and what
    ├── architecture/             # ARD, Solution Design Document, ADRs — how, and why this way
    ├── requirements/             # FRD, NFR, SRS, traceability matrix — precise, testable requirements
    ├── technical/                # Technical Design Document, data model, API design, event schema
    ├── data-sources/             # Catalog of verified, free/licensed financial & economic data sources
    ├── ai-agent/                 # Agentic AI design — scope, guardrails, audit
    ├── methodology/              # How this project is built: EDD + SDD + TDD combined
    ├── learning-guide/           # Standalone teaching guide: how to design a data platform, and why
    ├── backlog/                  # Epics, user stories, definition of ready/done
    ├── engineering/              # Coding standards and test strategy
    └── roadmap/                  # Phased MVP → team → cloud-native rollout plan
```

Every directory under `docs/` has its own `CLAUDE.md` explaining what belongs there, what doesn't, and how it relates to its neighbors — see [Context design](#context-design-for-llms-and-agents) below.

## Document index

| Document | Path | Answers |
|---|---|---|
| Executive Summary & Recommendation | `docs/01-executive-summary-and-recommendation.md` | Is this idea sound, and what's the verdict? |
| BRD — Business Requirements | `docs/business/BRD.md` | Why does this platform need to exist, for whom? |
| PRD — Product Requirements | `docs/business/PRD.md` | What can a user actually do with it? |
| ARD — Architecture Reference & Decisions | `docs/architecture/ARD.md` | What are the architecture's non-negotiable principles and patterns? |
| Solution Design Document | `docs/architecture/solution-design-document.md` | Why this architecture, these components, this data flow? |
| Architecture Decision Records | `docs/architecture/decisions/` | What was decided, what alternatives were rejected, and why? |
| FRD — Functional Requirements | `docs/requirements/FRD.md` | What must the system do, precisely, in each scenario? |
| NFR — Non-Functional Requirements | `docs/requirements/NFR.md` | How fast, how available, how secure, how observable? |
| SRS — Software Requirements Specification | `docs/requirements/SRS.md` | The single traceable reference tying BRD→PRD→FRD→NFR together |
| Technical Design Document | `docs/technical/technical-design-document.md` | Schemas, APIs, algorithms, retries, deployment detail |
| Data Model | `docs/technical/data-model.md` | Every table, key, and column |
| API Design | `docs/technical/api-design.md` | Every serving endpoint and its contract |
| Event Schema | `docs/technical/event-schema.md` | Every event, its shape, its consumers |
| Data Source Catalog | `docs/data-sources/catalog.md` | Which free/official sources are trustworthy, and for what |
| Agentic AI Design | `docs/ai-agent/agentic-ai-design.md` | What is the AI agent allowed to do, and how is that enforced? |
| Methodology (EDD + SDD + TDD) | `docs/methodology/edd-sdd-tdd.md` | How specs, events, and tests drive development together |
| System Design Learning Guide | `docs/learning-guide/system-design-guide.md` | How do you learn to design a system like this, from scratch? |
| Roadmap & MVP Plan | `docs/roadmap/mvp-plan.md` | What ships first, on a laptop, and what comes after? |
| **Project Status** | `STATUS.md` | **What is done, what is next, what is blocked?** |
| Epics & User Stories | `docs/backlog/` | Who does what, in what order, and when is it done? |
| Engineering Standards | `docs/engineering/engineering-standards.md` | How must code in this repo be written? |
| Test Strategy | `docs/engineering/test-strategy.md` | What tests exist, and what does each prove? |
| Contributing | `CONTRIBUTING.md` | How do I set up and submit a change? |

## Context design for LLMs and agents

This repository is built to be **navigable by an AI coding agent with zero prior context**, not only by humans who already know the project. That is a deliberate design goal, not an afterthought:

- **Root `CLAUDE.md`** gives any agent landing in the repo root the full orientation: what this project is, current phase, tech stack (target), how the folders relate, and where to go next for any given task.
- **Every subfolder under `docs/` has its own `CLAUDE.md`** scoped to that folder only — so an agent that jumps straight into `docs/requirements/` (e.g., because it was asked to update the FRD) gets exactly the context it needs without re-reading the whole tree.
- Documents cross-reference each other by relative path, not by restating content, so there is one place to update each fact and no drift between documents.
- `docs/00-glossary.md` is the single source of terminology (English term ↔ definition ↔ where it's used) that every other document assumes.

## Current status

**Phase 0 (design) is complete; Phase 1 (Local MVP) has not started.** No runtime code
exists yet. See [`STATUS.md`](STATUS.md) for the authoritative, continuously-updated
state — including the next actionable task and the open decisions currently blocking work.

## License and status

**No `LICENSE` file has been chosen yet** — this is an open owner decision (D-01 in
`STATUS.md`) and blocks any public release or outside contribution. Data source usage must respect each source's own license/terms — see `docs/data-sources/catalog.md`.
