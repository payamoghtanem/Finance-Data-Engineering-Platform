"""FRED (Federal Reserve Economic Data) connector.

Implements FR-ING-001 from docs/requirements/FRD.md:
- fetches a configured FRED series,
- persists the *original* response bytes with a SHA-256 checksum **before**
  anything parses them (architecture principle 2: immutable raw data),
- retries transient failures with exponential backoff, never retries 4xx,
- emits the documented events from docs/technical/event-schema.md.

Secrets discipline (NFR-SEC-003): the FRED API key travels in the query string,
so the full request URL is credential-bearing and is never logged. Log lines
carry the endpoint and series id only.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from src.common.config import PlatformConfig
from src.common.logging_config import setup_logging
from src.common.raw_storage import (
    LocalRawStorage,
    RawStorage,
    build_object_key,
    compute_sha256,
)
from src.events.models import EventEnvelope, EventType


class FREDConnectorError(Exception):
    """Base exception for FRED connector errors."""


class FREDTransientError(FREDConnectorError):
    """Transient error worth retrying (5xx, timeout, connection reset)."""


class FREDPermanentError(FREDConnectorError):
    """Permanent error that must not be retried (4xx other than 429)."""


class FREDConnector:
    """Connector for the FRED API.

    Args:
        api_key: FRED API key.
        raw_storage: Where original payloads are persisted. Injected so the
            MinIO backend can replace the local one in EPIC-03 without touching
            this class, and so tests need no filesystem assumptions.
        log_level: Logging level.
        sleep: Injected sleep, so retry tests do not actually wait.
    """

    BASE_URL = "https://api.stlouisfed.org/fred"
    USER_AGENT = "FinanceDataPlatform/0.1"
    MAX_RETRIES = 3
    BASE_DELAY_SECONDS = 2
    REQUEST_TIMEOUT_SECONDS = 30

    def __init__(
        self,
        api_key: str,
        raw_storage: RawStorage | None = None,
        log_level: str = "INFO",
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.api_key = api_key
        self.raw_storage: RawStorage = raw_storage or LocalRawStorage("raw_store")
        self.logger = setup_logging(__name__, level=log_level)
        self._sleep = sleep

    def _build_url(self, series_id: str, **extra: str) -> str:
        """Build the request URL. The result contains the API key: never log it."""
        params = {
            "series_id": series_id,
            "api_key": self.api_key,
            "file_type": "json",
            **extra,
        }
        return f"{self.BASE_URL}/series/observations?{urlencode(params)}"

    def fetch_series_raw(
        self,
        series_id: str,
        realtime_start: str | None = None,
        realtime_end: str | None = None,
    ) -> bytes:
        """Fetch a FRED series and return the response bytes exactly as received.

        Returning bytes rather than parsed JSON is deliberate: the caller must be
        able to persist the untouched payload, and the checksum must be taken
        over what the source actually sent (NFR-AUDIT-001).
        """
        extra: dict[str, str] = {}
        if realtime_start:
            extra["realtime_start"] = realtime_start
        if realtime_end:
            extra["realtime_end"] = realtime_end

        url = self._build_url(series_id, **extra)

        # Endpoint + series only. `url` carries the API key.
        self.logger.info("Fetching series %s from %s/series/observations", series_id, self.BASE_URL)

        last_error: Exception | None = None

        for attempt in range(self.MAX_RETRIES + 1):
            try:
                request = Request(url)  # noqa: S310 - fixed https FRED endpoint
                request.add_header("User-Agent", self.USER_AGENT)
                with urlopen(request, timeout=self.REQUEST_TIMEOUT_SECONDS) as response:  # noqa: S310
                    return bytes(response.read())

            except HTTPError as exc:
                if exc.code == 429:
                    retry_after = exc.headers.get("Retry-After") if exc.headers else None
                    delay = (
                        int(retry_after)
                        if retry_after and retry_after.isdigit()
                        else self.BASE_DELAY_SECONDS * (2**attempt)
                    )
                    last_error = FREDTransientError(f"Rate limited (429) on {series_id}")
                    self.logger.warning(
                        "Rate limited (429), waiting %ds before retry %d/%d",
                        delay,
                        attempt + 1,
                        self.MAX_RETRIES,
                    )
                elif 500 <= exc.code < 600:
                    last_error = FREDTransientError(f"Server error {exc.code}: {exc.reason}")
                    delay = self.BASE_DELAY_SECONDS * (2**attempt)
                    self.logger.warning(
                        "Transient error %s, retrying in %ds (attempt %d/%d)",
                        last_error,
                        delay,
                        attempt + 1,
                        self.MAX_RETRIES,
                    )
                else:
                    # 4xx: permanent. Retrying a bad request just burns rate limit.
                    raise FREDPermanentError(f"Client error {exc.code}: {exc.reason}") from exc

            except (TimeoutError, ConnectionResetError, URLError) as exc:
                last_error = FREDTransientError(f"Network error: {exc}")
                delay = self.BASE_DELAY_SECONDS * (2**attempt)
                self.logger.warning(
                    "Network error %s, retrying in %ds (attempt %d/%d)",
                    last_error,
                    delay,
                    attempt + 1,
                    self.MAX_RETRIES,
                )

            if attempt < self.MAX_RETRIES:
                self._sleep(delay)

        raise FREDConnectorError(
            f"Failed to fetch {series_id} after {self.MAX_RETRIES} retries"
        ) from last_error

    def store_raw(
        self,
        series_id: str,
        payload: bytes,
        retrieved_at: datetime | None = None,
    ) -> tuple[str, str]:
        """Persist the original payload and return (object_key, sha256).

        The checksum is taken over the exact bytes received, and the key is
        content-addressed, so storing the same payload twice is a no-op
        (the raw half of FR-ING-001's idempotency requirement).
        """
        if retrieved_at is None:
            retrieved_at = datetime.now(UTC)

        sha256 = compute_sha256(payload)
        key = build_object_key("fred", series_id, retrieved_at, sha256)
        self.raw_storage.put(key, payload)

        self.logger.info("Raw payload stored: key=%s sha256=%s bytes=%d", key, sha256, len(payload))
        return key, sha256

    def run_ingestion(
        self,
        series_id: str,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """Run the full ingestion flow for one FRED series.

        Order matters and is enforced here: fetch bytes -> persist raw -> only
        then parse. Parsing before persisting would make the stored artifact a
        re-serialization rather than the source's own response.
        """
        if correlation_id is None:
            correlation_id = f"fred_{series_id}_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"

        dataset_id = f"fred_{series_id.lower()}"
        self.logger.info(
            "Starting ingestion series=%s correlation_id=%s", series_id, correlation_id
        )

        requested = EventEnvelope(
            event_type=EventType.INGESTION_REQUESTED,
            producer="connectors.fred",
            dataset_id=dataset_id,
            correlation_id=correlation_id,
        )
        self.logger.info("Event %s: %s", requested.event_type.value, requested.event_id)

        raw_payload = self.fetch_series_raw(series_id)

        retrieved_at = datetime.now(UTC)
        object_key, sha256 = self.store_raw(series_id, raw_payload, retrieved_at)

        received = EventEnvelope(
            event_type=EventType.RAW_DATA_RECEIVED,
            producer="connectors.fred",
            dataset_id=dataset_id,
            correlation_id=correlation_id,
            payload_reference=object_key,
            metadata={"sha256": sha256, "series_id": series_id},
        )
        self.logger.info("Event %s: %s", received.event_type.value, received.event_id)

        # Parsed only after the original bytes are safely persisted.
        parsed: dict[str, Any] = json.loads(raw_payload.decode("utf-8"))
        observation_count = len(parsed.get("observations", []))

        return {
            "status": "success",
            "series_id": series_id,
            "dataset_id": dataset_id,
            "correlation_id": correlation_id,
            "retrieved_at": retrieved_at.isoformat(),
            "object_key": object_key,
            "sha256": sha256,
            "observation_count": observation_count,
            "requested_event_id": requested.event_id,
            "received_event_id": received.event_id,
        }

    @classmethod
    def from_config(
        cls, config: PlatformConfig, raw_storage: RawStorage | None = None
    ) -> FREDConnector:
        """Build a connector from platform configuration."""
        if not config.fred_api_key:
            raise ValueError("FRED_API_KEY is required but not set")
        return cls(
            api_key=config.fred_api_key,
            raw_storage=raw_storage,
            log_level=config.log_level,
        )
