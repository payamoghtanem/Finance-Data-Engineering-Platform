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
| FR-OPS-001 (run visibility) | §6 KPI: mean time to detect < 1 hour | §2.4 Omar's journey; AC-P4 | `src/common/ingestion_run.py` (recording only — **partial**: dashboard visibility is EPIC-08, not built yet) | `tests/unit/test_ingestion_run.py`; `tests/unit/test_fred_connector.py::TestIngestionRunRecording` |
| FR-OPS-002 (alerting) | §6 KPI: mean time to detect < 1 hour | §2.4 Omar's journey | — | — |
| FR-OPS-003 (safe replay) | §7 Risk: silent data quality degradation | §2.4 Omar's journey | — | — |

## Non-functional requirements

| Requirement | BRD goal / risk | NFR detail | Implementation verification |
|---|---|---|---|
| NFR-AVAIL-001..003 | §6 KPI: job success rate ≥ 99% | `NFR.md` §1 | — |
| NFR-FRESH-001..003 | §6 KPI: freshness SLO ≥ 95% | `NFR.md` §2 | — |
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
