# ADR-0002: Defer Apache Kafka until Phase 2 (Team-ready)

**Status:** Accepted

## Context

`../ARD.md` commits to an Event-Driven Architecture pattern for the platform's data flow. Apache Kafka is the natural production-grade event broker for this pattern. The question is *when* to introduce it: at MVP inception, or later.

## Decision

Define event **schemas and event types** from day one (`../../technical/event-schema.md`), but implement the event **transport** in Phase 1 as in-process function calls / a lightweight local queue (e.g., Dagster's own sensor/asset event mechanisms), and only introduce Apache Kafka as the transport starting in Phase 2, once there are enough independently deployable connectors and consumers to justify a real broker.

## Alternatives considered

1. **Kafka from day one.**
   - Pros: production-grade replay, true producer/consumer decoupling, matches the target production architecture exactly from the start.
   - Rejected because: for an MVP polling a handful of daily/periodic free APIs (FRED, World Bank, Eurostat, SEC EDGAR, CoinGecko), Kafka adds a stateful, operationally nontrivial cluster to run and monitor on a single laptop, for a decoupling benefit that has no real payoff yet — there are not yet multiple independently scaling producers/consumers. This directly risks the "over-engineering" business risk in `../../business/BRD.md` §7.

2. **No event-driven design at all in the MVP (plain sequential scripts), add events later.**
   - Rejected because: retrofitting event boundaries after pipelines are written sequentially is far more expensive than designing the event *contracts* up front and only swapping the *transport* later. This would also violate ARD §2.3 (separation of concerns) from the start.

3. **Define event schemas now; defer only the broker technology (chosen).**
   - Gets the architectural benefit (decoupled stages, explicit events like `raw_data.validated`) without the operational cost, and the swap to Kafka in Phase 2 changes only the transport implementation behind an already-stable event contract — no consumer/producer logic needs to be rewritten, only re-pointed at a new transport.

## Consequences

- Positive: MVP stays genuinely runnable on a laptop with minimal moving parts; the event contracts are validated early against real usage before being locked into a broker's schema registry.
- Negative: Phase 1's in-process transport does not provide real replay or true independent scaling — this is an accepted, explicit limitation of Phase 1, not a hidden one.
- Trigger to revisit: entering Phase 2 (see `../../roadmap/mvp-plan.md` exit criteria for Phase 1), or earlier if a second independently-scaling consumer is needed before Phase 1 is otherwise complete.
