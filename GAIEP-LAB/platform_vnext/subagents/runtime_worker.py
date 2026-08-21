"""Bridge bounded subagent requests into the same RuntimeVNext execution path."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from platform_vnext.runtime.contracts import AgentRun, ModelPolicy
from platform_vnext.runtime.engine import RuntimeVNext
from platform_vnext.skills.contracts import GreenSkill
from .contracts import SubagentRequest
from .worker import GovernedSubagentWorker, SubagentExecution


@dataclass(frozen=True)
class RuntimeSubagentWorker:
    """Build a child AgentRun and execute it through the parent runtime."""

    runtime: RuntimeVNext
    skill_resolver: Callable[[str], GreenSkill | None]

    def _resolve(self, skill_ref: str) -> GreenSkill:
        skill = self.skill_resolver(skill_ref)
        if skill is None:
            raise LookupError(f"unknown subagent skill: {skill_ref}")
        return skill

    def execute(self, request: SubagentRequest) -> SubagentExecution:
        skill = self._resolve(request.skill_ref)
        child = AgentRun(
            run_id=f"{request.parent_run_id}:child:{request.task_ref}",
            task_ref=request.task_ref,
            workspace_scope=request.workspace_scope,
            task_policy=request.task_policy,
            model_policy=ModelPolicy(
                capability_tag=request.model_policy_ref,
                require_certification=True,
            ),
            parent_run_id=request.parent_run_id,
            child_budget_tokens=0,
            child_budget_count=0,
            max_subagent_depth=0,
        )
        result = self.runtime.execute(child, skill, template="{{ payload }}")
        return SubagentExecution(
            output_text=result.response.text,
            model=result.response.model,
            provider=result.response.provider_name,
            execution_id=result.response.execution_id,
        )

    def worker(self) -> GovernedSubagentWorker:
        return GovernedSubagentWorker(self.execute)
