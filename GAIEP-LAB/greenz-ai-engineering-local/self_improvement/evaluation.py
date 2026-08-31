"""Evidence-first evaluation boundary for self-improvement experiments."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Mapping

from .task_factory import EngineeringTask


@dataclass(frozen=True)
class EvaluationResult:
    task_id: str
    passed: bool
    reward: float
    checks: Mapping[str, bool] = field(default_factory=dict)
    failure_class: str | None = None
    notes: str = ""


Check = Callable[[EngineeringTask, object], bool]


class EvaluationRunner:
    """Run externally-defined checks; never accept model self-reported success."""

    def __init__(self, checks: Mapping[str, Check]) -> None:
        if not checks:
            raise ValueError("at least one external check is required")
        self._checks = dict(checks)

    def evaluate(self, task: EngineeringTask, artifact: object) -> EvaluationResult:
        outcomes: dict[str, bool] = {}
        for name, check in self._checks.items():
            try:
                outcomes[name] = bool(check(task, artifact))
            except Exception:
                outcomes[name] = False

        passed = all(outcomes.values())
        reward = sum(1.0 for ok in outcomes.values() if ok) / len(outcomes)
        failure_class = None if passed else self._classify_failure(outcomes)
        return EvaluationResult(
            task_id=task.task_id,
            passed=passed,
            reward=reward,
            checks=outcomes,
            failure_class=failure_class,
        )

    @staticmethod
    def _classify_failure(outcomes: Mapping[str, bool]) -> str:
        if not outcomes.get("pytest", True):
            return "test_failure"
        if not outcomes.get("pyright", True):
            return "type_failure"
        if not outcomes.get("ruff", True):
            return "lint_failure"
        return "acceptance_failure"
