# Event Schema

**What this document answers:** what events exist in this platform's event-driven flow, what does each one look like, who produces and consumes it, and what happens when handling it fails?
**How it differs from its neighbors:** `../methodology/edd-sdd-tdd.md` explains *why* the platform is event-driven and shows the flow narratively; this document is the literal schema and transport contract.

## 1. Event envelope (every event shares this shape)

| Field | Type | Notes |
|---|---|---|
| `event_id` | UUID | Unique per event instance |
| `event_type` | string | e.g., `raw_data.received` |
| `occurred_at` | timestamp (UTC) | |
| `producer` | string | Service/connector that emitted the event |
| `schema_version` | string | Version of this event type's schema |
| `correlation_id` | UUID | Ties together every event in one end-to-end pipeline run |
| `payload_reference` | string | Pointer (object storage path or table row key) to the actual data — **never** the raw payload itself |
| `dataset_id` | string | The dataset this event concerns, e.g. `fred_cpiaucsl`. Lets a consumer route or filter without dereferencing `payload_reference` |
| `metadata` | object | Small, non-bulk context (checksum, source series id). Bound by the no-bulk-data rule below — a payload never goes here |

The envelope is implemented in `src/events/models.py`; the field names there are
these names exactly. A change to either side is a change to both.

**Rule (from the source design note, retained deliberately):** never put bulk data inside the event message itself. The event carries an identifier and a location; the consumer fetches the actual data from Raw Storage / Bronze / Silver as needed. This keeps the event transport lightweight regardless of whether it's an in-process call (Phase 1, ADR-0002) or Kafka (Phase 2+).

## 2. Event catalog (the full worked flow)

```
schedule.triggered
   -> ingestion.requested
   -> raw_data.received
   -> raw_data.validated        (or raw_data.quarantined, off the DLQ path)
   -> bronze_data.written
   -> silver_data.transformed
   -> gold_data.published
   -> data_product.ready
```

| Event type | Producer | Consumer(s) | Fires when |
|---|---|---|---|
| `schedule.triggered` | Orchestrator (Dagster) | Ingestion worker | A connector's schedule fires |
| `ingestion.requested` | Ingestion worker | (internal, tracing) | A fetch begins |
| `raw_data.received` | Ingestion worker | Validation job | Raw response is durably stored in Raw Object Storage |
| `raw_data.validated` | Validation job | Bronze writer | Schema + data contract checks pass (FR-QUAL-001) |
| `raw_data.quarantined` | Validation job | DLQ handler, alerting (FR-OPS-002) | Schema or contract checks fail |
| `bronze_data.written` | Bronze writer | Silver transformer | A new Bronze snapshot is committed |
| `silver_data.transformed` | dbt/Silver transformer | Gold aggregator | Canonical conformance (FR-MODEL-001) succeeds |
| `gold_data.published` | Gold aggregator | API cache refresher, dashboard refresher | A Gold table/KPI is updated |
| `data_product.ready` | Gold aggregator | Catalog, notification/alerting | The full pipeline for this run completed successfully |

## 3. Dead-letter queue (DLQ) policy

- Any event whose handler raises an unrecoverable error, or that fails validation (`raw_data.quarantined`), is routed to a DLQ rather than dropped.
- DLQ entries retain the full event envelope plus the specific failure reason.
- DLQ entries are replayable (FR-OPS-003) — reprocessing must be idempotent per `../architecture/ARD.md` §2.5.
- A DLQ entry older than the freshness SLO for its dataset automatically triggers an alert (FR-OPS-002), not just a passive queue entry.

## 4. Transport by phase (see ADR-0002)

- **Phase 1**: events are function calls / Dagster's native asset-event mechanism within a single process or docker-compose network — no external broker.
- **Phase 2+**: the same event types and envelope are published to Apache Kafka topics (one topic family per event type, e.g., `raw_data.received`), enabling independent scaling of producers and consumers, and true replay from a topic offset.

## 5. Schema evolution policy for events

- `schema_version` on the envelope means a consumer can detect and reject/handle an event shape it doesn't understand, rather than crashing on an unexpected field.
- A breaking change to an event payload shape requires a new `schema_version` and a migration window where both versions are accepted, mirroring the `change_policy` in the data contract example (`../architecture/solution-design-document.md` §4).

## 6. Relationship to other documents

- This is the literal schema for the flow diagrammed in `../architecture/solution-design-document.md` §1.
- The methodology reasoning for *why* the platform is built this way is in `../methodology/edd-sdd-tdd.md`.
- Alerting behavior triggered by `raw_data.quarantined` and DLQ aging is specified functionally in `../requirements/FRD.md` (FR-OPS-002) and measured in `../requirements/NFR.md` (NFR-FRESH-003).
