from self_improvement.evaluation import EvaluationResult
from self_improvement.provenance import RunProvenance
from self_improvement.research_outcome import ResearchOutcome, assess_intervention
from self_improvement.rollout import RolloutResult
from self_improvement.trajectory import TrajectoryRecord


def _record(task_id: str, passed: bool, failure_class: str | None) -> TrajectoryRecord:
    rollout = RolloutResult(
        task_id=task_id,
        artifact={"files": {"candidate.py": "pass\n"}},
        model_name="controlled-fixture",
        scaffold_name="research",
        provenance=RunProvenance(run_id=f"run-{task_id}"),
    )
    return TrajectoryRecord.from_results(
        rollout,
        EvaluationResult(
            task_id=task_id,
            passed=passed,
            reward=1.0 if passed else 0.0,
            checks={"pytest": passed},
            failure_class=failure_class,
        ),
    )


def test_improved_when_targeted_failure_disappears() -> None:
    source = [
        _record("source-1", False, "test_failure"),
        _record("source-2", False, "test_failure"),
    ]
    follow_up = [_record("follow-up", True, None)]
    assessment = assess_intervention(source, follow_up)
    assert assessment.outcome is ResearchOutcome.IMPROVED
    assert assessment.remaining_matching_failures == 0


def test_no_change_when_targeted_failure_persists() -> None:
    source = [
        _record("source-1", False, "test_failure"),
        _record("source-2", False, "test_failure"),
    ]
    follow_up = [_record("follow-up", False, "test_failure")]
    assessment = assess_intervention(source, follow_up)
    assert assessment.outcome is ResearchOutcome.NO_CHANGE
    assert assessment.remaining_matching_failures == 1


def test_regressed_when_new_failure_replaces_targeted_failure() -> None:
    source = [
        _record("source-1", False, "test_failure"),
        _record("source-2", False, "test_failure"),
    ]
    follow_up = [_record("follow-up", False, "type_failure")]
    assessment = assess_intervention(source, follow_up)
    assert assessment.outcome is ResearchOutcome.REGRESSED
    assert assessment.remaining_matching_failures == 0


def test_empty_follow_up_is_inconclusive() -> None:
    source = [
        _record("source-1", False, "test_failure"),
        _record("source-2", False, "test_failure"),
    ]
    assessment = assess_intervention(source, [])
    assert assessment.outcome is ResearchOutcome.INCONCLUSIVE
