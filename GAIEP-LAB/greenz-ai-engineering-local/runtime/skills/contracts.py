"""Pure GreenSkills contracts.

GreenSkills describe reusable procedure. They do not grant capability, choose
models, execute tools, or write durable memory.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum


class SkillValidationError(ValueError):
    """Raised when a GreenSkill contract invariant is violated."""


class SkillStatus(StrEnum):
    CANDIDATE = "candidate"
    REVIEWED = "reviewed"
    CERTIFIED = "certified"
    RETIRED = "retired"


def _require_non_empty(label: str, value: str) -> None:
    if not value.strip():
        raise SkillValidationError(f"{label} cannot be empty")


def _require_utc(label: str, value: datetime) -> None:
    if value.utcoffset() != timedelta(0):
        raise SkillValidationError(f"{label} must be timezone-aware UTC")


def _dedupe(values: tuple[str, ...], *, label: str) -> tuple[str, ...]:
    cleaned = tuple(value.strip() for value in values if value.strip())
    if len(set(cleaned)) != len(cleaned):
        raise SkillValidationError(f"{label} cannot contain duplicates")
    return tuple(sorted(cleaned))


@dataclass(frozen=True)
class ApplicabilityRule:
    task_types: tuple[str, ...]
    capability_ids: tuple[str, ...]
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "task_types", _dedupe(self.task_types, label="task_types"))
        object.__setattr__(
            self, "capability_ids", _dedupe(self.capability_ids, label="capability_ids")
        )
        object.__setattr__(self, "tags", _dedupe(self.tags, label="tags"))
        if not self.task_types:
            raise SkillValidationError("ApplicabilityRule.task_types cannot be empty")
        if not self.capability_ids:
            raise SkillValidationError("ApplicabilityRule.capability_ids cannot be empty")


@dataclass(frozen=True)
class GreenSkill:
    skill_id: str
    version: str
    name: str
    procedure_ref: str
    applicability: ApplicabilityRule
    status: SkillStatus
    created_at: datetime
    required_capability_ids: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    context_refs: tuple[str, ...] = ()
    progressive_disclosure: bool = True
    fingerprint: str | None = None

    def __post_init__(self) -> None:
        _require_non_empty("GreenSkill.skill_id", self.skill_id)
        _require_non_empty("GreenSkill.version", self.version)
        _require_non_empty("GreenSkill.name", self.name)
        _require_non_empty("GreenSkill.procedure_ref", self.procedure_ref)
        _require_utc("GreenSkill.created_at", self.created_at)
        object.__setattr__(
            self,
            "required_capability_ids",
            _dedupe(self.required_capability_ids, label="required_capability_ids"),
        )
        object.__setattr__(
            self, "evidence_refs", _dedupe(self.evidence_refs, label="evidence_refs")
        )
        object.__setattr__(
            self, "context_refs", _dedupe(self.context_refs, label="context_refs")
        )
        computed_fingerprint = self.compute_fingerprint()
        if self.fingerprint is None:
            object.__setattr__(self, "fingerprint", computed_fingerprint)
        elif self.fingerprint != computed_fingerprint:
            raise SkillValidationError("GreenSkill.fingerprint is not canonical")
        if not set(self.required_capability_ids).issubset(self.applicability.capability_ids):
            raise SkillValidationError("skill cannot require capabilities outside applicability")
        if self.status is SkillStatus.CERTIFIED and not self.evidence_refs:
            raise SkillValidationError("certified skills require evidence references")

    def canonical(self) -> dict[str, object]:
        return {
            "applicability": {
                "capability_ids": self.applicability.capability_ids,
                "tags": self.applicability.tags,
                "task_types": self.applicability.task_types,
            },
            "context_refs": self.context_refs,
            "evidence_refs": self.evidence_refs,
            "name": self.name,
            "procedure_ref": self.procedure_ref,
            "progressive_disclosure": self.progressive_disclosure,
            "required_capability_ids": self.required_capability_ids,
            "skill_id": self.skill_id,
            "status": self.status.value,
            "version": self.version,
        }

    def compute_fingerprint(self) -> str:
        payload = json.dumps(self.canonical(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SkillDisclosure:
    skill: GreenSkill
    context_refs: tuple[str, ...]
    capability_ids: tuple[str, ...]
    fingerprint: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "context_refs", _dedupe(self.context_refs, label="context_refs"))
        object.__setattr__(
            self, "capability_ids", _dedupe(self.capability_ids, label="capability_ids")
        )
        _require_non_empty("SkillDisclosure.fingerprint", self.fingerprint)
        if self.fingerprint != self.skill.fingerprint:
            raise SkillValidationError("SkillDisclosure fingerprint must match skill")


@dataclass(frozen=True)
class CertifiedSkillVersion:
    skill: GreenSkill
    certified_by: str
    certification_ref: str
    certified_at: datetime

    def __post_init__(self) -> None:
        if self.skill.status is not SkillStatus.CERTIFIED:
            raise SkillValidationError("CertifiedSkillVersion requires a certified skill")
        _require_non_empty("CertifiedSkillVersion.certified_by", self.certified_by)
        _require_non_empty("CertifiedSkillVersion.certification_ref", self.certification_ref)
        _require_utc("CertifiedSkillVersion.certified_at", self.certified_at)


@dataclass(frozen=True)
class GreenSkillRegistry:
    skills: tuple[GreenSkill, ...]

    def __post_init__(self) -> None:
        keys = tuple((skill.skill_id, skill.version) for skill in self.skills)
        if len(set(keys)) != len(keys):
            raise SkillValidationError("GreenSkillRegistry cannot contain duplicate versions")

    def applicable_to(
        self, *, task_type: str, capability_ids: tuple[str, ...]
    ) -> tuple[GreenSkill, ...]:
        available = set(capability_ids)
        return tuple(
            sorted(
                (
                    skill
                    for skill in self.skills
                    if task_type in skill.applicability.task_types
                    and set(skill.required_capability_ids).issubset(available)
                ),
                key=lambda skill: (skill.skill_id, skill.version),
            )
        )

    def disclose(
        self, *, task_type: str, capability_ids: tuple[str, ...], max_context_refs: int
    ) -> tuple[SkillDisclosure, ...]:
        if max_context_refs < 0:
            raise SkillValidationError("max_context_refs cannot be negative")
        disclosures: list[SkillDisclosure] = []
        for skill in self.applicable_to(task_type=task_type, capability_ids=capability_ids):
            refs = skill.context_refs[:max_context_refs] if skill.progressive_disclosure else ()
            disclosures.append(SkillDisclosure(
                skill=skill,
                context_refs=refs,
                capability_ids=skill.required_capability_ids,
                fingerprint=skill.fingerprint or skill.compute_fingerprint(),
            ))
        return tuple(disclosures)
