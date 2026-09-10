"""Unit tests for EventBus (EPIC-06, US-06-001)."""

from __future__ import annotations

from src.events.bus import EventBus
from src.events.models import EventEnvelope, EventType


def _event(event_type: EventType = EventType.RAW_DATA_RECEIVED) -> EventEnvelope:
    return EventEnvelope(event_type=event_type, producer="test", dataset_id="test_dataset")


class TestPublishSubscribe:
    def test_subscriber_receives_the_published_event(self) -> None:
        bus = EventBus()
        received: list[EventEnvelope] = []
        bus.subscribe(EventType.RAW_DATA_RECEIVED, received.append)

        event = _event()
        bus.publish(event)

        assert received == [event]

    def test_multiple_subscribers_to_the_same_type_all_fire(self) -> None:
        bus = EventBus()
        calls: list[str] = []
        bus.subscribe(EventType.RAW_DATA_RECEIVED, lambda _e: calls.append("first"))
        bus.subscribe(EventType.RAW_DATA_RECEIVED, lambda _e: calls.append("second"))

        bus.publish(_event())

        assert calls == ["first", "second"]

    def test_subscriber_to_a_different_type_is_not_called(self) -> None:
        bus = EventBus()
        calls: list[EventEnvelope] = []
        bus.subscribe(EventType.RAW_DATA_VALIDATED, calls.append)

        bus.publish(_event(EventType.RAW_DATA_RECEIVED))

        assert calls == []

    def test_publish_with_no_subscribers_does_not_raise(self) -> None:
        bus = EventBus()
        bus.publish(_event())  # must not raise


class TestConstructingAnEventDoesNotPublishIt:
    """The architectural point of US-06-001: a stage advances only on a
    *published* event, never merely because one was constructed somewhere."""

    def test_building_an_envelope_alone_triggers_no_subscriber(self) -> None:
        bus = EventBus()
        calls: list[EventEnvelope] = []
        bus.subscribe(EventType.RAW_DATA_RECEIVED, calls.append)

        _event()  # constructed, never published

        assert calls == []
        assert bus.history() == []


class TestSubscriberIsolation:
    def test_a_raising_subscriber_does_not_stop_other_subscribers(self) -> None:
        bus = EventBus()
        calls: list[str] = []

        def _broken(_e: EventEnvelope) -> None:
            raise RuntimeError("boom")

        bus.subscribe(EventType.RAW_DATA_RECEIVED, _broken)
        bus.subscribe(EventType.RAW_DATA_RECEIVED, lambda _e: calls.append("ran"))

        bus.publish(_event())  # must not raise despite _broken

        assert calls == ["ran"]

    def test_a_raising_subscriber_does_not_propagate_to_the_publisher(self) -> None:
        bus = EventBus()
        bus.subscribe(EventType.RAW_DATA_RECEIVED, lambda _e: (_ for _ in ()).throw(RuntimeError))
        bus.publish(_event())  # must not raise


class TestDeadLetterHandler:
    def test_a_raising_subscriber_invokes_the_dead_letter_handler(self) -> None:
        bus = EventBus()
        dead_lettered: list[tuple[EventEnvelope, Exception]] = []
        bus.set_dead_letter_handler(lambda event, exc: dead_lettered.append((event, exc)))

        def _broken(_e: EventEnvelope) -> None:
            raise RuntimeError("boom")

        bus.subscribe(EventType.RAW_DATA_RECEIVED, _broken)
        event = _event()
        bus.publish(event)

        assert len(dead_lettered) == 1
        dead_event, dead_exc = dead_lettered[0]
        assert dead_event == event
        assert isinstance(dead_exc, RuntimeError)

    def test_no_dead_letter_handler_registered_does_not_raise(self) -> None:
        bus = EventBus()

        def _broken(_e: EventEnvelope) -> None:
            raise RuntimeError("boom")

        bus.subscribe(EventType.RAW_DATA_RECEIVED, _broken)
        bus.publish(_event())  # must not raise -- no handler is registered

    def test_a_raising_dead_letter_handler_does_not_propagate_to_the_publisher(self) -> None:
        bus = EventBus()

        def _broken_handler(_e: EventEnvelope) -> None:
            raise RuntimeError("boom")

        def _broken_dead_letter(_e: EventEnvelope, _exc: Exception) -> None:
            raise RuntimeError("dead letter handler is broken too")

        bus.subscribe(EventType.RAW_DATA_RECEIVED, _broken_handler)
        bus.set_dead_letter_handler(_broken_dead_letter)
        bus.publish(_event())  # must not raise despite both handlers failing

    def test_a_successful_subscriber_never_invokes_the_dead_letter_handler(self) -> None:
        bus = EventBus()
        dead_lettered: list[EventEnvelope] = []
        bus.set_dead_letter_handler(lambda event, _exc: dead_lettered.append(event))
        bus.subscribe(EventType.RAW_DATA_RECEIVED, lambda _e: None)

        bus.publish(_event())

        assert dead_lettered == []


class TestHistory:
    def test_history_returns_every_published_event_oldest_first(self) -> None:
        bus = EventBus()
        first = _event(EventType.RAW_DATA_RECEIVED)
        second = _event(EventType.RAW_DATA_VALIDATED)
        bus.publish(first)
        bus.publish(second)

        assert bus.history() == [first, second]

    def test_history_filters_by_event_type(self) -> None:
        bus = EventBus()
        bus.publish(_event(EventType.RAW_DATA_RECEIVED))
        validated = _event(EventType.RAW_DATA_VALIDATED)
        bus.publish(validated)

        assert bus.history(EventType.RAW_DATA_VALIDATED) == [validated]
