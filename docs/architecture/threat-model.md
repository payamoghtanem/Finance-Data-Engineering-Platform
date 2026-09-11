# Threat Model (STRIDE Analysis)

## Purpose
This document identifies security threats to the Finance & Economic Data Platform using the STRIDE framework, with mitigations aligned to NFR-SEC requirements.

## System Boundaries

```
┌─────────────────────────────────────────────────────────────┐
│                     External Trust Zone                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │  FRED    │  │ Eurostat │  │  Other   │  Data Sources    │
│  │  API     │  │   API    │  │ Sources  │                  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                  │
│       │             │             │                         │
│       └─────────────┴──────┬──────┘                         │
│                            │                                │
│                   ┌────────▼────────┐                       │
│                   │  Ingestion API  │  Public Endpoint      │
│                   │  (Dagster)      │  (Phase 2: AuthZ)     │
│                   └────────┬────────┘                       │
└────────────────────────────│────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│                    Platform Trust Zone                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │    Bronze    │  │    Silver    │  │     Gold     │       │
│  │   (Raw)      │  │ (Validated)  │  │  (Serving)   │       │
│  │   S3/MinIO   │  │   S3/Iceberg │  │  S3/Material │       │
│  └──────────────┘  └──────────────┘  └──────┬───────┘       │
│                                             │                │
│                                    ┌────────▼────────┐       │
│                                    │   Query Layer   │       │
│                                    │  (Metabase/     │       │
│                                    │   Direct SQL)   │       │
│                                    └────────┬────────┘       │
└─────────────────────────────────────────────│────────────────┘
                                              │
┌─────────────────────────────────────────────▼────────────────┐
│                    Consumer Trust Zone                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                   │
│  │Analysts  │  │Dashboards│  │  Export  │   Users          │
│  └──────────┘  └──────────┘  └──────────┘                   │
└─────────────────────────────────────────────────────────────┘
```

## STRIDE Threat Analysis

### 1. Spoofing (Impersonation)

| ID | Threat | Likelihood | Impact | Mitigation | Status | NFR Ref |
|----|--------|------------|--------|------------|--------|---------|
| SPOOF-01 | Attacker impersonates data source API | Low | High | Mutual TLS, API key validation, certificate pinning | ✅ Phase 1 | NFR-SEC-001 |
| SPOOF-02 | Attacker spoofs internal pipeline component | Medium | High | Service mesh mTLS (Phase 3), container identity | 🟡 Phase 2 | NFR-SEC-002 |
| SPOOF-03 | Unauthorized user accesses Metabase dashboards | Medium | Medium | SSO integration, RBAC in Metabase | 🟡 Phase 2 | NFR-SEC-003 |
| SPOOF-04 | Credential stuffing on Dagster UI | Low | Medium | MFA enforcement, rate limiting | 🟡 Phase 2 | NFR-SEC-001 |

### 2. Tampering (Data Integrity)

| ID | Threat | Likelihood | Impact | Mitigation | Status | NFR Ref |
|----|--------|------------|--------|------------|--------|---------|
| TAMPER-01 | Raw Bronze data modified post-ingestion | Low | Critical | Immutable S3 bucket (Object Lock), SHA-256 checksums | ✅ Phase 1 | NFR-SEC-004 |
| TAMPER-02 | Validation rules bypassed | Medium | High | Code review, signed dbt models, CI enforcement | ✅ Phase 1 | NFR-SEC-004 |
| TAMPER-03 | Gold-layer materializations altered | Low | High | Append-only Iceberg tables, audit logging | 🟡 Phase 2 | NFR-SEC-004 |
| TAMPER-04 | Pipeline code tampered in Git repo | Low | Critical | Branch protection, signed commits, CODEOWNERS | ✅ Phase 1 | NFR-SEC-005 |
| TAMPER-05 | Environment variables injected at runtime | Medium | High | Secrets manager (AWS Secrets Manager), no env vars in Git | ✅ Phase 1 | NFR-SEC-006 |

### 3. Repudiation (Denial of Actions)

| ID | Threat | Likelihood | Impact | Mitigation | Status | NFR Ref |
|----|--------|------------|--------|------------|--------|---------|
| REPUD-01 | Operator denies running manual pipeline | Low | Medium | CloudTrail audit logs, Dagster event log retention | ✅ Phase 1 | NFR-SEC-007 |
| REPUD-02 | Analyst denies exporting sensitive dataset | Medium | Medium | Query logging, export audit trail | 🟡 Phase 2 | NFR-SEC-007 |
| REPUD-03 | Developer denies deploying untested code | Low | High | CI/CD logs, deployment provenance, PR linkage | ✅ Phase 1 | NFR-SEC-005 |

### 4. Information Disclosure (Data Leakage)

| ID | Threat | Likelihood | Impact | Mitigation | Status | NFR Ref |
|----|--------|------------|--------|------------|--------|---------|
| INFO-01 | S3 bucket publicly accessible due to misconfiguration | Medium | Critical | Bucket policies, S3 Block Public Access, Terraform guardrails | ✅ Phase 1 | NFR-SEC-008 |
| INFO-02 | API keys leaked in Git history | Low | High | git-secrets pre-commit hook, GitHub secret scanning | ✅ Phase 1 | NFR-SEC-006 |
| INFO-03 | Query results cached insecurely | Low | Medium | Encrypted Redis cache (Phase 3), TTL enforcement | ⚪ Phase 3 | NFR-SEC-008 |
| INFO-04 | Logs contain PII/sensitive values | Medium | Medium | Log redaction middleware, structured logging schema | 🟡 Phase 2 | NFR-SEC-008 |
| INFO-05 | Metabase shared links expose data | Medium | Medium | Link expiration, access token rotation | 🟡 Phase 2 | NFR-SEC-003 |

### 5. Denial of Service (Availability)

| ID | Threat | Likelihood | Impact | Mitigation | Status | NFR Ref |
|----|--------|------------|--------|------------|--------|---------|
| DOS-01 | FRED API rate limits exceeded | Medium | Medium | Exponential backoff, request queuing, daily quotas | ✅ Phase 1 | NFR-AVAIL-001 |
| DOS-02 | Storage quota exhausted | Low | High | Lifecycle policies, capacity alerts (70% threshold) | ✅ Phase 1 | NFR-AVAIL-002 |
| DOS-03 | Pipeline runs OOM and crashes repeatedly | Medium | Medium | Container memory limits, retry budgets, DLQ | ✅ Phase 1 | NFR-AVAIL-001 |
| DOS-04 | DDoS on public endpoints (Phase 2+) | Low | High | WAF, CloudFront Shield, rate limiting | ⚪ Phase 3 | NFR-AVAIL-003 |
| DOS-05 | Dependency supply chain attack | Low | Critical | Pin versions, Dependabot, private artifact mirror | ✅ Phase 1 | NFR-SEC-009 |

### 6. Elevation of Privilege (Unauthorized Access)

| ID | Threat | Likelihood | Impact | Mitigation | Status | NFR Ref |
|----|--------|------------|--------|------------|--------|---------|
| EOP-01 | Container escapes to host | Low | Critical | Rootless containers, seccomp profiles, minimal base images | 🟡 Phase 2 | NFR-SEC-010 |
| EOP-02 | IAM role over-permissioned | Medium | High | Least privilege principle, IAM Access Analyzer | ✅ Phase 1 | NFR-SEC-010 |
| EOP-03 | dbt user can DROP production tables | Low | Critical | Separate read/write roles, database GRANT restrictions | 🟡 Phase 2 | NFR-SEC-010 |
| EOP-04 | Dagster run launcher executes arbitrary code | Medium | High | Asset allowlist, sandboxed execution environment | 🟡 Phase 2 | NFR-SEC-010 |

## Risk Matrix

```
Impact
  ^
  │
H │  TAMPER-01    INFO-01      SPOOF-01
i │  REPUD-03     DOS-05       EOP-01
g │  TAMPER-04    INFO-02
h │
  │  SPOOF-02     TAMPER-02    EOP-02
M │  REPUD-02     INFO-04      DOS-01
e │  SPOOF-03     INFO-05      EOP-03
d │  REPUD-01     DOS-03       EOP-04
  │               DOS-02
L │               INFO-03
o │
w └──────────────────────────────────────────> Likelihood
     Low          Medium        High
```

## Mitigation Priority

| Priority | Threat IDs | Rationale | Target Phase |
|----------|------------|-----------|--------------|
| P0 (Critical) | TAMPER-01, INFO-01, DOS-05 | Data integrity, public exposure, supply chain | ✅ Phase 1 |
| P1 (High) | SPOOF-01, TAMPER-02, TAMPER-04, EOP-02 | Core security boundaries | ✅ Phase 1 |
| P2 (Medium) | SPOOF-02, SPOOF-03, REPUD-02, INFO-04, INFO-05, DOS-01, DOS-03, EOP-03, EOP-04 | Operational security | 🟡 Phase 2 |
| P3 (Low) | REPUD-01, REPUD-03, INFO-03, DOS-02, EOP-01 | Edge cases, future-scale | ⚪ Phase 3 |

## Compliance Mapping

| Requirement | Control | Evidence |
|-------------|---------|----------|
| SOC 2 CC6.1 | Logical access controls | IAM policies, SSO config |
| SOC 2 CC6.6 | Encryption at rest/in transit | S3 SSE, TLS 1.3 |
| SOC 2 CC7.2 | Intrusion detection | CloudTrail, GuardDuty (Phase 3) |
| GDPR Art. 32 | Data protection by design | Immutability, minimization, audit trails |

## Residual Risks

| Risk | Acceptance Level | Review Date | Owner |
|------|------------------|-------------|-------|
| Single-region deployment (Phase 1) | Medium | Phase 2 kickoff | Platform Lead |
| Manual secret rotation (Phase 1) | Low | Quarterly | DevOps |
| No formal penetration testing | Medium | Before Phase 3 | Security Team |

## Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-09-11 | 1.0 | Platform Team | Initial STRIDE analysis |

---

**Related Documents**: `nfr.md` (NFR-SEC-*, NFR-AVAIL-*), `architecture/security-model.md`, `runbooks/incident-response.md`, `policies/access-control.md`
