# System Design Learning Guide: How to Design a Data Engineering Platform

**What this document answers:** if you're starting from nothing, how do you actually learn to design a system like this one — what criteria matter, what topics must you consider, what constraints/risks/impacts are at play, what questions should you ask, where do you find trustworthy answers, and how do you evaluate tools and frameworks (including *why not* a popular one)?
**How it differs from its neighbors:** every other document in this repository documents a decision already made for *this* platform. This document teaches the general skill, using this project only as a running example — you should be able to read only this file and come away able to design a different data platform for a different domain.

## 1. Start with the mental model, not the tool list

Before naming a single technology, understand the shape every data platform shares:

```
Source → Ingest → Raw Storage → Validate → Transform → Serve → Observe & Govern
```

If you can't say, for your own project, what flows through each of these seven stages, you are not ready to pick tools yet — picking tools before this is the single most common design mistake, because it optimizes a stage in isolation without knowing what the whole pipeline actually needs.

## 2. The design criteria that matter, and why each one exists

| Criterion | What it means in practice | Why it matters |
|---|---|---|
| **Modularity** | Components with clear boundaries and interfaces, reusable and independently replaceable | Lets you swap one piece (a data source, a processing engine) without rewriting the system |
| **Cloud-readiness** | Compute and storage are separated from the start, even if both run on one laptop today | This is what makes "start local, move to cloud later" actually true instead of aspirational |
| **Scalability** | The storage and processing approach can grow horizontally (more nodes/regions) without a redesign | Growing data volume or user count should cost infrastructure, not a rewrite |
| **Observability** | You can see what the system is doing — job status, latency, failures — without reading raw logs by hand | Undetected failure is worse than visible failure; this is doubly true for AI-era pipelines with more moving, semi-autonomous parts |
| **Cost-awareness** | You know, at each stage, what running this actually costs — not just what the software license costs | Open-source software being free does not mean running it is free; see §3 |

## 3. The hard truth nobody puts in the first paragraph: you can't have everything at once

"Completely free," "cloud-native," and "enterprise production-ready" cannot all be true on day one. Open-source software has no license fee, but storage, network, a Kubernetes cluster, monitoring, and the operational labor to keep any of it reliable all cost real money the moment they run beyond a single machine you already own. The professional answer is not to abandon any of the three — it's to **sequence** them deliberately: prove the design cheaply and locally first, then add the infrastructure that makes it "production" once the design is validated. This project's own resolution of that tension is documented in `../roadmap/mvp-plan.md` — treat it as one worked example of the general principle, not the only valid sequencing.

## 4. Topics you must consider when designing a system like this, and why

- **Data domain and scope** — what kinds of data (macro, equity, crypto, ...) must be covered? Undefined scope makes every later decision unstable.
- **Scale** — what's the current data volume, and the realistic growth rate over 12 and 36 months? This determines whether you need distributed processing (Spark/Flink) on day one or ever.
- **Real-time vs. batch** — do you genuinely need sub-second data, or is daily/hourly enough? Real-time requirements cascade into much more infrastructure (a real broker, low-latency serving) than batch does — don't assume real-time by default.
- **Source of truth and trust** — for any given fact, which source is authoritative when two disagree? Skipping this leads to silently unreliable analysis built on an aggregator of unclear origin.
- **Time semantics** — when did something happen, versus when was it published, versus when did you retrieve it, versus what revision/vintage is this? Conflating these causes look-ahead bias — using information in a historical analysis that wouldn't actually have been knowable at that point in time.
- **Data quality** — what error rate is acceptable, and how is it measured, versioned, and enforced (not just hoped for)?
- **Security and compliance** — what regulations apply (e.g., data protection law), and how is data encrypted, access-controlled, and audited?
- **Legal/licensing** — is storing and redistributing this data actually permitted? "Publicly viewable" is not "licensed to store and redistribute."
- **Cost** — what's the actual budget, across compute, storage, and network egress — and how do you get the most out of genuinely free resources without overcommitting to what's merely *currently* free?
- **Recoverability** — what happens if a data source or your own infrastructure goes down? What's your acceptable data loss window (Recovery Point Objective) and acceptable downtime (Recovery Time Objective)?
- **AI agent scope** (if applicable) — exactly what is an AI agent allowed to do, and how is that enforced technically rather than just requested politely in a prompt?

## 5. The architecture-question checklist, and why each question matters

| Area | The exact question to ask | Why it matters |
|---|---|---|
| Purpose | What decision will a user make with this data? | Prevents building a system that produces data nobody needed |
| Users | Who reads, writes, and administers this system? | Determines your access-control (RBAC) and UX design |
| Data shape | Is the data batch or streaming? What's its cadence and volume? | Determines whether you need Kafka, Airflow/Dagster, or something simpler |
| Truth | What is the actual source of truth? | Prevents building analysis on top of an unreliable aggregator |
| License | Is storing and redistributing this data legal? | Reduces legal risk and the risk of a sudden forced takedown |
| Time | What's the difference between when something happened and when it was published? | Prevents look-ahead bias in any historical analysis |
| Quality | What error rate is acceptable? | Sets your Service-Level Objectives and what tests you need |
| Growth | What will data volume and user count look like in 12 and 36 months? | Prevents both over-engineering too early and hitting a wall too late |
| Cost | What's the actual monthly budget for compute, storage, and egress? | Keeps the design honest instead of aspirational |
| Security | What data or secrets are sensitive? | Determines your IAM and encryption approach |
| Recovery | What do you do if a source or your own infrastructure goes down? | Forces you to design backup, replay, and disaster recovery *before* you need them, not during an incident |
| AI | Exactly what is an AI agent allowed to do? | Prevents unauthorized action or a confidently wrong (hallucinated) answer from having real consequences |

## 6. Where to find trustworthy answers (in priority order)

1. **The official documentation of the data provider or tool itself** — for API behavior, rate limits, licensing, and schema, this is the primary source; everything else is secondary commentary.
2. **The official documentation of the open-source project** you're evaluating (Kafka, dbt, Iceberg, Kubernetes, OpenTelemetry, etc.) — not a blog post summarizing it.
3. **Formal standards**, where they exist (e.g., SDMX for statistical data exchange) — a standard's own specification is authoritative over any single implementation's interpretation of it.
4. **Official cloud reference architectures** — useful for comparing trade-offs across providers, but read them to understand the *trade-off*, not to copy a diagram uncritically; a reference architecture is written by a vendor with a reason to prefer their own services.
5. **Your own Architecture Decision Records** — once you've made a decision and recorded the evidence, alternatives, and consequences (see `../architecture/decisions/` for this project's worked examples), that record becomes your own most relevant source for related future decisions — don't re-litigate a settled trade-off without new evidence.
6. **A real proof-of-concept, benchmarked against your own data volume and access pattern** — no article, however well-written, substitutes for testing the actual tool against your actual data shape. If you take one habit from this guide, take this one.

## 7. Evaluating tools and frameworks: the "why, and why not" discipline

The temptation in system design is to justify a tool choice ("we chose X because it's popular/fast/free"). The useful version of that justification always has a matching rejection: what did you *not* choose, and under what condition would that rejected choice become the right one instead? A few worked examples from this project (full detail in `../architecture/ARD.md` §5 and the ADRs in `../architecture/decisions/`):

- **Apache Kafka**: excellent for decoupled, replayable, independently-scaling event processing — and unnecessary operational overhead if you're polling a handful of daily APIs with no independent scaling need yet. The "why not yet" is as important as the "why eventually."
- **Kubernetes**: excellent for elastic, self-healing, standardized deployment — and excessive complexity for a single-operator local MVP with no team to share operational burden with.
- **A full Data Mesh**: an excellent *organizational* answer when multiple independent teams each need to own a data domain — and pure overhead if there's no second team yet to mesh with. This is a case where the "why not" is about organizational reality, not raw technical merit.
- **Apache Iceberg vs. Delta Lake**: both are excellent open table formats; the deciding factor is often which processing engine ecosystem you're most likely to run across (multi-engine flexibility vs. deep Spark-specific integration), not an abstract "which is better."

The discipline this teaches: never adopt a tool because it's the default choice everyone reaches for. Adopt it because you can state, in one sentence, the specific problem it solves for your specific scale and team — and you can also state the condition under which you'd choose differently.

## 8. Constraints, risks, and impacts you must weigh explicitly

- **Free data source limitations**: coverage gaps, non-real-time or historical-only data, undocumented or informally-enforced rate limits.
- **API rate limits**: even generous free tiers (e.g., Alpha Vantage, Finnhub-style APIs) throttle request rates — design for backoff and caching from the start, not as an afterthought.
- **Security and privacy risk**: financial platforms especially must treat compliance (e.g., data protection regulation) as a first-class design constraint, not a launch-week checklist item.
- **Data quality risk**: incomplete or inconsistent data from different sources leads directly to wrong conclusions — cleansing, validation, and integration are not optional polish, they are the core of what makes a data platform trustworthy at all.
- **Over-engineering risk**: adopting production-scale complexity before an MVP has proven the design wastes time and money and is a common reason ambitious data platform projects stall or are abandoned before shipping any value.

## 9. A practical, sequenced learning path

1. Get genuinely solid at Python, HTTP, JSON, CSV, SQL, Git, Docker, and basic Linux — these are the load-bearing skills under everything else.
2. Build one simple connector (e.g., against the World Bank API or FRED) end to end.
3. Store the raw response in object storage (e.g., MinIO) and its metadata in a relational database (e.g., PostgreSQL).
4. Build a Silver and Gold model from it using dbt Core.
5. Add data-quality tests and a data contract for that one dataset.
6. Add scheduling, retries, and backfill support with an orchestrator (Dagster or Airflow).
7. Build one documented API endpoint (FastAPI/OpenAPI) over the Gold model.
8. Add Prometheus and Grafana for job success rate, latency, and freshness visibility.
9. Only then — once you have multiple connectors, real concurrent processing needs, or a genuine need for event replay — add Kafka and a full event-driven flow.
10. Last, and only when the team/scale genuinely requires it, add Kubernetes, GitOps, enterprise identity (Keycloak), a secrets manager (Vault), and a carefully-scoped AI agent.

The professional path is: build one small, genuinely reliable pipeline first — for example, one source flowing all the way through Raw → Bronze → Silver → Gold → dashboard — and only then repeat the same standard of contract, quality, lineage, security, and operations for each additional source. This is what prevents building an impressive-looking architecture that never actually runs reliably, and it's the same lesson this project's own roadmap (`../roadmap/mvp-plan.md`) applies to itself.
