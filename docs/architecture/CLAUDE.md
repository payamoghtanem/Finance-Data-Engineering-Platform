# CLAUDE.md — `docs/architecture/`

## Purpose

The "how, at a structural level, and why this way" layer.

- **`ARD.md`** (Architecture Reference & Decisions Document) — the layered reference architecture, the eight non-negotiable architecture principles, the architecture patterns in use (Event-Driven, Medallion/Bronze-Silver-Gold, Lakehouse) and why Lakehouse was chosen over a pure Data Warehouse or a full Data Mesh for this project's scale, plus the tool-selection table with explicit "why / why not."
- **`solution-design-document.md`** — the concrete end-to-end solution: data flow diagram, the specific technology chosen for each layer, alternatives that were considered and rejected (briefly — full reasoning lives in the relevant ADR), and the three-phase deployment shape.
- **`decisions/`** — individual Architecture Decision Records (ADRs), one file per decision, e.g. `ADR-0001-lakehouse-vs-warehouse.md`.

## How these relate to each other

`ARD.md` states principles and patterns that must hold; `solution-design-document.md` shows the concrete instantiation of those principles for this project; `decisions/*.md` is where the actual argument for a specific, consequential, hard-to-reverse choice is recorded, including what was rejected and why. If you're tempted to write more than 2-3 sentences of justification for a choice inside `ARD.md` or `solution-design-document.md`, that justification belongs in an ADR instead, referenced by number.

## ADR rules (strict)

- **Numbered sequentially**, zero-padded: `ADR-0001-...md`, `ADR-0002-...md`.
- **Append-only.** A merged ADR's "Decision" section is never edited after the fact. If circumstances change, write a new ADR with a "Supersedes ADR-000N" note, and edit the old ADR only to add a one-line "Status: Superseded by ADR-000M" banner at the top — the historical reasoning stays intact.
- Every ADR must have: Context, Decision, Alternatives Considered (with why each was rejected), Consequences (including negative ones), and Status.

## How this relates to the rest of `docs/`

- `../requirements/FRD.md` and `../requirements/NFR.md` state *what* the system must do; this folder states *how it's structured* to do it. A requirement should never silently assume an architecture choice that isn't documented here.
- `../technical/` goes one level deeper than this folder: this folder says "Lakehouse with Iceberg on object storage"; `../technical/data-model.md` says the actual table DDL.

## Current status

- **This folder:** Stable — ARD, Solution Design, and ADR-0001..0004 complete.
- Open gaps: no threat model (DEBT-04) and only one diagram (DEBT-02). Use `decisions/ADR-0000-template.md` for any new ADR.

**Live project state is in `/STATUS.md`, not here** — it records what is done, in
progress, and next. Do not duplicate that state into this file; it will drift.
