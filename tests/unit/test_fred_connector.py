"""Unit tests for the FRED connector (FR-ING-001).

No network access and no API key: every external call is faked, per
docs/engineering/test-strategy.md §2.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

import pytest
from src.common.config import DatabaseConfig, MinIOConfig, PlatformConfig
from src.common.ingestion_run import IngestionRunRecorder
from src.common.raw_storage import LocalRawStorage, compute_sha256
from src.connectors.fred.connector import (
    FREDConnector,
    FREDConnectorError,
    FREDPermanentError,
)
from src.events.models import EventType

SAMPLE_PAYLOAD = json.dumps({"observations": [{"date": "2024-01-01", "value": "308.417"}]}).encode(
    "utf-8"
)


def _response(payload: bytes = SAMPLE_PAYLOAD) -> MagicMock:
    """Build a urlopen context manager returning `payload`."""
    body = MagicMock()
    body.read.return_value = payload
    ctx = MagicMock()
    ctx.__enter__.return_value = body
    return ctx


def _connector(tmp_path, **kwargs) -> FREDConnector:
    kwargs.setdefault("ingestion_run_recorder", IngestionRunRecorder(db_path=":memory:"))
    return FREDConnector(
        api_key="test_api_key",
        raw_storage=LocalRawStorage(tmp_path),
        sleep=lambda _: None,  # never actually wait in tests
        **kwargs,
    )


class TestRetryBehaviour:
    """FR-ING-001: retry transient failures, never retry 4xx."""

    @patch("src.connectors.fred.connector.urlopen")
    def test_success_on_first_attempt(self, mock_urlopen, tmp_path):
        mock_urlopen.return_value = _response()
        payload = _connector(tmp_path).fetch_series_raw("CPIAUCSL")
        assert payload == SAMPLE_PAYLOAD
        assert mock_urlopen.call_count == 1

    @patch("src.connectors.fred.connector.urlopen")
    def test_retries_then_succeeds_on_5xx(self, mock_urlopen, tmp_path):
        mock_urlopen.side_effect = [
            HTTPError("url", 503, "Service Unavailable", {}, None),
            HTTPError("url", 503, "Service Unavailable", {}, None),
            _response(),
        ]
        payload = _connector(tmp_path).fetch_series_raw("CPIAUCSL")
        assert payload == SAMPLE_PAYLOAD
        assert mock_urlopen.call_count == 3

    @patch("src.connectors.fred.connector.urlopen")
    def test_gives_up_after_three_retries(self, mock_urlopen, tmp_path):
        mock_urlopen.side_effect = HTTPError("url", 500, "Server Error", {}, None)
        with pytest.raises(FREDConnectorError):
            _connector(tmp_path).fetch_series_raw("CPIAUCSL")
        # 1 initial attempt + 3 retries
        assert mock_urlopen.call_count == 4

    @patch("src.connectors.fred.connector.urlopen")
    def test_no_retry_on_4xx(self, mock_urlopen, tmp_path):
        mock_urlopen.side_effect = HTTPError("url", 403, "Forbidden", {}, None)
        with pytest.raises(FREDPermanentError, match="403"):
            _connector(tmp_path).fetch_series_raw("CPIAUCSL")
        assert mock_urlopen.call_count == 1

    @patch("src.connectors.fred.connector.urlopen")
    def test_429_is_retried_not_treated_as_permanent(self, mock_urlopen, tmp_path):
        mock_urlopen.side_effect = [
            HTTPError("url", 429, "Too Many Requests", {}, None),
            _response(),
        ]
        payload = _connector(tmp_path).fetch_series_raw("CPIAUCSL")
        assert payload == SAMPLE_PAYLOAD
        assert mock_urlopen.call_count == 2


class TestSecretHandling:
    """NFR-SEC-003: the API key must never reach a log line."""

    @patch("src.connectors.fred.connector.urlopen")
    def test_api_key_never_logged(self, mock_urlopen, tmp_path, caplog):
        mock_urlopen.return_value = _response()
        connector = _connector(tmp_path)
        with caplog.at_level("DEBUG"):
            connector.logger.propagate = True
            connector.fetch_series_raw("CPIAUCSL")
        assert "test_api_key" not in caplog.text
        assert "api_key" not in caplog.text

    def test_url_still_carries_the_key(self, tmp_path):
        # Guards the test above from passing trivially: the key really is in
        # the request URL, so keeping it out of the logs is a real constraint.
        url = _connector(tmp_path)._build_url("CPIAUCSL")
        assert "api_key=test_api_key" in url


class TestRawStorage:
    """FR-ING-001 / ARD principle 2: original bytes, stored before parsing."""

    @patch("src.connectors.fred.connector.urlopen")
    def test_stored_bytes_are_byte_identical_to_response(self, mock_urlopen, tmp_path):
        mock_urlopen.return_value = _response()
        storage = LocalRawStorage(tmp_path)
        connector = FREDConnector(
            api_key="k",
            raw_storage=storage,
            ingestion_run_recorder=IngestionRunRecorder(db_path=":memory:"),
            sleep=lambda _: None,
        )
        result = connector.run_ingestion("CPIAUCSL")
        assert storage.get(result["object_key"]) == SAMPLE_PAYLOAD

    @patch("src.connectors.fred.connector.urlopen")
    def test_checksum_matches_original_payload(self, mock_urlopen, tmp_path):
        mock_urlopen.return_value = _response()
        result = _connector(tmp_path).run_ingestion("CPIAUCSL")
        assert result["sha256"] == compute_sha256(SAMPLE_PAYLOAD)

    def test_store_raw_actually_persists(self, tmp_path):
        storage = LocalRawStorage(tmp_path)
        connector = FREDConnector(
            api_key="k",
            raw_storage=storage,
            ingestion_run_recorder=IngestionRunRecorder(db_path=":memory:"),
        )
        key, _ = connector.store_raw("CPIAUCSL", SAMPLE_PAYLOAD)
        assert storage.exists(key)

    def test_storing_same_payload_twice_is_idempotent(self, tmp_path):
        storage = LocalRawStorage(tmp_path)
        connector = FREDConnector(
            api_key="k",
            raw_storage=storage,
            ingestion_run_recorder=IngestionRunRecorder(db_path=":memory:"),
        )
        at = datetime(2026, 9, 10, tzinfo=UTC)
        key1, hash1 = connector.store_raw("CPIAUCSL", SAMPLE_PAYLOAD, at)
        key2, hash2 = connector.store_raw("CPIAUCSL", SAMPLE_PAYLOAD, at)
        assert (key1, hash1) == (key2, hash2)
        assert sum(1 for _ in tmp_path.rglob("*.json")) == 1


class TestEventEmission:
    """Events must be the documented ones, with stable identifiers."""

    @patch("src.connectors.fred.connector.urlopen")
    def test_emits_documented_event_types(self, mock_urlopen, tmp_path):
        mock_urlopen.return_value = _response()
        result = _connector(tmp_path).run_ingestion("CPIAUCSL")
        assert result["requested_event_id"] != result["received_event_id"]
        assert EventType.INGESTION_REQUESTED.value == "ingestion.requested"
        assert EventType.RAW_DATA_RECEIVED.value == "raw_data.received"

    def test_event_taxonomy_matches_documented_schema(self):
        # Exactly the nine events in docs/technical/event-schema.md.
        assert {e.value for e in EventType} == {
            "schedule.triggered",
            "ingestion.requested",
            "raw_data.received",
            "raw_data.validated",
            "raw_data.quarantined",
            "bronze_data.written",
            "silver_data.transformed",
            "gold_data.published",
            "data_product.ready",
        }


class TestConfig:
    def _config(self, **kwargs) -> PlatformConfig:
        return PlatformConfig(
            database=DatabaseConfig(
                host="localhost",
                port=5432,
                database="test",
                user="test",
                password="unused",  # noqa: S106 - test fixture, not a credential
            ),
            minio=MinIOConfig(
                endpoint="http://localhost:9000",
                access_key="test",
                secret_key="unused",  # noqa: S106 - test fixture, not a credential
            ),
            **kwargs,
        )

    def test_from_config_requires_api_key(self):
        with pytest.raises(ValueError, match="FRED_API_KEY"):
            FREDConnector.from_config(self._config(fred_api_key=None))

    def test_from_config_success(self, tmp_path):
        # Explicit raw_storage: the default now builds a real S3RawStorage
        # (EPIC-03) that would otherwise try to reach MinIO. See
        # TestFromConfigDefaultsToS3 below for that path, mocked via moto.
        # Explicit ingestion_run_recorder: the default writes a real DuckDB
        # file to disk (ops_store/), which a test must never do.
        connector = FREDConnector.from_config(
            self._config(fred_api_key="test_key", log_level="DEBUG"),
            raw_storage=LocalRawStorage(tmp_path),
            ingestion_run_recorder=IngestionRunRecorder(db_path=":memory:"),
        )
        assert connector.api_key == "test_key"


class TestFromConfigDefaultsToS3:
    """EPIC-03: from_config wires config.minio into a real S3RawStorage."""

    def _config(self, **kwargs):
        return PlatformConfig(
            database=DatabaseConfig(
                host="localhost",
                port=5432,
                database="test",
                user="test",
                password="unused",  # noqa: S106 - test fixture, not a credential
            ),
            minio=MinIOConfig(
                endpoint="http://localhost:9000",
                access_key="test",
                secret_key="unused",  # noqa: S106 - test fixture, not a credential
                raw_bucket="raw",
            ),
            **kwargs,
        )

    def test_omitting_raw_storage_builds_s3_backend(self):
        from src.common.raw_storage import S3RawStorage

        # ensure_bucket() is a real network call (head/create_bucket); this
        # test is about from_config's wiring, not S3RawStorage's own request
        # behaviour — that's already covered by test_s3_raw_storage.py against
        # a moto-mocked client. Stubbing it out keeps this test network-free
        # without depending on moto's handling of a custom endpoint_url.
        with patch.object(S3RawStorage, "ensure_bucket", return_value=None) as ensure_bucket:
            connector = FREDConnector.from_config(
                self._config(fred_api_key="test_key"),
                ingestion_run_recorder=IngestionRunRecorder(db_path=":memory:"),
            )

        assert isinstance(connector.raw_storage, S3RawStorage)
        assert connector.raw_storage.bucket == "raw"
        ensure_bucket.assert_called_once()


class TestIngestionRunRecording:
    """US-02-005 / FR-OPS-001: every run, success or failure, is recorded."""

    @patch("src.connectors.fred.connector.urlopen")
    def test_successful_run_is_recorded(self, mock_urlopen, tmp_path):
        mock_urlopen.return_value = _response()
        recorder = IngestionRunRecorder(db_path=":memory:")
        connector = _connector(tmp_path, ingestion_run_recorder=recorder)

        result = connector.run_ingestion("CPIAUCSL")

        runs = recorder.list_for_dataset("fred_cpiaucsl")
        assert len(runs) == 1
        assert runs[0].run_id == result["run_id"]
        assert runs[0].status == "success"
        assert runs[0].retry_count == 0
        assert runs[0].raw_storage_path == result["object_key"]
        assert runs[0].error is None

    @patch("src.connectors.fred.connector.urlopen")
    def test_retried_then_successful_run_records_retry_count(self, mock_urlopen, tmp_path):
        mock_urlopen.side_effect = [
            HTTPError("url", 503, "Service Unavailable", {}, None),
            HTTPError("url", 503, "Service Unavailable", {}, None),
            _response(),
        ]
        recorder = IngestionRunRecorder(db_path=":memory:")
        connector = _connector(tmp_path, ingestion_run_recorder=recorder)

        connector.run_ingestion("CPIAUCSL")

        runs = recorder.list_for_dataset("fred_cpiaucsl")
        assert runs[0].retry_count == 2

    @patch("src.connectors.fred.connector.urlopen")
    def test_failed_run_is_recorded_and_exception_still_raised(self, mock_urlopen, tmp_path):
        mock_urlopen.side_effect = HTTPError("url", 500, "Server Error", {}, None)
        recorder = IngestionRunRecorder(db_path=":memory:")
        connector = _connector(tmp_path, ingestion_run_recorder=recorder)

        with pytest.raises(FREDConnectorError):
            connector.run_ingestion("CPIAUCSL")

        runs = recorder.list_for_dataset("fred_cpiaucsl")
        assert len(runs) == 1
        assert runs[0].status == "failed"
        assert runs[0].raw_storage_path is None
        assert runs[0].error is not None

    @patch("src.connectors.fred.connector.urlopen")
    def test_request_hash_excludes_the_api_key(self, mock_urlopen, tmp_path):
        mock_urlopen.return_value = _response()
        recorder = IngestionRunRecorder(db_path=":memory:")
        connector = _connector(tmp_path, ingestion_run_recorder=recorder)

        connector.run_ingestion("CPIAUCSL")

        run = recorder.list_for_dataset("fred_cpiaucsl")[0]
        assert "test_api_key" not in run.request_hash
        assert len(run.request_hash) == 64  # sha256 hex digest
