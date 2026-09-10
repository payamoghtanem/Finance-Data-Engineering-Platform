"""Tests for src/validation/contract.py (US-04-001)."""

from __future__ import annotations

from pathlib import Path

import pytest
from src.validation.contract import ContractError, load_contract

FRED_CONTRACT_PATH = Path("src/connectors/fred/contract.yaml")


class TestLoadContract:
    def test_loads_real_fred_contract(self) -> None:
        contract = load_contract(FRED_CONTRACT_PATH)

        assert contract.dataset == "fred_cpi_daily"
        assert contract.owner == "connectors.fred"
        assert contract.source == "fred"
        assert contract.version == "1.0.0"
        assert contract.primary_key == ("source_id", "observed_at")
        assert "08:30" in contract.freshness_slo
        assert contract.schema == {
            "observed_at": "timestamp_utc",
            "value": "decimal(20,8)",
            "source_id": "string",
            "series_id": "string",
            "realtime_start": "date",
            "realtime_end": "date",
        }
        assert "value_positive" in contract.quality_rules
        assert contract.metadata["units"] == "Index 1982-1984=100"
        assert contract.metadata["seasonal_adjustment"] == "Seasonally Adjusted"
        assert contract.change_policy["breaking_change_requires"] == (
            "major_version_and_consumer_approval"
        )

    def test_missing_file_raises_contract_error(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_contract(tmp_path / "does_not_exist.yaml")

    def test_non_mapping_yaml_raises_contract_error(self, tmp_path: Path) -> None:
        bad_file = tmp_path / "contract.yaml"
        bad_file.write_text("- just\n- a\n- list\n", encoding="utf-8")

        with pytest.raises(ContractError, match="must be a YAML mapping"):
            load_contract(bad_file)

    def test_missing_required_field_raises_contract_error(self, tmp_path: Path) -> None:
        bad_file = tmp_path / "contract.yaml"
        bad_file.write_text("dataset: foo\nowner: bar\n", encoding="utf-8")

        with pytest.raises(ContractError, match="missing required contract field"):
            load_contract(bad_file)

    def test_optional_fields_default_sensibly(self, tmp_path: Path) -> None:
        minimal = tmp_path / "contract.yaml"
        minimal.write_text(
            "dataset: d\nowner: o\nsource: s\nversion: 1\n"
            "primary_key: [id]\nschema: {id: string}\n",
            encoding="utf-8",
        )

        contract = load_contract(minimal)

        assert contract.freshness_slo == ""
        assert contract.quality_rules == ()
        assert contract.metadata == {}
        assert contract.change_policy == {}
