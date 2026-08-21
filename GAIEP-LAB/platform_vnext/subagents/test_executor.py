from platform_vnext.runtime.contracts import AgentRun, ModelPolicy, TaskPolicy, WorkspaceScope
from platform_vnext.subagents.contracts import SubagentResult, SubagentStatus
from platform_vnext.subagents.executor import BoundedSubagentExecutor


class Worker:
    def run(self, request):
        assert request.depth == 1
        assert request.task_policy.allow_subagents is False
        return SubagentResult(subagent_id="worker-id", status=SubagentStatus.COMPLETED)


def make_parent() -> AgentRun:
    return AgentRun(
        run_id="parent-1",
        task_ref="task-1",
        workspace_scope=WorkspaceScope(root="/tmp", mode="read-only"),
        task_policy=TaskPolicy(
            task_type="research",
            allowed_skills=frozenset({"research"}),
            allow_subagents=True,
        ),
        model_policy=ModelPolicy(capability_tag="reasoning"),
        child_budget_tokens=1000,
        child_budget_count=1,
        max_subagent_depth=1,
    )


def test_bounded_executor_disables_recursive_children():
    handle, result = BoundedSubagentExecutor(Worker()).execute(
        make_parent(),
        task_ref="child-task",
        skill_ref="research",
        model_policy_ref="reasoning",
        token_budget=500,
        max_steps=5,
        timeout_seconds=30,
    )
    assert handle.depth == 1
    assert handle.status is SubagentStatus.COMPLETED
    assert result.status is SubagentStatus.COMPLETED


def test_bounded_executor_rejects_when_parent_disallows_children():
    parent = make_parent()
    parent = AgentRun(
        run_id=parent.run_id,
        task_ref=parent.task_ref,
        workspace_scope=parent.workspace_scope,
        task_policy=TaskPolicy(task_type="research"),
        model_policy=parent.model_policy,
    )
    try:
        BoundedSubagentExecutor(Worker()).execute(
            parent,
            task_ref="child-task",
            skill_ref="research",
            model_policy_ref="reasoning",
            token_budget=100,
            max_steps=1,
            timeout_seconds=5,
        )
    except PermissionError:
        return
    raise AssertionError("expected PermissionError")
