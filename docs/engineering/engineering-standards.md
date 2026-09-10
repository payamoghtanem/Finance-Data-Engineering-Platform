# Engineering Standards

**What this document answers:** what is the required standard for any code committed to this repository?
**How it differs from its neighbors:** `../technical/technical-design-document.md` says what to build; this says how it must be written. `../backlog/definition-of-done.md` is the per-story checklist that enforces these rules.

> **Status:** these standards apply from the first line of runtime code (EPIC-01).
> No runtime code exists yet, so nothing here is retroactive.

## 1. Language and tooling

| Concern | Choice | Enforced by |
|---|---|---|
| Language | Python 3.11+ | `pyproject.toml` `requires-python` |
| Formatting | `ruff format` (Black-compatible), line length 100 | pre-commit + CI |
| Linting | `ruff` (pycodestyle, pyflakes, isort, bugbear, comprehensions) | pre-commit + CI |
| Typing | `mypy --strict` on `src/` | CI |
| Testing | `pytest` + `pytest-cov` | CI |
| Data quality | Great Expectations or Soda Core suites under `tests/data_quality/` | CI |
| Dependency pinning | `pyproject.toml` + a committed lockfile | CI |
| Secrets scanning | `gitleaks` (or `detect-secrets`) | pre-commit + CI |

**Rationale for `mypy --strict`:** this is a data platform where a silently wrong
type (a string where a `decimal` belongs) corrupts stored history rather than
crashing loudly. Static typing is a data-integrity control here, not style.

## 2. Repository layout

Exactly as specified in `../technical/technical-design-document.md` §1. Do not
invent new top-level directories without updating that document in the same change.

Every `src/connectors/<name>/` package must contain (NFR-MAINT-001):
`README.md`, `contract.yaml`, `connector.py`, `tests/`.

## 3. Naming

| Thing | Convention | Example |
|---|---|---|
| Module / package | `snake_case` | `sec_edgar` |
| Class | `PascalCase` | `FredConnector` |
| Function / variable | `snake_case` | `fetch_series` |
| Constant | `UPPER_SNAKE_CASE` | `MAX_RETRIES` |
| Database table | `snake_case`, `dim_` / `fact_` prefix | `fact_economic_observation` |
| Event type | `noun.past_tense_verb` | `raw_data.validated` |
| Test | `test_<unit>_<condition>_<expected>` | `test_retry_on_timeout_stops_after_three` |

Names must match `../00-glossary.md`. A new domain term is added there in the same change.

## 4. Error handling

1. **Never swallow an exception.** No bare `except:`; no `except Exception: pass`.
2. **Distinguish transient from permanent.** Transient (5xx, timeout, reset) → retry with backoff per TDD §3. Permanent (4xx, contract violation) → **do not retry**; quarantine and route to DLQ.
3. **Never silently drop a record.** Every rejected record produces a `raw_data.quarantined` event and a `data_quality_result` row (FR-OPS-003).
4. **Fail closed on validation.** An unknown code, an unresolvable FK, or a missing unit fails the record — it is never guessed, coerced, or defaulted (FR-QUAL-001, FR-ING-003).
5. Custom exceptions inherit from a package base (`PlatformError`), so callers can catch by category.

## 5. Logging and observability

- Structured JSON logs; no `print()` in `src/`.
- Every log line in a pipeline carries `run_id`, `connector`, `source_id`, `code_version`.
- **Never log a secret, API key, token, or full credentialed URL.** Redact query strings that may carry keys.
- Log levels: `ERROR` = human action needed; `WARNING` = self-healing but notable; `INFO` = lifecycle events; `DEBUG` = developer detail, off in production.

## 6. Secrets

- Configuration comes from environment variables, loaded once in `src/common/config.py`.
- `.env` is git-ignored; `.env.example` is committed with **placeholder values only**.
- No secret in code, fixtures, notebooks, docker images, or CI logs (NFR-SEC-003).
- Phase 1 uses `.env`; Phase 2 migrates to Vault per ADR-0004.

## 7. Determinism and idempotency

- Never use "now" implicitly inside pipeline logic — pass an explicit run timestamp so runs are reproducible and testable.
- Every write is an upsert on the contract-declared key (TDD §4).
- Re-running any job must leave state identical (FR-ING-001). This must be covered by a test, not asserted by hand.

## 8. Git and review

- Branch from `main`; develop on a feature branch (agents: `Claude-Code-Agent`).
- Commit messages: imperative mood, explain **why** in the body, reference the story/requirement ID (`US-02-003`, `FR-ING-001`).
- **Never force-push a shared branch; never rewrite merged history; never skip hooks.**
- Every PR: green CI, a filled-in PR template, and the `definition-of-done.md` checklist satisfied.
- Docs and code change together — a PR that diverges code from a design doc without updating it is incomplete.

## 9. What CI blocks

A PR cannot merge if any of these fail (mirrors `../technical/technical-design-document.md` §5):

1. Format / lint
2. Type check
3. Secret scan
4. Unit tests + coverage floor (≥ 80% on core pipeline logic)
5. Data-contract validation
6. Data-quality suite
7. Documentation link check
