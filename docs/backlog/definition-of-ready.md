# Definition of Ready (DoR)

**What this document answers:** when is a story actually safe to start?
**How it differs from its neighbors:** `definition-of-done.md` gates the *exit*; this gates the *entry*.

A story may not be started until **every** box is true. If a box cannot be ticked,
the story goes back to the backlog — starting anyway is how undocumented scope and
silent design drift enter the project.

- [ ] The story has an ID in `user-stories.md` and belongs to an epic in `epics.md`.
- [ ] The story names at least one `FR-xxx` or `NFR-xxx` from `../requirements/`.
- [ ] That requirement has been **read** — the story's summary is not the spec.
- [ ] Acceptance criteria are testable (a machine can decide pass/fail).
- [ ] The story's epic is in the **current phase** per `../roadmap/mvp-plan.md`.
- [ ] Dependencies listed on the epic are complete or explicitly waived.
- [ ] Any new external data source has a resolved licence (`../data-sources/catalog.md` five-question test).
- [ ] If the story introduces a Phase-2/3 tool early, an ADR exists justifying the phase-boundary crossing.
- [ ] If the story changes a schema, API, or event shape, the doc to update is identified up front.
