# STATUS — Living Project State

**This file is the single source of truth for "where is this project right now."**
Read it immediately after the root `CLAUDE.md`. Any agent, on any harness, at any
time, must be able to answer *what is done, what is in progress, and what to pick
up next* from this file alone — without access to a prior chat session.

> **Maintenance rule (binding):** this file is updated **in the same pull request**
> as the work it describes. A PR that completes a task without moving that task's
> row here is incomplete, exactly like an FR without a traceability row.

- **Last updated:** 2026-09-10
- **Current phase:** Phase 1 — Local MVP, **in progress** (EPIC-01 done, EPIC-02 partial). Fix PR #12 open, green, awaiting owner merge. `main` now branch-protected.
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
| PR #12 (EPIC-01/02 fixes) → `main` | **Ready — awaiting owner merge** | human | 6/6 checks green, `mergeable_state: clean`. Owner merges, not the agent. |

## 4. What to do next (ordered)

The next agent should start at the **top unchecked item**.

1. [ ] **Owner:** merge PR #12 into `main` (green, clean, ready).
2. [ ] **Owner decision:** pick a `LICENSE` (D-01) — blocks any public release.
3. [x] ~~Owner decision: approve seeding GitHub Issues~~ — **Done 2026-09-10.** Phase 1 backlog seeded as Issues #13-#58 (see §8). Phase 2-3 epics (EPIC-14..EPIC-24) intentionally not seeded yet, matching `docs/backlog/user-stories.md`'s own rule against decomposing them early.
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
| D-02 | Seed GitHub Issues + project board? | Outward-facing, hard to reverse | **Resolved 2026-09-10** — Issues seeded (§8). Auto-add to Project #6 still needs a one-time owner action, see §8. |
| D-03 | Confirm Python version + package manager (assumed 3.11 + pip in `pyproject.toml`) | Environment ownership | Phase 1 scaffolding |
| D-04 | Enable branch protection on `main` requiring green CI | Repository administration | **Resolved 2026-09-10.** Ruleset `main-protection` active: PR required (0 approvals needed — solo dev), 6 status checks required, force-push and deletion blocked. Pitfall for future agents: pasting all 6 check names into the search box at once registers ONE concatenated context that can never pass — add each check separately, selecting it from the dropdown, and verify via `GET /repos/.../rules/branches/main` that `required_status_checks` has 6 separate entries before trusting the UI. |

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

## 8. GitHub Issues (Phase 1 backlog, seeded 2026-09-10)

Every Phase 1 epic and user story now exists as a real GitHub Issue, linked
parent (Epic) → child (Story) via GitHub's native sub-issue relationship —
not just described in `docs/backlog/`. Phase 2-3 epics (EPIC-14..EPIC-24) are
deliberately **not** seeded yet: `docs/backlog/user-stories.md` itself says not
to decompose those until their phase is closer, and the same restraint applies
to issue-seeding.

| Epic | Issue | State | Stories |
|---|---|---|---|
| EPIC-00 (cross-cutting) | [#14](https://github.com/payamoghtanem/Finance-Data-Engineering-Platform/issues/14) | Closed (done) | — |
| EPIC-01 | [#13](https://github.com/payamoghtanem/Finance-Data-Engineering-Platform/issues/13) | Closed (done) | #27-#30, all closed |
| EPIC-02 | [#15](https://github.com/payamoghtanem/Finance-Data-Engineering-Platform/issues/15) | Open (partial) | #31-#36: #31,#33 closed; #32,#34 partial (open); #35,#36 open |
| EPIC-03 | [#16](https://github.com/payamoghtanem/Finance-Data-Engineering-Platform/issues/16) | Open (next up) | #37-#39, open |
| EPIC-04 | [#17](https://github.com/payamoghtanem/Finance-Data-Engineering-Platform/issues/17) | Open | #40-#48, open |
| EPIC-05 | [#18](https://github.com/payamoghtanem/Finance-Data-Engineering-Platform/issues/18) | Open | #49-#51, open |
| EPIC-06 | [#19](https://github.com/payamoghtanem/Finance-Data-Engineering-Platform/issues/19) | Open | #52, open |
| EPIC-07 | [#20](https://github.com/payamoghtanem/Finance-Data-Engineering-Platform/issues/20) | Open | #53, open |
| EPIC-08 | [#21](https://github.com/payamoghtanem/Finance-Data-Engineering-Platform/issues/21) | Open | #54-#55, open |
| EPIC-09 | [#22](https://github.com/payamoghtanem/Finance-Data-Engineering-Platform/issues/22) | Open | #56-#57, open |
| EPIC-10 | [#23](https://github.com/payamoghtanem/Finance-Data-Engineering-Platform/issues/23) | Open | #58, open |
| EPIC-11 | [#24](https://github.com/payamoghtanem/Finance-Data-Engineering-Platform/issues/24) | Open | not decomposed yet (by design) |
| EPIC-12 | [#25](https://github.com/payamoghtanem/Finance-Data-Engineering-Platform/issues/25) | Open | not decomposed yet (by design) |
| EPIC-13 | [#26](https://github.com/payamoghtanem/Finance-Data-Engineering-Platform/issues/26) | Open | not decomposed yet (by design) |

**Labels used:** `epic`, `phase-1-mvp`, `epic:EPIC-NN` (one per epic, applied to
the epic issue and every one of its stories so both can be filtered together).
No per-requirement labels — the FR/NFR ID is in the issue title/body, not a label.

**Known label-creation quirk (for the next agent):** GitHub issue label
auto-creation via `issue_write` appears to hit a secondary rate limit after
roughly a dozen brand-new label names in quick succession — further new labels
then fail to resolve even though the call itself is otherwise valid. If you hit
`failed to resolve label "X": label 'X' not found`, don't assume the label name
is bad — check `get_label` first, and if genuinely new labels are needed, pace
the creates out or reuse an existing label instead of inventing more at once.

**One remaining manual step — Project #6 (`github.com/users/payamoghtanem/projects/6`):**
this repo has no tool access to that board directly (Projects v2 for a *personal*
User account isn't reachable the way an Organization project's custom fields
are). To get these issues flowing onto the board automatically: open Project #6
→ `⋯` menu → **Workflows** → **Auto-add to project**, and add a rule matching
this repository. Every issue above already exists and will appear once that
one-time rule is set — no re-seeding needed.
