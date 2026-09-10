"""Data contract loading.

Each connector's `contract.yaml` (docs/architecture/solution-design-document.md
§4) is the single source of truth for what a dataset's records must look
like. This module is the only place that turns that YAML file into the shape
`validation/rules.py` and `validation/engine.py` operate on — loading it at
runtime instead of hardcoding a second copy in Python keeps the two from
silently drifting apart.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


class ContractError(Exception):
    """Raised when a contract.yaml is missing, malformed, or missing required fields."""


_REQUIRED_FIELDS = ("dataset", "owner", "source", "version", "primary_key", "schema")


@dataclass(frozen=True)
class DataContract:
    """The subset of a connector's contract.yaml the validation engine needs."""

    dataset: str
    owner: str
    source: str
    version: str
    primary_key: tuple[str, ...]
    freshness_slo: str
    schema: dict[str, str]
    quality_rules: tuple[str, ...]
    metadata: dict[str, Any] = field(default_factory=dict)
    change_policy: dict[str, Any] = field(default_factory=dict)


def load_contract(path: str | Path) -> DataContract:
    """Load and validate a `contract.yaml` file into a `DataContract`."""
    text = Path(path).read_text(encoding="utf-8")
    raw = yaml.safe_load(text)
    if not isinstance(raw, dict):
        raise ContractError(f"{path}: contract must be a YAML mapping")

    missing = [name for name in _REQUIRED_FIELDS if name not in raw]
    if missing:
        raise ContractError(f"{path}: missing required contract field(s): {missing}")

    return DataContract(
        dataset=raw["dataset"],
        owner=raw["owner"],
        source=raw["source"],
        version=str(raw["version"]),
        primary_key=tuple(raw["primary_key"]),
        freshness_slo=str(raw.get("freshness_slo", "")),
        schema=dict(raw["schema"]),
        quality_rules=tuple(raw.get("quality_rules", [])),
        metadata=dict(raw.get("metadata", {})),
        change_policy=dict(raw.get("change_policy", {})),
    )
