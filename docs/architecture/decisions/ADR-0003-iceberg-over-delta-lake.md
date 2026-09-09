# ADR-0003: Apache Iceberg over Delta Lake as the table format

**Status:** Accepted

## Context

`../ARD.md` §2.8 requires open, non-lock-in formats for stored data. A table format is needed on top of Parquet files in object storage to provide snapshots, ACID semantics, and schema evolution. The two leading open table formats are Apache Iceberg and Delta Lake.

## Decision

Use **Apache Iceberg** as the table format for Bronze/Silver/Gold tables, read/written via PyIceberg and queried via DuckDB (MVP) or Trino (Phase 2+).

## Alternatives considered

1. **Delta Lake.**
   - Pros: mature, strong native integration with Apache Spark, widely used, good tooling in the Databricks ecosystem.
   - Rejected (not disqualified, but not chosen) because: Delta Lake's strongest tooling and performance advantages are most pronounced within a Spark/Databricks-centric stack, which this platform is deliberately not committing to at MVP stage (`../ARD.md` defers heavy Spark processing until genuinely needed). Iceberg has broader, more format-neutral multi-engine support (Trino, DuckDB, Spark, Flink, PyIceberg) without steering the project toward one vendor's ecosystem, which better serves ARD §2.8's anti-lock-in principle.

2. **No table format — raw Parquet files with manual partitioning.**
   - Rejected because: without snapshots and schema evolution, safe reprocessing (ARD §2.2), idempotent backfills (ARD §2.5), and safe schema changes (ARD §2.4) all become manual, error-prone processes instead of guaranteed table-format features.

3. **Apache Iceberg (chosen).**
   - Broadest multi-engine support of the open table formats, strong schema-evolution and time-travel semantics, and an active open governance model (Apache Software Foundation) rather than single-vendor stewardship.

## Consequences

- Positive: query engine flexibility is preserved — DuckDB today, Trino or Spark later, without a data migration.
- Negative: Iceberg's ecosystem, while strong, is not as deeply battle-tested inside a pure-Spark pipeline as Delta Lake is — if the platform later adopts Spark as its primary heavy-processing engine, some Delta-specific Spark optimizations will not be directly available and should be re-evaluated then.
- Trigger to revisit: if Phase 3 processing needs become Spark-dominated and Iceberg's Spark integration proves materially worse than Delta's for this workload, reopen this decision with a follow-up ADR rather than silently mixing table formats.
