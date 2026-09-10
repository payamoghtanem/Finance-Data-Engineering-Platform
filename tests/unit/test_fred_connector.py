"""Unit tests for FRED connector.

Tests FR-ING-001 implementation without requiring network access or API keys.
"""

import json
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from src.connectors.fred.connector import (
    FREDConnector,
    FREDConnectorError,
    FREDTransientError,
    FREDPermanentError,
)
from src.events.models import EventType


class TestFREDConnectorRetry:
    """Test retry behavior per FR-ING-001 and TDD §3."""

    def setup_method(self):
        """Set up test fixtures."""
        self.connector = FREDConnector(
            api_key="test_api_key",
            minio_endpoint="http://localhost:9000",
            minio_access_key="test_access",
            minio_secret_key="test_secret",
            log_level="DEBUG",
        )
        # Reduce delays for faster testing
        self.connector.base_delay_seconds = 0.01

    @patch('src.connectors.fred.connector.urlopen')
    def test_success_on_first_attempt(self, mock_urlopen):
        """Test successful fetch on first attempt."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "observations": [
                {"date": "2024-01-01", "value": "308.417"}
            ]
        }).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = self.connector.fetch_series("CPIAUCSL")

        assert "observations" in result
        assert len(result["observations"]) == 1
        assert result["observations"][0]["value"] == "308.417"
        mock_urlopen.assert_called_once()

    @patch('src.connectors.fred.connector.urlopen')
    def test_retry_on_5xx_error(self, mock_urlopen):
        """Test retry on transient 5xx server error."""
        from urllib.error import HTTPError

        # Create a mock context manager that succeeds on third call
        mock_context = MagicMock()
        mock_context.read.return_value = json.dumps({"observations": []}).encode('utf-8')
        
        # Fail twice with 503, succeed on third attempt
        mock_urlopen.side_effect = [
            HTTPError("url", 503, "Service Unavailable", {}, None),
            HTTPError("url", 503, "Service Unavailable", {}, None),
            MagicMock(**{
                "__enter__.return_value": mock_context
            })
        ]

        result = self.connector.fetch_series("CPIAUCSL")

        # Should have been called 3 times (initial + 2 retries)
        assert mock_urlopen.call_count == 3
        assert "observations" in result

    @patch('src.connectors.fred.connector.urlopen')
    def test_no_retry_on_4xx_error(self, mock_urlopen):
        """Test no retry on permanent 4xx client error."""
        from urllib.error import HTTPError

        mock_urlopen.side_effect = HTTPError(
            "url", 403, "Forbidden", {}, None
        )

        with pytest.raises(FREDPermanentError) as exc_info:
            self.connector.fetch_series("CPIAUCSL")

        assert "403" in str(exc_info.value)
        # Should only be called once (no retries)
        assert mock_urlopen.call_count == 1


class TestFREDConnectorEventEmission:
    """Test event emission per event-schema.md."""

    def setup_method(self):
        """Set up test fixtures."""
        self.connector = FREDConnector(
            api_key="test_api_key",
            minio_endpoint="http://localhost:9000",
            minio_access_key="test_access",
            minio_secret_key="test_secret",
        )

    def test_emit_received_event(self):
        """Test raw_data.received event structure."""
        event = self.connector.emit_received_event(
            series_id="CPIAUCSL",
            payload_reference="raw/fred/CPIAUCSL/date=2024-01-01/abc123.json",
            sha256_hash="abc123",
            correlation_id="test-correlation-123",
        )

        assert event.event_type == EventType.RAW_DATA_RECEIVED
        assert event.source == "connectors.fred"
        assert event.dataset_id == "fred_cpiaucsl"
        assert event.correlation_id == "test-correlation-123"
        assert event.payload_reference == "raw/fred/CPIAUCSL/date=2024-01-01/abc123.json"
        assert event.metadata["sha256"] == "abc123"
        assert event.metadata["series_id"] == "CPIAUCSL"

    def test_event_has_required_fields(self):
        """Test that emitted events have all required fields per event-schema.md."""
        event = self.connector.emit_received_event(
            series_id="CPIAUCSL",
            payload_reference="test/path.json",
            sha256_hash="test_hash",
        )

        event_dict = event.to_dict()

        # Required fields per EventEnvelope
        assert "event_id" in event_dict
        assert "event_type" in event_dict
        assert "source" in event_dict
        assert "dataset_id" in event_dict
        assert "timestamp" in event_dict
        assert event_dict["event_type"] == "raw_data.received"
        assert event_dict["source"] == "connectors.fred"


class TestFREDConnectorConfig:
    """Test configuration loading."""

    def test_from_config_requires_api_key(self):
        """Test that from_config raises if API key is missing."""
        from src.common.config import PlatformConfig, DatabaseConfig, MinIOConfig

        config = PlatformConfig(
            database=DatabaseConfig(
                host="localhost",
                port=5432,
                database="test",
                user="test",
                password="test",
            ),
            minio=MinIOConfig(
                endpoint="http://localhost:9000",
                access_key="test",
                secret_key="test",
            ),
            fred_api_key=None,  # Missing API key
        )

        with pytest.raises(ValueError, match="FRED_API_KEY"):
            FREDConnector.from_config(config)

    def test_from_config_success(self):
        """Test successful connector creation from config."""
        from src.common.config import PlatformConfig, DatabaseConfig, MinIOConfig

        config = PlatformConfig(
            database=DatabaseConfig(
                host="localhost",
                port=5432,
                database="test",
                user="test",
                password="test",
            ),
            minio=MinIOConfig(
                endpoint="http://localhost:9000",
                access_key="test",
                secret_key="test",
            ),
            fred_api_key="test_key",
            log_level="DEBUG",
        )

        connector = FREDConnector.from_config(config)

        assert connector.api_key == "test_key"
        assert connector.minio_endpoint == "http://localhost:9000"
        assert connector.log_level == "DEBUG"
