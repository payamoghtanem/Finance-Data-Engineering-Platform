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

_logger = logging.getLogger(__name__)


class EventBus:
    """Synchronous, in-process publish/subscribe.

    Pure in-memory: nothing here touches disk or the network, so it needs no
    special handling in tests the way the DuckDB-backed writers do.
    """

    def __init__(self) -> None:
        self._subscribers: defaultdict[EventType, list[Handler]] = defaultdict(list)
        self._published: list[EventEnvelope] = []

    def subscribe(self, event_type: EventType, handler: Handler) -> None:
        """Register `handler` to be called whenever `event_type` is published."""
        self._subscribers[event_type].append(handler)

    def publish(self, event: EventEnvelope) -> None:
        """Publish `event` and synchronously invoke every matching subscriber.

        One handler raising does not stop the others, and never propagates to
        the publisher — a bug in an unrelated downstream consumer must not be
        able to break the producer that published the event.
        """
        self._published.append(event)
        for handler in self._subscribers.get(event.event_type, []):
            try:
                handler(event)
            except Exception:
                _logger.exception(
                    "Subscriber to %s raised while handling event %s",
                    event.event_type.value,
                    event.event_id,
                )

    def history(self, event_type: EventType | None = None) -> list[EventEnvelope]:
        """Every event published so far, oldest first. Phase 1 has no
        persistence or replay beyond this in-memory list — see DEBT note in
        STATUS.md; EPIC-09 (DLQ) and EPIC-15 (Kafka) are where that lands."""
        if event_type is None:
            return list(self._published)
        return [e for e in self._published if e.event_type == event_type]
