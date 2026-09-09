# Methodology: Combining Event-Driven, Spec-Driven, and Test-Driven Development

**What this document answers:** how, specifically, do Event-Driven Development (EDD), Spec-Driven Development (SDD), and Test-Driven Development (TDD) combine on this project — what does each contribute, and in what order does work actually happen?
**How it differs from its neighbors:** `../architecture/ARD.md` §4.1 explains EDD as an *architecture pattern* (why the system is shaped around events); this document explains the three methodologies together as a *development process* — how a feature actually gets built, day to day.

## 1. Why combine all three, and what each one answers

| Methodology | Core question it answers | What it produces |
|---|---|---|
| **Spec-Driven Development (SDD)** | What, exactly, does the system commit to doing? | Requirement, API contract, data contract, acceptance criteria |
| **Test-Driven Development (TDD)** | How do we prove it works, mechanically? | Unit tests, integration tests, data-quality tests |
| **Event-Driven Development (EDD)** | What event triggers what process, and what happens on failure? | Event schema, topic/transport, consumer, retry policy, DLQ |

None of the three alone is sufficient for this kind of system: SDD alone produces well-specified but unverified behavior; TDD alone produces verified but potentially poorly-specified behavior (tests for the wrong thing, correctly); EDD alone produces a decoupled system with no guarantee any individual stage does the right thing. Combined, they produce a system that is specified, verified, and safely decoupled.

## 2. Spec-Driven Development in detail

SDD treats a specification as an **executable contract**, not passive documentation — increasingly literal in an AI-assisted development context, where an AI coding agent generates code *from* the specification rather than the specification merely describing code written by intuition. This is what prevents **architectural drift**: the gradual divergence between documented design and actual system behavior that happens when documentation is descriptive-only and nobody enforces it.

### 2.1 Three levels of SDD maturity

| Level | Description | Where this project is/aims to be |
|---|---|---|
| **Spec-First** | A good specification is written first, then used to guide one task's AI-assisted development | Baseline requirement for every FR in `../requirements/FRD.md` |
| **Spec-Anchored** | The specification is maintained *after* the task ships, and used for the feature's future evolution | Required for every connector (`contract.yaml`, per NFR-MAINT-001) |
| **Spec-as-Source** | The specification is the actual source of truth over time; humans edit only the specification, never the generated code directly, and spec changes automatically propagate to code | Aspirational target for well-isolated, high-change-frequency areas (e.g., data contracts driving generated validation code) — not assumed everywhere yet |

### 2.2 What makes a specification good enough to build from

A good specification states: the intended outcome, the boundaries of scope, constraints, prior decisions it must respect (cross-referencing the relevant ADR), how the work is broken into sub-tasks, and acceptance criteria. Anything the specification leaves genuinely open, an implementing agent (human or AI) fills in reasonably — but anything the specification does state is binding, not a suggestion.

## 3. Test-Driven Development in detail

Tests are written from the specification's acceptance criteria **before** implementation code. For this project specifically, "tests" spans three categories, all required, none optional:

1. **Unit tests** — a connector's parsing logic, a validation rule's logic, an API handler's request/response shape.
2. **Integration tests** — a full run of the Phase 1 local stack (`../technical/technical-design-document.md` §6), asserting Bronze/Silver/Gold rows land correctly and idempotently.
3. **Data-quality tests** — the FR-QUAL-xxx rules in `../requirements/FRD.md`, implemented as versioned Great Expectations/Soda Core suites, run in CI (`../technical/technical-design-document.md` §5).

## 4. Event-Driven Development in detail

See `../technical/event-schema.md` for the literal event catalog and envelope; this section is about the *process* implication. Because every pipeline stage only proceeds on a validated event (e.g., the Silver transformer only runs after `raw_data.validated`, never after a bare "the script finished" assumption), a stage's correctness is independently testable and independently retriable.

## 5. The required order of work

For any new feature, connector, or pipeline stage, the order is fixed — skipping ahead is the anti-pattern this methodology exists to prevent (sometimes called "vibe coding": writing implementation directly from an idea, with no specification and no test plan in between):

1. **Write the specification first**: which dataset, from where, under what license, at what cadence, with what quality bar. This becomes an FR in `../requirements/FRD.md` and/or a data contract (`../architecture/solution-design-document.md` §4).
2. **Write acceptance criteria and tests** derived from that specification, before implementation.
3. **Implement the connector/pipeline** until the tests pass — implementation is the last step, not the first.
4. **Wire it into the event flow** so downstream stages only proceed on a validated event, never on an unvalidated assumption.
5. **Route every failure to the dead-letter queue.** Silent drops are forbidden at every stage — a failure that disappears without a DLQ entry and an alert is a defect in the pipeline itself, independent of whatever caused the original failure.

## 6. Worked example: the full event flow

```
schedule.triggered
   -> ingestion.requested
   -> raw_data.received
   -> raw_data.validated
   -> bronze_data.written
   -> silver_data.transformed
   -> gold_data.published
   -> data_product.ready
```

Each arrow is a point where SDD's contract is checked, TDD's tests apply, and EDD's decoupling lets the next stage react independently — full technical detail (envelope fields, producers, consumers, DLQ policy) is in `../technical/event-schema.md`, not duplicated here.

## 7. How this applies to AI-assisted development specifically

Because AI coding agents (including the one that authored this documentation set) increasingly write the implementation step in §5.3, SDD's role becomes load-bearing rather than advisory: the specification is what keeps an AI agent's output aligned with intent, and the Coordinator/Implementor/Verifier pattern (`../ai-agent/agentic-ai-design.md` §8) exists specifically to check that alignment independently rather than trusting an implementing agent to self-certify.

## 8. Relationship to other documents

- `../requirements/FRD.md` is where SDD's specifications formally live.
- `../technical/technical-design-document.md` §5 is where TDD's tests are mechanically enforced in CI.
- `../technical/event-schema.md` is where EDD's event contracts are formally specified.
- `../ai-agent/agentic-ai-design.md` §8 is the AI-specific application of this methodology to building the agent's own features.
