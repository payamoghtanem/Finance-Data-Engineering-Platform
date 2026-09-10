"""Events module for platform event backbone.

Implements the event envelope and transport per docs/technical/event-schema.md
and docs/architecture/solution-design-document.md. `EventBus` is the Phase 1
in-process transport ADR-0002 calls for (EPIC-06).
"""

from src.events.bus import DeadLetterHandler, EventBus, Handler
from src.events.dlq import attach_dlq, replay
from src.events.models import (
    EventEnvelope,
    EventType,
    compute_payload_hash,
)

__all__ = [
    "DeadLetterHandler",
    "EventBus",
    "EventEnvelope",
    "EventType",
    "Handler",
    "attach_dlq",
    "compute_payload_hash",
    "replay",
]
