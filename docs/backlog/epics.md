# Epics

**What this document answers:** what are the coarse-grained units of work that turn the frozen design into a running platform, in what order, and which requirement does each one discharge?
**How it differs from its neighbors:** `../roadmap/mvp-plan.md` defines *phases and exit criteria*; this document defines the *work items* inside those phases. `user-stories.md` decomposes each epic below into individually assignable stories.

Epic IDs are stable (`EPIC-nn`) and are referenced by story IDs (`US-nn-nnn`), by
GitHub issues (once seeded), and by `/STATUS.md`.

## Legend

- **Phase** — from `../roadmap/mvp-plan.md`. An epic may not start before its phase.
- **Delivers** — the `FR-xxx` / `NFR-xxx` IDs this epic satisfies. Every epic must have at least one.
- **Depends on** — epics that must be substantially complete first.

## Phase 1 — Local MVP

| Epic | Title | Delivers | Depends on | Est. |
|---|---|---|---|---|
| **EPIC-01** | Repository & environment scaffolding | NFR-MAINT-001, NFR-SEC-003 | — | S |
| **EPIC-02** | FRED connector, end to end (reference implementation) | FR-ING-001, FR-ING-006 | EPIC-01 | L |
| **EPIC-03** | Raw & Bronze storage layer with provenance | FR-ING-001, NFR-AUDIT-001, NFR-GOV-002 | EPIC-01 | M |
| **EPIC-04** | Data-quality rule engine | FR-QUAL-001 … FR-QUAL-009 | EPIC-03 | L |
| **EPIC-05** | Canonical Silver/Gold modelling (dbt) | FR-MODEL-001, FR-MODEL-002, FR-MODEL-003 | EPIC-03, EPIC-04 | L |
| **EPIC-06** | Event backbone (in-process transport, Phase 1) | FR-OPS-003, per ADR-0002 | EPIC-03 | M |
| **EPIC-07** | Orchestration & scheduling (Dagster) | NFR-AVAIL-002, FR-OPS-001 | EPIC-02, EPIC-06 | M |
| **EPIC-08** | Observability, alerting & operator dashboard | FR-OPS-001, FR-OPS-002, NFR-FRESH-003 | EPIC-07 | M |
| **EPIC-09** | DLQ, quarantine & safe replay | FR-OPS-003, FR-ING-001 | EPIC-06 | M |
| **EPIC-10** | Metabase dashboard on Gold | NFR-PERF-001 | EPIC-05 | S |

## Phase 1–2 — Serving

| Epic | Title | Delivers | Depends on | Est. |
|---|---|---|---|---|
| **EPIC-11** | Serving API (FastAPI, `/v1`) | FR-API-001, FR-API-004 | EPIC-05 | L |
| **EPIC-12** | Point-in-time / vintage queries | FR-API-002, FR-MODEL-002 | EPIC-11 | M |
| **EPIC-13** | API authentication & rate limiting | FR-API-003, NFR-SEC-004 | EPIC-11 | M |

## Phase 2 — Team-ready

| Epic | Title | Delivers | Depends on | Est. |
|---|---|---|---|---|
| **EPIC-14** | Remaining MVP-priority connectors (World Bank, Eurostat, SEC EDGAR, CoinGecko) | FR-ING-002 … FR-ING-005 | EPIC-02 | XL |
| **EPIC-15** | Kafka event transport migration | ADR-0002 trigger | EPIC-06 | L |
| **EPIC-16** | Secrets management: `.env` → Vault | NFR-SEC-003, NFR-SEC-005, ADR-0004 | EPIC-01 | M |
| **EPIC-17** | Identity & RBAC (Keycloak) | NFR-SEC-004, NFR-SEC-005 | EPIC-13 | L |
| **EPIC-18** | Data catalog & lineage (OpenMetadata) | NFR-GOV-001, NFR-GOV-002 | EPIC-05 | L |
| **EPIC-19** | Tamper-evident audit logging | NFR-AUDIT-002, NFR-AUDIT-003 | EPIC-16 | M |
| **EPIC-20** | In-product AI agent (read-only, gated) | FR-AGENT-001, FR-AGENT-002, FR-AGENT-003 | EPIC-11, EPIC-18, EPIC-19 | XL |

## Phase 3 — Cloud-native production

| Epic | Title | Delivers | Depends on | Est. |
|---|---|---|---|---|
| **EPIC-21** | Kubernetes deployment + IaC (OpenTofu) | NFR-SCALE-002 | EPIC-15, EPIC-17 | XL |
| **EPIC-22** | Backup, DR & restore drill | NFR-RPO-001, NFR-RTO-001 | EPIC-21 | L |
| **EPIC-23** | GitOps delivery (Argo CD) | NFR-MAINT-002 | EPIC-21 | M |
| **EPIC-24** | Cost monitoring & budget ceiling | NFR-COST-002, NFR-COST-003 | EPIC-21 | M |

## Cross-cutting (runs alongside every phase)

| Epic | Title | Delivers | Est. |
|---|---|---|---|
| **EPIC-00** | Engineering standards, CI/CD & agent configuration | NFR-MAINT-003, NFR-SEC-003 | M |

## Coverage check

Every `FR-xxx` in `../requirements/FRD.md` appears above at least once:

- Ingestion: FR-ING-001 (EPIC-02/03/09), 002–005 (EPIC-14), 006 (EPIC-02).
- Quality: FR-QUAL-001…009 (EPIC-04).
- Modelling: FR-MODEL-001…003 (EPIC-05), FR-MODEL-002 also EPIC-12.
- API: FR-API-001/004 (EPIC-11), 002 (EPIC-12), 003 (EPIC-13).
- Agent: FR-AGENT-001…003 (EPIC-20).
- Ops: FR-OPS-001 (EPIC-07/08), 002 (EPIC-08), 003 (EPIC-06/09).

If you add an FR, add it to an epic here in the same change.
