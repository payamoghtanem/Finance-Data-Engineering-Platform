"""Unit tests for src/events/dlq.py -- EventBus <-> DLQRecorder wiring and
replay (EPIC-09, FR-OPS-003, US-09-001/002)."""

from __future__ import annotations

from src.common.dlq import DLQRecorder
from src.events.bus import EventBus
from src.events.dlq import attach_dlq, replay
from src.events.models import EventEnvelope, EventType


def _recorder() -> DLQRecorder:
    return DLQRecorder(db_path=":memory:")


class TestAttachDLQHandlerFailures:
    def test_a_raising_subscriber_lands_in_the_dlq(self) -> None:
        bus = EventBus()
        recorder = _recorder()
        attach_dlq(bus, recorder)

        def _broken(_e: EventEnvelope) -> None:
            raise ValueError("payload parser blew up")

        bus.subscribe(EventType.RAW_DATA_RECEIVED, _broken)
        event = EventEnvelope(
            event_type=EventType.RAW_DATA_RECEIVED,
            producer="connectors.fred",
            dataset_id="fred_cpiaucsl",
        )
        bus.publish(event)

        entry = recorder.get(event.event_id)
        assert entry is not None
        assert entry.status == "pending"
        assert entry.dataset_id == "fred_cpiaucsl"
        assert "payload parser blew up" in entry.failure_reason

    def test_a_successful_subscriber_leaves_the_dlq_empty(self) -> None:
        bus = EventBus()
        recorder = _recorder()
        attach_dlq(bus, recorder)
        bus.subscribe(EventType.RAW_DATA_RECEIVED, lambda _e: None)

        bus.publish(
            EventEnvelope(
                event_type=EventType.RAW_DATA_RECEIVED,
                producer="connectors.fred",
                dataset_id="fred_cpiaucsl",
            )
        )

        assert recorder.list_pending() == []


class TestAttachDLQQuarantine:
    def test_a_quarantined_event_lands_in_the_dlq_with_failed_rules(self) -> None:
        bus = EventBus()
        recorder = _recorder()
        attach_dlq(bus, recorder)

        event = EventEnvelope(
            event_type=EventType.RAW_DATA_QUARANTINED,
            producer="validation.engine",
            dataset_id="fred_cpiaucsl",
            metadata={"failed_rules": ["nonnegative_volume"]},
        )
        bus.publish(event)

        entry = recorder.get(event.event_id)
        assert entry is not None
        assert entry.status == "pending"
        assert "nonnegative_volume" in entry.failure_reason
        assert entry.metadata == {"failed_rules": ["nonnegative_volume"]}

    def test_a_validated_event_never_lands_in_the_dlq(self) -> None:
        bus = EventBus()
        recorder = _recorder()
        attach_dlq(bus, recorder)

        bus.publish(
            EventEnvelope(
                event_type=EventType.RAW_DATA_VALIDATED,
                producer="validation.engine",
                dataset_id="fred_cpiaucsl",
            )
        )

        assert recorder.list_pending() == []


class TestReplay:
    def test_replay_republishes_raw_data_received(self) -> None:
        bus = EventBus()
        recorder = _recorder()
        attach_dlq(bus, recorder)
        bus.publish(
            EventEnvelope(
                event_type=EventType.RAW_DATA_QUARANTINED,
                producer="validation.engine",
                dataset_id="fred_cpiaucsl",
                correlation_id="corr-1",
                payload_reference="s3://raw/fred/2026-09-11.json",
            )
        )
        entry = recorder.list_pending()[0]
        received: list[EventEnvelope] = []
        bus.subscribe(EventType.RAW_DATA_RECEIVED, received.append)

        replayed = replay(entry.event_id, event_bus=bus, recorder=recorder)

        assert replayed is not None
        assert replayed.event_type is EventType.RAW_DATA_RECEIVED
        assert replayed.dataset_id == "fred_cpiaucsl"
        assert replayed.correlation_id == "corr-1"
        assert replayed.payload_reference == "s3://raw/fred/2026-09-11.json"
        assert received == [replayed]

    def test_replay_marks_the_entry_replayed(self) -> None:
        bus = EventBus()
        recorder = _recorder()
        attach_dlq(bus, recorder)
        bus.publish(
            EventEnvelope(
                event_type=EventType.RAW_DATA_QUARANTINED,
                producer="validation.engine",
                dataset_id="fred_cpiaucsl",
            )
        )
        entry = recorder.list_pending()[0]

        replay(entry.event_id, event_bus=bus, recorder=recorder)

        assert recorder.get(entry.event_id).status == "replayed"  # type: ignore[union-attr]

    def test_replaying_twice_is_a_no_op_the_second_time(self) -> None:
        bus = EventBus()
        recorder = _recorder()
        attach_dlq(bus, recorder)
        bus.publish(
            EventEnvelope(
                event_type=EventType.RAW_DATA_QUARANTINED,
                producer="validation.engine",
                dataset_id="fred_cpiaucsl",
            )
        )
        entry = recorder.list_pending()[0]
        received: list[EventEnvelope] = []
        bus.subscribe(EventType.RAW_DATA_RECEIVED, received.append)

        first = replay(entry.event_id, event_bus=bus, recorder=recorder)
        second = replay(entry.event_id, event_bus=bus, recorder=recorder)

        assert first is not None
        assert second is None
        assert len(received) == 1  # no duplicate publish on the second call

    def test_replaying_an_unknown_event_id_returns_none(self) -> None:
        bus = EventBus()
        recorder = _recorder()

        assert replay("does-not-exist", event_bus=bus, recorder=recorder) is None
