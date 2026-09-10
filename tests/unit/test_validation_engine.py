"""Tests for src/validation/engine.py (US-04-001..009, event wiring)."""

from __future__ import annotations

from typing import Any

from src.events.bus import EventBus
from src.events.models import EventType
from src.validation.contract import DataContract
from src.validation.engine import ValidationEngine
from src.validation.models import RuleStatus


def _contract(**overrides: Any) -> DataContract:
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


class TestValidate:
    def test_clean_batch_is_validated_and_published(self) -> None:
        bus = EventBus()
        engine = ValidationEngine(event_bus=bus)

        report = engine.validate(
            dataset_id="fred_cpiaucsl",
            records=[_record()],
            contract=_contract(),
            payload_reference="raw/fred/foo.json",
        )

        assert not report.has_failures
        published = bus.history(EventType.RAW_DATA_VALIDATED)
        assert len(published) == 1
        assert published[0].dataset_id == "fred_cpiaucsl"
        assert published[0].producer == "validation.engine"
        assert published[0].payload_reference == "raw/fred/foo.json"
        assert bus.history(EventType.RAW_DATA_QUARANTINED) == []

    def test_bad_batch_is_quarantined_and_published(self) -> None:
        bus = EventBus()
        engine = ValidationEngine(event_bus=bus)

        record = _record()
        del record["series_id"]  # missing field -> FR-QUAL-001 failure

        report = engine.validate(
            dataset_id="fred_cpiaucsl",
            records=[record],
            contract=_contract(),
        )

        assert report.has_failures
        quarantined = bus.history(EventType.RAW_DATA_QUARANTINED)
        assert len(quarantined) == 1
        assert "FR-QUAL-001" in quarantined[0].metadata["failed_rules"]
        assert bus.history(EventType.RAW_DATA_VALIDATED) == []

    def test_flagged_outlier_does_not_quarantine(self) -> None:
        bus = EventBus()
        engine = ValidationEngine(event_bus=bus)

        records = [
            _record(observed_at="2024-01-01T00:00:00+00:00", value="300.0"),
            _record(observed_at="2024-02-01T00:00:00+00:00", value="4000.0"),
        ]

        report = engine.validate(
            dataset_id="fred_cpiaucsl",
            records=records,
            contract=_contract(),
        )

        assert not report.has_failures
        assert report.has_flags
        validated = bus.history(EventType.RAW_DATA_VALIDATED)
        assert len(validated) == 1
        assert "FR-QUAL-008" in validated[0].metadata["flagged_rules"]
        assert bus.history(EventType.RAW_DATA_QUARANTINED) == []

    def test_defaults_to_private_event_bus(self) -> None:
        engine = ValidationEngine()
        report = engine.validate(
            dataset_id="fred_cpiaucsl", records=[_record()], contract=_contract()
        )
        assert not report.has_failures
        assert len(engine.event_bus.history(EventType.RAW_DATA_VALIDATED)) == 1

    def test_report_includes_all_nine_rules(self) -> None:
        engine = ValidationEngine()
        report = engine.validate(
            dataset_id="fred_cpiaucsl", records=[_record()], contract=_contract()
        )
        rule_ids = {result.rule_id for result in report.results}
        assert rule_ids == {
            "FR-QUAL-001",
            "FR-QUAL-002",
            "FR-QUAL-003",
            "FR-QUAL-004",
            "FR-QUAL-005",
            "FR-QUAL-006",
            "FR-QUAL-007",
            "FR-QUAL-008",
            "FR-QUAL-009",
        }
        skipped = report.by_status(RuleStatus.SKIPPED)
        skipped_ids = {result.rule_id for result in skipped}
        # FR-QUAL-002/004/006/007 need external context this call didn't supply
        # (calendar, max_lag, dimension keys, source counts) — SKIPPED, not a
        # false pass. FR-QUAL-008 also skips: it needs >= 2 records to compare
        # an interval move against.
        assert skipped_ids == {
            "FR-QUAL-002",
            "FR-QUAL-004",
            "FR-QUAL-006",
            "FR-QUAL-007",
            "FR-QUAL-008",
        }
