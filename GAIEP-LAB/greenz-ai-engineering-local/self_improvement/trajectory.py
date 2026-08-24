"""Immutable research trajectory record for self-improvement experiments."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any
import json

from .evaluation import EvaluationResult
from .rollout import RolloutResult


@dataclass(frozen=True)
class TrajectoryRecord:
    task_id: str
    model_name: str
    scaffold_name: str
    artifact_files: tuple[str, ...]
    passed: bool
    reward: float
    checks: tuple[tuple[str, bool], ...]
    failure_class: str | None = None

    @classmethod
    def from_results(cls, rollout: RolloutResult, evaluation: EvaluationResult) -> "TrajectoryRecord":
        checks = tuple(sorted(evaluation.checks.items()))
        files = tuple(sorted(getattr(rollout.artifact, "files", {}).keys()))
        return cls(
            task_id=rollout.task_id,
            model_name=rollout.model_name,
            scaffold_name=rollout.scaffold_name,
            artifact_files=files,
            passed=evaluation.passed,
            reward=evaluation.reward,
            checks=checks,
            failure_class=evaluation.failure_class,
        )

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True)
