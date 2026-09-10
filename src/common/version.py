"""Code version resolution for provenance fields (FR-ING-001, NFR-AUDIT-001).

Every `ingestion_run` row records the connector code version that produced
it. Reading it from the installed package metadata means it can never drift
out of sync with `pyproject.toml` the way a hand-maintained constant would.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

_PACKAGE_NAME = "finance-data-platform"
_FALLBACK_VERSION = "0.0.0-dev"


def get_code_version() -> str:
    """Return the installed package version, or a fallback if not installed.

    The fallback covers running `src/` directly off `PYTHONPATH` without an
    editable install — a valid setup that should still work, not require
    `pip install -e .` first.
    """
    try:
        return version(_PACKAGE_NAME)
    except PackageNotFoundError:
        return _FALLBACK_VERSION
