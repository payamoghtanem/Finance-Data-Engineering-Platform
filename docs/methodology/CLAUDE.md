# CLAUDE.md — `docs/methodology/`

## Purpose

`edd-sdd-tdd.md` explains how this project is actually *built*, day to day: the combination of Event-Driven Development (EDD), Spec-Driven Development (SDD), and Test-Driven Development (TDD), including the exact order of work and a full sample event flow from `schedule.triggered` to `data_product.ready`.

## Why this matters to you as an agent working in this repo

If you (or another agent) are asked to implement a feature once code exists, the required order is:

1. Write or update the specification first (the relevant FR in `../requirements/FRD.md`, and/or a data contract in `../technical/data-model.md` / `../data-sources/catalog.md`).
2. Write acceptance tests / data-quality tests against that specification.
3. Implement the connector/pipeline/service until the tests pass.
4. Wire it into the event flow so downstream stages only proceed on a validated event (e.g., `raw_data.validated`), never on a bare "the script ran" assumption.
5. Route every failure to a dead-letter queue (DLQ) — silent drops are forbidden.

Skipping straight to step 3 ("vibe coding") is explicitly the anti-pattern this methodology exists to prevent — see `edd-sdd-tdd.md` for why, and `../ai-agent/agentic-ai-design.md` for how this applies specifically to AI-generated code (Spec-as-Source: the spec is the source of truth; code is generated from it, not edited independently of it).

## How this relates to the rest of `docs/`

- EDD's event shapes are formally specified in `../technical/event-schema.md` — this file explains *why* events drive the flow; that file specifies exactly *what* each event looks like.
- SDD's "specification as executable contract" maps directly onto `../requirements/FRD.md` (behavioral spec) and `../technical/data-model.md` / `../data-sources/catalog.md` (data contracts).
- TDD's tests are the acceptance criteria referenced throughout `../requirements/` — a requirement without a corresponding test plan is incomplete.

## Current status

- **This folder:** Stable.
- The order of work here is enforced per-story by `../backlog/definition-of-done.md`.

**Live project state is in `/STATUS.md`, not here** — it records what is done, in
progress, and next. Do not duplicate that state into this file; it will drift.
