"""The nine data-quality rules from docs/requirements/FRD.md §2 (FR-QUAL-001..009).

Every function here is pure: given a batch of records (already shaped to the
contract's field names — this module does no source-specific parsing) and a
`DataContract`, it returns one `RuleResult`, never raises for a data problem,
and never touches the network or a database.

Several rules (FR-QUAL-002, 004, 006, 007) need context this engine has no
independent way to obtain yet — an expected-record calendar, a freshness
budget, a dimension table's known keys, a source's own count/checksum. Rather
than fake a pass, each one returns RuleStatus.SKIPPED when that context isn't
supplied by the caller. Wiring real context into these (a scheduler calling
with today's expected calendar, a reconciliation job calling with the
source's count) is EPIC-07's job, not this module's.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from collections.abc import Set as AbstractSet
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

from src.validation.contract import DataContract
from src.validation.models import RuleResult, RuleStatus

_OHLC_FIELDS = ("open", "high", "low", "close")
_DEFAULT_SEMANTIC_KEYS = ("units", "seasonal_adjustment")


def _matches_type(type_spec: str, value: Any) -> bool:
    """Check one value against one contract schema type string.

    Values arriving from a source API are frequently strings even for
    numeric/date fields (that's how FRED's own JSON reads); a string that
    parses cleanly into the target type counts as matching, so this rule
    catches genuine structural problems rather than a source's usual string
    encoding of numbers and dates.
    """
    if value is None:
        return False
    spec = type_spec.strip().lower()
    if spec == "string":
        return isinstance(value, str)
    if spec.startswith("decimal"):
        if isinstance(value, bool):
            return False
        if isinstance(value, int | float | Decimal):
            return True
        if isinstance(value, str):
            try:
                Decimal(value)
            except InvalidOperation:
                return False
            return True
        return False
    if spec == "date":
        if isinstance(value, datetime):
            return False
        if isinstance(value, date):
            return True
        if isinstance(value, str):
            try:
                date.fromisoformat(value)
            except ValueError:
                return False
            return True
        return False
    if spec == "timestamp_utc":
        if isinstance(value, datetime):
            return True
        if isinstance(value, str):
            try:
                datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return False
            return True
        return False
    # An unrecognized type string in a contract is a contract-authoring
    # problem, not a data problem this rule can detect — don't block
    # ingestion on an engine gap.
    return True


def _parse_timestamp(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    return None


def check_schema(records: Sequence[Mapping[str, Any]], contract: DataContract) -> RuleResult:
    """FR-QUAL-001: reject (quarantine), never silently coerce, a structural mismatch."""
    expected_fields = set(contract.schema)
    bad: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        actual_fields = set(record)
        missing = expected_fields - actual_fields
        extra = actual_fields - expected_fields
        type_errors = sorted(
            field_name
            for field_name in expected_fields & actual_fields
            if not _matches_type(contract.schema[field_name], record[field_name])
        )
        if missing or extra or type_errors:
            bad.append(
                {
                    "index": index,
                    "missing": sorted(missing),
                    "extra": sorted(extra),
                    "type_errors": type_errors,
                }
            )
    if bad:
        return RuleResult(
            rule_id="FR-QUAL-001",
            status=RuleStatus.FAILED,
            message=f"{len(bad)} of {len(records)} record(s) do not match the contract schema",
            details={"records": bad},
        )
    return RuleResult(
        rule_id="FR-QUAL-001",
        status=RuleStatus.PASSED,
        message=f"All {len(records)} record(s) match the contract schema",
    )


def check_completeness(
    records: Sequence[Mapping[str, Any]],
    contract: DataContract,
    *,
    expected_keys: Iterable[Any] | None = None,
    key_field: str = "observed_at",
) -> RuleResult:
    """FR-QUAL-002: a missing expected record must be flagged, not presented as a silent gap."""
    if expected_keys is None:
        return RuleResult(
            rule_id="FR-QUAL-002",
            status=RuleStatus.SKIPPED,
            message="No expected-keys calendar supplied; completeness not checked",
        )
    expected = set(expected_keys)
    actual = {record.get(key_field) for record in records}
    missing = expected - actual
    if missing:
        return RuleResult(
            rule_id="FR-QUAL-002",
            status=RuleStatus.FAILED,
            message=f"{len(missing)} expected record(s) missing",
            details={"missing_keys": sorted(str(key) for key in missing)},
        )
    return RuleResult(
        rule_id="FR-QUAL-002",
        status=RuleStatus.PASSED,
        message="No missing records against the supplied calendar",
    )


def check_uniqueness(records: Sequence[Mapping[str, Any]], contract: DataContract) -> RuleResult:
    """FR-QUAL-003: enforce the contract's declared primary key — never silently double-count."""
    counts: Counter[tuple[Any, ...]] = Counter(
        tuple(record.get(field_name) for field_name in contract.primary_key) for record in records
    )
    duplicates = [key for key, count in counts.items() if count > 1]
    if duplicates:
        return RuleResult(
            rule_id="FR-QUAL-003",
            status=RuleStatus.FAILED,
            message=f"{len(duplicates)} duplicate primary key value(s) found",
            details={"duplicate_keys": [list(key) for key in duplicates]},
        )
    return RuleResult(
        rule_id="FR-QUAL-003",
        status=RuleStatus.PASSED,
        message="Primary key is unique across all records",
    )


def check_freshness(
    records: Sequence[Mapping[str, Any]],
    contract: DataContract,
    *,
    now: datetime | None = None,
    max_lag: timedelta | None = None,
    timestamp_field: str = "observed_at",
) -> RuleResult:
    """FR-QUAL-004: raise an alert when the freshness SLO is breached.

    `contract.freshness_slo` is free text (e.g. "available by 08:30
    America/New_York on release days") — this rule does not parse natural
    language into a schedule. Pass `max_lag` (that SLO translated to a
    maximum age) to actually run the check.
    """
    if max_lag is None:
        return RuleResult(
            rule_id="FR-QUAL-004",
            status=RuleStatus.SKIPPED,
            message="No max_lag supplied for this dataset's freshness_slo; freshness not checked",
            details={"freshness_slo": contract.freshness_slo},
        )
    if not records:
        return RuleResult(
            rule_id="FR-QUAL-004",
            status=RuleStatus.FAILED,
            message="No records to evaluate freshness against",
        )
    now = now or datetime.now(UTC)
    timestamps = [
        ts for ts in (_parse_timestamp(record.get(timestamp_field)) for record in records) if ts
    ]
    if not timestamps:
        return RuleResult(
            rule_id="FR-QUAL-004",
            status=RuleStatus.FAILED,
            message=f"No parseable {timestamp_field!r} values to evaluate freshness against",
        )
    latest = max(timestamps)
    lag = now - latest
    if lag > max_lag:
        return RuleResult(
            rule_id="FR-QUAL-004",
            status=RuleStatus.FAILED,
            message=f"Latest record is {lag} old, exceeding max_lag of {max_lag}",
            details={"latest": latest.isoformat(), "lag_seconds": lag.total_seconds()},
        )
    return RuleResult(
        rule_id="FR-QUAL-004",
        status=RuleStatus.PASSED,
        message=f"Latest record is {lag} old, within max_lag of {max_lag}",
    )


def check_range_and_consistency(
    records: Sequence[Mapping[str, Any]],
    contract: DataContract,
    *,
    value_field: str = "value",
) -> RuleResult:
    """FR-QUAL-005: reject impossible values and cross-field inconsistencies.

    `value_positive` only runs when the contract declares it. OHLCV
    consistency only runs when the schema declares open/high/low/close — most
    datasets (e.g. an economic indicator like CPI) don't have those fields,
    which is "not applicable", not a failure.
    """
    checks_run: list[str] = []
    violations: list[dict[str, Any]] = []

    if "value_positive" in contract.quality_rules and value_field in contract.schema:
        checks_run.append("value_positive")
        for index, record in enumerate(records):
            raw_value = record.get(value_field)
            try:
                numeric = float(raw_value)  # type: ignore[arg-type]
            except (TypeError, ValueError):
                continue  # a structural mismatch is FR-QUAL-001's job, not this rule's
            if numeric <= 0:
                violations.append({"index": index, "rule": "value_positive", "value": raw_value})

    if all(field_name in contract.schema for field_name in _OHLC_FIELDS):
        checks_run.append("ohlcv_consistency")
        for index, record in enumerate(records):
            try:
                open_, high, low, close = (float(record[f]) for f in _OHLC_FIELDS)
            except (TypeError, ValueError, KeyError):
                continue
            if not (low <= open_ <= high and low <= close <= high):
                violations.append({"index": index, "rule": "ohlcv_consistency"})

    if not checks_run:
        return RuleResult(
            rule_id="FR-QUAL-005",
            status=RuleStatus.SKIPPED,
            message="No range/consistency rules apply to this contract's schema",
        )
    if violations:
        return RuleResult(
            rule_id="FR-QUAL-005",
            status=RuleStatus.FAILED,
            message=f"{len(violations)} range/consistency violation(s) found",
            details={"violations": violations},
        )
    return RuleResult(
        rule_id="FR-QUAL-005",
        status=RuleStatus.PASSED,
        message=f"All records pass range/consistency checks ({', '.join(checks_run)})",
    )


def check_referential_integrity(
    records: Sequence[Mapping[str, Any]],
    contract: DataContract,
    *,
    known_keys: Mapping[str, AbstractSet[Any]] | None = None,
) -> RuleResult:
    """FR-QUAL-006: a fact record's foreign key must resolve to an existing dimension row.

    No dimension tables exist in this platform yet (EPIC-05) — pass
    `known_keys` (field name -> the set of valid values from that dimension)
    to actually run the check.
    """
    if not known_keys:
        return RuleResult(
            rule_id="FR-QUAL-006",
            status=RuleStatus.SKIPPED,
            message="No dimension key sets supplied; referential integrity not checked",
        )
    violations: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        for field_name, valid_values in known_keys.items():
            if field_name not in record:
                continue
            if record[field_name] not in valid_values:
                violations.append(
                    {"index": index, "field": field_name, "value": record[field_name]}
                )
    if violations:
        return RuleResult(
            rule_id="FR-QUAL-006",
            status=RuleStatus.FAILED,
            message=f"{len(violations)} foreign key value(s) do not resolve to a known dimension row",
            details={"violations": violations},
        )
    return RuleResult(
        rule_id="FR-QUAL-006",
        status=RuleStatus.PASSED,
        message="All foreign key values resolve to a known dimension row",
    )


def check_reconciliation(
    local_count: int,
    *,
    source_count: int | None = None,
    local_checksum: str | None = None,
    source_checksum: str | None = None,
) -> RuleResult:
    """FR-QUAL-007: periodically compare counts/checksums against the source.

    This rule never re-fetches from a source itself — pass what the source
    reports (from a scheduled reconciliation job, EPIC-07) to run the check.
    """
    if source_count is None and source_checksum is None:
        return RuleResult(
            rule_id="FR-QUAL-007",
            status=RuleStatus.SKIPPED,
            message="No source count/checksum supplied; reconciliation not checked",
        )
    mismatches: list[str] = []
    if source_count is not None and source_count != local_count:
        mismatches.append(f"count: local={local_count} source={source_count}")
    if (
        source_checksum is not None
        and local_checksum is not None
        and source_checksum != local_checksum
    ):
        mismatches.append(f"checksum: local={local_checksum} source={source_checksum}")
    if mismatches:
        return RuleResult(
            rule_id="FR-QUAL-007",
            status=RuleStatus.FAILED,
            message="Reconciliation mismatch: " + "; ".join(mismatches),
            details={"local_count": local_count, "source_count": source_count},
        )
    return RuleResult(
        rule_id="FR-QUAL-007",
        status=RuleStatus.PASSED,
        message="Local data reconciles with the source",
    )


def check_outliers(
    records: Sequence[Mapping[str, Any]],
    contract: DataContract,
    *,
    value_field: str = "value",
    timestamp_field: str = "observed_at",
    threshold_pct: float = 1000.0,
) -> RuleResult:
    """FR-QUAL-008: flag, don't reject, a statistically extreme single-interval move.

    FLAGGED is a distinct outcome from FAILED — this rule never causes a
    quarantine on its own; a flagged batch still needs "confirmed invalid"
    review, which is FR-OPS-002/human-or-agent territory, not this rule's.
    """
    if value_field not in contract.schema or len(records) < 2:
        return RuleResult(
            rule_id="FR-QUAL-008",
            status=RuleStatus.SKIPPED,
            message="Not enough records, or no value field, to evaluate interval moves",
        )
    parsed: list[tuple[datetime, float]] = []
    for record in records:
        ts = _parse_timestamp(record.get(timestamp_field))
        if ts is None:
            continue
        try:
            value = float(record.get(value_field))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            continue
        parsed.append((ts, value))
    parsed.sort(key=lambda pair: pair[0])

    flagged: list[dict[str, Any]] = []
    for (prev_ts, prev_value), (ts, value) in zip(parsed, parsed[1:], strict=False):
        if prev_value == 0:
            continue
        pct_change = abs((value - prev_value) / prev_value) * 100
        if pct_change > threshold_pct:
            flagged.append(
                {
                    "from": prev_ts.isoformat(),
                    "to": ts.isoformat(),
                    "from_value": prev_value,
                    "to_value": value,
                    "pct_change": pct_change,
                }
            )
    if flagged:
        return RuleResult(
            rule_id="FR-QUAL-008",
            status=RuleStatus.FLAGGED,
            message=f"{len(flagged)} interval move(s) exceed {threshold_pct}% and are flagged for review",
            details={"flagged": flagged},
        )
    return RuleResult(
        rule_id="FR-QUAL-008",
        status=RuleStatus.PASSED,
        message="No statistically extreme interval moves detected",
    )


def check_semantic_metadata(
    contract: DataContract,
    *,
    required_keys: Sequence[str] = _DEFAULT_SEMANTIC_KEYS,
) -> RuleResult:
    """FR-QUAL-009: unit/index-base/seasonal-adjustment metadata must be present before Gold.

    Index base is expected embedded within the `units` string for this
    platform's contracts (e.g. "Index 1982-1984=100" in
    src/connectors/fred/contract.yaml), matching how FRED itself represents
    it, rather than a separately named field. A contract that does declare an
    explicit `index_base` metadata key is also checked, if present.
    """
    missing = [key for key in required_keys if not str(contract.metadata.get(key, "")).strip()]
    if "index_base" in contract.metadata and not str(contract.metadata["index_base"]).strip():
        missing.append("index_base")
    if missing:
        return RuleResult(
            rule_id="FR-QUAL-009",
            status=RuleStatus.FAILED,
            message=f"Missing or empty semantic metadata: {', '.join(missing)}",
            details={"missing_keys": missing},
        )
    return RuleResult(
        rule_id="FR-QUAL-009",
        status=RuleStatus.PASSED,
        message="Required semantic metadata is present",
    )
