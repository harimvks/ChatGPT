from pathlib import Path

from self_improvement.evaluation import EvaluationResult
from self_improvement.evidence_store import GreenMemoryStore
from self_improvement.research_loop import FailureResearchLoop
from self_improvement.task_factory import TaskFactory
from self_improvement.trajectory import TrajectoryRecord
from self_improvement.rollout import RolloutResult
from self_improvement.provenance import RunProvenance


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
    memory.append(_record("task-1", run_id="run-1"))
    memory.append(_record("task-2", run_id="run-2"))

    task = _task()
    proposals = FailureResearchLoop(memory).propose([task])

    assert len(proposals) == 1
    proposal = proposals[0]
    assert proposal.hypothesis.failure_class == "test_failure"
    assert proposal.hypothesis.source_task_ids == ("task-1", "task-2")
    assert len(proposal.hypothesis.evidence_record_ids) == 2
    assert proposal.task.source == "failure_research_loop"
    assert "research_hypothesis=" in " ".join(proposal.task.constraints)


def test_research_loop_is_bounded(tmp_path: Path) -> None:
    memory = GreenMemoryStore(tmp_path / "memory.sqlite3")
    memory.append(_record("task-1", run_id="run-1"))
    memory.append(_record("task-2", run_id="run-2"))
    task = _task()
    proposals = FailureResearchLoop(memory).propose([task], limit=0)
    assert proposals == ()
