# Security Policy

## Reporting a vulnerability

Please report security issues privately via GitHub's
[private vulnerability reporting](https://github.com/payamoghtanem/Finance-Data-Engineering-Platform/security/advisories/new)
rather than opening a public issue. Include reproduction steps and the affected component.

## Security posture

This platform's security requirements are specified, not improvised:

- **Non-negotiable principle:** no API key, password, or token may reach Git, Docker
  images, notebooks, or shared config (root `CLAUDE.md`, ARD §2.7).
- **Measurable targets:** `docs/requirements/NFR.md` §5 (NFR-SEC-001 … NFR-SEC-005).
- **Secrets handling:** `.env` in Phase 1, HashiCorp Vault from Phase 2 — see
  `docs/architecture/decisions/ADR-0004-secrets-env-file-then-vault.md`.
- **AI agent boundary:** the in-product agent is read-only with an allow-listed tool
  set and full audit logging — `docs/ai-agent/agentic-ai-design.md`. This is a hard
  boundary, enforced in code, not a guideline.

## Automated controls

- `gitleaks` runs in pre-commit and in CI on every push and pull request (NFR-SEC-003).
- CI fails closed: a detected secret blocks the merge.

## If a secret is committed

1. Treat it as compromised — **rotate it at the provider immediately.** Removing the
   commit does not un-leak it.
2. Then purge it from history and force-rotate any derived credential.
3. Record the incident and the rotation in the PR that remediates it.

## Known gap

A formal threat model does not exist yet. It is tracked as **DEBT-04** in `STATUS.md`
and is a prerequisite for Phase 2.
