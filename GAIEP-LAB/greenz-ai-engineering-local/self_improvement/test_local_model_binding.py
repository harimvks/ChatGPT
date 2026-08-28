from self_improvement.local_model_binding import LocalGovernedModelRunner
from self_improvement.model_runner import ModelRequest
from self_improvement.task_factory import EngineeringTask


def test_local_backend_is_reached_through_gateway_rollout() -> None:
    calls = []

    def backend(system: str, user: str) -> dict[str, object]:
        calls.append((system, user))
        return {"files": {"candidate.py": "print('ok')"}, "model": "local-test"}

    task = EngineeringTask(
        task_id="binding-001",
        task_type="implementation",
        title="Add a candidate",
        objective="Return a candidate artifact.",
        acceptance=("candidate.py is present",),
        constraints=("Use only the supplied task",),
    )
    result = LocalGovernedModelRunner(
        backend,
        model_name="local-test",
        endpoint_model="local-test:latest",
    ).run(ModelRequest(task=task))

    assert len(calls) == 1
    assert calls[0][0].startswith("You are a GAIEP research coding agent.")
    assert "Task ID: binding-001" in calls[0][1]
    assert result.model_name == "local-test"
    assert result.endpoint_model == "local-test:latest"
    assert result.artifact.task_id == "binding-001"
    assert result.artifact.artifact == {
        "files": {"candidate.py": "print('ok')"},
        "model": "local-test",
    }
