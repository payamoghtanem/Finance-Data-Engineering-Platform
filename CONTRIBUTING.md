# Contributing

This repository is built to be worked on by **humans and AI agents interchangeably**,
across different tools and sessions. The rules below are what make that possible.

## Before you start

1. Read `STATUS.md` — it is the single source of truth for what is done and what is next.
2. Read the root `CLAUDE.md` — orientation and the non-negotiable architecture principles.
3. Read the `CLAUDE.md` in the folder you're about to touch.
4. Find your story in `docs/backlog/user-stories.md` and check `docs/backlog/definition-of-ready.md`.

## The order of work (non-negotiable)

From `docs/methodology/edd-sdd-tdd.md`:

1. **Spec first** — write or update the requirement / data contract.
2. **Tests second** — acceptance and data-quality tests against that spec.
3. **Implementation third** — until the tests pass.
4. **Wire the event** — downstream stages advance only on a validated event.
5. **Route failures to the DLQ** — silent drops are forbidden.

Skipping to step 3 is the anti-pattern this project explicitly exists to prevent.

## Docs are the contract

If code needs to diverge from a design doc, **update the doc in the same pull request.**
Code that silently disagrees with `docs/technical/data-model.md` or `api-design.md` is a
bug in the code, not evidence the doc was wrong.

## Local setup

```bash
cp .env.example .env          # fill in real values; never commit this file
pip install -e ".[dev]"
pre-commit install
```

Run the checks the CI runs:

```bash
ruff check src tests && ruff format --check src tests
mypy src
pytest tests/unit
./scripts/check_doc_links.sh
./scripts/check_traceability.sh
```

## Git workflow

- Branch from `main`. Agents develop on `Claude-Code-Agent`.
- Commit messages: imperative mood, and reference the story/requirement ID.
- Push with `git push -u origin <branch>`.
- Never force-push a shared branch, rewrite merged history, or skip hooks.

## Before opening a pull request

Work through `docs/backlog/definition-of-done.md` line by line, and update `STATUS.md`
in the same PR. A PR that completes work without moving its row in `STATUS.md` is
incomplete — that file is how the next agent, on a different tool, knows where things stand.

## Adding a data source

A source is not usable just because it is free or reachable. It must pass the
five-question test in `docs/data-sources/CLAUDE.md`, and a source that fails the
licence question is never wired into a connector, however good the data looks.
Web scraping is not an acceptable production ingestion method in this project.
