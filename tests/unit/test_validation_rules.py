"""Tests for src/validation/rules.py — FR-QUAL-001..009 (EPIC-04)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from src.validation.contract import DataContract
from src.validation.models import RuleStatus
from src.validation.rules import (
    check_completeness,
    check_freshness,
    check_outliers,
    check_range_and_consistency,
    check_reconciliation,
    check_referential_integrity,
    check_schema,
    check_semantic_metadata,
    check_uniqueness,
)


def _fred_like_contract(**overrides: Any) -> DataContract:
    defaults: dict[str, Any] = {
        "dataset": "fred_cpi_daily",
        "owner": "connectors.fred",
        "source": "fred",
        "version": "1.0.0",
        "primary_key": ("source_id", "observed_at"),
        "freshness_slo": "available by 08:30 America/New_York on release days",
        "schema": {
            "observed_at": "timestamp_utc",
            "value": "decimal(20,8)",
            "source_id": "string",
            "series_id": "string",
            "realtime_start": "date",
            "realtime_end": "date",
        },
        "quality_rules": ("value_not_null", "value_positive", "primary_key_unique", "schema_valid"),
        "metadata": {"units": "Index 1982-1984=100", "seasonal_adjustment": "Seasonally Adjusted"},
        "change_policy": {},
    }
    defaults.update(overrides)
    return DataContract(**defaults)


def _record(**overrides: Any) -> dict[str, Any]:
    base = {
        "observed_at": "2024-01-01T00:00:00+00:00",
        "value": "300.5",
        "source_id": "fred",
        "series_id": "CPIAUCSL",
        "realtime_start": "2024-01-15",
        "realtime_end": "2024-01-15",
    }
    base.update(overrides)
    return base


class TestCheckSchema:
    def test_passes_when_all_records_match(self) -> None:
        contract = _fred_like_contract()
        result = check_schema(
            [_record(), _record(observed_at="2024-02-01T00:00:00+00:00")], contract
        )
        assert result.status is RuleStatus.PASSED
        assert result.rule_id == "FR-QUAL-001"

    def test_fails_on_missing_field(self) -> None:
        contract = _fred_like_contract()
        record = _record()
        del record["series_id"]
        result = check_schema([record], contract)
        assert result.status is RuleStatus.FAILED
        assert result.details["records"][0]["missing"] == ["series_id"]

    def test_fails_on_extra_field(self) -> None:
        contract = _fred_like_contract()
        result = check_schema([_record(unexpected_field="oops")], contract)
        assert result.status is RuleStatus.FAILED
        assert result.details["records"][0]["extra"] == ["unexpected_field"]

    def test_fails_on_type_mismatch(self) -> None:
        contract = _fred_like_contract()
        result = check_schema([_record(value="not-a-number")], contract)
        assert result.status is RuleStatus.FAILED
        assert result.details["records"][0]["type_errors"] == ["value"]

    def test_accepts_native_python_types_too(self) -> None:
        contract = _fred_like_contract()
        record = _record(
            observed_at=datetime(2024, 1, 1, tzinfo=UTC),
            value=300.5,
        )
        result = check_schema([record], contract)
        assert result.status is RuleStatus.PASSED


class TestCheckCompleteness:
    def test_skipped_without_expected_keys(self) -> None:
        result = check_completeness([_record()], _fred_like_contract())
        assert result.status is RuleStatus.SKIPPED

    def test_passes_when_nothing_missing(self) -> None:
        records = [_record(observed_at="2024-01-01T00:00:00+00:00")]
        result = check_completeness(
            records, _fred_like_contract(), expected_keys=["2024-01-01T00:00:00+00:00"]
        )
        assert result.status is RuleStatus.PASSED

    def test_fails_when_expected_key_missing(self) -> None:
        records = [_record(observed_at="2024-01-01T00:00:00+00:00")]
        result = check_completeness(
            records,
            _fred_like_contract(),
            expected_keys=["2024-01-01T00:00:00+00:00", "2024-02-01T00:00:00+00:00"],
        )
        assert result.status is RuleStatus.FAILED
        assert "2024-02-01T00:00:00+00:00" in result.details["missing_keys"]


class TestCheckUniqueness:
    def test_passes_when_keys_unique(self) -> None:
        records = [
            _record(observed_at="2024-01-01T00:00:00+00:00"),
            _record(observed_at="2024-02-01T00:00:00+00:00"),
        ]
        result = check_uniqueness(records, _fred_like_contract())
        assert result.status is RuleStatus.PASSED

    def test_fails_on_duplicate_primary_key(self) -> None:
        records = [_record(), _record()]
        result = check_uniqueness(records, _fred_like_contract())
        assert result.status is RuleStatus.FAILED
        assert len(result.details["duplicate_keys"]) == 1


class TestCheckFreshness:
    def test_skipped_without_max_lag(self) -> None:
        result = check_freshness([_record()], _fred_like_contract())
        assert result.status is RuleStatus.SKIPPED

    def test_fails_with_no_records(self) -> None:
        result = check_freshness([], _fred_like_contract(), max_lag=timedelta(days=1))
        assert result.status is RuleStatus.FAILED

    def test_passes_within_max_lag(self) -> None:
        now = datetime(2024, 1, 2, tzinfo=UTC)
        record = _record(observed_at="2024-01-01T00:00:00+00:00")
        result = check_freshness(
            [record], _fred_like_contract(), now=now, max_lag=timedelta(days=2)
        )
        assert result.status is RuleStatus.PASSED

    def test_fails_beyond_max_lag(self) -> None:
        now = datetime(2024, 2, 1, tzinfo=UTC)
        record = _record(observed_at="2024-01-01T00:00:00+00:00")
        result = check_freshness(
            [record], _fred_like_contract(), now=now, max_lag=timedelta(days=2)
        )
        assert result.status is RuleStatus.FAILED


class TestCheckRangeAndConsistency:
    def test_skipped_when_no_applicable_rules(self) -> None:
        contract = _fred_like_contract(quality_rules=())
        result = check_range_and_consistency([_record()], contract)
        assert result.status is RuleStatus.SKIPPED

    def test_passes_for_positive_values(self) -> None:
        result = check_range_and_consistency([_record(value="300.5")], _fred_like_contract())
        assert result.status is RuleStatus.PASSED

    def test_fails_for_non_positive_value(self) -> None:
        result = check_range_and_consistency([_record(value="-1.0")], _fred_like_contract())
        assert result.status is RuleStatus.FAILED
        assert result.details["violations"][0]["rule"] == "value_positive"

    def test_ohlcv_consistency_checked_when_schema_declares_it(self) -> None:
        contract = _fred_like_contract(
            schema={
                "open": "decimal(20,8)",
                "high": "decimal(20,8)",
                "low": "decimal(20,8)",
                "close": "decimal(20,8)",
            },
            quality_rules=(),
        )
        bad_record = {"open": "10", "high": "5", "low": "1", "close": "3"}  # open > high
        result = check_range_and_consistency([bad_record], contract)
        assert result.status is RuleStatus.FAILED
        assert result.details["violations"][0]["rule"] == "ohlcv_consistency"

    def test_ohlcv_consistency_passes_for_valid_bar(self) -> None:
        contract = _fred_like_contract(
            schema={
                "open": "decimal(20,8)",
                "high": "decimal(20,8)",
                "low": "decimal(20,8)",
                "close": "decimal(20,8)",
            },
            quality_rules=(),
        )
        good_record = {"open": "3", "high": "5", "low": "1", "close": "4"}
        result = check_range_and_consistency([good_record], contract)
        assert result.status is RuleStatus.PASSED


class TestCheckReferentialIntegrity:
    def test_skipped_without_known_keys(self) -> None:
        result = check_referential_integrity([_record()], _fred_like_contract())
        assert result.status is RuleStatus.SKIPPED

    def test_passes_when_fk_resolves(self) -> None:
        result = check_referential_integrity(
            [_record(source_id="fred")],
            _fred_like_contract(),
            known_keys={"source_id": {"fred", "worldbank"}},
        )
        assert result.status is RuleStatus.PASSED

    def test_fails_when_fk_does_not_resolve(self) -> None:
        result = check_referential_integrity(
            [_record(source_id="unknown_source")],
            _fred_like_contract(),
            known_keys={"source_id": {"fred", "worldbank"}},
        )
        assert result.status is RuleStatus.FAILED
        assert result.details["violations"][0]["value"] == "unknown_source"


class TestCheckReconciliation:
    def test_skipped_without_source_data(self) -> None:
        result = check_reconciliation(10)
        assert result.status is RuleStatus.SKIPPED

    def test_passes_when_counts_match(self) -> None:
        result = check_reconciliation(10, source_count=10)
        assert result.status is RuleStatus.PASSED

    def test_fails_when_counts_differ(self) -> None:
        result = check_reconciliation(10, source_count=12)
        assert result.status is RuleStatus.FAILED

    def test_fails_when_checksums_differ(self) -> None:
        result = check_reconciliation(
            10, source_count=10, local_checksum="abc", source_checksum="def"
        )
        assert result.status is RuleStatus.FAILED


class TestCheckOutliers:
    def test_skipped_with_fewer_than_two_records(self) -> None:
        result = check_outliers([_record()], _fred_like_contract())
        assert result.status is RuleStatus.SKIPPED

    def test_passes_for_normal_moves(self) -> None:
        records = [
            _record(observed_at="2024-01-01T00:00:00+00:00", value="300.0"),
            _record(observed_at="2024-02-01T00:00:00+00:00", value="301.0"),
        ]
        result = check_outliers(records, _fred_like_contract())
        assert result.status is RuleStatus.PASSED

    def test_flags_extreme_move_without_failing(self) -> None:
        records = [
            _record(observed_at="2024-01-01T00:00:00+00:00", value="300.0"),
            _record(observed_at="2024-02-01T00:00:00+00:00", value="4000.0"),
        ]
        result = check_outliers(records, _fred_like_contract())
        assert result.status is RuleStatus.FLAGGED
        assert len(result.details["flagged"]) == 1


class TestCheckSemanticMetadata:
    def test_passes_when_required_keys_present(self) -> None:
        result = check_semantic_metadata(_fred_like_contract())
        assert result.status is RuleStatus.PASSED

    def test_fails_when_units_missing(self) -> None:
        contract = _fred_like_contract(metadata={"seasonal_adjustment": "Seasonally Adjusted"})
        result = check_semantic_metadata(contract)
        assert result.status is RuleStatus.FAILED
        assert "units" in result.details["missing_keys"]

    def test_fails_when_explicit_index_base_present_but_empty(self) -> None:
        contract = _fred_like_contract(
            metadata={
                "units": "Index 1982-1984=100",
                "seasonal_adjustment": "Seasonally Adjusted",
                "index_base": "",
            }
        )
        result = check_semantic_metadata(contract)
        assert result.status is RuleStatus.FAILED
        assert "index_base" in result.details["missing_keys"]
