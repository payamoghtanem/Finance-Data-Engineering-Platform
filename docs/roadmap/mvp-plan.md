# Roadmap and MVP Plan

**What this document answers:** what ships first, on a laptop, and what comes after — with explicit exit criteria per phase, not a vague "and then we scale"?
**How it differs from its neighbors:** `../architecture/solution-design-document.md` §5 summarizes the three phases briefly; this document is the operational detail — the exact stack, the exact exit checklist, and the explicit cost/complexity trigger for moving to the next phase.

## 1. Why phases exist, and why they must not be skipped

Jumping straight to a Phase 3 stack (Kubernetes, Kafka, managed cloud everything) before a working, validated Phase 1 pipeline exists is one of the most common ways a project like this fails — it spends time and money on infrastructure before anyone has proven the data model, the connectors, or the quality checks are even right. Each phase below exists specifically to de-risk the next one, per `../learning-guide/system-design-guide.md` §3 and §9.

## 2. Phase 1 — Local MVP (laptop)

### Stack

Docker Compose running: Python connectors, PostgreSQL, MinIO, Dagster, dbt Core, DuckDB, Metabase, Prometheus, Grafana. See `../technical/technical-design-document.md` §6 for the compose file shape — it must match this list exactly.

### Scope

One data domain, end to end: **FRED (or World Bank) macro indicator → Raw → Bronze → Silver → Gold → dashboard**, with:
- A registered data contract and `dim_source` entry (license resolved).
- Passing data-quality tests (FR-QUAL-001..009 subset relevant to this dataset).
- A working retry/idempotency implementation (FR-ING-001).
- Basic lineage (Bronze row traceable to its Raw file).
- An audit trail (`ingestion_run`, `data_quality_result` populated).
- A Metabase dashboard consuming the Gold table, never Bronze/Silver directly.

### Exit criteria (all must hold for ≥ 3 consecutive days, unattended)

- [ ] NFR-AVAIL-002: ≥ 95% of scheduled ingestion runs complete without manual intervention.
- [ ] NFR-FRESH-001: the dataset meets its documented freshness SLO.
- [ ] 100% of blocking data-quality tests pass before data reaches Silver/Gold (NFR-GOV-001 subset).
- [ ] A deliberately triggered failure (e.g., simulated API outage) is visible on the operator dashboard within NFR-FRESH-003's detection latency, and recovers via replay (FR-OPS-003) without manual data surgery.
- [ ] No secret appears in Git history (NFR-SEC-003, checked by CI secret scanning).
- [ ] NFR-COST-001: $0 infrastructure spend beyond the operator's existing hardware.

### Explicit non-goals for Phase 1

No Kafka, no Kubernetes, no Keycloak, no Vault, no multi-environment (dev/staging/prod) setup. Introducing any of these early is itself an architecture decision and needs an ADR explaining why the phase boundary was crossed (see `../architecture/CLAUDE.md`).

## 3. Phase 2 — Team-ready

### Trigger to enter this phase

Phase 1's exit criteria are met **and** at least one of: a second team member/contributor joins, a second independently-scaling connector/consumer is genuinely needed, or the platform needs to be shared beyond the operator's own laptop.

### Stack additions

Apache Kafka (event transport — see ADR-0002 for why it waits until here), OpenMetadata (catalog, replacing the Phase-1 Git-based data dictionary), Keycloak (identity/RBAC), HashiCorp Vault (secrets — see ADR-0004), CI/CD via GitHub Actions with enforced data-contract validation, and separate dev/staging/prod environments.

### Scope

Expand from one data domain to the MVP-priority set in `../data-sources/catalog.md` §3 (FRED, World Bank, Eurostat, SEC EDGAR, CoinGecko), each meeting the same Phase 1 exit-criteria bar independently.

### Exit criteria

- [ ] NFR-AVAIL-001/002 targets tightened and met across all connectors in scope.
- [ ] NFR-SEC-004/005: authenticated, role-scoped access; privileged actions attributable to a human identity.
- [ ] NFR-AUDIT-003: audit logs are append-only/tamper-evident.
- [ ] CI blocks any PR that fails lint, secret scanning, unit tests, contract validation, integration tests, or the data-quality suite (`../technical/technical-design-document.md` §5, steps 1–6).
- [ ] NFR-COST-002: Phase 2 infrastructure cost is estimated and explicitly approved before provisioning — no silent cloud spend.

## 4. Phase 3 — Cloud-native production

### Trigger to enter this phase

Phase 2's exit criteria are met **and** there's a genuine production user base or SLA commitment that justifies managed infrastructure cost.

### Stack additions

Managed Kubernetes, real cloud object storage (S3-compatible), GitOps via Argo CD, autoscaling, backup and disaster recovery automation, enterprise IAM integration, 24/7 monitoring/alerting, and Infrastructure as Code (OpenTofu/Terraform) for all provisioning — no hand-edited production infrastructure (`../architecture/ARD.md` §5 IaC row).

### Exit criteria (this is "done," not a further phase)

- [ ] NFR-AVAIL-001/002 targets fully met (99.5%+).
- [ ] NFR-RPO-001/RTO-001: disaster recovery drilled and proven to meet the ≤24h/≤4h targets, not just documented.
- [ ] NFR-COST-003: a documented monthly budget ceiling is reviewed and approved before go-live, and monitored against actual spend afterward.
- [ ] Full three-phase architecture principles from `../architecture/ARD.md` §2 hold with no exceptions, verified by an architecture review referencing the traceability matrix (`../requirements/traceability-matrix.md`).

## 5. What does not change between phases

The architecture shape — Source → Ingest → Raw → Validate → Transform → Serve → Observe & Govern, on a Bronze/Silver/Gold Lakehouse with separated compute/storage — is identical in all three phases. Only the concrete infrastructure realizing each already-designed layer changes. This is the entire point of designing the architecture up front in `../architecture/ARD.md`: phases add operational robustness, they never require redesigning the data model, the API contract, or the event schema.

## 6. Relationship to other documents

- Every checkbox above references a specific NFR/FR ID — see `../requirements/NFR.md` and `../requirements/FRD.md` for the full definition, and `../requirements/traceability-matrix.md` for how they trace back to business goals.
- The Phase 1 stack must match `../technical/technical-design-document.md` §6 exactly.
- Any tool introduced ahead of its documented phase requires a new ADR in `../architecture/decisions/`, per `../roadmap/CLAUDE.md`.
