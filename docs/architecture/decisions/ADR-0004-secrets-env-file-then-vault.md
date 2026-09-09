# ADR-0004: `.env` files for Phase 1, HashiCorp Vault (or cloud secrets manager) from Phase 2

**Status:** Accepted

## Context

`../ARD.md` §2.7 (Secure by default) forbids committing secrets to Git, Docker images, notebooks, or shared config. A concrete secrets-management approach is still needed for local development, and must not silently become the production approach by default.

## Decision

Phase 1 (local MVP, single operator): use a git-ignored `.env` file, loaded by Docker Compose and local processes, with `.env.example` (no real values) committed instead so the required variables are documented. Phase 2+ (team-ready and beyond): introduce HashiCorp Vault (or the target cloud provider's managed secrets manager) with rotation, and remove reliance on `.env` files entirely for any shared or deployed environment.

## Alternatives considered

1. **Vault from day one.**
   - Rejected for Phase 1 because: running and operating a Vault instance for a single local operator with no team to grant differentiated access to is pure operational overhead with no corresponding benefit yet, conflicting with the "small MVP first" principle (`../ARD.md` §5) and the over-engineering risk (`../../business/BRD.md` §7).

2. **Secrets hard-coded or placed in a general, committed config file "just for now."**
   - Rejected outright, at any phase — this is precisely what ARD §2.7 exists to forbid. Even in a solo MVP, a committed secret can leak via a public repository, a shared screen, or a later contributor cloning the repo.

3. **`.env` for Phase 1, Vault/cloud secrets manager from Phase 2 (chosen).**
   - Matches the actual risk profile of each phase: Phase 1 has one operator and no shared deployment target; Phase 2 introduces a team and shared environments, at which point secret sprawl and rotation become real risks that a proper secrets manager is built to solve.

## Consequences

- Positive: zero operational overhead in Phase 1; a clear, planned point (Phase 2 entry) at which the more robust approach is adopted, rather than an indefinitely deferred "we'll do it properly later."
- Negative: Phase 1's `.env` approach has no rotation and no audit trail for secret access — accepted for Phase 1 only, explicitly not acceptable once real users or a shared environment exist.
- Enforcement: CI includes secret-scanning (e.g., gitleaks or equivalent) from Phase 1 onward, so this decision does not rely solely on developer discipline — see `../../requirements/NFR.md` security requirements.
