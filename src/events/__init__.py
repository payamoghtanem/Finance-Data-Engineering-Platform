"""Events module for platform event backbone.

Implements the event envelope and transport per docs/technical/event-schema.md
and docs/architecture/solution-design-document.md. `EventBus` is the Phase 1
in-process transport ADR-0002 calls for (EPIC-06).
"""

from src.events.bus import EventBus, Handler
from src.events.models import (
    EventEnvelope,
    EventType,
    compute_payload_hash,
)

__all__ = [
    "EventBus",
    "EventEnvelope",
    "EventType",
    "Handler",
    "compute_payload_hash",
]
