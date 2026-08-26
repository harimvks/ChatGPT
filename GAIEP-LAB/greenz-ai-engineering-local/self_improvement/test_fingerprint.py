from self_improvement.evaluation import EvaluationResult
from self_improvement.fingerprint import failure_fingerprint, provenance_fingerprint
from self_improvement.provenance import RunProvenance
from self_improvement.rollout import RolloutResult
from self_improvement.trajectory import TrajectoryRecord


def _record(task_id: str, passed: bool = False) -> TrajectoryRecord:
    rollout = RolloutResult(
        task_id=task_id,
        artifact=type("Artifact", (), {"files": {"candidate.py": "x"}})(),
        model_name="model-a",
        scaffold_name="scaffold-a",
        provenance=RunProvenance(
            run_id=f"run-{task_id}",
            skill_fingerprints=("skill-a",),
            capability_ids_requested=("coding.execute",),
            capability_ids_authorized=("coding.execute",),
        ),
    )
    return TrajectoryRecord.from_results(
        rollout,
        EvaluationResult(
            task_id=task_id,
            passed=passed,
            reward=0.0 if not passed else 1.0,
            checks={"pytest": passed},
            failure_class=None if passed else "test_failure",
        ),
    )


def test_failure_fingerprint_clusters_same_failure_across_task_identity() -> None:
    assert failure_fingerprint(_record("task-a")) == failure_fingerprint(_record("task-b"))


def test_failure_fingerprint_is_none_for_success() -> None:
    assert failure_fingerprint(_record("task-a", passed=True)) is None


def test_provenance_fingerprint_is_stable_for_same_governance_context() -> None:
    assert provenance_fingerprint(_record("task-a")) == provenance_fingerprint(_record("task-b"))
