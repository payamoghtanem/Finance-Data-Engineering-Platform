"""Unit tests for DLQRecorder (EPIC-09, FR-OPS-003)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from src.common.dlq import DLQRecorder

_T0 = datetime(2026, 9, 11, 9, 0, 0, tzinfo=UTC)


@pytest.fixture
def recorder() -> DLQRecorder:
    return DLQRecorder(db_path=":memory:")


class TestRecord:
    def test_record_creates_a_pending_entry(self, recorder: DLQRecorder) -> None:
        entry = recorder.record(
            event_id="evt-1",
            event_type="raw_data.quarantined",
            producer="validation.engine",
            dataset_id="fred_cpiaucsl",
            failure_reason="data-quality rule(s) failed: nonnegative_volume",
            quarantined_at=_T0,
        )

        assert entry.event_id == "evt-1"
        assert entry.status == "pending"
        assert entry.replayed_at is None
        assert entry.quarantined_at == _T0

    def test_metadata_round_trips(self, recorder: DLQRecorder) -> None:
        entry = recorder.record(
            event_id="evt-1",
            event_type="raw_data.quarantined",
            producer="validation.engine",
            dataset_id="fred_cpiaucsl",
            failure_reason="boom",
            metadata={"failed_rules": ["nonnegative_volume"]},
        )

        assert entry.metadata == {"failed_rules": ["nonnegative_volume"]}

    def test_recording_the_same_event_id_twice_does_not_duplicate(
        self, recorder: DLQRecorder
    ) -> None:
        first = recorder.record(
            event_id="evt-1",
            event_type="raw_data.quarantined",
            producer="validation.engine",
            dataset_id="fred_cpiaucsl",
            failure_reason="first failure",
        )
        second = recorder.record(
            event_id="evt-1",
            event_type="raw_data.quarantined",
            producer="validation.engine",
            dataset_id="fred_cpiaucsl",
            failure_reason="a different failure reason",
        )

        assert first == second
        assert first.failure_reason == "first failure"
        assert len(recorder.list_pending()) == 1


class TestMarkReplayed:
    def test_transitions_pending_to_replayed(self, recorder: DLQRecorder) -> None:
        recorder.record(
            event_id="evt-1",
            event_type="raw_data.quarantined",
            producer="validation.engine",
            dataset_id="fred_cpiaucsl",
            failure_reason="boom",
        )

        updated = recorder.mark_replayed("evt-1", replayed_at=_T0)

        assert updated is not None
        assert updated.status == "replayed"
        assert updated.replayed_at == _T0

    def test_is_idempotent_on_an_already_replayed_entry(self, recorder: DLQRecorder) -> None:
        recorder.record(
            event_id="evt-1",
            event_type="raw_data.quarantined",
            producer="validation.engine",
            dataset_id="fred_cpiaucsl",
            failure_reason="boom",
        )
        recorder.mark_replayed("evt-1", replayed_at=_T0)

        second_call = recorder.mark_replayed("evt-1", replayed_at=_T0.replace(hour=23))

        assert second_call is not None
        assert second_call.replayed_at == _T0  # not overwritten by the second call

    def test_returns_none_for_an_unknown_event_id(self, recorder: DLQRecorder) -> None:
        assert recorder.mark_replayed("does-not-exist") is None


class TestListPending:
    def test_excludes_replayed_entries(self, recorder: DLQRecorder) -> None:
        recorder.record(
            event_id="evt-1",
            event_type="raw_data.quarantined",
            producer="validation.engine",
            dataset_id="fred_cpiaucsl",
            failure_reason="boom",
        )
        recorder.record(
            event_id="evt-2",
            event_type="raw_data.quarantined",
            producer="validation.engine",
            dataset_id="fred_cpiaucsl",
            failure_reason="boom",
        )
        recorder.mark_replayed("evt-1")

        pending = recorder.list_pending()

        assert [entry.event_id for entry in pending] == ["evt-2"]


class TestGet:
    def test_returns_none_for_an_unknown_event_id(self, recorder: DLQRecorder) -> None:
        assert recorder.get("does-not-exist") is None
