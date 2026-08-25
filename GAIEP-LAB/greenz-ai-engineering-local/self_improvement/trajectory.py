"""Immutable research trajectory record for self-improvement experiments."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from typing import Any

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
    endpoint_model: str | None = None
    latency_s: float | None = None
    usage: Mapping[str, object] = field(default_factory=dict)

    @classmethod
    def from_results(cls, rollout: RolloutResult, evaluation: EvaluationResult) -> TrajectoryRecord:
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
            endpoint_model=rollout.endpoint_model,
            latency_s=rollout.latency_s,
            usage=dict(rollout.usage),
        )

    @classmethod
    def from_json(cls, line: str) -> TrajectoryRecord:
        payload: dict[str, Any] = json.loads(line)
        payload["artifact_files"] = tuple(payload.get("artifact_files", ()))
        payload["checks"] = tuple(tuple(item) for item in payload.get("checks", ()))
        payload["usage"] = payload.get("usage", {})
        return cls(**payload)

    def key(self) -> tuple[str, str, str]:
        return (self.task_id, self.model_name, self.scaffold_name)

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True)
