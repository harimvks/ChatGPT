"""Research-only rollout boundary for GAIEP self-improvement experiments."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .task_factory import EngineeringTask


@dataclass(frozen=True)
class RolloutResult:
    task_id: str
    artifact: object
    model_name: str
    scaffold_name: str


RolloutFn = Callable[[EngineeringTask], object]


class ResearchRolloutRunner:
    """Execute an injected model/agent function without owning model routing."""

    def __init__(self, rollout: RolloutFn, *, model_name: str, scaffold_name: str = "default") -> None:
        self._rollout = rollout
        self._model_name = model_name
        self._scaffold_name = scaffold_name

    def run(self, task: EngineeringTask) -> RolloutResult:
        artifact = self._rollout(task)
        return RolloutResult(
            task_id=task.task_id,
            artifact=artifact,
            model_name=self._model_name,
            scaffold_name=self._scaffold_name,
        )
