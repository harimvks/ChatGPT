from self_improvement.gateway_rollout import GatewayResearchRollout
from self_improvement.task_factory import TaskFactory


def test_gateway_rollout_builds_structured_request_and_preserves_response():
    calls = []

    def model_call(system, user):
        calls.append((system, user))
        return {"patch": "candidate"}

    task = TaskFactory().from_seed(
        task_type="implementation",
        title="Implement feature",
        objective="Implement X",
        repository_path="src/x.py",
        acceptance=("pytest passes",),
        constraints=("do not modify API",),
    )
    runner = GatewayResearchRollout(model_call, model_name="qwen3.6:27b")
    result = runner.run(task)

    assert result.artifact == {"patch": "candidate"}
    assert result.model_name == "qwen3.6:27b"
    assert result.scaffold_name == "inspect-plan-implement-test"
    assert len(calls) == 1
    assert task.task_id in calls[0][1]
    assert "pytest passes" in calls[0][1]
    assert "do not modify API" in calls[0][1]
