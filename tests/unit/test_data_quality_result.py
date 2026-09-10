"""Unit tests for DataQualityResultRecorder (FR-OPS-001, EPIC-08)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from src.common.data_quality_result import DataQualityResultRecorder


@pytest.fixture
def recorder() -> DataQualityResultRecorder:
    return DataQualityResultRecorder(db_path=":memory:")


class TestRecord:
    def test_record_returns_matching_result(self, recorder: DataQualityResultRecorder) -> None:
        evaluated_at = datetime(2026, 9, 10, 12, 0, 0, tzinfo=UTC)
        result = recorder.record(
            test_id="value_positive",
            table_name="fact_economic_observation",
            run_id="run-1",
            status="pass",
            failed_rows=0,
            evaluated_at=evaluated_at,
        )
        assert result.test_id == "value_positive"
        assert result.table_name == "fact_economic_observation"
        assert result.status == "pass"
        assert result.failed_rows == 0

    def test_get_round_trips_a_recorded_result(self, recorder: DataQualityResultRecorder) -> None:
        evaluated_at = datetime(2026, 9, 10, 12, 0, 0, tzinfo=UTC)
        written = recorder.record(
            test_id="value_positive",
            table_name="fact_economic_observation",
            run_id="run-1",
            status="fail",
            failed_rows=3,
            evaluated_at=evaluated_at,
        )
        fetched = recorder.get("value_positive", "fact_economic_observation")
        assert fetched == written

    def test_evaluated_at_round_trips_as_utc(self, recorder: DataQualityResultRecorder) -> None:
        evaluated_at = datetime(2026, 9, 10, 12, 0, 0, tzinfo=UTC)
        recorder.record(
            test_id="value_positive",
            table_name="fact_economic_observation",
            run_id="run-1",
            status="pass",
            failed_rows=0,
            evaluated_at=evaluated_at,
        )
        fetched = recorder.get("value_positive", "fact_economic_observation")
        assert fetched is not None
        assert fetched.evaluated_at.tzinfo is not None
        assert fetched.evaluated_at == evaluated_at

    def test_get_missing_result_returns_none(self, recorder: DataQualityResultRecorder) -> None:
        assert recorder.get("no_such_test", "no_such_table") is None


class TestUpsertSemantics:
    """The PK is (test_id, table_name) -- this table holds the *latest*
    evaluation of a rule against a table, not full history."""

    def test_re_recording_the_same_rule_overwrites_the_prior_result(
        self, recorder: DataQualityResultRecorder
    ) -> None:
        t0 = datetime(2026, 9, 10, 12, 0, 0, tzinfo=UTC)
        recorder.record(
            test_id="value_positive",
            table_name="fact_economic_observation",
            run_id="run-1",
            status="pass",
            failed_rows=0,
            evaluated_at=t0,
        )
        recorder.record(
            test_id="value_positive",
            table_name="fact_economic_observation",
            run_id="run-2",
            status="fail",
            failed_rows=5,
            evaluated_at=t0.replace(hour=13),
        )
        result = recorder.get("value_positive", "fact_economic_observation")
        assert result is not None
        assert result.run_id == "run-2"
        assert result.status == "fail"
        assert result.failed_rows == 5

    def test_list_for_table_returns_one_row_per_test_id(
        self, recorder: DataQualityResultRecorder
    ) -> None:
        t0 = datetime(2026, 9, 10, 12, 0, 0, tzinfo=UTC)
        for test_id in ("value_positive", "primary_key_unique"):
            recorder.record(
                test_id=test_id,
                table_name="fact_economic_observation",
                run_id="run-1",
                status="pass",
                failed_rows=0,
                evaluated_at=t0,
            )
        results = recorder.list_for_table("fact_economic_observation")
        assert [r.test_id for r in results] == ["primary_key_unique", "value_positive"]

    def test_list_for_table_ignores_other_tables(self, recorder: DataQualityResultRecorder) -> None:
        t0 = datetime(2026, 9, 10, 12, 0, 0, tzinfo=UTC)
        recorder.record(
            test_id="value_positive",
            table_name="fact_economic_observation",
            run_id="run-1",
            status="pass",
            failed_rows=0,
            evaluated_at=t0,
        )
        recorder.record(
            test_id="value_positive",
            table_name="fact_economic_kpi",
            run_id="run-1",
            status="pass",
            failed_rows=0,
            evaluated_at=t0,
        )
        assert len(recorder.list_for_table("fact_economic_observation")) == 1
