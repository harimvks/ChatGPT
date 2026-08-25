"""Pure GreenMemory contracts.

Memory promotion is governed. A model observation can create a candidate memory
reference, but it cannot directly become durable GreenMemory.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum


class MemoryValidationError(ValueError):
    """Raised when a GreenMemory invariant is violated."""


class MemoryStatus(StrEnum):
    CANDIDATE = "candidate"
    APPROVED = "approved"
    REJECTED = "rejected"
    RETIRED = "retired"


def _require_non_empty(label: str, value: str) -> None:
    if not value.strip():
        raise MemoryValidationError(f"{label} cannot be empty")


def _require_utc(label: str, value: datetime) -> None:
    if value.utcoffset() != timedelta(0):
        raise MemoryValidationError(f"{label} must be timezone-aware UTC")


def _dedupe(values: tuple[str, ...], *, label: str) -> tuple[str, ...]:
    cleaned = tuple(value.strip() for value in values if value.strip())
    if len(set(cleaned)) != len(cleaned):
        raise MemoryValidationError(f"{label} cannot contain duplicates")
    return tuple(sorted(cleaned))


@dataclass(frozen=True)
class CandidateMemory:
    candidate_id: str
    run_id: str
    observation_id: str
    summary: str
    evidence_refs: tuple[str, ...]
    created_at: datetime

    def __post_init__(self) -> None:
        _require_non_empty("CandidateMemory.candidate_id", self.candidate_id)
        _require_non_empty("CandidateMemory.run_id", self.run_id)
        _require_non_empty("CandidateMemory.observation_id", self.observation_id)
        _require_non_empty("CandidateMemory.summary", self.summary)
        _require_utc("CandidateMemory.created_at", self.created_at)
        object.__setattr__(
            self, "evidence_refs", _dedupe(self.evidence_refs, label="evidence_refs")
        )
        if not self.evidence_refs:
            raise MemoryValidationError("candidate memory requires evidence references")


@dataclass(frozen=True)
class GovernanceDecision:
    decision_id: str
    candidate_id: str
    status: MemoryStatus
    decided_by: str
    decision_ref: str
    decided_at: datetime

    def __post_init__(self) -> None:
        _require_non_empty("GovernanceDecision.decision_id", self.decision_id)
        _require_non_empty("GovernanceDecision.candidate_id", self.candidate_id)
        _require_non_empty("GovernanceDecision.decided_by", self.decided_by)
        _require_non_empty("GovernanceDecision.decision_ref", self.decision_ref)
        _require_utc("GovernanceDecision.decided_at", self.decided_at)
        if self.status is MemoryStatus.CANDIDATE:
            raise MemoryValidationError("governance decision cannot leave memory as candidate")


@dataclass(frozen=True)
class GreenMemoryRecord:
    memory_id: str
    candidate: CandidateMemory
    governance: GovernanceDecision
    tags: tuple[str, ...]
    promoted_at: datetime

    def __post_init__(self) -> None:
        _require_non_empty("GreenMemoryRecord.memory_id", self.memory_id)
        _require_utc("GreenMemoryRecord.promoted_at", self.promoted_at)
        object.__setattr__(self, "tags", _dedupe(self.tags, label="tags"))
        if self.governance.candidate_id != self.candidate.candidate_id:
            raise MemoryValidationError("governance decision must reference candidate memory")
        if self.governance.status is not MemoryStatus.APPROVED:
            raise MemoryValidationError("durable GreenMemory requires approved governance")
