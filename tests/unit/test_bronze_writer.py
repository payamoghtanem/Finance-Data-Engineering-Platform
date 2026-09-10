"""Unit tests for the Bronze writer (US-03-002, US-03-003)."""

from __future__ import annotations

import socket
from datetime import UTC, datetime

import pytest
from src.bronze.writer import BronzeWriteError, BronzeWriter
from src.common.raw_storage import LocalRawStorage, compute_sha256

PAYLOAD = b'{"observations": [{"date": "2024-01-01", "value": "308.417"}]}'


@pytest.fixture
def raw_storage(tmp_path) -> LocalRawStorage:  # type: ignore[no-untyped-def]
    storage = LocalRawStorage(tmp_path / "raw")
    storage.put("raw/fred/CPIAUCSL/date=2024-01-01/abc.json", PAYLOAD)
    return storage


@pytest.fixture
def writer(raw_storage: LocalRawStorage) -> BronzeWriter:  # type: ignore[no-untyped-def]
    return BronzeWriter(raw_storage=raw_storage, db_path=":memory:")


class TestBronzeWrite:
    def test_write_returns_record_with_correct_lineage(self, writer: BronzeWriter) -> None:
        retrieved_at = datetime(2024, 1, 1, tzinfo=UTC)
        record = writer.write(
            source_id="fred",
            dataset_id="fred_cpiaucsl",
            raw_object_key="raw/fred/CPIAUCSL/date=2024-01-01/abc.json",
            raw_sha256=compute_sha256(PAYLOAD),
            retrieved_at=retrieved_at,
            code_version="0.1.0",
        )
        assert record.source_id == "fred"
        assert record.raw_object_key == "raw/fred/CPIAUCSL/date=2024-01-01/abc.json"
        assert record.retrieved_at == retrieved_at
        assert record.code_version == "0.1.0"
        assert record.payload == PAYLOAD

    def test_lineage_round_trip(self, writer: BronzeWriter) -> None:
        key = "raw/fred/CPIAUCSL/date=2024-01-01/abc.json"
        written = writer.write(
            source_id="fred",
            dataset_id="fred_cpiaucsl",
            raw_object_key=key,
            raw_sha256=compute_sha256(PAYLOAD),
            retrieved_at=datetime(2024, 1, 1, tzinfo=UTC),
            code_version="0.1.0",
        )
        looked_up = writer.get_by_raw_object_key(key)
        assert looked_up == written

    def test_writing_same_raw_object_twice_is_idempotent(self, writer: BronzeWriter) -> None:
        key = "raw/fred/CPIAUCSL/date=2024-01-01/abc.json"
        kwargs = {
            "source_id": "fred",
            "dataset_id": "fred_cpiaucsl",
            "raw_object_key": key,
            "raw_sha256": compute_sha256(PAYLOAD),
            "retrieved_at": datetime(2024, 1, 1, tzinfo=UTC),
            "code_version": "0.1.0",
        }
        first = writer.write(**kwargs)
        second = writer.write(**kwargs)
        assert first.bronze_id == second.bronze_id
        count = writer._conn.execute("SELECT COUNT(*) FROM bronze_raw_records").fetchone()[0]
        assert count == 1

    def test_checksum_mismatch_raises(self, writer: BronzeWriter) -> None:
        with pytest.raises(BronzeWriteError, match="Checksum mismatch"):
            writer.write(
                source_id="fred",
                dataset_id="fred_cpiaucsl",
                raw_object_key="raw/fred/CPIAUCSL/date=2024-01-01/abc.json",
                raw_sha256="0" * 64,  # deliberately wrong
                retrieved_at=datetime(2024, 1, 1, tzinfo=UTC),
                code_version="0.1.0",
            )

    def test_missing_raw_object_raises(self, writer: BronzeWriter) -> None:
        with pytest.raises(BronzeWriteError):
            writer.write(
                source_id="fred",
                dataset_id="fred_cpiaucsl",
                raw_object_key="raw/does/not/exist.json",
                raw_sha256="0" * 64,
                retrieved_at=datetime(2024, 1, 1, tzinfo=UTC),
                code_version="0.1.0",
            )


class TestNoNetworkAccess:
    """US-03-003: a full Bronze rebuild must run with the network disabled."""

    def test_write_succeeds_with_sockets_blocked(
        self, raw_storage: LocalRawStorage, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _blocked_connect(*_args: object, **_kwargs: object) -> None:
            raise AssertionError("Bronze writer attempted a network connection")

        monkeypatch.setattr(socket.socket, "connect", _blocked_connect)

        writer = BronzeWriter(raw_storage=raw_storage, db_path=":memory:")
        record = writer.write(
            source_id="fred",
            dataset_id="fred_cpiaucsl",
            raw_object_key="raw/fred/CPIAUCSL/date=2024-01-01/abc.json",
            raw_sha256=compute_sha256(PAYLOAD),
            retrieved_at=datetime(2024, 1, 1, tzinfo=UTC),
            code_version="0.1.0",
        )
        assert record.payload == PAYLOAD


class TestEventPublication:
    """EPIC-06: BronzeWriter is bronze_data.written's documented producer."""

    def test_successful_write_publishes_bronze_data_written(
        self, raw_storage: LocalRawStorage
    ) -> None:
        from src.events.bus import EventBus
        from src.events.models import EventType

        bus = EventBus()
        writer = BronzeWriter(raw_storage=raw_storage, db_path=":memory:", event_bus=bus)

        writer.write(
            source_id="fred",
            dataset_id="fred_cpiaucsl",
            raw_object_key="raw/fred/CPIAUCSL/date=2024-01-01/abc.json",
            raw_sha256=compute_sha256(PAYLOAD),
            retrieved_at=datetime(2024, 1, 1, tzinfo=UTC),
            code_version="0.1.0",
        )

        published = bus.history(EventType.BRONZE_DATA_WRITTEN)
        assert len(published) == 1
        assert published[0].dataset_id == "fred_cpiaucsl"
        assert published[0].payload_reference == "raw/fred/CPIAUCSL/date=2024-01-01/abc.json"

    def test_idempotent_noop_write_does_not_republish(self, raw_storage: LocalRawStorage) -> None:
        from src.events.bus import EventBus
        from src.events.models import EventType

        bus = EventBus()
        writer = BronzeWriter(raw_storage=raw_storage, db_path=":memory:", event_bus=bus)
        kwargs = {
            "source_id": "fred",
            "dataset_id": "fred_cpiaucsl",
            "raw_object_key": "raw/fred/CPIAUCSL/date=2024-01-01/abc.json",
            "raw_sha256": compute_sha256(PAYLOAD),
            "retrieved_at": datetime(2024, 1, 1, tzinfo=UTC),
            "code_version": "0.1.0",
        }

        writer.write(**kwargs)
        writer.write(**kwargs)  # same raw object again — a no-op

        assert len(bus.history(EventType.BRONZE_DATA_WRITTEN)) == 1
