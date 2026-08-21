"""Worker bridge for bounded subagent execution.

The worker deliberately accepts an injected executor. It does not call models directly; the
injected executor is expected to use the same skill/context/platform Gateway path as a primary
run. This keeps subagents governed by the same runtime rather than creating a second AI path.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .contracts import SubagentRequest, SubagentResult, SubagentStatus


@dataclass(frozen=True)
class SubagentExecution:
    output_text: str
    model: str
    provider: str
    execution_id: str | None = None


class GovernedSubagentWorker:
    """Adapt a governed execution callback into the subagent worker contract."""

    def __init__(self, execute: Callable[[SubagentRequest], SubagentExecution]) -> None:
        self._execute = execute

    def run(self, request: SubagentRequest) -> SubagentResult:
        if request.depth != 1:
            raise PermissionError("subagent worker accepts only depth-1 requests")
        if request.task_policy.allow_subagents:
            raise PermissionError("child task policy must disable recursive subagents")
        if request.token_budget <= 0 or request.max_steps <= 0 or request.timeout_seconds <= 0:
            raise ValueError("subagent resource budgets must be positive")

        execution = self._execute(request)
        if not execution.output_text.strip():
            return SubagentResult(
                subagent_id="pending",
                status=SubagentStatus.FAILED,
                error="empty subagent output",
            )

        return SubagentResult(
            subagent_id="pending",
            status=SubagentStatus.COMPLETED,
            output_text=execution.output_text,
            execution_id=execution.execution_id,
            model=execution.model,
            provider=execution.provider,
        )
