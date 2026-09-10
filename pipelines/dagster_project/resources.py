"""Dagster resources wrapping this platform's own components.

Kept thin per the `pipelines/` module boundary (technical-design-document.md
§2): a resource's job is to hand an asset a configured instance of an
existing class, never to reimplement fetch/storage logic itself.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from dagster import ConfigurableResource
from src.bronze.writer import BronzeWriter
from src.common.config import PlatformConfig
from src.common.raw_storage import S3RawStorage
from src.common.version import get_code_version
from src.connectors.fred.connector import FREDConnector


class FREDIngestionResource(ConfigurableResource):  # type: ignore[type-arg]
    """Runs one FRED series ingestion using the real `FREDConnector`.

    Builds a fresh `FREDConnector` from environment configuration on every
    call rather than holding one across the resource's lifetime -- matches
    `FREDConnector`'s own statelessness (a new instance per run is cheap and
    avoids any accidental cross-run state carried between schedule firings).
    """

    series_id: str = "CPIAUCSL"

    def run_ingestion(self) -> dict[str, Any]:
        config = PlatformConfig.from_env()
        connector = FREDConnector.from_config(config)
        return connector.run_ingestion(self.series_id)


class BronzeResource(ConfigurableResource):  # type: ignore[type-arg]
    """Loads one raw object into Bronze using the real `BronzeWriter`."""

    db_path: str = "bronze_store/bronze.duckdb"

    def write_bronze(
        self,
        *,
        source_id: str,
        dataset_id: str,
        raw_object_key: str,
        raw_sha256: str,
        retrieved_at: datetime,
    ) -> dict[str, Any]:
        config = PlatformConfig.from_env()
        raw_storage = S3RawStorage.from_config(config.minio)
        writer = BronzeWriter(raw_storage, db_path=self.db_path)
        try:
            record = writer.write(
                source_id=source_id,
                dataset_id=dataset_id,
                raw_object_key=raw_object_key,
                raw_sha256=raw_sha256,
                retrieved_at=retrieved_at,
                code_version=get_code_version(),
            )
        finally:
            writer.close()
        return {"bronze_id": record.bronze_id, "raw_object_key": record.raw_object_key}
