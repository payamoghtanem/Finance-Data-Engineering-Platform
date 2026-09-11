# STATUS — Living Project State

**This file is the single source of truth for "where is this project right now."**
Read it immediately after the root `CLAUDE.md`. Any agent, on any harness, at any
time, must be able to answer *what is done, what is in progress, and what to pick
up next* from this file alone — without access to a prior chat session.

> **Maintenance rule (binding):** this file is updated **in the same pull request**
> as the work it describes. A PR that completes a task without moving that task's
> row here is incomplete, exactly like an FR without a traceability row.

- **Last updated:** 2026-09-11
- **Current phase:** Phase 1 — Local MVP, **in progress** (EPIC-01 done, EPIC-02 mostly done, EPIC-03 done, EPIC-04 mostly done, EPIC-05 mostly done, EPIC-06 done, EPIC-07 mostly done, EPIC-08 mostly done, EPIC-09 mostly done, EPIC-10 partial). `main` branch-protected. Phase 1 backlog is live as GitHub Issues (§8). 157 unit tests, 91% coverage, plus a real `dbt build` (31 seed/model/test steps), a Gold query-latency check, and `dagster definitions validate` in CI.
- **Active branch:** `Claude-Code-Agent`
- **Runtime code exists:** **Yes.** `src/`, `infra/`, `tests/`, `pipelines/` (Dagster, EPIC-07) all exist.

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
- [x] **EPIC-02 (mostly done)** — FRED connector: fetch, retry/backoff with transient-vs-permanent split, content-addressed immutable raw storage, documented event emission, `ingestion_run` recording for every attempt (success and failure — US-02-005). US-02-004 (idempotent re-run) and US-02-006 (vintage awareness) closed by EPIC-05's Silver model. US-02-002 (scheduled daily fetch) is now **also done**: `pipelines/dagster_project/schedules.py` defines a real daily schedule targeting the fetch job — see EPIC-07 below.
- [x] **EPIC-03** — `S3RawStorage` (real MinIO/S3 backend behind the existing `RawStorage` protocol, US-03-001) and `src/bronze/writer.py` (Bronze lineage — `raw_object_key`/`source_id`/`retrieved_at`/`code_version`, US-03-002; proven to need no network access, US-03-003). `FREDConnector.from_config` now defaults to `S3RawStorage` instead of the local filesystem. Done at the unit-test level only — never run against a *live* MinIO container, only moto-mocked S3 and in-memory DuckDB; first real run happens naturally once EPIC-07 (Dagster) exercises the full local stack.
- [x] **EPIC-06** — `src/events/bus.py`'s `EventBus`: the Phase 1 in-process publish/subscribe transport ADR-0002 calls for. One subscriber raising never stops the others or propagates to the publisher (proven by test). `connectors/fred` and `bronze/writer.py` now actually *publish* through it — not just construct and log an `EventEnvelope`, which is what US-06-001 is really about (a stage advances only on a real published event, never a bare signal). The rest of the documented producers (Dagster, validation, Silver/Gold) don't exist yet, so this bus currently has exactly two real producers and no real consumers — the mechanism is proven, not yet the full flow.
- [x] **EPIC-04** — `src/validation/` (contract loading, the nine FR-QUAL-001..009 rules, `ValidationEngine`): `load_contract()` parses a connector's real `contract.yaml` at runtime (no second hand-copied schema); each rule is a pure function returning `PASSED`/`FAILED`/`FLAGGED`/`SKIPPED`; `ValidationEngine.validate()` runs all nine and publishes `raw_data.validated`/`raw_data.quarantined` through `EventBus` — validation is now the 3rd real event producer (`docs/technical/event-schema.md` §4). **Honest scope limits, not gaps papered over**: FR-QUAL-002/004/006/007 need external context this engine has no independent source for yet (an expected-record calendar, a freshness `max_lag`, dimension-table keys, a source's own count/checksum) and return `SKIPPED` rather than a false pass when it's absent (`docs/technical/technical-design-document.md` §2c has the full table of what/who). Not yet wired as a live consumer of `raw_data.received` — that needs a source-specific payload parser (FRED's raw JSON → the contract's record shape), which doesn't exist for any connector yet; `BronzeWriter` also still isn't rewired onto events (still called directly), deliberately left alone rather than bolting on a second half-finished integration in the same change.
- [x] **EPIC-05 (mostly done)** — `src/transform/dbt_project/` (dbt-duckdb, EPIC-05): reads Bronze **in place** via dbt-duckdb's `attach` (never copies it), conforms it to `fact_economic_observation` (FR-MODEL-001), keeps all six time fields independently populated (FR-MODEL-002), and computes MoM/YoY % change exactly once in `fact_economic_kpi` (FR-MODEL-003) — see `docs/technical/technical-design-document.md` §2d. **Proven against real data, not just written**: `scripts/verify_epic05_acceptance.py` (run in CI's `dbt-transform` job) seeds a synthetic Bronze row through the real `BronzeWriter`, runs `dbt build`, re-runs it against identical data to prove no row duplication, then seeds a later revision and proves it lands as an additional, independently queryable `vintage_date` row with Gold correctly picking the latest one. This closed two previously-blocked EPIC-02 stories for real: **US-02-004** (idempotent re-run) and **US-02-006** (vintage awareness). **Honest scope limits**: only FRED feeds this today — Eurostat conformance needs EPIC-14's connector, not just this table shape; `published_at` is left `NULL` for FRED rather than faked (its JSON exposes no distinct publication timestamp). `dbt build` is now invoked automatically by EPIC-07's `silver_gold_conformance` asset — no longer a manual step.
- [x] **EPIC-07 (mostly done)** — `pipelines/dagster_project/`: three assets (`fred_cpi_raw` → `fred_cpi_bronze` → `silver_gold_conformance`) wire the existing connector, Bronze, and dbt modules into one job, with a daily `ScheduleDefinition` and a Dagster-level `RetryPolicy` on the fetch step (layered above `FREDConnector`'s own per-HTTP-call retry). Closes **US-02-002** (scheduled daily fetch). Dagster's own UI now gives the orchestrated pipeline real run visibility (FR-OPS-001) — status, duration, a failure's logs per run. See `docs/technical/technical-design-document.md` §2e. **Proven, not just written**: `tests/unit/test_dagster_pipeline.py` materializes the fetch→Bronze chain end-to-end against fake resources (no live network/S3/dbt); CI's new `dagster-pipeline` job runs `dagster definitions validate` to catch a structural wiring mistake before merge. **Honest scope limits**: the schedule defaults to `STOPPED` (an operator must deliberately enable it — it fetches from a real external API on every fire); US-07-001's actual acceptance criterion ("≥95% success over ≥3 consecutive days," NFR-AVAIL-002) is a measurement of real elapsed operation that no build or test run can produce — the mechanism is built and validated, the metric is measured once enabled. Also found and fixed a real infra defect along the way: `infra/docker-compose.yml` had a standalone `dbt:` service using the wrong adapter (`dbt-postgres`, not `dbt-duckdb`) that nothing ever invoked, contradicting the file's own header comment and `technical-design-document.md` §6 ("invoked by dagster, not standalone long-running") — removed. `infra/docker-compose.yml`'s `dagster` service still references a `Dockerfile.dagster` that doesn't exist — not fixed here (untestable without a Docker daemon in this session), tracked in §6 debt instead of guessed at.
- [x] **EPIC-08 (mostly done)** — `src/common/alerting.py`: `detect_consecutive_failures`, `detect_freshness_breach`, `detect_blocking_quality_failure` (the three FR-OPS-002 alert conditions) and `emit_alert` (structured JSON ERROR-level log line — the only alert-delivery mechanism `engineering-standards.md` §5 actually specifies for Phase 1; no Prometheus/Grafana/Alertmanager channel exists or is named in any design doc). Wired into the real pipeline as two `@asset_check`s on `fred_cpi_raw` (`pipelines/dagster_project/asset_checks.py`), giving genuine FR-OPS-001 per-check visibility in the Dagster UI alongside FR-OPS-002 alerting — not left orphaned. Also built `src/common/data_quality_result.py` (`DataQualityResultRecorder`), the previously-missing home for `ValidationEngine`'s (EPIC-04) output, implementing `data-model.md` §4's `(test_id, table_name)` composite PK literally as upsert/current-state semantics, not an audit log. Fixed a real doc/code drift along the way: `src/common/logging_config.py` claimed "structured logging" but emitted plain text — rewritten to actually emit structured JSON (`_JSONFormatter`), now actually satisfying `engineering-standards.md` §5. See `docs/technical/technical-design-document.md` §2f. **Scope deliberately chosen by the owner** (asked directly: Docker/Prometheus/Grafana can't be run or verified in this session): build and thoroughly unit-test the detection logic + the one documented delivery mechanism; explicitly skip Grafana dashboard/alert-rule JSON rather than write unverifiable provisioning files. **Honest scope limits**: delivery is JSON-log-only, no live alert-routing to a human exists yet; `detect_blocking_quality_failure` has no real caller since `ValidationEngine` doesn't write to `data_quality_result` yet (deliberately not wired in this change — a second half-finished integration bolted onto EPIC-08's own scope); the `_DEFAULT_MAX_LAG = 48h` freshness threshold is a Phase 1 default, not derived from any per-dataset SLO (FRED's `contract.yaml` `freshness_slo` is free text, same reasoning as `validation/rules.py::check_freshness`).
- [x] **EPIC-09 (mostly done)** — `src/common/dlq.py` (`DLQRecorder`, the `dlq` operational table from `data-model.md` §4) and `src/events/dlq.py` (`attach_dlq`, `replay`) close FR-OPS-003. `attach_dlq()` wires both DLQ paths event-schema.md §3 actually specifies: a subscriber's raised exception, via a new `EventBus.set_dead_letter_handler` hook that replaces silent logging-only failure handling; and `raw_data.quarantined` itself, via an explicit subscription — both land in the same `DLQRecorder`, idempotently on `event_id` (recording the same event twice never creates a second row). `replay()` re-emits `raw_data.received` for a pending entry and marks it `replayed`; calling it twice on the same entry is a no-op the second time, proven by test — the concrete answer to US-09-002's "idempotent, produces no duplicates." Along the way, found and fixed a real doc defect: `technical-design-document.md` §7 had described the `dlq` table as "Iceberg," which was never true of its two sibling operational tables (`ingestion_run`, `data_quality_result` — both plain DuckDB) and contradicts ADR-0003's Iceberg scope (Bronze/Silver/Gold only) — corrected in the same change. **Honest scope limits**: proven against `EventBus` directly (`tests/unit/test_dlq.py`, `tests/unit/test_events_dlq.py`, `tests/unit/test_event_bus.py::TestDeadLetterHandler`), not yet wired into the live Dagster pipeline — same reason `ValidationEngine` itself isn't wired there yet (no source-specific payload parser turning a connector's raw bytes into the contract's record shape exists, so there is no real `raw_data.received`/`raw_data.quarantined` traffic on the live pipeline to attach to). No Docker/Grafana dependency this time — this epic's whole scope was buildable and testable in-process.
- [x] **EPIC-10 (partial, by owner-approved design)** — US-10-001/NFR-PERF-001 split into its verifiable and unverifiable halves rather than guessing at either (owner asked directly, chose "verify the real, testable half only"). **Verified**: `scripts/verify_epic10_gold_query_latency.py` seeds a synthetic multi-year fixture through the real Bronze/dbt path, times the SQL a Gold dashboard card would run against `main_gold.fact_economic_kpi` over 20 repetitions, and asserts median latency under NFR-PERF-001's 5s target — wired into CI's `dbt-transform` job, genuinely running on every push. **Built but unverified**: `scripts/provision_metabase_gold_dashboard.py` provisions a Metabase database connection, a Gold-only SQL card, and a dashboard via Metabase's REST API, idempotently — never run against a live Metabase (no Docker daemon in this session); `tests/unit/test_provision_metabase_gold_dashboard.py` instead proves the request shape/ordering/idempotency against a fake transport, and that the provisioned SQL only ever touches Gold, never Bronze/Silver (the one thing about US-10-001 checkable without Metabase itself). See `docs/technical/technical-design-document.md` §2g. **Honest scope limits**: the latency check uses a laptop-sized synthetic fixture, not real production volumes (no capacity model exists yet, DEBT-03); the provisioning script's real target connection (Postgres cache vs. a DuckDB driver plugin) is an open architecture question the SDD diagram doesn't fully resolve, left open rather than guessed at — see DEBT-11.

## 3. What is in progress

| Item | State | Owner | Notes |
|---|---|---|---|
| US-05-001: Eurostat conformance (2nd source through the canonical shape) | **Not started** | — | Needs EPIC-14's Eurostat connector; FRED's own conformance is done |
| US-07-001: ≥95% unattended success over ≥3 consecutive days | **Mechanism built, metric unmeasured** | human (enable the schedule) | Needs real elapsed operational time — see EPIC-07 in §2 |
| `Dockerfile.dagster` for `infra/docker-compose.yml`'s `dagster` service | **Not started** | — | Referenced by the compose file since EPIC-01 scaffolding; still doesn't exist. Untestable without a Docker daemon in an agent session — see DEBT-09 |
| US-08-001/US-08-002: operator dashboard (Grafana) + live alert routing | **Detection logic done, dashboard/routing not started** | human (needs live Docker/Prometheus/Grafana) | Alert detection + JSON-log delivery built and tested (EPIC-08); no Grafana dashboard or alert-rule JSON exists — untestable without a Docker daemon, see DEBT-10 |
| `ValidationEngine` → `DataQualityResultRecorder` wiring | **Not started** | — | `data_quality_result` table exists (EPIC-08) but nothing writes to it yet; needed for `detect_blocking_quality_failure` to have a real caller |
| US-09-001/US-09-002: DLQ + replay wired into the live Dagster pipeline | **Mechanism built against `EventBus` directly, not yet attached to `pipelines/dagster_project/`** | — | Needs a real consumer of `raw_data.received`/`raw_data.quarantined` on the live pipeline first — same blocker as `ValidationEngine`'s own pipeline wiring (EPIC-04) |
| US-10-001: live Metabase dashboard over Gold | **Provisioning script built and unit-tested against a fake transport, never run against real Metabase** | human (needs live Docker + resolving the Postgres-vs-DuckDB-driver connection question) | See DEBT-11 |
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
9. [x] ~~EPIC-05: Silver/Gold dbt modelling~~ — **Done 2026-09-10** (`src/transform/dbt_project/`; see §2 above). Closed US-02-004 and US-02-006 from EPIC-02 as a side effect, verified against real data.
10. [x] ~~EPIC-07: Dagster project under `pipelines/`~~ — **Done 2026-09-10** (`pipelines/dagster_project/`; see §2 above). Invokes `dbt build` automatically now, closed US-02-002. Did **not** end up wiring `ValidationEngine` into the live pipeline — that needs a source-specific FRED payload parser that still doesn't exist (see EPIC-04's note in §2); an earlier version of this file floated EPIC-07 as fixing that, corrected here since this session's scope was fetch→Bronze→dbt only, not validation.
11. [x] ~~EPIC-08: alerting logic + `data_quality_result` recorder~~ — **Done 2026-09-10** (`src/common/alerting.py`, `src/common/data_quality_result.py`, `pipelines/dagster_project/asset_checks.py`; see §2 above). Owner-selected scope: logic + tests only, no Grafana provisioning (Docker unavailable in this session — see DEBT-10).
12. [x] ~~EPIC-09: DLQ + safe replay~~ — **Done 2026-09-11** (`src/common/dlq.py`, `src/events/dlq.py`; see §2 above). Owner-selected next epic per the dependency graph (EPIC-06 and EPIC-08 both ready). Fully buildable/testable without Docker — no scope deferral needed this time.
13. [x] ~~EPIC-10: Metabase dashboard on Gold~~ — **Partial, 2026-09-11** (`scripts/verify_epic10_gold_query_latency.py`, `scripts/provision_metabase_gold_dashboard.py`; see §2 above). Owner asked directly how to handle the Docker blocker and chose to verify only the real, testable half (NFR-PERF-001's query latency) and write the Metabase provisioning script unverified rather than guess at either.
14. [ ] Write `docs/architecture/capacity-model.md` — data volumes at 12/36 months. NFR targets currently have no load model behind them.
15. [ ] Write `docs/architecture/threat-model.md` — STRIDE pass over ingestion, API, agent, secrets.
16. [ ] Create `runbooks/` + `runbook-template.md` (required by NFR-MAINT-001).
17. [ ] Write `Dockerfile.dagster` (and fix/verify `infra/docker-compose.yml`'s `dagster` service end-to-end) — needs a Docker daemon to validate, not available in this session.
18. [ ] Build the Grafana operator dashboard + alert-rule provisioning that EPIC-08 deliberately deferred — needs a Docker daemon to verify, not available in this session; see DEBT-10.
19. [ ] Run `scripts/provision_metabase_gold_dashboard.py` against a live Metabase once Docker is available, resolving how it connects to Gold (Postgres cache vs. a DuckDB driver plugin) along the way — see DEBT-11.

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
| DEBT-08 | ~~`pipelines/` (Dagster) does not exist; nothing schedules the connector~~ | Medium | **Resolved 2026-09-10** — `pipelines/dagster_project/` exists (EPIC-07); see §2. |
| DEBT-09 | `infra/docker-compose.yml`'s `dagster` service references a `Dockerfile.dagster` that doesn't exist | Medium | Open — needs a Docker daemon to build/verify, not available in an agent session |
| DEBT-10 | No Grafana dashboard or alert-rule provisioning exists despite Prometheus+Grafana being deployed since EPIC-01, and EPIC-08's alert-detection logic (`src/common/alerting.py`) now exists with nowhere to render/route to besides structured logs | Medium | Open — needs a Docker daemon to build/verify a live Grafana instance against, not available in an agent session |
| DEBT-11 | `scripts/provision_metabase_gold_dashboard.py` (EPIC-10) has never been run against a live Metabase instance, and how Metabase actually connects to Gold is an unresolved architecture question — the SDD diagram's "PostgreSQL cache" doesn't exist in code, and ARD.md reserves PostgreSQL for metadata/fast-reads only, not the full Gold volume; Metabase's official image also ships no DuckDB driver | Medium | Open — needs a Docker daemon to test against, not available in an agent session |

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
| EPIC-02 | [#15](https://github.com/payamoghtanem/Finance-Data-Engineering-Platform/issues/15) | Closed (done) | #31-#36, all closed — #32 closed once EPIC-07's schedule existed |
| EPIC-03 | [#16](https://github.com/payamoghtanem/Finance-Data-Engineering-Platform/issues/16) | Closed (done) | #37-#39, all closed |
| EPIC-04 | [#17](https://github.com/payamoghtanem/Finance-Data-Engineering-Platform/issues/17) | Open (mostly done) | #40,#42,#44,#47,#48 closed (rules needing no external context); #41,#43,#45,#46 open (rule logic done, real invocation blocked on EPIC-05/EPIC-07 — see issue comments) |
| EPIC-05 | [#18](https://github.com/payamoghtanem/Finance-Data-Engineering-Platform/issues/18) | Open (mostly done) | #50,#51 closed; #49 open (only FRED feeds the canonical shape — Eurostat needs EPIC-14) |
| EPIC-06 | [#19](https://github.com/payamoghtanem/Finance-Data-Engineering-Platform/issues/19) | Closed (done) | #52, closed |
| EPIC-07 | [#20](https://github.com/payamoghtanem/Finance-Data-Engineering-Platform/issues/20) | Open (mostly done) | #53 open — mechanism built and structurally validated; the ≥95%-over-3-days success metric itself needs real elapsed operation once an operator enables the schedule |
| EPIC-08 | [#21](https://github.com/payamoghtanem/Finance-Data-Engineering-Platform/issues/21) | Open (mostly done) | #54 open (dashboard half of run visibility still missing — Grafana, see DEBT-10); #55 open (alert detection + JSON-log delivery done; no live routing to a human beyond the log line) |
| EPIC-09 | [#22](https://github.com/payamoghtanem/Finance-Data-Engineering-Platform/issues/22) | Open (mostly done) | #56 open (DLQ mechanism done and tested against `EventBus`, not yet attached to the live Dagster pipeline); #57 open (replay built, idempotent, proven by test — same live-pipeline caveat as #56) |
| EPIC-10 | [#23](https://github.com/payamoghtanem/Finance-Data-Engineering-Platform/issues/23) | Open (partial) | #58 open — NFR-PERF-001's query latency verified in CI against a synthetic fixture; the Metabase provisioning script is built and unit-tested but never run against a live instance, see DEBT-11 |
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
