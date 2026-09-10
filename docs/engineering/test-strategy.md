# Test Strategy

**What this document answers:** what kinds of tests exist, what each layer is responsible for, and how a test proves a specific requirement?
**How it differs from its neighbors:** `../backlog/definition-of-done.md` says tests must exist; this says *which* tests, *where* they live, and *what* they may assume.

## 1. Why a data platform needs a different pyramid

In a normal application a bug crashes. In a data platform a bug **silently stores a
wrong number that someone later trades on.** Correctness therefore has to be
asserted about *data at rest*, not only about functions. That is why a fourth layer
(data-quality tests) sits alongside the usual three, and why it runs continuously in
production, not only in CI.

## 2. Layers

| Layer | Location | Scope | May touch network? |
|---|---|---|---|
| Unit | `tests/unit/` | One function/class. Parsing, retry logic, key derivation, transformations. | **No** — fixtures only |
| Integration | `tests/integration/` | Component + real local dependency (Postgres, MinIO) via compose. | Local services only; **no external APIs** |
| Contract | `tests/integration/contracts/` | A connector's declared `contract.yaml` vs. a recorded real response. | No — recorded fixtures |
| Data quality | `tests/data_quality/` | Assertions about stored data (completeness, uniqueness, ranges, freshness). | Runs in CI **and** in the pipeline |

External APIs are never called in CI: they are rate-limited, flaky, and would make
the suite non-deterministic. Real responses are captured once as fixtures and
refreshed deliberately.

## 3. Mapping tests to requirements

Every `FR-xxx` must be provable by at least one test, and the test path is recorded
in the `Test` column of `../requirements/traceability-matrix.md` as it is written.

| Requirement | Test layer | Asserts |
|---|---|---|
| FR-ING-001 (retry/backoff) | Unit | 3 retries on 5xx/timeout; **no** retry on 4xx |
| FR-ING-001 (idempotency) | Integration | Job run twice → identical row count and content |
| FR-ING-001 (raw-before-parse) | Integration | Raw object with checksum exists before any Bronze row |
| FR-ING-003 (SDMX codes) | Unit | Unknown dimension code fails validation, is not guessed |
| FR-QUAL-001…009 | Data quality | One suite per rule; blocking rules stop promotion to Silver/Gold |
| FR-MODEL-002 (time discipline) | Unit + data quality | Six timestamp fields present and independently populated |
| FR-API-001…004 | Integration | Schema, auth, rate limit, and quality status on every value |
| FR-AGENT-001 | Unit | The agent's tool registry contains **no** write-capable tool |
| FR-OPS-003 (replay) | Integration | Forced failure → DLQ → replay → no duplicates |

## 4. Coverage

- ≥ 80% line coverage on `src/connectors`, `src/validation`, `src/transform` (NFR-MAINT-003).
- Coverage is a floor, not a goal. A connector at 95% coverage with no idempotency test is **not** done.

## 5. Fixtures

- Recorded API responses live in `tests/fixtures/<source>/`, committed, with the capture date in the filename.
- Fixtures must be scrubbed of any API key before commit.
- A fixture refresh is its own PR, so a schema drift is visible as a reviewable diff.

## 6. What is intentionally not tested

- Third-party library internals.
- The external source's own correctness — that is what FR-QUAL-007 (reconciliation) monitors in production, not something CI can assert.
