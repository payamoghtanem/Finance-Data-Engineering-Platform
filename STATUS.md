# STATUS — Living Project State

**This file is the single source of truth for "where is this project right now."**
Read it immediately after the root `CLAUDE.md`. Any agent, on any harness, at any
time, must be able to answer *what is done, what is in progress, and what to pick
up next* from this file alone — without access to a prior chat session.

> **Maintenance rule (binding):** this file is updated **in the same pull request**
> as the work it describes. A PR that completes a task without moving that task's
> row here is incomplete, exactly like an FR without a traceability row.

- **Last updated:** 2026-09-10
- **Current phase:** Phase 1 — Local MVP, **in progress** (EPIC-01 done, EPIC-02 partial)
- **Active branch:** `Claude-Code-Agent`
- **Runtime code exists:** **Yes.** `src/`, `infra/`, `tests/` exist. `pipelines/` (Dagster) does not yet.

---

## 1. Phase status

| Phase | State | Exit criteria |
|---|---|---|
| Phase 0 — Design & documentation | **Complete** | Full doc set + traceability + ADRs — see §2 |
| Phase 0.5 — Execution scaffolding | **Complete** | Backlog, standards, CI, agent config |
| Phase 1 — Local MVP | **In progress** | `docs/roadmap/mvp-plan.md` §2 |
| Phase 2 — Team-ready | Not started | `docs/roadmap/mvp-plan.md` §3 |
| Phase 3 — Cloud-native production | Not started | `docs/roadmap/mvp-plan.md` §4 |

## 2. What is done

- [x] Full documentation set: BRD, PRD, ARD, SDD, FRD, NFR, SRS, TDD, data model, API design, event schema, glossary, executive summary.
- [x] 4 ADRs with alternatives, negative consequences, and revisit triggers.
- [x] Traceability matrix covering all 26 FRs and all 10 NFR groups.
- [x] Data source catalog: 8 countries, trust tiers, five-question license test.
- [x] Agentic-AI design spec (read-only, allow-listed, audited).
- [x] Distributed `CLAUDE.md` context network (root + `docs/` + 9 subfolders).
- [x] Engineering standards, CI, issue/PR templates, backlog.
- [x] **EPIC-01** — repository scaffolding (`src/`, `tests/`, `infra/`), config loading, structured logging, Phase 1 `docker-compose` with Prometheus/Grafana.
- [x] **EPIC-02 (partial)** — FRED connector: fetch, retry/backoff with transient-vs-permanent split, content-addressed immutable raw storage, documented event emission. 15 unit tests.

## 3. What is in progress

| Item | State | Owner | Notes |
|---|---|---|---|
| EPIC-02 remainder: `ingestion_run` record, DLQ, full idempotency | **Not started** | — | Needs the storage/DB layer from EPIC-03 |
| EPIC-03 — Raw & Bronze with provenance | **Next** | — | MinIO backend behind the existing `RawStorage` protocol |
| GitHub Issues / milestones / project board seeding | **Blocked — awaiting owner approval** | human | Outward-facing; see §5 |
| Branch protection on `main` | **Blocked — awaiting owner** | human | See D-04; without it, red CI can still be merged |

## 4. What to do next (ordered)

The next agent should start at the **top unchecked item**.

1. [ ] **Owner decision:** enable branch protection on `main` requiring green CI (D-04). Until then any agent can merge a red branch — this already happened once.
2. [ ] **Owner decision:** pick a `LICENSE` (D-01) — blocks any public release.
3. [ ] **Owner decision:** approve seeding GitHub Issues + milestones + project board from `docs/backlog/epics.md` (D-02).
4. [ ] **EPIC-03:** MinIO/S3 backend implementing the `RawStorage` protocol in `src/common/raw_storage.py`; Bronze writer with lineage back to the raw object key.
5. [ ] **EPIC-02 remainder:** `ingestion_run` record (FR-OPS-001), DLQ routing (FR-OPS-003), end-to-end idempotency test (US-02-004).
6. [ ] **EPIC-07:** Dagster project under `pipelines/` — this directory still does not exist.
7. [ ] Write `docs/architecture/capacity-model.md` — data volumes at 12/36 months. NFR targets currently have no load model behind them.
8. [ ] Write `docs/architecture/threat-model.md` — STRIDE pass over ingestion, API, agent, secrets.
9. [ ] Create `runbooks/` + `runbook-template.md` (required by NFR-MAINT-001).

## 5. Open decisions blocking work

| # | Decision | Why it's the owner's call | Blocks |
|---|---|---|---|
| D-01 | Repository license (MIT / Apache-2.0 / proprietary) | Legal and ownership; not an agent's call | Public release, any external contribution |
| D-02 | Seed GitHub Issues + project board? | Outward-facing, hard to reverse | Multi-agent task coordination |
| D-03 | Confirm Python version + package manager (assumed 3.11 + pip in `pyproject.toml`) | Environment ownership | Phase 1 scaffolding |
| D-04 | Enable branch protection on `main` requiring green CI | Repository administration | Prevents red code reaching `main`, as it did via PR #10/#11 |

## 6. Known defects / debt

| ID | Item | Severity | State |
|---|---|---|---|
| DEBT-01 | `docs/` had two broken relative links to the NFR document (wrong parent-directory prefix) | Low | **Fixed** in this change |
| DEBT-02 | Only one diagram exists (SDD mermaid); no component/sequence/deployment diagrams | Medium | Open |
| DEBT-03 | No capacity/volume model; NFR targets unanchored to load | Medium | Open — see §4.3 |
| DEBT-04 | No threat model despite "secure by default" being ARD principle 7 | Medium | Open — see §4.4 |
| DEBT-05 | ADRs lack the "What this document answers" header used by other docs | Low | Accepted (ADR format is its own standard) |
| DEBT-06 | FRED raw storage is filesystem-backed; MinIO backend not yet written | Medium | Open — EPIC-03, behind the `RawStorage` protocol |
| DEBT-07 | Events are constructed and logged but never published to a transport | Medium | Open — EPIC-06 (in-process transport per ADR-0002) |
| DEBT-08 | `pipelines/` (Dagster) does not exist; nothing schedules the connector | Medium | Open — EPIC-07 |

## 7. Related

- Backlog / epics / stories: `docs/backlog/epics.md`
- Engineering standards: `docs/engineering/engineering-standards.md`
- Roadmap and phase exit criteria: `docs/roadmap/mvp-plan.md`
