"""Event envelope and event taxonomy.

The event types here are exactly the nine defined in
docs/technical/event-schema.md. That document is the contract: an event type
that does not appear there does not exist. If a new event is genuinely needed,
update the schema document in the same change that adds it here — see the
"Docs are the contract" rule in the root CLAUDE.md.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

SCHEMA_VERSION = "1.0.0"


class EventType(Enum):
    """The nine platform event types, per docs/technical/event-schema.md."""

    SCHEDULE_TRIGGERED = "schedule.triggered"
    INGESTION_REQUESTED = "ingestion.requested"
    RAW_DATA_RECEIVED = "raw_data.received"
    RAW_DATA_VALIDATED = "raw_data.validated"
    RAW_DATA_QUARANTINED = "raw_data.quarantined"
    BRONZE_DATA_WRITTEN = "bronze_data.written"
    SILVER_DATA_TRANSFORMED = "silver_data.transformed"
    GOLD_DATA_PUBLISHED = "gold_data.published"
    DATA_PRODUCT_READY = "data_product.ready"


@dataclass(frozen=True)
class EventEnvelope:
    """Standard envelope carried by every platform event.

    Field names follow the envelope table in docs/technical/event-schema.md
    (`occurred_at`, `producer`, `schema_version`), not convenient synonyms.

    `event_id` is a real field with a factory default, not a computed property:
    it is generated once at construction and never changes. An identifier that
    varies between reads cannot support the audit trail NFR-AUDIT-001 requires.
    """

    event_type: EventType
    producer: str
    dataset_id: str
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    schema_version: str = SCHEMA_VERSION
    correlation_id: str | None = None
    payload_reference: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the envelope, preserving the stable event_id."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "occurred_at": self.occurred_at.isoformat(),
            "producer": self.producer,
            "schema_version": self.schema_version,
            "dataset_id": self.dataset_id,
            "correlation_id": self.correlation_id,
            "payload_reference": self.payload_reference,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EventEnvelope:
        """Rebuild an envelope, keeping the original event_id if present."""
        kwargs: dict[str, Any] = {
            "event_type": EventType(data["event_type"]),
            "producer": data["producer"],
            "dataset_id": data["dataset_id"],
            "occurred_at": datetime.fromisoformat(data["occurred_at"]),
            "schema_version": data.get("schema_version", SCHEMA_VERSION),
            "correlation_id": data.get("correlation_id"),
            "payload_reference": data.get("payload_reference"),
            "metadata": data.get("metadata", {}),
        }
        if "event_id" in data:
            kwargs["event_id"] = data["event_id"]
        return cls(**kwargs)


def compute_payload_hash(payload: bytes) -> str:
    """Compute SHA-256 of a payload for integrity verification."""
    return hashlib.sha256(payload).hexdigest()
