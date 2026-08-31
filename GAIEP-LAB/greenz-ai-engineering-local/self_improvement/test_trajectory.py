from self_improvement.evaluation import EvaluationResult
from self_improvement.rollout import RolloutResult
from self_improvement.trajectory import TrajectoryRecord


def test_trajectory_is_deterministic_and_excludes_file_contents():
    rollout = RolloutResult(
        task_id="task-1",
        artifact=type("Artifact", (), {"files": {"b.py": "secret", "a.py": "code"}})(),
        model_name="small-python-coder",
        scaffold_name="default",
    )
    evaluation = EvaluationResult(
        task_id="task-1",
        passed=False,
        reward=0.5,
        checks={"ruff": True, "pytest": False},
        failure_class="test_failure",
    )
    record = TrajectoryRecord.from_results(rollout, evaluation)
    assert record.artifact_files == ("a.py", "b.py")
    assert "secret" not in record.to_json()
    assert "test_failure" in record.to_json()
