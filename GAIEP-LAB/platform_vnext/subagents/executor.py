"""Bounded depth-1 subagent executor for GAIEP Runtime VNext.

This executor deliberately keeps subagents narrow: one child, no recursive
subagents, explicit resource budgets, and evidence-bearing lifecycle states.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Protocol
from uuid import uuid4

from platform_vnext.runtime.contracts import AgentRun, derive_child_policy
from .contracts import SubagentHandle, SubagentRequest, SubagentResult, SubagentStatus


class SubagentWorker(Protocol):
    def run(self, request: SubagentRequest) -> SubagentResult: ...


class BoundedSubagentExecutor:
    """Create and execute a single bounded child task.

    The parent must explicitly permit subagents and provide positive budgets.
    The derived child policy always disables recursive subagents.
    """

    def __init__(self, worker: SubagentWorker) -> None:
        self._worker = worker

    def execute(
        self,
        parent: AgentRun,
        *,
        task_ref: str,
        skill_ref: str,
        model_policy_ref: str,
        token_budget: int,
        max_steps: int,
        timeout_seconds: int,
        allow_write: bool = False,
    ) -> tuple[SubagentHandle, SubagentResult]:
        if not parent.task_policy.allow_subagents:
            raise PermissionError("parent task policy does not allow subagents")
        if parent.max_subagent_depth < 1:
            raise PermissionError("parent task policy allows no subagent depth")
        if parent.child_budget_count < 1:
            raise ValueError("parent child budget count is exhausted")
        if token_budget > parent.child_budget_tokens:
            raise ValueError("requested token budget exceeds parent child budget")

        policy = derive_child_policy(parent, allow_write=allow_write)
        request = SubagentRequest(
            parent_run_id=parent.run_id,
            task_ref=task_ref,
            skill_ref=skill_ref,
            workspace_scope=parent.workspace_scope,
            task_policy=policy,
            model_policy_ref=model_policy_ref,
            token_budget=token_budget,
            max_steps=max_steps,
            timeout_seconds=timeout_seconds,
            depth=1,
        )
        handle = SubagentHandle(
            subagent_id=f"sub-{uuid4().hex}",
            parent_run_id=parent.run_id,
            task_ref=task_ref,
            status=SubagentStatus.AUTHORIZED,
            depth=1,
        )
        result = self._worker.run(request)
        if result.subagent_id != handle.subagent_id:
            result = replace(result, subagent_id=handle.subagent_id)
        return replace(handle, status=result.status), result
