from self_improvement.evaluation import EvaluationRunner
from self_improvement.loop import SelfImprovementLoop
from self_improvement.rollout import ResearchRolloutRunner
from self_improvement.task_factory import TaskFactory


def test_loop_uses_external_evidence_and_preserves_model_metadata():
    task = TaskFactory().from_seed(
        task_type="implementation",
        title="Implement feature",
        objective="Implement X",
    )
    rollout = ResearchRolloutRunner(
        lambda _task: {"code": "candidate"},
        model_name="test-model",
        scaffold_name="inspect-plan-implement-test",
    )
    evaluator = EvaluationRunner({
        "pytest": lambda _task, artifact: artifact["code"] == "candidate",
        "ruff": lambda _task, _artifact: True,
    })
    run = SelfImprovementLoop(rollout, evaluator).run_task(task)
    assert run.evaluation.passed
    assert run.evaluation.reward == 1.0
    assert run.model_name == "test-model"
    assert run.scaffold_name == "inspect-plan-implement-test"
