"""Result types shared by every rule in `validation/rules.py`.

Kept separate from `rules.py` so `engine.py` and callers can import the
result shapes without importing the rule functions themselves.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RuleStatus(Enum):
    """Outcome of one data-quality rule against one batch of records.

    FAILED and FLAGGED are deliberately distinct (FR-QUAL-008): a failure
    means the batch is not fit to publish, a flag means a human or agent
    should look at it but it is not, on its own, "confirmed invalid".
    SKIPPED means the rule could not run at all — e.g. it needs external
    context (an expected-record calendar, a source checksum) the caller
    did not supply — and is never reported as a false PASSED.
    """

    PASSED = "passed"
    FAILED = "failed"
    FLAGGED = "flagged"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class RuleResult:
    """The outcome of one FR-QUAL-xxx rule."""

    rule_id: str
    status: RuleStatus
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ValidationReport:
    """The outcome of running every rule in `rules.py` against one batch."""

    dataset_id: str
    record_count: int
    results: tuple[RuleResult, ...]

    @property
    def has_failures(self) -> bool:
        return any(result.status is RuleStatus.FAILED for result in self.results)

    @property
    def has_flags(self) -> bool:
        return any(result.status is RuleStatus.FLAGGED for result in self.results)

    def by_status(self, status: RuleStatus) -> tuple[RuleResult, ...]:
        return tuple(result for result in self.results if result.status is status)
