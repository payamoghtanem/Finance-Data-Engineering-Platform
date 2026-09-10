# CLAUDE.md — `docs/backlog/`

## Purpose

This folder is the bridge between **design** (`../requirements/`) and **execution**.
Everything else under `docs/` says *what the system must be*; this folder says
*who does what, in what order, and how we know it's finished*.

- **`epics.md`** — the coarse work breakdown. Every epic carries the `FR-xxx` /
  `NFR-xxx` IDs it delivers, a phase, and a dependency list.
- **`user-stories.md`** — epics decomposed into `US-<epic>-<nnn>` stories in
  "As a … I want … so that …" form, each with acceptance criteria and its
  source requirement ID.
- **`definition-of-ready.md`** / **`definition-of-done.md`** — the gates a story
  passes through. These are what stop an agent from declaring victory early.

## The rule this folder enforces

**No orphan work.** Every story traces up to an epic, every epic traces up to at
least one `FR-xxx` or `NFR-xxx` in `../requirements/`. A story with no requirement
ID is either undocumented scope (fix the FRD first) or work that shouldn't happen.

This mirrors the existing rule in `../requirements/CLAUDE.md`: there, no requirement
exists without a traceability row; here, no *task* exists without a requirement.

## How this relates to the rest of `docs/`

- Upstream: `../requirements/FRD.md` and `NFR.md` supply the IDs.
  `../requirements/traceability-matrix.md` is where the eventual
  Implementation/Test columns get filled in as stories complete.
- Upstream: `../roadmap/mvp-plan.md` supplies the phase boundaries and exit
  criteria. An epic's phase must not contradict the roadmap.
- Sideways: `../engineering/engineering-standards.md` defines the code quality bar
  referenced by the Definition of Done.
- Live state: `/STATUS.md` at repo root records which of these are actually done.
  **Update `STATUS.md` in the same PR as the work**, not afterwards.

## For agents picking up work

1. Read `/STATUS.md` §4 for the ordered next actions.
2. Find the story in `user-stories.md`; read its acceptance criteria and FR ID.
3. Read the FR itself in `../requirements/FRD.md` — the story is a summary, the FR is binding.
4. Follow the order in `../methodology/edd-sdd-tdd.md`: spec → tests → implementation → event wiring → DLQ.
5. Before opening a PR, check `definition-of-done.md` line by line.
