"""Wires a real DLQ (`src/common/dlq.py`) into `EventBus` (EPIC-09).

Per docs/technical/event-schema.md §3, two distinct things belong in the DLQ:

1. Any event whose subscriber handler raised — `EventBus`'s dead-letter hook
   (`set_dead_letter_handler`) is where that lands instead of only a log
   line.
2. `raw_data.quarantined` itself — this isn't a handler failure, it *is* the
   failure the DLQ exists for (a batch that failed a data-quality rule,
   published by `src/validation/engine.py`).

`attach_dlq()` wires both paths into one `DLQRecorder`. `replay()` re-emits
`raw_data.received` for one DLQ entry, per
docs/technical/technical-design-document.md §7 — reprocessing itself is
idempotent because every downstream layer it lands on already is (content
-addressed Raw Storage, Bronze's lineage write, Silver's `vintage_date`-keyed
upsert); this module's own contribution to that guarantee is that replaying
an *already-replayed* entry is a no-op rather than a second publish.
"""

from __future__ import annotations

from src.common.dlq import DLQRecorder
from src.events.bus import EventBus
from src.events.models import EventEnvelope, EventType


def attach_dlq(event_bus: EventBus, recorder: DLQRecorder) -> None:
    """Route every dead-lettered event on `event_bus` into `recorder`."""

    def _on_dead_letter(event: EventEnvelope, exc: Exception) -> None:
        recorder.record(
            event_id=event.event_id,
            event_type=event.event_type.value,
            producer=event.producer,
            dataset_id=event.dataset_id,
            correlation_id=event.correlation_id,
            payload_reference=event.payload_reference,
            metadata=event.metadata,
            failure_reason=f"{type(exc).__name__}: {exc}",
            quarantined_at=event.occurred_at,
        )

    def _on_quarantined(event: EventEnvelope) -> None:
        failed_rules = event.metadata.get("failed_rules", [])
        recorder.record(
            event_id=event.event_id,
            event_type=event.event_type.value,
            producer=event.producer,
            dataset_id=event.dataset_id,
            correlation_id=event.correlation_id,
            payload_reference=event.payload_reference,
            metadata=event.metadata,
            failure_reason=(
                f"data-quality rule(s) failed: {', '.join(failed_rules)}"
                if failed_rules
                else "raw_data.quarantined"
            ),
            quarantined_at=event.occurred_at,
        )

    event_bus.set_dead_letter_handler(_on_dead_letter)
    event_bus.subscribe(EventType.RAW_DATA_QUARANTINED, _on_quarantined)


def replay(event_id: str, *, event_bus: EventBus, recorder: DLQRecorder) -> EventEnvelope | None:
    """Re-publish `raw_data.received` for a pending DLQ entry.

    Returns the re-published envelope, or `None` if `event_id` is unknown or
    already replayed — the no-op path that makes calling this twice on the
    same entry safe (US-09-002's "idempotent, produces no duplicates").
    """
    entry = recorder.get(event_id)
    if entry is None or entry.status == "replayed":
        return None

    recorder.mark_replayed(event_id)
    replayed_event = EventEnvelope(
        event_type=EventType.RAW_DATA_RECEIVED,
        producer="dlq.replay",
        dataset_id=entry.dataset_id,
        correlation_id=entry.correlation_id,
        payload_reference=entry.payload_reference,
        metadata={"replayed_from_dlq_event_id": entry.event_id},
    )
    event_bus.publish(replayed_event)
    return replayed_event
