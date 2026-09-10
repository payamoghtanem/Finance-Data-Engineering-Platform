# STATUS — Living Project State

**This file is the single source of truth for "where is this project right now."**
Read it immediately after the root `CLAUDE.md`. Any agent, on any harness, at any
time, must be able to answer *what is done, what is in progress, and what to pick
up next* from this file alone — without access to a prior chat session.

> **Maintenance rule (binding):** this file is updated **in the same pull request**
> as the work it describes. A PR that completes a task without moving that task's
> row here is incomplete, exactly like an FR without a traceability row.

- **Last updated:** 2026-09-10
- **Current phase:** Phase 0 — Design & Planning (complete) → Phase 1 — Local MVP (not started)
- **Active branch:** `Claude-Code-Agent`
- **Runtime code exists:** No. `src/`, `pipelines/`, `infra/`, `tests/` are specified in `docs/technical/technical-design-document.md` §1 but not yet created.

---

## 1. Phase status

| Phase | State | Exit criteria |
|---|---|---|
| Phase 0 — Design & documentation | **Complete** | Full doc set + traceability + ADRs — see §2 |
| Phase 0.5 — Execution scaffolding | **In progress** | Backlog, standards, CI, agent config — see §3 |
| Phase 1 — Local MVP | Not started | `docs/roadmap/mvp-plan.md` §2 |
| Phase 2 — Team-ready | Not started | `docs/roadmap/mvp-plan.md` §3 |
| Phase 3 — Cloud-native production | Not started | `docs/roadmap/mvp-plan.md` §4 |

## 2. What is done

- [x] Full documentation set: BRD, PRD, ARD, SDD, FRD, NFR, SRS, TDD, data model, API design, event schema, glossary, executive summary.
- [x] 4 ADRs with alternatives, negative consequences, and revisit triggers.
- [x] Traceability matrix covering all 26 FRs and all 10 NFR groups.
- [x] Data source catalog: 8 countries, trust tiers, five-question license test.
- [x] Agentic-AI design spec (read-only, allow-listed, audited).
- [x] Distributed `CLAUDE.md` context network (root + `docs/` + 9 subfolders).
- [x] Engineering standards, CI, issue/PR templates, backlog (this change — see §3).

## 3. What is in progress

| Item | State | Owner | Notes |
|---|---|---|---|
| Execution scaffolding (standards, CI, backlog, `.claude/`) | **This change** | agent | See `docs/backlog/` and `docs/engineering/` |
| GitHub Issues / milestones / project board seeding | **Blocked — awaiting owner approval** | human | Outward-facing; see §5 |

## 4. What to do next (ordered)

The next agent should start at the **top unchecked item**.

1. [ ] **Owner decision:** pick a `LICENSE` (see §5) — blocks any public release.
2. [ ] **Owner decision:** approve seeding GitHub Issues + milestones + project board from `docs/backlog/epics.md`.
3. [ ] Write `docs/architecture/capacity-model.md` — data volumes at 12/36 months. **Currently NFR targets have no load model behind them.**
4. [ ] Write `docs/architecture/threat-model.md` — STRIDE pass over ingestion, API, agent, secrets.
5. [ ] Create `runbooks/` + `runbook-template.md` (required by NFR-MAINT-001).
6. [ ] Create `contract.template.yaml` from `docs/architecture/solution-design-document.md` §4.
7. [ ] **Begin Phase 1, EPIC-01:** scaffold `src/`, `pipelines/`, `infra/` per TDD §1.
8. [ ] EPIC-02: implement the FRED connector (`US-02-*`) end to end — Raw → Bronze → Silver → Gold → dashboard.

## 5. Open decisions blocking work

| # | Decision | Why it's the owner's call | Blocks |
|---|---|---|---|
| D-01 | Repository license (MIT / Apache-2.0 / proprietary) | Legal and ownership; not an agent's call | Public release, any external contribution |
| D-02 | Seed GitHub Issues + project board? | Outward-facing, hard to reverse | Multi-agent task coordination |
| D-03 | Confirm Python version + package manager (assumed 3.11 + `uv`/pip in `pyproject.toml`) | Environment ownership | Phase 1 scaffolding |

## 6. Known defects / debt

| ID | Item | Severity | State |
|---|---|---|---|
| DEBT-01 | `docs/` had two broken relative links to the NFR document (wrong parent-directory prefix) | Low | **Fixed** in this change |
| DEBT-02 | Only one diagram exists (SDD mermaid); no component/sequence/deployment diagrams | Medium | Open |
| DEBT-03 | No capacity/volume model; NFR targets unanchored to load | Medium | Open — see §4.3 |
| DEBT-04 | No threat model despite "secure by default" being ARD principle 7 | Medium | Open — see §4.4 |
| DEBT-05 | ADRs lack the "What this document answers" header used by other docs | Low | Accepted (ADR format is its own standard) |

## 7. Related

- Backlog / epics / stories: `docs/backlog/epics.md`
- Engineering standards: `docs/engineering/engineering-standards.md`
- Roadmap and phase exit criteria: `docs/roadmap/mvp-plan.md`
