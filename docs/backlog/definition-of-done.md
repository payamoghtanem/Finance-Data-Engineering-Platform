# Definition of Done (DoD)

**What this document answers:** when may an agent or contributor claim a story is finished?
**How it differs from its neighbors:** `definition-of-ready.md` gates the entry; this gates the exit and is what a reviewer checks against.

"The code runs" is **not** done. Every box below must be true before a PR is merged.

## Specification

- [ ] The behaviour matches the `FR-xxx` it claims to deliver — no silent divergence.
- [ ] If implementation required deviating from a design doc, **the doc was updated in this same PR** (root `CLAUDE.md`, "Docs are the contract").
- [ ] New/changed requirements have a row in `../requirements/traceability-matrix.md`.
- [ ] Any new term is defined in `../00-glossary.md`.

## Tests

- [ ] Tests were written **before** the implementation (`../methodology/edd-sdd-tdd.md`).
- [ ] Unit tests cover the happy path and each failure branch.
- [ ] Idempotency is proven by a test that runs the job twice and asserts identical state.
- [ ] Data-quality tests exist for every contract rule the story touches.
- [ ] Core pipeline line coverage ≥ 80% (NFR-MAINT-003).
- [ ] The `Test` column in the traceability matrix is filled in for the delivered requirement.

## Quality gates

- [ ] Lint, format, and type checks pass.
- [ ] Secret scan passes; no credential in code, config, fixture, or history (NFR-SEC-003).
- [ ] CI is green on the PR head.

## Operability

- [ ] Every failure path routes to the DLQ — no silent drops (FR-OPS-003).
- [ ] The run is visible in the operator dashboard with status and duration (FR-OPS-001).
- [ ] A runbook entry exists for any new connector or service (NFR-MAINT-001).
- [ ] Provenance fields are populated: source, `retrieved_at`, code version, checksum (NFR-AUDIT-001).

## Traceability & state

- [ ] `/STATUS.md` is updated in this PR: the story moved out of "in progress", and §4 "what to do next" reflects reality.
- [ ] The PR description names the story ID and the requirement ID it discharges.
