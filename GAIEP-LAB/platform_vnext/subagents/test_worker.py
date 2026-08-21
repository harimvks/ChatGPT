import pytest

from platform_vnext.subagents.contracts import SubagentRequest
from platform_vnext.subagents.worker import GovernedSubagentWorker, SubagentExecution
from platform_vnext.runtime.contracts import TaskPolicy, WorkspaceScope


def request(depth=1, allow_subagents=False, token_budget=100, max_steps=2, timeout_seconds=10):
    return SubagentRequest(
        parent_run_id="parent",
        task_ref="child",
        skill_ref="skill",
        workspace_scope=WorkspaceScope(root="/tmp", mode="read-only"),
        task_policy=TaskPolicy(task_type="research", allow_subagents=allow_subagents),
        model_policy_ref="model-policy",
        token_budget=token_budget,
        max_steps=max_steps,
        timeout_seconds=timeout_seconds,
        depth=depth,
    )


def test_worker_uses_injected_governed_executor():
    seen = []

    def execute(req):
        seen.append(req)
        return SubagentExecution("answer", "model", "provider", "exec")

    result = GovernedSubagentWorker(execute).run(request())
    assert result.status.value == "COMPLETED"
    assert result.output_text == "answer"
    assert seen[0].depth == 1


def test_worker_rejects_recursive_depth():
    with pytest.raises(PermissionError):
        GovernedSubagentWorker(lambda _: None).run(request(depth=2))


def test_worker_rejects_recursive_policy():
    with pytest.raises(PermissionError):
        GovernedSubagentWorker(lambda _: None).run(request(allow_subagents=True))


def test_worker_rejects_invalid_budget():
    with pytest.raises(ValueError):
        GovernedSubagentWorker(lambda _: None).run(request(token_budget=0))
