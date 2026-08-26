from self_improvement.evaluation import EvaluationResult
from self_improvement.failure_miner import FailureMiner
from self_improvement.provenance import RunProvenance
from self_improvement.rollout import RolloutResult
from self_improvement.trajectory import TrajectoryRecord


def _trajectory(task_id: str) -> TrajectoryRecord:
    rollout = RolloutResult(
        task_id=task_id,
        artifact=type("Artifact", (), {"files": {"candidate.py": "x"}})(),
        model_name="model-a",
        scaffold_name="scaffold-a",
        provenance=RunProvenance(run_id=f"run-{task_id}"),
    )
    return TrajectoryRecord.from_results(
        rollout,
        EvaluationResult(
            task_id=task_id,
            passed=False,
            reward=0.0,
            checks={"pytest": False},
            failure_class="test_failure",
        ),
    )


def test_failure_miner_clusters_durable_failure_fingerprints() -> None:
    clusters = FailureMiner().cluster_trajectories((_trajectory("task-a"), _trajectory("task-b")))

    assert len(clusters) == 1
    assert clusters[0].failure_class == "test_failure"
    assert clusters[0].count == 2
    assert clusters[0].task_ids == ("task-a", "task-b")
