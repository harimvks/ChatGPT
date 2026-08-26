"""Evidence-based assessment of controlled research interventions."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum

from .fingerprint import failure_fingerprint
from .trajectory import TrajectoryRecord


class ResearchOutcome(StrEnum):
    """Conservative outcome classification for a research intervention."""

    IMPROVED = "IMPROVED"
    NO_CHANGE = "NO_CHANGE"
    REGRESSED = "REGRESSED"
    INCONCLUSIVE = "INCONCLUSIVE"


@dataclass(frozen=True)
class ResearchOutcomeAssessment:
    """Evidence-only comparison of source failures and follow-up results."""

    outcome: ResearchOutcome
    source_count: int
    follow_up_count: int
    source_failure_fingerprint: str
    remaining_matching_failures: int
    follow_up_failure_fingerprints: tuple[str, ...]


def assess_intervention(
    source: Iterable[TrajectoryRecord],
    follow_up: Iterable[TrajectoryRecord],
    *,
    failure_fingerprint_value: str | None = None,
) -> ResearchOutcomeAssessment:
    """Classify a follow-up without treating model claims as evidence.

    IMPROVED requires the targeted fingerprint to disappear from the follow-up
    and every follow-up trajectory to pass. NO_CHANGE means the targeted failure
    persists. REGRESSED means the targeted failure is gone but a new failing
    fingerprint appears. Otherwise the result is INCONCLUSIVE.
    """
    source_records = tuple(source)
    follow_up_records = tuple(follow_up)
    source_fingerprints = tuple(
        fingerprint for record in source_records if (fingerprint := failure_fingerprint(record))
    )
    if failure_fingerprint_value is None:
        if not source_fingerprints:
            raise ValueError("source evidence contains no failure fingerprint")
        failure_fingerprint_value = source_fingerprints[0]
    follow_up_fingerprints = tuple(
        fingerprint for record in follow_up_records if (fingerprint := failure_fingerprint(record))
    )
    remaining = sum(
        fingerprint == failure_fingerprint_value for fingerprint in follow_up_fingerprints
    )
    unique_follow_up = tuple(sorted(set(follow_up_fingerprints)))
    all_passed = bool(follow_up_records) and all(record.passed for record in follow_up_records)

    if all_passed and remaining == 0:
        outcome = ResearchOutcome.IMPROVED
    elif remaining > 0:
        outcome = ResearchOutcome.NO_CHANGE
    elif follow_up_fingerprints:
        outcome = ResearchOutcome.REGRESSED
    else:
        outcome = ResearchOutcome.INCONCLUSIVE

    return ResearchOutcomeAssessment(
        outcome=outcome,
        source_count=len(source_records),
        follow_up_count=len(follow_up_records),
        source_failure_fingerprint=failure_fingerprint_value,
        remaining_matching_failures=remaining,
        follow_up_failure_fingerprints=unique_follow_up,
    )
