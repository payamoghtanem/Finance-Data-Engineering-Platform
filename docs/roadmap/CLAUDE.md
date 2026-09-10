# CLAUDE.md — `docs/roadmap/`

## Purpose

`mvp-plan.md` is the phased execution plan: Local MVP (laptop, Docker Compose) → Team-ready → Cloud-native Production, each phase with an explicit exit criteria checklist and the exact tool stack for that phase — not a generic "and then we scale" hand-wave.

## Why phases exist and must not be skipped

Jumping straight to the Phase-3 stack (Kubernetes, Kafka, managed cloud everything) before there is a working, validated Phase-1 pipeline is the single most common way this kind of project fails — it burns time and money on infrastructure before anyone has proven the data model, the connectors, or the quality checks are even right. Each phase in `mvp-plan.md` exists specifically to de-risk the next one.

## How this relates to the rest of `docs/`

- Phase exit criteria reference specific NFR targets from `../requirements/NFR.md` (e.g., "Phase 1 exit requires the Freshness NFR to be met for at least 3 consecutive days on the FRED connector").
- The Phase 1 tool stack must match exactly what `../technical/technical-design-document.md`'s `docker-compose` section specifies — if they disagree, that's a defect to fix, not a stylistic difference.
- Introducing a Phase-2/3 tool (Kafka, Kubernetes, Vault, Keycloak) ahead of schedule is itself an architecture decision and should get an ADR in `../architecture/decisions/` explaining why the phase boundary was crossed early.

## Current status

- **This folder:** Stable — three phases with exit criteria.
- Phase 1 not started. Epics are decomposed in `../backlog/epics.md`.

**Live project state is in `/STATUS.md`, not here** — it records what is done, in
progress, and next. Do not duplicate that state into this file; it will drift.
