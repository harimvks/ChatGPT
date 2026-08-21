"""Worker bridge for bounded subagent execution."""
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
                failure_refs=("empty-subagent-output",),
            )

        artifact_refs = (f"model:{execution.model}", f"provider:{execution.provider}")
        evidence_refs = (f"execution:{execution.execution_id}",) if execution.execution_id else ()
        return SubagentResult(
            subagent_id="pending",
            status=SubagentStatus.COMPLETED,
            artifact_refs=artifact_refs,
            evidence_refs=evidence_refs,
        )
