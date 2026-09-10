# CLAUDE.md — `.claude/`

Harness configuration so that any agent, on any Claude tooling, behaves consistently
in this repository.

- **`settings.json`** — permission allow/deny list. Read-only inspection and the
  project's own check scripts are pre-approved; force-push, recursive delete, and
  reading `.env` / `secrets/` are denied outright.
- **`commands/`** — reusable slash commands:
  - `/status` — where the project stands and what to do next (reports only, never acts).
  - `/new-connector <source>` — scaffolds a connector in the required order, licence gate first.
  - `/check` — runs every gate CI runs and reports pass/fail.

## Adding a command

Keep each command a *procedure*, not a description. It should encode the order of
work from `../docs/methodology/edd-sdd-tdd.md` so an agent cannot accidentally skip
the spec-and-tests-first sequence.

## Note on the deny list

`Read(./.env)` is denied deliberately. Even in a session where the operator trusts the
agent, a secret pulled into a transcript is a secret that has left its boundary
(NFR-SEC-003). Use `.env.example` to learn the shape of the configuration instead.
