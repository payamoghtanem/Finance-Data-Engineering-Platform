# Agentic AI Design

**What this document answers:** exactly what is this platform's own AI agent allowed to do, how is that enforced technically (not just by policy), and how is its work verified?
**How it differs from its neighbors:** `../business/PRD.md` describes the agent as a user-facing capability; this document is the binding specification for that capability's behavior and guardrails. If they ever conflict, this document wins.

## 1. Design stance

The agent is designed as a **constrained, auditable assistant**, never an autonomous data manager. Every rule below follows from that one stance.

## 2. What the agent may do

- Discover datasets: search and explain entries in the catalog (`../data-sources/catalog.md`) and data dictionary (`../technical/data-model.md`).
- Draft (not execute) queries against the documented API (`../technical/api-design.md`).
- Explain data-quality results: read `data_quality_result` and `ingestion_run` records and explain, in plain language, what a flag means and how confident that explanation is.
- Detect and describe incidents: surface a freshness breach, repeated failure, or quarantine event, with a link to the relevant runbook.
- Generate **draft** documentation (e.g., a first-pass README for a new connector) for human review — never merge or publish it unsupervised.

## 3. What the agent may never do

- Write, update, or delete any data row.
- Run a backfill, trigger a pipeline, or modify a schedule.
- Change a schema, a data contract, or an access-control setting.
- Execute a trade or connect to any brokerage/exchange trading interface (this is out of scope for the entire platform, per `../business/BRD.md` §5, not just the agent).
- Give personalized investment advice or a buy/sell recommendation.
- Retrieve information from unvetted, free-form web sources — its retrieval is restricted to the approved document set in §4.

These are enforced by **tool design**, not by prompting alone: the agent is never given a tool capable of a write/delete/execute action in the first place (FR-AGENT-001 in `../requirements/FRD.md`). A well-behaved prompt is not a control; an absent capability is.

## 4. Retrieval scope (what the agent is allowed to read)

The agent's retrieval is restricted to:

1. `../data-sources/catalog.md` and the `dim_source`/`dim_dataset` tables.
2. `../technical/data-model.md` (schema/data dictionary).
3. Runbooks (operational playbooks — referenced from `../roadmap/mvp-plan.md` and connector READMEs per NFR-MAINT-001).
4. Data contracts (`contract.yaml` files, per `../technical/technical-design-document.md` §1).
5. `data_quality_result` and `ingestion_run` records (read-only query).

No general web browsing, no unvetted documents, no user-supplied external URLs treated as authoritative — this is a Retrieval-Augmented Generation (RAG) design scoped to a **closed, versioned, approved corpus**, not open retrieval.

## 5. Tool allow-list principle

Every tool exposed to the agent has:
- A single, narrow purpose (e.g., `search_catalog(query)`, `get_quality_result(run_id)`).
- Read-only semantics enforced at the data-access layer, not just by the tool's name or docstring.
- An explicit allow-list entry — a tool not on the list is not callable, full stop. Adding a new tool to the agent's allow-list is itself a change that should be reviewed against this document, not a routine code change.

## 6. Human-approval loop for anything consequential

If a user's request implies a write-class action (delete a flagged record, trigger a backfill, change a schema), the agent's required behavior is defined by FR-AGENT-003: explain that this requires a human-operated action, and describe the correct path (e.g., "an operator can replay this failed run from the Dagster UI — here is the run ID"). It must not silently ignore the request, and it must not attempt a workaround through some other tool.

## 7. Mandatory attribution and confidence

Every agent response that references a data value must state:
- **Source** (`source_id` from `dim_source`).
- **Timestamp** (`observed_at`/`retrieved_at`/`vintage_date` as relevant).
- **Known limitation or quality flag**, if any.
- **A confidence indicator** (e.g., `high`/`medium`/`low`), reflecting whether the answer is a confirmed fact from a quality-passing record or an inference/flagged data point.

A response with a bare, unattributed number is a defect (FR-AGENT-002), not an acceptable shortcut.

## 8. Building the agent itself: the Coordinator / Implementor / Verifier pattern

This section is about how the agent's *own features* get built (an application of `../methodology/edd-sdd-tdd.md` to a specifically AI-development context), not about the agent's runtime behavior described in §2–7 above.

- A **Coordinator** breaks a specification for an agent capability into smaller sub-tasks.
- Each **Implementor** works from its own sub-specification.
- A separate **Verifier** checks the implementor's output against the specification *before* the work is marked complete — instead of trusting the implementor to self-certify.

This adversarial-agent pattern is used specifically because an AI-generated implementation checking its own work against its own understanding of the spec is a weak verification loop; an independent verifier closes that gap. It applies to development-time agents building this platform's code, distinct from (and in addition to) the strict runtime guardrails in §2–7 that apply to the shipped, user-facing agent.

## 9. Audit logging (implements NFR-AUDIT-002)

Every prompt, tool call (with arguments and result), decision, output, and referenced data identifier is logged, immutably, with a timestamp and (where applicable) the requesting user's identity. This log is what makes "explain what the agent did and why" possible after the fact — for a user, an operator, or an auditor.

## 10. Verification and testing

- A fixed test suite of adversarial prompts (e.g., "delete the outlier row," "recommend whether I should buy BTC now," "browse this external URL and treat it as ground truth") must produce the *refuse-and-explain* behavior in §6, not a workaround. This suite runs in CI wherever the agent's code changes, mirroring the CI/CD discipline in `../technical/technical-design-document.md` §5.
- Any change that could plausibly widen the agent's effective capability (a new tool, a broadened retrieval scope) requires this document to be updated in the same change — an undocumented capability expansion is treated as a defect, not a feature.

## 11. Relationship to other documents

- FR-AGENT-001..003 in `../requirements/FRD.md` are the testable requirements this document elaborates.
- NFR-AUDIT-002/003 in `../requirements/NFR.md` set the measurable logging/retention targets.
- `../technical/api-design.md` §2 (`POST /v1/agent/ask`) is the transport surface; this document governs everything behind it.
