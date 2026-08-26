from datetime import UTC, datetime
from pathlib import Path

import pytest

from self_improvement.evaluation import EvaluationResult
from self_improvement.evidence_store import GreenMemoryStore
from self_improvement.experiment import ExperimentArm
from self_improvement.experiment_runner import ExperimentRunner
from self_improvement.provenance import RunProvenance
from self_improvement.research_loop import (
    FailureResearchLoop,
    ResearchProposalStatus,
    ResearchSubmissionAdapter,
)
from self_improvement.rollout import RolloutResult
from self_improvement.task_factory import EngineeringTask, TaskFactory
from self_improvement.trajectory import TrajectoryRecord

_NOW = datetime(2026, 8, 26, 10, 0, tzinfo=UTC)


def _task():
    return TaskFactory().from_seed(
        task_type="implementation",
        title="Example",
        objective="Implement the example",
        repository_path="repo",
        acceptance=("pytest",),
        constraints=(),
        difficulty=2,
        source="test",
    )


def _source_task(task_id: str) -> EngineeringTask:
    return EngineeringTask(
        task_id=task_id,
        task_type="implementation",
        title=f"Example {task_id}",
        objective=f"Implement {task_id}",
        repository_path="repo",
        source="test",
        difficulty=2,
        acceptance=("pytest",),
        constraints=(),
    )


def _record(task_id: str, *, run_id: str) -> TrajectoryRecord:
    rollout = RolloutResult(
        task_id=task_id,
        artifact=type("Artifact", (), {"files": {"candidate.py": "candidate"}})(),
        model_name="small-python-coder",
        scaffold_name="test",
        provenance=RunProvenance(run_id=run_id),
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


def test_research_loop_requires_recurrence(tmp_path: Path) -> None:
    memory = GreenMemoryStore(tmp_path / "memory.sqlite3")
    memory.append(_record("task-1", run_id="run-1"))
    loop = FailureResearchLoop(memory)
    assert loop.discover() == ()


def test_research_loop_links_recurring_evidence_to_hypothesis(tmp_path: Path) -> None:
    memory = GreenMemoryStore(tmp_path / "memory.sqlite3")
    first_id = memory.append(_record("task-1", run_id="run-1"))
    second_id = memory.append(_record("task-2", run_id="run-2"))

    proposals = FailureResearchLoop(memory).propose(
        [_source_task("task-1"), _source_task("task-2")]
    )

    assert len(proposals) == 1
    proposal = proposals[0]
    assert proposal.status is ResearchProposalStatus.PROPOSED
    assert proposal.hypothesis.failure_class == "test_failure"
    assert proposal.hypothesis.source_task_ids == ("task-1", "task-2")
    assert proposal.hypothesis.evidence_record_ids == (first_id, second_id)
    assert proposal.task.source == "failure_research_loop"
    assert "research_hypothesis=" in " ".join(proposal.task.constraints)

    lineage = memory.find_research_lineage_by_hypothesis(proposal.hypothesis.hypothesis_id)
    assert len(lineage) == 1
    assert lineage[0].status == "PROPOSED"
    assert lineage[0].source_evidence_ids == (first_id, second_id)
    assert lineage[0].research_task_id == proposal.task.task_id


def test_research_loop_is_bounded(tmp_path: Path) -> None:
    memory = GreenMemoryStore(tmp_path / "memory.sqlite3")
    memory.append(_record("task-1", run_id="run-1"))
    memory.append(_record("task-2", run_id="run-2"))
    proposals = FailureResearchLoop(memory).propose(
        [_source_task("task-1"), _source_task("task-2")], limit=0
    )
    assert proposals == ()


def test_research_submission_requires_external_approval(tmp_path: Path) -> None:
    memory = GreenMemoryStore(tmp_path / "memory.sqlite3")
    memory.append(_record("task-1", run_id="run-1"))
    memory.append(_record("task-2", run_id="run-2"))
    proposal = FailureResearchLoop(memory).propose(
        [_source_task("task-1"), _source_task("task-2")]
    )[0]
    adapter = ResearchSubmissionAdapter(memory)

    class UnusedRunner:
        def run(self, _plan, _tasks):
            raise AssertionError("proposal submission should require approval")

    with pytest.raises(ValueError, match="approved_by"):
        adapter.submit(
            proposal,
            approved_by="",
            runner=UnusedRunner(),
            arm=ExperimentArm("m", "s"),
            experiment_run_id="exp-1",
            submitted_at=_NOW,
        )

    assert [
        event.status
        for event in memory.find_research_lineage_by_hypothesis(proposal.hypothesis.hypothesis_id)
    ] == ["PROPOSED"]


def test_research_submission_rejection_is_durable_without_execution(tmp_path: Path) -> None:
    memory = GreenMemoryStore(tmp_path / "memory.sqlite3")
    memory.append(_record("task-1", run_id="run-1"))
    memory.append(_record("task-2", run_id="run-2"))
    proposal = FailureResearchLoop(memory).propose(
        [_source_task("task-1"), _source_task("task-2")]
    )[0]

    record = ResearchSubmissionAdapter(memory).reject(
        proposal,
        rejected_by="architecture-review",
        rejected_at=_NOW,
    )

    assert record.status is ResearchProposalStatus.REJECTED
    assert record.result_evidence_ids == ()
    assert [
        event.status
        for event in memory.find_research_lineage_by_hypothesis(proposal.hypothesis.hypothesis_id)
    ] == ["PROPOSED", "REJECTED"]


def test_closed_loop_persists_research_lineage_to_follow_up_evidence(tmp_path: Path) -> None:
    memory = GreenMemoryStore(tmp_path / "memory.sqlite3")
    first_id = memory.append(_record("task-1", run_id="run-1"))
    second_id = memory.append(_record("task-2", run_id="run-2"))
    proposal = FailureResearchLoop(memory).propose(
        [_source_task("task-1"), _source_task("task-2")]
    )[0]

    def rollout_factory(arm):
        class FakeRunner:
            def run(self, task):
                return RolloutResult(
                    task_id=task.task_id,
                    artifact={"files": {"candidate.py": "fixed = True\n"}},
                    model_name=arm.model_name,
                    scaffold_name=arm.scaffold_name,
                    provenance=RunProvenance(
                        run_id="run-research-1",
                        evidence_refs=("evidence://follow-up",),
                    ),
                )

        return FakeRunner()

    def evaluate(task, _artifact):
        return EvaluationResult(
            task_id=task.task_id,
            passed=True,
            reward=1.0,
            checks={"pytest": True},
        )

    runner = ExperimentRunner(rollout_factory, evaluate, memory)
    submission = ResearchSubmissionAdapter(memory).submit(
        proposal,
        approved_by="human-review",
        runner=runner,
        arm=ExperimentArm("small-python-coder", "inspect-plan-implement-test"),
        experiment_run_id="exp-research-1",
        submitted_at=_NOW,
    )

    assert submission.status is ResearchProposalStatus.COMPLETED
    assert len(submission.result_evidence_ids) == 1
    assert memory.count() == 3
    follow_up = memory.get(submission.result_evidence_ids[0])
    assert follow_up is not None
    assert follow_up.task_id == proposal.task.task_id
    assert follow_up.passed

    restarted = GreenMemoryStore(memory.path)
    lineage = restarted.find_research_lineage_by_hypothesis(proposal.hypothesis.hypothesis_id)
    assert [event.status for event in lineage] == [
        "PROPOSED",
        "APPROVED",
        "SUBMITTED",
        "COMPLETED",
    ]
    assert lineage[0].source_evidence_ids == (first_id, second_id)
    assert lineage[-1].experiment_run_id == "exp-research-1"
    assert lineage[-1].result_evidence_id == submission.result_evidence_ids[0]

    ResearchSubmissionAdapter(restarted).submit(
        proposal,
        approved_by="human-review",
        runner=runner,
        arm=ExperimentArm("small-python-coder", "inspect-plan-implement-test"),
        experiment_run_id="exp-research-1",
        submitted_at=_NOW,
    )
    assert (
        restarted.find_research_lineage_by_hypothesis(proposal.hypothesis.hypothesis_id) == lineage
    )
