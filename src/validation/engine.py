"""Validation engine: runs every FR-QUAL-xxx rule and emits the outcome.

Per docs/technical/event-schema.md, this module is the documented producer of
`raw_data.validated` / `raw_data.quarantined`. It is not, as of EPIC-04, wired
as a consumer of `raw_data.received` — doing that for real requires a
source-specific parser turning a connector's raw bytes into the contract's
record shape (e.g. FRED's `{"date": ..., "value": ...}` observations into
`observed_at`/`value`/`source_id`/...), which does not exist yet for any
connector. `ValidationEngine.validate()` is the piece that exists now: given
records already in a contract's shape, it runs all nine rules and publishes
the result. Wiring a connector's output into it is follow-on work, tracked in
STATUS.md rather than faked here.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from collections.abc import Set as AbstractSet
from datetime import datetime, timedelta
from typing import Any

from src.events.bus import EventBus
from src.events.models import EventEnvelope, EventType
from src.validation.contract import DataContract
from src.validation.models import RuleStatus, ValidationReport
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


class ValidationEngine:
    """Runs the FR-QUAL-001..009 rules against one batch and reports the outcome.

    Args:
        event_bus: Where `raw_data.validated`/`raw_data.quarantined` are
            published (this module's documented role per
            docs/technical/event-schema.md §2). Defaults to a fresh, private
            `EventBus` — pass a shared one to let another component subscribe.
    """

    def __init__(self, event_bus: EventBus | None = None) -> None:
        self.event_bus = event_bus or EventBus()

    def validate(
        self,
        *,
        dataset_id: str,
        records: Sequence[Mapping[str, Any]],
        contract: DataContract,
        correlation_id: str | None = None,
        payload_reference: str | None = None,
        expected_keys: Any = None,
        now: datetime | None = None,
        max_lag: timedelta | None = None,
        known_keys: Mapping[str, AbstractSet[Any]] | None = None,
        source_count: int | None = None,
        local_checksum: str | None = None,
        source_checksum: str | None = None,
    ) -> ValidationReport:
        """Run every rule and publish `raw_data.validated` or `raw_data.quarantined`.

        A batch is quarantined only on a genuine FAILED rule. A FLAGGED
        outcome (FR-QUAL-008's outlier check) does not, by itself, quarantine
        the batch — it is carried in the validated event's metadata for
        downstream review instead.
        """
        results = (
            check_schema(records, contract),
            check_completeness(records, contract, expected_keys=expected_keys),
            check_uniqueness(records, contract),
            check_freshness(records, contract, now=now, max_lag=max_lag),
            check_range_and_consistency(records, contract),
            check_referential_integrity(records, contract, known_keys=known_keys),
            check_reconciliation(
                len(records),
                source_count=source_count,
                local_checksum=local_checksum,
                source_checksum=source_checksum,
            ),
            check_outliers(records, contract),
            check_semantic_metadata(contract),
        )
        report = ValidationReport(dataset_id=dataset_id, record_count=len(records), results=results)

        if report.has_failures:
            self.event_bus.publish(
                EventEnvelope(
                    event_type=EventType.RAW_DATA_QUARANTINED,
                    producer="validation.engine",
                    dataset_id=dataset_id,
                    correlation_id=correlation_id,
                    payload_reference=payload_reference,
                    metadata={
                        "failed_rules": [
                            result.rule_id for result in report.by_status(RuleStatus.FAILED)
                        ]
                    },
                )
            )
        else:
            self.event_bus.publish(
                EventEnvelope(
                    event_type=EventType.RAW_DATA_VALIDATED,
                    producer="validation.engine",
                    dataset_id=dataset_id,
                    correlation_id=correlation_id,
                    payload_reference=payload_reference,
                    metadata={
                        "flagged_rules": [
                            result.rule_id for result in report.by_status(RuleStatus.FLAGGED)
                        ]
                    },
                )
            )
        return report
