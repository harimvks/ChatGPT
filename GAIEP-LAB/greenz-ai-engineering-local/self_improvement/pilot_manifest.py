"""Frozen manifest for the first GAIEP self-improvement pilot."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from typing import Iterable

from .experiment import ExperimentArm, ExperimentPlan


@dataclass(frozen=True)
class PilotManifest:
    experiment_id: str
    corpus_version: str
    task_ids: tuple[str, ...]
    arms: tuple[ExperimentArm, ...]
    validation_profile: str

    @classmethod
    def from_plan(
        cls,
        plan: ExperimentPlan,
        *,
        corpus_version: str,
        validation_profile: str = "pytest-ruff-pyright",
    ) -> "PilotManifest":
        if not plan.task_ids:
            raise ValueError("pilot manifest requires at least one task")
        if not plan.arms:
            raise ValueError("pilot manifest requires at least one experiment arm")
        return cls(
            experiment_id=plan.name,
            corpus_version=corpus_version,
            task_ids=tuple(plan.task_ids),
            arms=tuple(plan.arms),
            validation_profile=validation_profile,
        )

    def trial_count(self) -> int:
        return len(self.task_ids) * len(self.arms)

    def to_json(self) -> str:
        payload = asdict(self)
        payload["arms"] = [asdict(arm) for arm in self.arms]
        return json.dumps(payload, indent=2, sort_keys=True)


def freeze_task_ids(task_ids: Iterable[str], *, expected: int = 3) -> tuple[str, ...]:
    ids = tuple(task_ids)
    if len(ids) != expected:
        raise ValueError(f"pilot requires exactly {expected} task IDs; got {len(ids)}")
    if len(set(ids)) != len(ids):
        raise ValueError("pilot task IDs must be unique")
    return ids
