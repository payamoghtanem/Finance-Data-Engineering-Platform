# CLAUDE.md — `docs/engineering/`

## Purpose

How code in this repository is written, reviewed, tested, and shipped. Everything
else under `docs/` describes *the system*; this folder describes *the craft standard*
applied to building it.

- **`engineering-standards.md`** — language/version, layout, naming, typing, error
  handling, logging, secrets, commits, branches, review. The binding coding standard.
- **`test-strategy.md`** — the test pyramid for a data platform, what each layer
  covers, and how tests map back to `FR-xxx` IDs.

## Why this is separate from `../technical/`

`../technical/` specifies **what to build** (this table, this endpoint, this event).
This folder specifies **how any code is written**, regardless of what it does. A
change to the data model belongs there; a change to the lint rules belongs here.

## Binding-ness

These standards are enforced mechanically in CI (`.github/workflows/ci.yml`), not by
reviewer memory. If a rule here cannot be automated, say so explicitly in the rule —
an unenforceable standard is a wish, not a standard.
