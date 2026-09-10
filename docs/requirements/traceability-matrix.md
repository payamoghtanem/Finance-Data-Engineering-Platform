# Traceability Matrix

**What this document answers:** for every functional and non-functional requirement, which business goal or product capability does it serve — and (once implementation exists) which code and test satisfy it?
**How it differs from its neighbors:** every other requirements document defines requirements; this one only maps them. Nothing here should restate a requirement's content — link to it.

## How to read this table

`Implementation` and `Test` columns are populated once code exists (Phase 1 implementation, not part of this documentation-only change) — they are included now so the structure is ready, and are marked `—` until then. Adding a new FR/NFR without adding its row here is an incomplete change (see `../CLAUDE.md`).

## Functional requirements

| Requirement | BRD goal (`../business/BRD.md`) | PRD capability (`../business/PRD.md`) | Implementation | Test |
|---|---|---|---|---|
| FR-ING-001 (FRED CPI ingestion) | §4 Eliminates manual data collection; §4 Provenance provable | §3 Must-have: Canonical query API; §2.1 Ana's journey | `src/connectors/fred/connector.py` (fetch, raw store via `S3RawStorage`, retry, `ingestion_run` recording) + `src/bronze/writer.py` (Bronze lineage) — **partial**: fact-table idempotency (`fact_economic_observation` deduplication) needs the Silver layer, EPIC-05, not built yet | `tests/unit/test_fred_connector.py::TestRetryBehaviour`, `::TestRawStorage`, `::TestIngestionRunRecording`; `tests/unit/test_s3_raw_storage.py`; `tests/unit/test_bronze_writer.py`; `tests/unit/test_ingestion_run.py` |
| FR-ING-002 (World Bank ingestion) | §4 Eliminates manual data collection | §3 Must-have: Dataset catalog & search | — | — |
| FR-ING-003 (Eurostat SDMX ingestion) | §4 Reproducible analysis | §2.1 Ana's journey (aligned inflation comparison) | — | — |
| FR-ING-004 (SEC EDGAR ingestion) | §4 Provenance provable | §3 Must-have: Canonical query API | — | — |
| FR-ING-005 (CoinGecko ingestion) | §4 Eliminates manual data collection | §2.2 Dev's journey (BTC OHLCV via API) | — | — |
| FR-ING-006 (connector onboarding gate) | §7 License/legal risk mitigation | §3 Should-have: self-service onboarding (Phase 3) | `src/connectors/fred/contract.yaml` | `.github/workflows/ci.yml` job `contracts` |
| FR-QUAL-001..009 (data quality controls) | §6 KPI: data-quality test pass rate = 100% blocking | §3 Must-have: data-quality visibility | `src/validation/rules.py` (all 9 rules), `src/validation/engine.py` (`ValidationEngine`, publishes `raw_data.validated`/`raw_data.quarantined`), `src/validation/contract.py` (`load_contract`) — **partial**: FR-QUAL-001/003/005/008/009 run against per-batch context alone; FR-QUAL-002/004/006/007 need external context (expected-record calendar, freshness budget, dimension keys, source counts) this engine has no independent source for yet and are honestly `SKIPPED` without it — see `src/validation/rules.py` module docstring. Not yet wired as a consumer of `raw_data.received` (needs a source-specific payload parser, none exists) | `tests/unit/test_contract.py`, `tests/unit/test_validation_rules.py`, `tests/unit/test_validation_engine.py` |
| FR-MODEL-001 (canonical conformance) | §4 Reproducible analysis across sources | §2.1 Ana's journey (aligned charts) | `src/transform/dbt_project/models/silver/fact_economic_observation.sql` — conforms Bronze into `fact_economic_observation`, routed source-agnostically via `seeds/seed_dataset_indicator_map.csv` — **partial**: only FRED feeds it today; Eurostat conformance is proved once EPIC-14 builds that connector, not before | `src/transform/dbt_project/tests/assert_fact_economic_observation_pk_unique.sql`; verified via `dbt build` against a real Bronze row (`scripts/seed_bronze_fixture.py`), including a second revision to prove `vintage_date` correctness — see technical-design-document.md §2d |
| FR-MODEL-002 (time field discipline) | §1 Business problem: look-ahead bias | §2.3 Rae's journey (point-in-time query) | `fact_economic_observation.sql` populates `period`/`period_start`/`period_end`/`vintage_date`/`retrieved_at`/`processed_at` independently; `published_at` is left `NULL` for FRED rather than faked — see the model's `schema.yml` | `src/transform/dbt_project/tests/assert_fact_economic_observation_time_fields_distinct.sql` |
| FR-MODEL-003 (versioned KPI definitions) | §4 Provenance provable | AC-P3 (consistent chart sourcing) | `src/transform/dbt_project/models/gold/fact_economic_kpi.sql` — MoM/YoY % change computed exactly once | Verified via `dbt build`: MoM/YoY values checked by hand against the fixture's known inputs — see technical-design-document.md §2d |
| FR-API-001 (documented versioned API) | §4 One API instead of N | §3 Must-have: canonical query API | — | — |
| FR-API-002 (point-in-time queries) | §1 Business problem: look-ahead bias | §2.3 Rae's journey; AC-P2 | — | — |
| FR-API-003 (auth & rate limiting) | §7 Risk: none listed directly — enforces NFR-SEC-004 | — | — | — |
| FR-API-004 (quality status surfaced) | §4 Provenance provable | §3 Must-have: data-quality visibility; AC-P3 | — | — |
| FR-AGENT-001 (read-only agent) | §5 Stakeholder: AI Agent (scoped); §7 Risk: hallucination/scope creep | §5: Won't-have — unrestricted AI write access | — | — |
| FR-AGENT-002 (mandatory attribution) | §4 Provenance provable | AC-P5 | — | — |
| FR-AGENT-003 (escalation not silent action) | §7 Risk: hallucination/scope creep | §2.5 Ana's journey (agent explains limits) | — | — |
| FR-OPS-001 (run visibility) | §6 KPI: mean time to detect < 1 hour | §2.4 Omar's journey; AC-P4 | `src/common/ingestion_run.py` (recording); `pipelines/dagster_project/` (EPIC-07) gives the orchestrated pipeline real status/duration/failure-link visibility through Dagster's own UI (`dagster dev`); `pipelines/dagster_project/asset_checks.py` (EPIC-08) adds per-run pass/fail visibility for each FR-OPS-002 alert condition in that same UI; `src/common/data_quality_result.py` (EPIC-08) gives `ValidationEngine` output a queryable home — **partial**: a dedicated cross-cutting operator dashboard (Grafana, EPIC-08) still doesn't exist; nothing calls `DataQualityResultRecorder.record` yet | `tests/unit/test_ingestion_run.py`; `tests/unit/test_fred_connector.py::TestIngestionRunRecording`; `tests/unit/test_dagster_pipeline.py`; `tests/unit/test_dagster_asset_checks.py`; `tests/unit/test_data_quality_result.py` |
| FR-OPS-002 (alerting) | §6 KPI: mean time to detect < 1 hour | §2.4 Omar's journey | `src/common/alerting.py` (`detect_consecutive_failures`, `detect_freshness_breach`, `detect_blocking_quality_failure`, `emit_alert`); wired into the real pipeline via `pipelines/dagster_project/asset_checks.py` — **partial**: delivery is a structured JSON ERROR log line (no Prometheus/Grafana/Alertmanager channel exists or is specified in any design doc for Phase 1 — see `technical-design-document.md` §2f); `detect_blocking_quality_failure` has no real caller yet since `ValidationEngine` doesn't write to `data_quality_result` | `tests/unit/test_alerting.py`, `tests/unit/test_dagster_asset_checks.py` |
| FR-OPS-003 (safe replay) | §7 Risk: silent data quality degradation | §2.4 Omar's journey | `src/common/dlq.py` (`DLQRecorder` — the `dlq` operational table, idempotent on `event_id`); `src/events/dlq.py` (`attach_dlq` wires both DLQ paths — a raising subscriber via `EventBus.set_dead_letter_handler`, and `raw_data.quarantined` itself — into the recorder; `replay` re-emits `raw_data.received` and is idempotent: replaying an already-replayed entry is a no-op) — **partial**: proven against `EventBus` directly, not yet wired into the live Dagster pipeline (`pipelines/dagster_project/`), since nothing there yet consumes `raw_data.received`/`raw_data.quarantined` for real (see FR-QUAL-001..009's note above) | `tests/unit/test_dlq.py`, `tests/unit/test_events_dlq.py`, `tests/unit/test_event_bus.py::TestDeadLetterHandler` |

## Non-functional requirements

| Requirement | BRD goal / risk | NFR detail | Implementation verification |
|---|---|---|---|
| NFR-AVAIL-001..003 | §6 KPI: job success rate ≥ 99% | `NFR.md` §1 | NFR-AVAIL-002: `pipelines/dagster_project/schedules.py` — daily schedule + a Dagster-level `RetryPolicy` on the fetch asset, layered above `FREDConnector`'s own per-call retry — **partial**: the ≥95%-over-≥3-consecutive-days success rate itself is a measurement of real elapsed operation, not something any single build/test run can produce; the mechanism is built and structurally validated (`tests/unit/test_dagster_pipeline.py`, `dagster definitions validate` in CI), the metric is measured once an operator enables the schedule |
| NFR-FRESH-001..003 | §6 KPI: freshness SLO ≥ 95% | `NFR.md` §2 | NFR-FRESH-003 (<1h detection-to-alert latency): `src/common/alerting.py::detect_freshness_breach`, wired via `pipelines/dagster_project/asset_checks.py::fred_cpi_freshness_check` — met by construction, since the check is a synchronous read-then-alert with no queueing of its own; the ≥95%-freshness SLO itself (NFR-FRESH-001/002) is a measurement of real elapsed operation, not verifiable from a single build/test run | `tests/unit/test_alerting.py::TestDetectFreshnessBreach`, `tests/unit/test_dagster_asset_checks.py::TestFreshnessCheck` |
| NFR-RPO-001, NFR-RTO-001..002 | §6 KPI: recovery time < 4h | `NFR.md` §3 | — |
| NFR-PERF-001..003 | §4 Value proposition: reproducible, fast analysis | `NFR.md` §4 | — |
| NFR-SEC-001..005 | §7 Risk: secret leakage, license/legal exposure | `NFR.md` §5 | `tests/unit/test_fred_connector.py::TestSecretHandling` (NFR-SEC-003); gitleaks in CI |
| NFR-GOV-001..003 | §6 KPI: 100% complete metadata | `NFR.md` §6 | `src/bronze/writer.py` (lineage columns: `raw_object_key`, `source_id`, `retrieved_at`, `code_version`); `tests/unit/test_bronze_writer.py::TestBronzeWrite::test_lineage_round_trip` (NFR-GOV-002) |
| NFR-MAINT-001..003 | §7 Risk: over-engineering / unsustainable solo maintenance | `NFR.md` §7 | — |
| NFR-AUDIT-001..003 | §4 Provenance provable; §7 Risk: AI agent scope creep | `NFR.md` §8 | `tests/unit/test_fred_connector.py::TestRawStorage::test_checksum_matches_original_payload`; `tests/unit/test_bronze_writer.py::TestBronzeWrite::test_checksum_mismatch_raises` (independently recomputed checksum, not trusted from the caller) (NFR-AUDIT-001) |
| NFR-SCALE-001..003 | §1 Vision: laptop → cloud without rewrite | `NFR.md` §9 | — |
| NFR-COST-001..003 | §7 Risk: cloud cost growth outpacing value | `NFR.md` §10 | — |

## Architecture decisions referenced by requirements

| ADR | Requirements it directly enables/constrains |
|---|---|
| ADR-0001 (Lakehouse over Warehouse/Mesh) | NFR-SCALE-002/003, NFR-COST-001 |
| ADR-0002 (defer Kafka) | FR-OPS-003, NFR-MAINT-002, NFR-COST-001 |
| ADR-0003 (Iceberg over Delta) | NFR-SCALE-002, FR-QUAL-007 (reconciliation via snapshots) |
| ADR-0004 (`.env` then Vault) | NFR-SEC-003, NFR-SEC-005 |

## Maintenance rule

This file is updated in the same change as any addition/removal in `FRD.md` or `NFR.md`. A pull request that touches either file without a corresponding update here should be treated as incomplete in review.
