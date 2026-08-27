from self_improvement.model_runner import ModelRequest
from self_improvement.runner_adapter import GovernedModelRunner, model_runner_metadata
from self_improvement.task_factory import EngineeringTask


def test_governed_runner_preserves_identity_and_measures_latency() -> None:
    task = EngineeringTask(
        task_id="task-adapter-001",
        task_type="implementation",
        title="adapter test",
        objective="test governed adapter",
        difficulty=1,
    )

    def rollout(request: ModelRequest) -> object:
        assert request.task.task_id == task.task_id
        return {"status": "ok"}

    runner = GovernedModelRunner(
        rollout,
        model_name="local-test",
        endpoint_model="local-test:latest",
    )
    result = runner.run(ModelRequest(task=task))

    assert result.artifact == {"status": "ok"}
    assert result.model_name == "local-test"
    assert result.endpoint_model == "local-test:latest"
    assert result.latency_s is not None
    assert result.latency_s >= 0


def test_metadata_is_provenance_safe() -> None:
    task = EngineeringTask(
        task_id="task-adapter-002",
        task_type="implementation",
        title="metadata test",
        objective="test metadata",
        difficulty=1,
    )
    result = GovernedModelRunner(
        lambda request: "artifact",
        model_name="local-test",
    ).run(ModelRequest(task=task))

    metadata = model_runner_metadata(result)
    assert metadata["model_name"] == "local-test"
    assert metadata["endpoint_model"] is None
    assert metadata["latency_s"] is not None
    assert metadata["usage"] == {}
