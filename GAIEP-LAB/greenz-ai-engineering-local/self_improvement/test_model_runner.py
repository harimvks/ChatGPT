from __future__ import annotations

from self_improvement.model_runner import CallableModelRunner, ModelRequest, ModelResult
from self_improvement.task_factory import TaskFactory


def test_callable_runner_preserves_model_contract() -> None:
    task = TaskFactory().create(
        task_type="implementation",
        title="Implement deterministic helper",
        specification="Return the requested value.",
    )
    runner = CallableModelRunner(
        lambda received: {"task_id": received.task_id},
        model_name="fake-model",
        endpoint_model="fake-endpoint",
    )

    result = runner.run(ModelRequest(task=task))

    assert isinstance(result, ModelResult)
    assert result.artifact == {"task_id": task.task_id}
    assert result.model_name == "fake-model"
    assert result.endpoint_model == "fake-endpoint"


def test_model_request_keeps_research_metadata() -> None:
    task = TaskFactory().create(
        task_type="implementation",
        title="Metadata task",
        specification="Return the requested value.",
    )
    request = ModelRequest(task=task, metadata={"experiment_id": "exp-1"})

    assert request.metadata["experiment_id"] == "exp-1"
