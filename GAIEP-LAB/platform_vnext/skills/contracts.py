from dataclasses import dataclass
from enum import StrEnum


class SkillStatus(StrEnum):
    DRAFT = "DRAFT"
    REVIEW = "REVIEW"
    VALIDATED = "VALIDATED"
    APPROVED = "APPROVED"
    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"
    RETIRED = "RETIRED"


@dataclass(frozen=True)
class SkillStep:
    step_id: str
    purpose: str
    required: bool = True
    allowed_toolsets: tuple[str, ...] = ()
    input_refs: tuple[str, ...] = ()
    output_artifacts: tuple[str, ...] = ()
    validation_refs: tuple[str, ...] = ()
    max_attempts: int = 1


@dataclass(frozen=True)
class GreenSkill:
    skill_id: str
    name: str
    version: str
    owner: str
    capability: str
    status: SkillStatus
    procedure: tuple[SkillStep, ...]
    prerequisites: tuple[str, ...] = ()
    allowed_toolsets: tuple[str, ...] = ()
    expected_artifacts: tuple[str, ...] = ()
    validation_gates: tuple[str, ...] = ()
    evidence_requirements: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in ("skill_id", "name", "version", "owner", "capability"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} cannot be empty")
        if not self.procedure:
            raise ValueError("skill must contain at least one procedure step")
