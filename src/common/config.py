"""Configuration loading utilities for the finance data platform.

This module provides centralized configuration loading from environment variables,
following the design in docs/technical/technical-design-document.md.
"""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class DatabaseConfig:
    """PostgreSQL database configuration."""

    host: str
    port: int
    database: str
    user: str
    password: str

    @property
    def connection_url(self) -> str:
        """Build PostgreSQL connection URL."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


@dataclass(frozen=True)
class MinIOConfig:
    """MinIO S3-compatible object storage configuration."""

    endpoint: str
    access_key: str
    secret_key: str
    raw_bucket: str = "raw"


@dataclass(frozen=True)
class PlatformConfig:
    """Main platform configuration container."""

    database: DatabaseConfig
    minio: MinIOConfig
    log_level: str = "INFO"
    fred_api_key: str | None = None
    coingecko_api_key: str | None = None
    sec_edgar_user_agent: str = "FinanceDataPlatform/0.1 (contact@example.com)"

    @classmethod
    def from_env(cls) -> "PlatformConfig":
        """Load configuration from environment variables.

        Returns:
            PlatformConfig with values from environment.

        Raises:
            ValueError: If required configuration is missing.
        """
        # Database config
        db_host = os.getenv("POSTGRES_HOST", "localhost")
        db_port = int(os.getenv("POSTGRES_PORT", "5432"))
        db_name = os.getenv("POSTGRES_DB", "finance_platform")
        db_user = os.getenv("POSTGRES_USER", "platform")
        db_password = os.getenv("POSTGRES_PASSWORD", "")

        if not db_password:
            raise ValueError("POSTGRES_PASSWORD environment variable is required")

        # MinIO config
        minio_endpoint = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
        minio_access_key = os.getenv("MINIO_ACCESS_KEY", "")
        minio_secret_key = os.getenv("MINIO_SECRET_KEY", "")

        if not minio_access_key or not minio_secret_key:
            raise ValueError("MINIO_ACCESS_KEY and MINIO_SECRET_KEY are required")

        # API keys (optional for some connectors)
        fred_api_key = os.getenv("FRED_API_KEY")
        coingecko_api_key = os.getenv("COINGECKO_API_KEY")
        sec_edgar_user_agent = os.getenv(
            "SEC_EDGAR_USER_AGENT",
            "FinanceDataPlatform/0.1 (contact@example.com)",
        )

        log_level = os.getenv("LOG_LEVEL", "INFO").upper()

        return cls(
            database=DatabaseConfig(
                host=db_host,
                port=db_port,
                database=db_name,
                user=db_user,
                password=db_password,
            ),
            minio=MinIOConfig(
                endpoint=minio_endpoint,
                access_key=minio_access_key,
                secret_key=minio_secret_key,
            ),
            log_level=log_level,
            fred_api_key=fred_api_key,
            coingecko_api_key=coingecko_api_key,
            sec_edgar_user_agent=sec_edgar_user_agent,
        )
