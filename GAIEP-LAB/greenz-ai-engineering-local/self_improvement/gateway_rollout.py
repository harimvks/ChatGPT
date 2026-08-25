"""Gateway-compatible research rollout adapter.

The adapter accepts an existing GAIEP ModelCall callable rather than importing or
mutating the production Gateway. The LAB runner remains dependency-injected: it
can bind to the real runtime when available, but it never owns routing logic.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from time import perf_counter
from typing import Any

from .rollout import RolloutResult
from .task_factory import EngineeringTask


@dataclass(frozen=True)
class GatewayRolloutRequest:
    system: str
    user: str


ModelCall = Callable[[str, str], Any]


def _maybe_mapping(response: Any) -> Mapping[str, Any] | None:
    return response if isinstance(response, Mapping) else None


def _response_value(response: Any, *names: str) -> Any:
    mapped = _maybe_mapping(response)
    for name in names:
        if mapped is not None and name in mapped:
            return mapped[name]
        if hasattr(response, name):
            return getattr(response, name)
    return None


def _extract_artifact(response: Any) -> object:
    mapped = _maybe_mapping(response)
    if mapped is not None:
        if "files" in mapped:
            return mapped
        for key in ("artifact", "candidate", "output", "content"):
            if key in mapped:
                return mapped[key]
    for key in ("artifact", "candidate", "output", "content"):
        if hasattr(response, key):
            return getattr(response, key)
    return response


class GatewayResearchRollout:
    """Turn an existing Gateway ModelCall into a GAIEP research rollout."""

    def __init__(
        self,
        model_call: ModelCall,
        *,
        model_name: str,
        endpoint_model: str | None = None,
        scaffold_name: str = "inspect-plan-implement-test",
        system_prompt: str = "You are a GAIEP research coding agent. Work only on the supplied task.",
    ) -> None:
        self._model_call = model_call
        self._model_name = model_name
        self._endpoint_model = endpoint_model
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
            f"Repository path: {task.repository_path or '(not specified)'}\n"
            f"Logical model: {self._model_name}\n"
            f"Endpoint model: {self._endpoint_model or '(runtime-routed)'}\n"
            f"Scaffold: {self._scaffold_name}\n\n"
            f"Acceptance criteria:\n{acceptance}\n\n"
            f"Constraints:\n{constraints}\n\n"
            "Return only an explicit candidate artifact shaped as "
            '{"files": {"relative/path.py": "file contents"}}.'
        )
        return GatewayRolloutRequest(system=self._system_prompt, user=user)

    def run(self, task: EngineeringTask) -> RolloutResult:
        request = self.build_request(task)
        started = perf_counter()
        response = self._model_call(request.system, request.user)
        elapsed = perf_counter() - started
        usage = _response_value(response, "usage", "usage_metadata") or {}
        if not isinstance(usage, Mapping):
            usage = {"raw_usage": usage}
        endpoint_model = (
            _response_value(response, "endpoint_model", "model", "model_name")
            or self._endpoint_model
        )
        return RolloutResult(
            task_id=task.task_id,
            artifact=_extract_artifact(response),
            model_name=self._model_name,
            scaffold_name=self._scaffold_name,
            endpoint_model=str(endpoint_model) if endpoint_model else None,
            latency_s=elapsed,
            usage=dict(usage),
        )
