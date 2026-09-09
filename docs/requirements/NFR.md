# Non-Functional Requirements (NFR)

**What this document answers:** how well must the system perform — how fast, how available, how secure, how observable, how maintainable — expressed as measurable targets, not adjectives?
**How it differs from its neighbors:** `../requirements/FRD.md` says the system must retry a failed ingestion; this document says how many times, within what latency, and what "available" means numerically.

Every NFR below has an ID (`NFR-<AREA>-<NNN>`), a measurable target, and a phase it applies from (targets tighten across phases; a Phase-1 target is a floor, not a ceiling).

## 1. Availability

| ID | Requirement | Phase 1 target | Phase 3 target |
|---|---|---|---|
| NFR-AVAIL-001 | Internal API uptime | 99.0% (best-effort, single laptop) | 99.5%+ |
| NFR-AVAIL-002 | Scheduled ingestion jobs complete without manual intervention | ≥ 95% of scheduled runs | ≥ 99% |
| NFR-AVAIL-003 | Dashboard availability during business hours | Best-effort | 99.5%+ |

## 2. Freshness

| ID | Requirement | Target |
|---|---|---|
| NFR-FRESH-001 | Daily macro/economic datasets available | By the time declared in that dataset's contract (e.g., "by 22:00 Europe/Berlin on release days") |
| NFR-FRESH-002 | Crypto market data staleness | ≤ 15 minutes behind source under normal operation (subject to the free-tier source's own latency) |
| NFR-FRESH-003 | Freshness breach detection-to-alert latency | < 1 hour (matches BRD KPI) |

## 3. Recovery

| ID | Requirement | Target |
|---|---|---|
| NFR-RPO-001 | Recovery Point Objective — maximum acceptable data loss | ≤ 24 hours of ingested data |
| NFR-RTO-001 | Recovery Time Objective — maximum acceptable service restoration time | ≤ 4 hours for core ingestion/serving services |
| NFR-RTO-002 | A single connector's failure must not block unrelated connectors | 100% isolation — enforced by FRD's separation-of-concerns requirement |

## 4. Performance

| ID | Requirement | Target |
|---|---|---|
| NFR-PERF-001 | Typical Gold-layer dashboard query latency | < 5 seconds |
| NFR-PERF-002 | API p95 response latency for a single-indicator lookup | < 1 second (Phase 1), < 300ms (Phase 3, cached) |
| NFR-PERF-003 | Ingestion connector must not exceed the source's documented rate limit | 0 rate-limit violations per rolling 24h (hard requirement, not best-effort) |

## 5. Security

| ID | Requirement | Target |
|---|---|---|
| NFR-SEC-001 | All external API traffic uses TLS | 100% |
| NFR-SEC-002 | Data at rest is encrypted | 100% of object storage and database volumes from Phase 2 onward; best-effort (host-disk encryption) in Phase 1 |
| NFR-SEC-003 | No secret ever committed to version control | 0 incidents; enforced by automated secret scanning in CI |
| NFR-SEC-004 | API access is authenticated and role-scoped | 100% of non-health-check endpoints |
| NFR-SEC-005 | Every privileged action (schema change, backfill, secret rotation) is attributable to a human identity | 100%, from Phase 2 (RBAC) onward |

## 6. Data governance

| ID | Requirement | Target |
|---|---|---|
| NFR-GOV-001 | Every dataset published as a "data product" has license, trust tier, and owner recorded | 100% |
| NFR-GOV-002 | Every Gold-layer value is traceable to its Bronze raw source | 100%, verified by periodic lineage audit |
| NFR-GOV-003 | Schema changes to a published contract follow the documented change policy (see `../architecture/solution-design-document.md` §4) | 100% — no unannounced breaking change |

## 7. Maintainability

| ID | Requirement | Target |
|---|---|---|
| NFR-MAINT-001 | Every connector has an owner, README, data contract, automated tests, and a runbook entry | 100% before production use |
| NFR-MAINT-002 | New connector onboarding time (from contract-approved to first successful production run) | < 2 working days at Phase 1 scale |
| NFR-MAINT-003 | Test coverage for ingestion/validation/transformation code | ≥ 80% line coverage on core pipeline logic |

## 8. Auditability

| ID | Requirement | Target |
|---|---|---|
| NFR-AUDIT-001 | Every published KPI value is traceable to raw file, code version, and retrieval timestamp | 100% |
| NFR-AUDIT-002 | Every AI agent tool call, prompt, and output is logged | 100%, retained per the retention policy in `../ai-agent/agentic-ai-design.md` |
| NFR-AUDIT-003 | Audit logs are tamper-evident (append-only) | Required from Phase 2 onward |

## 9. Scalability

| ID | Requirement | Target |
|---|---|---|
| NFR-SCALE-001 | Adding a new data source must not require changing the core pipeline architecture | 0 architecture rewrites per new source — only new connector code and contract |
| NFR-SCALE-002 | Storage layer must scale horizontally without a full migration when moving from local to cloud | Guaranteed by Parquet/Iceberg on S3-compatible storage (`../architecture/ARD.md` §2.8) |
| NFR-SCALE-003 | Compute and storage scale independently | Guaranteed by the Lakehouse architecture (ADR-0001) |

## 10. Cost (Phase-aware, honest targets)

| ID | Requirement | Target |
|---|---|---|
| NFR-COST-001 | Phase 1 (local MVP) infrastructure cost | $0 beyond the operator's existing laptop/electricity |
| NFR-COST-002 | Phase 2 (team-ready) infrastructure cost | Must be estimated and explicitly approved before provisioning — no silent cloud spend |
| NFR-COST-003 | Phase 3 (cloud-native) infrastructure cost | Must have a documented monthly budget ceiling reviewed before go-live |

## 11. How these targets are used

- Phase exit criteria in `../roadmap/mvp-plan.md` reference specific NFR IDs — a phase is not "done" if its referenced NFRs are not met.
- `../requirements/traceability-matrix.md` links each NFR to the BRD KPI or business risk it addresses.
- Data-quality-specific NFRs here are enforced mechanically via the FR-QUAL-xxx requirements in `../requirements/FRD.md`, not by manual review.
