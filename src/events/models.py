"""Types and exceptions for the events module.

Defines the event envelope structure per docs/technical/event-schema.md.
"""

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional


class EventType(str, Enum):
    """Event types in the platform event taxonomy."""

    # Ingestion events
    RAW_DATA_RECEIVED = "raw_data.received"
    RAW_DATA_VALIDATED = "raw_data.validated"
    RAW_DATA_QUARANTINED = "raw_data.quarantined"

    # Transformation events
    SILVER_DATA_TRANSFORMED = "silver_data.transformed"
    GOLD_DATA_PUBLISHED = "gold_data.published"

    # Data quality events
    DATA_QUALITY_PASSED = "data_quality.passed"
    DATA_QUALITY_FAILED = "data_quality.failed"

    # Operations events
    INGESTION_STARTED = "ingestion.started"
    INGESTION_COMPLETED = "ingestion.completed"
    INGESTION_FAILED = "ingestion.failed"
    REPLAY_REQUESTED = "replay.requested"
    REPLAY_COMPLETED = "replay.completed"


@dataclass(frozen=True)
class EventEnvelope:
    """Standard event envelope for all platform events.

    Per docs/technical/event-schema.md, every event must contain:
    - event_id: Unique identifier (UUID v4)
    - event_type: One of EventType values
    - source: Originating service/module (e.g., "connectors.fred")
    - dataset_id: Identifier for the dataset this event concerns
    - timestamp: UTC timestamp when event was created
    - correlation_id: Groups related events for traceability
    - payload_reference: Reference to actual payload (e.g., S3 path)
    - metadata: Additional context
    """

    event_type: EventType
    source: str
    dataset_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: Optional[str] = None
    payload_reference: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Generate event_id if not provided."""
        # Use object.__setattr__ because dataclass is frozen
        if not hasattr(self, "event_id"):
            object.__setattr__(self, "event_id", str(uuid.uuid4()))

    @property
    def event_id(self) -> str:
        """Return the event ID (generated on first access)."""
        # This is a workaround for frozen dataclass with computed field
        return getattr(self, "_event_id", str(uuid.uuid4()))

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "source": self.source,
            "dataset_id": self.dataset_id,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "payload_reference": self.payload_reference,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EventEnvelope":
        """Reconstruct event from dictionary."""
        return cls(
            event_type=EventType(data["event_type"]),
            source=data["source"],
            dataset_id=data["dataset_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            correlation_id=data.get("correlation_id"),
            payload_reference=data.get("payload_reference"),
            metadata=data.get("metadata", {}),
        )


def compute_payload_hash(payload: bytes) -> str:
    """Compute SHA-256 hash of a payload for integrity verification.

    Args:
        payload: Raw bytes to hash.

    Returns:
        Hex-encoded SHA-256 hash.
    """
    return hashlib.sha256(payload).hexdigest()
