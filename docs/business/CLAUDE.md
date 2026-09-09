# CLAUDE.md — `docs/business/`

## Purpose

The "why" and "what" layer, before any technology is chosen. Two documents:

- **`BRD.md`** (Business Requirements Document) — why this platform must exist, for whom, what value it creates, what's explicitly out of scope, and what business-level risk it carries. Written for a reader who has never seen a schema and shouldn't need to.
- **`PRD.md`** (Product Requirements Document) — turns the BRD's "why" into "what a user can actually do": personas, journeys, prioritized capabilities, product-level acceptance criteria.

## How these relate to the rest of `docs/`

- Every capability in `PRD.md` should trace to a goal in `BRD.md`.
- Every FR-xxx in `../requirements/FRD.md` should trace to a capability here (see `../requirements/traceability-matrix.md`).
- Nothing here should mention a specific database, message broker, or cloud provider — that's `../architecture/` and `../technical/` territory. If you catch yourself writing "PostgreSQL" in this folder, the sentence belongs elsewhere.

## Editing rules

- Changing scope here (adding/removing an out-of-scope item, adding a KPI) is a BRD-level decision — it should be deliberate, not a side effect of a technical change. If a technical constraint forces a scope change, document that link explicitly (cross-reference the ADR that caused it).
- Personas and journeys in `PRD.md` must stay consistent with the stakeholders listed in `BRD.md` — don't introduce a new persona in one file without the other.
