"""In-process event bus (EPIC-06, US-06-001).

Implements the Phase 1 transport ADR-0002 calls for: "in-process function
calls / a lightweight local queue," explicitly deferring Kafka until Phase 2
(EPIC-15) once there are enough independently scaling producers/consumers to
justify a real broker. `publish`/`subscribe` is the shape that swap happens
behind — a consumer written against `EventBus` does not change when the
transport underneath it does.

The architectural point of US-06-001 ("a stage advances only on a validated
event, never a bare 'script ran' signal") is enforced by construction here:
a subscriber is only ever invoked with a real `EventEnvelope`, published
through this bus — there is no other channel for a stage to learn that
upstream work happened.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Callable

from src.events.models import EventEnvelope, EventType

Handler = Callable[[EventEnvelope], None]
DeadLetterHandler = Callable[[EventEnvelope, Exception], None]

_logger = logging.getLogger(__name__)


class EventBus:
    """Synchronous, in-process publish/subscribe.

    Pure in-memory: nothing here touches disk or the network, so it needs no
    special handling in tests the way the DuckDB-backed writers do.
    """

    def __init__(self) -> None:
        self._subscribers: defaultdict[EventType, list[Handler]] = defaultdict(list)
        self._published: list[EventEnvelope] = []
        self._dead_letter_handler: DeadLetterHandler | None = None

    def subscribe(self, event_type: EventType, handler: Handler) -> None:
        """Register `handler` to be called whenever `event_type` is published."""
        self._subscribers[event_type].append(handler)

    def set_dead_letter_handler(self, handler: DeadLetterHandler) -> None:
        """Register where a raised subscriber exception is routed (EPIC-09,
        FR-OPS-003), per docs/technical/event-schema.md §3: "Any event whose
        handler raises an unrecoverable error ... is routed to a DLQ rather
        than dropped." The exception is still logged either way; this adds
        somewhere durable for it to land instead of only the log line. See
        `src/events/dlq.py::attach_dlq` for the real wiring to `DLQRecorder`.
        """
        self._dead_letter_handler = handler

    def publish(self, event: EventEnvelope) -> None:
        """Publish `event` and synchronously invoke every matching subscriber.

        One handler raising does not stop the others, and never propagates to
        the publisher — a bug in an unrelated downstream consumer must not be
        able to break the producer that published the event. If a dead-letter
        handler is registered, it is invoked too (and is itself isolated the
        same way: a broken dead-letter handler cannot break the publisher or
        the other subscribers either).
        """
        self._published.append(event)
        for handler in self._subscribers.get(event.event_type, []):
            try:
                handler(event)
            except Exception as exc:
                _logger.exception(
                    "Subscriber to %s raised while handling event %s",
                    event.event_type.value,
                    event.event_id,
                )
                if self._dead_letter_handler is not None:
                    try:
                        self._dead_letter_handler(event, exc)
                    except Exception:
                        _logger.exception(
                            "Dead-letter handler itself raised for event %s", event.event_id
                        )

    def history(self, event_type: EventType | None = None) -> list[EventEnvelope]:
        """Every event published so far, oldest first. This in-memory list is
        not the DLQ (EPIC-09, `src/common/dlq.py`) — it is every event ever
        published, success or failure alike, and (like `EventBus` itself) is
        lost when the process ends; the DLQ is the durable, failure-only
        record with its own replay path."""
        if event_type is None:
            return list(self._published)
        return [e for e in self._published if e.event_type == event_type]
