"""Gateway-compatible research rollout adapter.

The adapter accepts an existing GAIEP ModelCall callable rather than importing or
mutating the production Gateway. This keeps the LAB runner contract-neutral until
the exact Gateway checkout is available for binding.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .rollout import RolloutResult
from .task_factory import EngineeringTask


@dataclass(frozen=True)
class GatewayRolloutRequest:
    system: str
    user: str


ModelCall = Callable[[str, str], Any]


class GatewayResearchRollout:
    """Turn an existing Gateway ModelCall into a GAIEP research rollout."""

    def __init__(
        self,
        model_call: ModelCall,
        *,
        model_name: str,
        scaffold_name: str = "inspect-plan-implement-test",
        system_prompt: str = "You are a GAIEP research coding agent. Work only on the supplied task.",
    ) -> None:
        self._model_call = model_call
        self._model_name = model_name
        self._scaffold_name = scaffold_name
        self._system_prompt = system_prompt

    def build_request(self, task: EngineeringTask) -> GatewayRolloutRequest:
        acceptance = "\n".join(f"- {item}" for item in task.acceptance) or "- satisfy the task objective"
        constraints = "\n".join(f"- {item}" for item in task.constraints) or "- stay within the supplied repository scope"
        user = (
            f"Task ID: {task.task_id}\n"
            f"Type: {task.task_type}\n"
            f"Title: {task.title}\n"
            f"Objective: {task.objective}\n"
            f"Repository path: {task.repository_path or '(not specified)'}\n\n"
            f"Acceptance criteria:\n{acceptance}\n\n"
            f"Constraints:\n{constraints}\n"
        )
        return GatewayRolloutRequest(system=self._system_prompt, user=user)

    def run(self, task: EngineeringTask) -> RolloutResult:
        request = self.build_request(task)
        response = self._model_call(request.system, request.user)
        return RolloutResult(
            task_id=task.task_id,
            artifact=response,
            model_name=self._model_name,
            scaffold_name=self._scaffold_name,
        )
