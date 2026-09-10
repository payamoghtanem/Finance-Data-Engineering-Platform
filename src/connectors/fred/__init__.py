"""FRED connector package.

Implements FR-ING-001: FRED (Federal Reserve Economic Data) ingestion.
"""

from src.connectors.fred.connector import (
    FREDConnector,
    FREDConnectorError,
    FREDPermanentError,
    FREDTransientError,
)

__all__ = [
    "FREDConnector",
    "FREDConnectorError",
    "FREDPermanentError",
    "FREDTransientError",
]
