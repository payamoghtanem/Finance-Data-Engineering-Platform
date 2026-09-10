"""Events module for platform event backbone.

Implements the event envelope and transport per docs/technical/event-schema.md
and docs/architecture/solution-design-document.md.
"""

from src.events.models import (
    EventEnvelope,
    EventType,
    compute_payload_hash,
)

__all__ = [
    "EventEnvelope",
    "EventType",
    "compute_payload_hash",
]
