# CLAUDE.md — Root Agent Context

You are an LLM/agent (Claude Code or similar) that just landed in this repository. This file is your orientation. Read it before touching anything. Every subfolder under `docs/` has its own `CLAUDE.md` scoped to that folder — go there once you know which part of the system you're working on.

> **Read `STATUS.md` immediately after this file.** It is the single source of truth for
> what is done, what is in progress, and what to pick up next. This file tells you how the
> project is *shaped*; `STATUS.md` tells you where it *stands*. Never infer current state
> from a prior chat session — it is not durable. `STATUS.md` is.

## What this project is

**Finance & Economic Data Engineering Platform** — a free-to-start, cloud-ready, modular, secure, agentic-AI-assisted platform that ingests financial, economic, trade, and crypto data from official/licensed free sources, proves its provenance and quality, conforms it to a canonical model, and serves it through APIs and dashboards. Full narrative: `README.md` and `docs/01-executive-summary-and-recommendation.md`.

## Current phase

**Documentation / design phase; execution scaffolding in place.** Live state lives in `STATUS.md` — consult it rather than this paragraph for anything time-sensitive. There is no runtime code yet (`src/`, `pipelines/`, `infra/` do not exist yet). Everything under `docs/` is the frozen design that future implementation work must follow. If you are asked to write code, first check whether the relevant design doc under `docs/technical/` or `docs/architecture/` already specifies the shape of what you're building — do not improvise a different schema, API contract, or module boundary than what's documented. If a doc is silent or wrong for the task at hand, update the doc in the same change, don't silently diverge.

Roadmap phases (see `docs/roadmap/mvp-plan.md` for full detail):
1. **Local MVP** — Docker Compose on a laptop: Python + PostgreSQL + MinIO + Dagster + dbt Core + DuckDB + Metabase + Prometheus/Grafana.
2. **Team-ready** — add Kafka, OpenMetadata, Keycloak, Vault, CI/CD, data contracts, dev/staging/prod environments.
3. **Cloud-native production** — managed Kubernetes, real object storage, GitOps, autoscaling, backup/DR, enterprise IAM, 24/7 monitoring.

## Non-negotiable architecture principles

These come from `docs/architecture/ARD.md` and apply to every piece of code written in this repo, forever:

1. **Data provenance** — every record traces to source, retrieval time, API version, request, and code version.
2. **Immutable raw data** — store the original API/file response untouched; never mutate it; reprocess from it instead.
3. **Separation of concerns** — ingestion, storage, validation, modeling, serving, observability, and UI are separate services/modules, never tangled into one script.
4. **Data contracts** — schema, semantics, keys, units, cadence, valid ranges, and schema-change policy are defined *before* a pipeline runs, and enforced in CI.
5. **Idempotency** — re-running a job never creates duplicates or inconsistent results.
6. **Data quality as code** — validation lives in CI/CD and the pipeline itself, never as a manual/eyeball step.
7. **Secure by default** — no API key, password, or token ever goes into Git, Docker images, notebooks, or shared config files.
8. **Avoid vendor lock-in** — prefer open formats (Parquet, Apache Iceberg) so the compute engine or cloud can change later without a rewrite.

Full rationale for each: `docs/architecture/ARD.md` §2.

## Repository map

```
.
├── CLAUDE.md                     ← you are here
├── STATUS.md                     LIVE STATE: what's done, in progress, next — read this second
├── README.md                     Human-facing overview + doc index
├── PLAN.md                       Original design-phase plan (historical record)
├── CONTRIBUTING.md               How to work here: order of work, setup, PR rules
├── SECURITY.md                   Reporting, secrets posture, incident response
├── scripts/                      check_doc_links.sh, check_traceability.sh (run by CI)
├── .github/                      CI workflows, issue templates, PR template
├── .claude/                      Agent harness config: permissions + slash commands
└── docs/
    ├── CLAUDE.md                 Context for the docs/ tree
    ├── 00-glossary.md            Canonical term definitions — check here before assuming a term's meaning
    ├── 01-executive-summary-and-recommendation.md
    ├── business/                 CLAUDE.md + BRD.md, PRD.md
    ├── architecture/             CLAUDE.md + ARD.md, solution-design-document.md, decisions/ (ADRs)
    ├── requirements/             CLAUDE.md + FRD.md, NFR.md, SRS.md, traceability-matrix.md
    ├── technical/                CLAUDE.md + technical-design-document.md, data-model.md, api-design.md, event-schema.md
    ├── data-sources/             CLAUDE.md + catalog.md (verified free/official data sources by domain and country)
    ├── ai-agent/                 CLAUDE.md + agentic-ai-design.md (this file's own governing spec)
    ├── methodology/              CLAUDE.md + edd-sdd-tdd.md (how this project is actually built)
    ├── learning-guide/           CLAUDE.md + system-design-guide.md (standalone teaching document)
    ├── backlog/                  CLAUDE.md + epics.md, user-stories.md, definition-of-ready/done
    ├── engineering/              CLAUDE.md + engineering-standards.md, test-strategy.md
    └── roadmap/                  CLAUDE.md + mvp-plan.md
```

## How to navigate by task

| If you're asked to... | Start at |
|---|---|
| Understand why the project exists at all | `docs/01-executive-summary-and-recommendation.md`, `docs/business/BRD.md` |
| Add/change a user-facing capability | `docs/business/PRD.md`, then `docs/requirements/FRD.md` |
| Make an architecture decision or evaluate a tool | `docs/architecture/ARD.md`, then write an ADR in `docs/architecture/decisions/` |
| Design or change a database table | `docs/technical/data-model.md` |
| Design or change an API endpoint | `docs/technical/api-design.md` |
| Add a new event type or connector | `docs/technical/event-schema.md`, `docs/methodology/edd-sdd-tdd.md` |
| Add a new data source/connector | `docs/data-sources/catalog.md` (verify license/trust tier first), then `docs/requirements/FRD.md` for the FR-ING-xxx pattern |
| Touch anything the AI agent itself can do | `docs/ai-agent/agentic-ai-design.md` — this is a hard boundary, not a suggestion |
| Check a non-functional target (latency, SLA, freshness) | `docs/requirements/NFR.md` |
| Understand full requirement traceability | `docs/requirements/SRS.md` and `docs/requirements/traceability-matrix.md` |
| Just learn how to design a system like this | `docs/learning-guide/system-design-guide.md` — written to stand alone, no other doc required |
| Know what to work on next | `STATUS.md` §4, then `docs/backlog/user-stories.md` |
| Write any code at all | `docs/engineering/engineering-standards.md` — binding, enforced in CI |
| Know when a task is finished | `docs/backlog/definition-of-done.md` |
| Write or plan tests | `docs/engineering/test-strategy.md` |

## Working conventions for agents in this repo

- **Language**: all content in this repository is English. A parallel Persian/Farsi documentation set may exist in conversation history but is not part of this repo's source of truth — do not mix languages in committed files.
- **Terminology discipline**: use the exact English terms defined in `docs/00-glossary.md`. If you introduce a new term, add it there in the same change.
- **Traceability**: every functional requirement (FR-xxx) in `docs/requirements/FRD.md` must appear in `docs/requirements/traceability-matrix.md` linked back to a BRD/PRD goal. If you add an FR, add the traceability row.
- **ADRs are append-only**: never edit a merged ADR's decision; if a decision changes, write a new ADR that supersedes it and say so explicitly in both files.
- **Git workflow**: develop on `Claude-Code-Agent`, commit with descriptive messages, push with `-u origin Claude-Code-Agent`, open PRs against `main`. Never force-push, never rewrite shared history, never skip hooks.
- **State is durable, sessions are not**: update `STATUS.md` in the same change as the work it describes. A completed task that doesn't move its row in `STATUS.md` is not finished — the next agent, on a different tool, has no other way to know.
- **No orphan work**: every task traces to a story, every story to an `FR-xxx`/`NFR-xxx`. See `docs/backlog/CLAUDE.md`.
- **Docs are the contract**: if implementation code (once it exists) needs to diverge from a design doc, update the doc in the same PR — the docs must never silently drift from reality.
