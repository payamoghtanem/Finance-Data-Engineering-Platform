# CLAUDE.md — `docs/ai-agent/`

## Purpose

`agentic-ai-design.md` is the governing specification for the platform's *own* AI agent feature — not for you (the coding agent reading this repo), but for the in-product agent this platform will eventually expose to end users (analysts, researchers) to help them discover datasets, write queries, and understand data quality/incidents.

## Why this folder exists separately from `../business/PRD.md`

The agent is powerful enough, and risky enough (hallucination, unauthorized action, unbounded tool access), that its constraints need to be a first-class, independently reviewable spec — not a bullet point buried in the product requirements. If you are implementing anything the in-product agent touches, `agentic-ai-design.md` is binding, not advisory.

## The non-negotiable constraints this document enforces

1. The agent is **read-only** by default. Writing, deleting, running a backfill, or changing a schema requires explicit human approval — never agent-initiated.
2. The agent retrieves only from **approved, versioned sources**: the data catalog, data dictionary, runbooks, data contracts, and quality-test results — never free-form web browsing, never unvetted documents.
3. Every tool the agent can call has a **narrow scope and an allow-list** — no general-purpose shell, filesystem, or network access.
4. Every prompt, tool call, decision, output, and referenced data identifier is **audit-logged**.
5. The agent must **never give trading advice or execute trades** — its role is dataset discovery, query generation, data-quality explanation, incident detection, and draft documentation generation only.
6. Every agent response must surface its **data source, data timestamp, known limitations, and a confidence indicator** — never a bare, unattributed number.

## How this relates to the rest of `docs/`

- This is a specialization of the general architecture principles in `../architecture/ARD.md` (especially "secure by default" and "data provenance") applied specifically to an LLM-driven feature.
- If a capability described in `../business/PRD.md` involves the agent, that PRD entry must reference this document, not restate its constraints inline (to avoid drift).
- This document itself follows the Coordinator/Implementor/Verifier adversarial-agent pattern described in `../methodology/edd-sdd-tdd.md` for how *building* the agent's own features should work — don't confuse "how the product's agent behaves at runtime" (this file) with "how we use AI-assisted development to build the platform" (the methodology file).
