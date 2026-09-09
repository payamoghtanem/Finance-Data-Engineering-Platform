# ADR-0001: Central Lakehouse over pure Data Warehouse or full Data Mesh

**Status:** Accepted

## Context

The platform must store and serve large volumes of historical, semi-structured financial/economic data, cheaply, while remaining queryable with standard SQL, and while keeping a credible path from a single-laptop MVP to a cloud-native production system without a rewrite. Three broad architectural shapes were considered: a pure Data Warehouse, a full Data Mesh, and a Lakehouse with centralized ownership.

## Decision

Adopt a **Central Lakehouse**: object storage (MinIO locally, S3-compatible in the cloud) holding Parquet files organized as Apache Iceberg tables, queried via DuckDB (MVP) or Trino (team/cloud), with PostgreSQL reserved for metadata and low-latency serving only. Domain ownership (macro, equity, trade, crypto, filings) is enforced by convention and contract (clear `owner` field per data contract), not by a fully independent per-domain platform stack.

## Alternatives considered

1. **Pure Data Warehouse (e.g., commit to Snowflake or BigQuery from day one).**
   - Pros: excellent governed SQL experience, mature tooling, less operational assembly required.
   - Rejected because: (a) it is not free at any meaningful data volume, breaking the MVP's laptop-first, zero-cost requirement; (b) storing large volumes of raw/semi-structured historical data (needed for reprocessing per ARD §2.2) in a warehouse is expensive and often awkward compared to columnar object storage; (c) it creates a hard vendor dependency from day one, in direct tension with ARD §2.8 (avoid vendor lock-in).

2. **Full Data Mesh** (independent domain teams, each owning end-to-end ingestion-to-serving for their domain, backed by shared self-service platform infrastructure).
   - Pros: strong ownership model, scales well across many independent teams, avoids a central bottleneck team.
   - Rejected (for now) because: Data Mesh is primarily an *organizational* answer to a problem (many independent teams needing autonomy) that does not yet exist here — there is one owner/small team, not multiple domain teams needing organizational decoupling. Adopting the full operational overhead of a mesh (self-service platform infra, federated computational governance, multiple independently deployed domain stacks) without multiple independent teams to justify it would be pure overhead, violating the "small MVP first" principle in `../ARD.md` §5 and directly risking the "over-engineering" business risk in `../../business/BRD.md` §7.

3. **Central Lakehouse with clear per-domain ownership conventions (chosen).**
   - Captures the useful part of Data Mesh thinking — explicit ownership, data-as-product discipline (each dataset has an owner, a contract, and a trust tier) — without requiring multiple independent teams or duplicated platform infrastructure.

## Consequences

- Positive: minimal cost at MVP scale; open formats avoid lock-in; a single, coherent catalog and quality framework instead of N duplicated ones.
- Negative: if the project later grows into multiple genuinely independent teams each owning a domain, this decision should be revisited — a full Data Mesh may then become the better fit. This ADR does not forbid that evolution; it states why it is not the right starting point.
- Follow-up: if a second independent contributor/team joins and owns an entire domain end-to-end, open a new ADR to reassess, rather than silently drifting toward mesh-like behavior without a decision record.
