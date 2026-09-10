# STATUS — Living Project State

**This file is the single source of truth for "where is this project right now."**
Read it immediately after the root `CLAUDE.md`. Any agent, on any harness, at any
time, must be able to answer *what is done, what is in progress, and what to pick
up next* from this file alone — without access to a prior chat session.

> **Maintenance rule (binding):** this file is updated **in the same pull request**
> as the work it describes. A PR that completes a task without moving that task's
> row here is incomplete, exactly like an FR without a traceability row.

- **Last updated:** 2026-09-10
- **Current phase:** Phase 1 — Local MVP, **in progress** (EPIC-01 done, EPIC-02 mostly done, EPIC-03 done, EPIC-04 done, EPIC-06 done). `main` branch-protected. Phase 1 backlog is live as GitHub Issues (§8). 95 unit tests, 90% coverage.
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
- [x] **EPIC-02 (mostly done)** — FRED connector: fetch, retry/backoff with transient-vs-permanent split, content-addressed immutable raw storage, documented event emission, `ingestion_run` recording for every attempt (success and failure — US-02-005). Still open: US-02-006 (vintage awareness) and fact-table idempotency, both genuinely blocked on EPIC-05 (Silver layer), not just unstarted.
- [x] **EPIC-03** — `S3RawStorage` (real MinIO/S3 backend behind the existing `RawStorage` protocol, US-03-001) and `src/bronze/writer.py` (Bronze lineage — `raw_object_key`/`source_id`/`retrieved_at`/`code_version`, US-03-002; proven to need no network access, US-03-003). `FREDConnector.from_config` now defaults to `S3RawStorage` instead of the local filesystem. Done at the unit-test level only — never run against a *live* MinIO container, only moto-mocked S3 and in-memory DuckDB; first real run happens naturally once EPIC-07 (Dagster) exercises the full local stack.
- [x] **EPIC-06** — `src/events/bus.py`'s `EventBus`: the Phase 1 in-process publish/subscribe transport ADR-0002 calls for. One subscriber raising never stops the others or propagates to the publisher (proven by test). `connectors/fred` and `bronze/writer.py` now actually *publish* through it — not just construct and log an `EventEnvelope`, which is what US-06-001 is really about (a stage advances only on a real published event, never a bare signal). The rest of the documented producers (Dagster, validation, Silver/Gold) don't exist yet, so this bus currently has exactly two real producers and no real consumers — the mechanism is proven, not yet the full flow.
- [x] **EPIC-04** — `src/validation/` (contract loading, the nine FR-QUAL-001..009 rules, `ValidationEngine`): `load_contract()` parses a connector's real `contract.yaml` at runtime (no second hand-copied schema); each rule is a pure function returning `PASSED`/`FAILED`/`FLAGGED`/`SKIPPED`; `ValidationEngine.validate()` runs all nine and publishes `raw_data.validated`/`raw_data.quarantined` through `EventBus` — validation is now the 3rd real event producer (`docs/technical/event-schema.md` §4). **Honest scope limits, not gaps papered over**: FR-QUAL-002/004/006/007 need external context this engine has no independent source for yet (an expected-record calendar, a freshness `max_lag`, dimension-table keys, a source's own count/checksum) and return `SKIPPED` rather than a false pass when it's absent (`docs/technical/technical-design-document.md` §2c has the full table of what/who). Not yet wired as a live consumer of `raw_data.received` — that needs a source-specific payload parser (FRED's raw JSON → the contract's record shape), which doesn't exist for any connector yet; `BronzeWriter` also still isn't rewired onto events (still called directly), deliberately left alone rather than bolting on a second half-finished integration in the same change.

## 3. What is in progress

| Item | State | Owner | Notes |
|---|---|---|---|
| US-02-006: vintage awareness | **Not started** | — | Needs the canonical Silver model (EPIC-05) to mean anything real |
| Fact-table idempotency (rest of US-02-004) | **Not started** | — | Needs the Silver layer (EPIC-05); the raw-layer half is already proven |
| Project #6 auto-add workflow | **Blocked — awaiting owner** | human | One-time board setting; see §8. Issues themselves are already seeded. |

## 4. What to do next (ordered)

The next agent should start at the **top unchecked item**.

1. [x] ~~Owner: merge PR #12 into `main`~~ — **Merged 2026-09-10** (`9ae5e24`).
2. [x] ~~Owner decision: pick a `LICENSE`~~ — **Decided 2026-09-10: stay unlicensed for now** (see D-01). Revisit if/when external contribution or reuse is actually wanted.
3. [x] ~~Owner decision: approve seeding GitHub Issues~~ — **Done 2026-09-10.** Phase 1 backlog seeded as Issues #13-#58 (see §8). Phase 2-3 epics (EPIC-14..EPIC-24) intentionally not seeded yet, matching `docs/backlog/user-stories.md`'s own rule against decomposing them early.
4. [x] ~~Optional cleanup: delete superseded branches~~ — **Done.** `QWEN-Code-Agent` and `mvp-implementation-analysis-6b834` are gone (auto-deleted on merge).
5. [x] ~~EPIC-03: MinIO/S3 backend + Bronze writer~~ — **Done 2026-09-10** (unit-test level; see §2 above for the live-MinIO caveat).
6. [x] ~~EPIC-02 remainder: `ingestion_run` record~~ — **Done 2026-09-10** (US-02-005; see §2 above). DLQ routing was mis-scoped here originally: `docs/backlog/epics.md` actually assigns FR-OPS-003 to **EPIC-09**, which depends on EPIC-06 (event transport) being further along than it is — building DLQ now would jump the epic sequence the backlog itself warns against. Corrected rather than followed blindly.
7. [x] ~~EPIC-06: in-process event transport~~ — **Done 2026-09-10** (`EventBus`; see §2 above). Mechanism proven with two real producers; no real consumer exists yet since Validation/Silver (EPIC-04/05) don't.
8. [x] ~~EPIC-04: data-quality rule engine~~ — **Done 2026-09-10** (`src/validation/`; see §2 above). Built ahead of EPIC-05 by explicit owner choice, because `docs/backlog/epics.md` lists EPIC-05 as depending on **both** EPIC-03 and EPIC-04, not EPIC-03 alone.
9. [ ] **EPIC-05:** Silver/Gold dbt modelling (`src/transform/`) — now unblocked (EPIC-03 and EPIC-04 both done, per `docs/backlog/epics.md`). This is what finally closes US-02-004 (fact-table idempotency) and US-02-006 (vintage awareness) from EPIC-02, and would also be the natural place to give `ValidationEngine`'s FR-QUAL-006 rule its first real dimension-table keys.
10. [ ] **EPIC-07:** Dagster project under `pipelines/` — this directory still does not exist. Depends on EPIC-02 (done) and EPIC-06 (done) per `docs/backlog/epics.md`, so this is unblocked independently of EPIC-05, and is also what would give FR-QUAL-002/004/007 their missing scheduling context (§2 above).
11. [ ] Write `docs/architecture/capacity-model.md` — data volumes at 12/36 months. NFR targets currently have no load model behind them.
12. [ ] Write `docs/architecture/threat-model.md` — STRIDE pass over ingestion, API, agent, secrets.
13. [ ] Create `runbooks/` + `runbook-template.md` (required by NFR-MAINT-001).

## 5. Open decisions blocking work

| # | Decision | Why it's the owner's call | Blocks |
|---|---|---|---|
| D-01 | Repository license (MIT / Apache-2.0 / proprietary) | Legal and ownership; not an agent's call | **Resolved 2026-09-10 — deliberately staying unlicensed.** No `LICENSE` file exists, so default copyright applies: all rights reserved, no one (including a contributor or another agent) has legal permission to copy, modify, or reuse this code, even though the repo is public. This was a conscious choice, not an oversight — revisit if external contribution, forking, or reuse is ever wanted. |
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
| DEBT-06 | ~~FRED raw storage is filesystem-backed; MinIO backend not yet written~~ | Low | **Resolved 2026-09-10** — `S3RawStorage` exists and is the default (EPIC-03). Remaining gap: verified only against moto-mocked S3, not a live MinIO container yet. |
| DEBT-07 | ~~Events are constructed and logged but never published to a transport~~ | Low | **Resolved 2026-09-10** — `EventBus` exists and both `connectors/fred` and `bronze/writer.py` publish through it (EPIC-06). Remaining gap: only 2 of 9 documented producers exist, so there is no real consumer yet either — this is the transport mechanism proven, not the full event-driven flow. |
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
| EPIC-02 | [#15](https://github.com/payamoghtanem/Finance-Data-Engineering-Platform/issues/15) | Open (mostly done) | #31-#36: #31,#33,#35 closed; #32,#34 partial (open, blocked on EPIC-05); #36 open (blocked on EPIC-05) |
| EPIC-03 | [#16](https://github.com/payamoghtanem/Finance-Data-Engineering-Platform/issues/16) | Closed (done) | #37-#39, all closed |
| EPIC-04 | [#17](https://github.com/payamoghtanem/Finance-Data-Engineering-Platform/issues/17) | Open | #40-#48, open |
| EPIC-05 | [#18](https://github.com/payamoghtanem/Finance-Data-Engineering-Platform/issues/18) | Open | #49-#51, open |
| EPIC-06 | [#19](https://github.com/payamoghtanem/Finance-Data-Engineering-Platform/issues/19) | Closed (done) | #52, closed |
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
