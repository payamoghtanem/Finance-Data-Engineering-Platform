"""Schema + data-quality rule engine (FR-QUAL-001..009, EPIC-04)."""

from src.validation.contract import ContractError, DataContract, load_contract
from src.validation.engine import ValidationEngine
from src.validation.models import RuleResult, RuleStatus, ValidationReport
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

__all__ = [
    "ContractError",
    "DataContract",
    "RuleResult",
    "RuleStatus",
    "ValidationEngine",
    "ValidationReport",
    "check_completeness",
    "check_freshness",
    "check_outliers",
    "check_range_and_consistency",
    "check_reconciliation",
    "check_referential_integrity",
    "check_schema",
    "check_semantic_metadata",
    "check_uniqueness",
    "load_contract",
]
