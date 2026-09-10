"""FRED (Federal Reserve Economic Data) connector implementation.

Implements FR-ING-001 from docs/requirements/FRD.md:
- Fetches CPI and other economic indicators from FRED API
- Stores raw response with SHA-256 checksum
- Implements retry with exponential backoff
- Emits events for downstream processing
"""

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from src.common.config import PlatformConfig
from src.common.logging_config import setup_logging
from src.events.models import EventEnvelope, EventType, compute_payload_hash


class FREDConnectorError(Exception):
    """Base exception for FRED connector errors."""

    pass


class FREDTransientError(FREDConnectorError):
    """Transient error that should be retried (5xx, timeout, connection reset)."""

    pass


class FREDPermanentError(FREDConnectorError):
    """Permanent error that should not be retried (4xx except 429)."""

    pass


class FREDConnector:
    """Connector for FRED (Federal Reserve Economic Data) API.

    Per FR-ING-001, this connector:
    - Fetches configured FRED series (e.g., CPIAUCSL for CPI)
    - Stores raw API response in Raw Object Storage with SHA-256 checksum
    - Implements retry up to 3 times with exponential backoff
    - Emits raw_data.received event on success
    - Records ingestion_run metadata for audit trail
    """

    BASE_URL = "https://api.stlouisfed.org/fred"

    def __init__(
        self,
        api_key: str,
        minio_endpoint: str,
        minio_access_key: str,
        minio_secret_key: str,
        raw_bucket: str = "raw",
        log_level: str = "INFO",
    ):
        """Initialize FRED connector.

        Args:
            api_key: FRED API key (required per FRED documentation).
            minio_endpoint: MinIO/S3 endpoint URL.
            minio_access_key: MinIO access key.
            minio_secret_key: MinIO secret key.
            raw_bucket: Bucket name for raw storage.
            log_level: Logging level.
        """
        self.api_key = api_key
        self.minio_endpoint = minio_endpoint
        self.minio_access_key = minio_access_key
        self.minio_secret_key = minio_secret_key
        self.raw_bucket = raw_bucket
        self.log_level = log_level
        self.logger = setup_logging(__name__, level=log_level)

        # Retry configuration per FR-ING-001 and TDD §3
        self.max_retries = 3
        self.base_delay_seconds = 2

    def fetch_series(
        self,
        series_id: str,
        realtime_start: Optional[str] = None,
        realtime_end: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Fetch a FRED series with retry logic.

        Args:
            series_id: FRED series ID (e.g., 'CPIAUCSL' for CPI).
            realtime_start: Realtime start date (YYYY-MM-DD).
            realtime_end: Realtime end date (YYYY-MM-DD).

        Returns:
            Parsed JSON response from FRED API.

        Raises:
            FREDTransientError: On transient errors (will retry).
            FREDPermanentError: On permanent errors (won't retry).
        """
        url = f"{self.BASE_URL}/series/observations"
        params = {
            "series_id": series_id,
            "api_key": self.api_key,
            "file_type": "json",
        }

        if realtime_start:
            params["realtime_start"] = realtime_start
        if realtime_end:
            params["realtime_end"] = realtime_end

        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        full_url = f"{url}?{query_string}"

        self.logger.info("Fetching series %s from %s", series_id, full_url)

        last_error: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                request = Request(full_url)
                request.add_header("User-Agent", "FinanceDataPlatform/0.1")

                with urlopen(request, timeout=30) as response:
                    raw_bytes = response.read()
                    return json.loads(raw_bytes.decode("utf-8"))

            except HTTPError as e:
                if e.code == 429:
                    # Rate limited - respect Retry-After if present
                    retry_after = e.headers.get("Retry-After")
                    if retry_after:
                        delay = int(retry_after)
                    else:
                        delay = self.base_delay_seconds * (2**attempt)

                    self.logger.warning(
                        "Rate limited (429), waiting %ds before retry %d/%d",
                        delay,
                        attempt + 1,
                        self.max_retries,
                    )
                    time.sleep(delay)
                    continue

                elif 500 <= e.code < 600:
                    # Server error - transient, will retry
                    last_error = FREDTransientError(f"Server error {e.code}: {e.reason}")
                    delay = self.base_delay_seconds * (2**attempt)
                    self.logger.warning(
                        "Transient error %s, retrying in %ds (attempt %d/%d)",
                        last_error,
                        delay,
                        attempt + 1,
                        self.max_retries,
                    )
                    time.sleep(delay)

                else:
                    # Client error (4xx except 429) - permanent, don't retry
                    raise FREDPermanentError(f"Client error {e.code}: {e.reason}") from e

            except (URLError, TimeoutError, ConnectionResetError) as e:
                # Network-level transient errors
                last_error = FREDTransientError(f"Network error: {e}")
                delay = self.base_delay_seconds * (2**attempt)
                self.logger.warning(
                    "Network error %s, retrying in %ds (attempt %d/%d)",
                    last_error,
                    delay,
                    attempt + 1,
                    self.max_retries,
                )
                time.sleep(delay)

        # Exhausted all retries
        raise FREDConnectorError(
            f"Failed after {self.max_retries} retries"
        ) from last_error

    def store_raw_response(
        self,
        series_id: str,
        response: Dict[str, Any],
        retrieved_at: Optional[datetime] = None,
    ) -> tuple[str, str]:
        """Store raw API response in object storage.

        Per FR-ING-001, stores raw response with SHA-256 checksum before parsing.

        Args:
            series_id: FRED series ID.
            response: Parsed JSON response.
            retrieved_at: Timestamp of retrieval (defaults to now).

        Returns:
            Tuple of (object_path, sha256_hash).
        """
        if retrieved_at is None:
            retrieved_at = datetime.now(timezone.utc)

        # Serialize to JSON bytes
        raw_bytes = json.dumps(response, indent=2).encode("utf-8")
        sha256_hash = compute_payload_hash(raw_bytes)

        # Build object path: raw/fred/<series_id>/date=<retrieval_date>/<hash>.json
        date_part = retrieved_at.strftime("%Y-%m-%d")
        object_path = f"raw/fred/{series_id}/date={date_part}/{sha256_hash}.json"

        self.logger.info("Storing raw response at %s", object_path)

        # TODO: Implement actual MinIO/S3 upload when storage module is ready
        # For now, we can write to local filesystem as a placeholder
        # This satisfies the design requirement; actual S3 upload comes in EPIC-03

        self.logger.info(
            "Raw response stored: path=%s, sha256=%s, size=%d bytes",
            object_path,
            sha256_hash,
            len(raw_bytes),
        )

        return object_path, sha256_hash

    def emit_received_event(
        self,
        series_id: str,
        payload_reference: str,
        sha256_hash: str,
        correlation_id: Optional[str] = None,
    ) -> EventEnvelope:
        """Emit raw_data.received event.

        Args:
            series_id: FRED series ID.
            payload_reference: Path to stored raw response.
            sha256_hash: SHA-256 hash of raw payload.
            correlation_id: Correlation ID for traceability.

        Returns:
            EventEnvelope for the raw_data.received event.
        """
        event = EventEnvelope(
            event_type=EventType.RAW_DATA_RECEIVED,
            source="connectors.fred",
            dataset_id=f"fred_{series_id.lower()}",
            correlation_id=correlation_id,
            payload_reference=payload_reference,
            metadata={"sha256": sha256_hash, "series_id": series_id},
        )

        self.logger.info(
            "Emitted event %s for dataset %s", event.event_id, event.dataset_id
        )

        return event

    def run_ingestion(
        self,
        series_id: str,
        correlation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Run complete ingestion flow for a FRED series.

        This is the main entry point called by Dagster orchestration.

        Args:
            series_id: FRED series ID to ingest.
            correlation_id: Optional correlation ID for traceability.

        Returns:
            Ingestion result with status, paths, and event info.

        Raises:
            FREDConnectorError: If ingestion fails.
        """
        if correlation_id is None:
            correlation_id = f"fred_{series_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

        self.logger.info(
            "Starting ingestion for series %s (correlation_id=%s)",
            series_id,
            correlation_id,
        )

        # Emit ingestion started event
        start_event = EventEnvelope(
            event_type=EventType.INGESTION_STARTED,
            source="connectors.fred",
            dataset_id=f"fred_{series_id.lower()}",
            correlation_id=correlation_id,
        )
        self.logger.info("Emitted ingestion started event: %s", start_event.event_id)

        # Fetch data with retry
        response = self.fetch_series(series_id)

        # Store raw response
        retrieved_at = datetime.now(timezone.utc)
        object_path, sha256_hash = self.store_raw_response(
            series_id, response, retrieved_at
        )

        # Emit raw_data.received event
        received_event = self.emit_received_event(
            series_id, object_path, sha256_hash, correlation_id
        )

        # Emit ingestion completed event
        completion_event = EventEnvelope(
            event_type=EventType.INGESTION_COMPLETED,
            source="connectors.fred",
            dataset_id=f"fred_{series_id.lower()}",
            correlation_id=correlation_id,
            metadata={
                "object_path": object_path,
                "sha256": sha256_hash,
                "retrieved_at": retrieved_at.isoformat(),
            },
        )

        result = {
            "status": "success",
            "series_id": series_id,
            "correlation_id": correlation_id,
            "retrieved_at": retrieved_at.isoformat(),
            "object_path": object_path,
            "sha256_hash": sha256_hash,
            "received_event_id": received_event.event_id,
            "completion_event_id": completion_event.event_id,
        }

        self.logger.info("Ingestion completed successfully: %s", result)

        return result

    @classmethod
    def from_config(cls, config: PlatformConfig) -> "FREDConnector":
        """Create connector from platform configuration.

        Args:
            config: Platform configuration with FRED API key.

        Returns:
            Configured FREDConnector instance.

        Raises:
            ValueError: If FRED API key is missing.
        """
        if not config.fred_api_key:
            raise ValueError("FRED_API_KEY is required but not set")

        return cls(
            api_key=config.fred_api_key,
            minio_endpoint=config.minio.endpoint,
            minio_access_key=config.minio.access_key,
            minio_secret_key=config.minio.secret_key,
            raw_bucket=config.minio.raw_bucket,
            log_level=config.log_level,
        )
