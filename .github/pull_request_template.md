## What and why

<!-- What changes, and which problem it solves. Link the story and requirement IDs. -->

- **Story:** US-__-___
- **Requirement:** FR-___-___ / NFR-___-___
- **Epic:** EPIC-__

## Definition of Done

Checked against `docs/backlog/definition-of-done.md`:

- [ ] Behaviour matches the requirement it claims to deliver
- [ ] Any design-doc deviation was updated **in this PR** (docs are the contract)
- [ ] Tests written before implementation; failure branches covered
- [ ] Idempotency proven by a test (if this touches a pipeline)
- [ ] Traceability matrix `Implementation` / `Test` columns updated
- [ ] Lint, type check, secret scan, and CI all green
- [ ] Every failure path routes to the DLQ — no silent drops
- [ ] `STATUS.md` updated to reflect the new state

## Docs touched

<!-- List any doc updated, or write "none - no design surface changed". -->

## Notes for the reviewer

<!-- Anything non-obvious: a rejected alternative, a deliberate limitation, a follow-up. -->
