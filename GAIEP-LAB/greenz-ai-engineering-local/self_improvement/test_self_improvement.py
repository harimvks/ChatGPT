from self_improvement.evaluation import EvaluationRunner
from self_improvement.failure_miner import FailureMiner
from self_improvement.task_factory import TaskFactory


def test_task_ids_are_reproducible():
    factory = TaskFactory()
    kwargs = dict(
        task_type="implementation",
        title="Add feature",
        objective="Implement feature X",
        acceptance=("pytest",),
        constraints=("no public API break",),
    )
    assert factory.from_seed(**kwargs).task_id == factory.from_seed(**kwargs).task_id


def test_evaluation_requires_external_checks():
    factory = TaskFactory()
    task = factory.from_seed(task_type="testing", title="Add test", objective="Cover branch")
    runner = EvaluationRunner({
        "ruff": lambda _task, _artifact: True,
        "pytest": lambda _task, _artifact: False,
    })
    result = runner.evaluate(task, object())
    assert not result.passed
    assert result.failure_class == "test_failure"
    assert result.reward == 0.5


def test_failure_mining_generates_harder_followup():
    factory = TaskFactory()
    task = factory.from_seed(task_type="debug", title="Fix bug", objective="Fix X", difficulty=2)
    result = EvaluationRunner({"pytest": lambda _task, _artifact: False}).evaluate(task, object())
    proposals = FailureMiner().propose_followups([task], [result])
    assert len(proposals) == 1
    assert proposals[0].source == "failure_mining"
    assert proposals[0].difficulty == 3
