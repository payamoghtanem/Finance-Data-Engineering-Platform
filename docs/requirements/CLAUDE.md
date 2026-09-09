# CLAUDE.md — `docs/requirements/`

## Purpose

The precise, testable, traceable layer. Four documents:

- **`FRD.md`** (Functional Requirements Document) — exact system behaviors, per data domain, as identified requirements (`FR-ING-xxx`, `FR-QUAL-xxx`, `FR-API-xxx`, ...) in Given/When/Then form.
- **`NFR.md`** (Non-Functional Requirements) — measurable quality targets: availability, freshness, performance, security, RPO/RTO, maintainability, auditability. Every NFR must have a number, not an adjective ("under 5 seconds," not "fast").
- **`SRS.md`** (Software Requirements Specification) — the single reference that ties `../business/BRD.md` → `../business/PRD.md` → `FRD.md` → `NFR.md` together into one coherent, structured document, following the ISO/IEC/IEEE 29148 shape (introduction, overall description, specific requirements, external interfaces, design constraints).
- **`traceability-matrix.md`** — a table: every `FR-xxx` and every `NFR-xxx` maps to the BRD/PRD goal it serves, and (once implementation exists) to the code/test that satisfies it.

## Hard rule: nothing here without a home in the matrix

If you add a requirement to `FRD.md` or `NFR.md`, you **must** add a row to `traceability-matrix.md` in the same change. An orphaned requirement (no traceability row) or an orphaned traceability row (no matching requirement) is a defect in this folder, not a style nitpick.

## How this relates to the rest of `docs/`

- Requirements here describe *what*, never *how*. "The system must retry a transient ingestion failure up to 3 times with exponential backoff" is a valid FR. "The system must use Python's `tenacity` library" is not — that's `../technical/technical-design-document.md`.
- Every FR in a given data domain should be consistent with the source's trust tier and license terms recorded in `../data-sources/catalog.md` — don't write a requirement to redistribute data a source's license forbids.
