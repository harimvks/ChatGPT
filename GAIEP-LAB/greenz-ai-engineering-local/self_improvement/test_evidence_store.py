from pathlib import Path

from self_improvement.evaluation import EvaluationResult
from self_improvement.evidence_store import GreenMemoryStore
from self_improvement.provenance import RunProvenance
from self_improvement.rollout import RolloutResult
from self_improvement.trajectory import TrajectoryRecord


def _record(task_id: str = "task-1", passed: bool = True) -> TrajectoryRecord:
    rollout = RolloutResult(
        task_id=task_id,
        artifact=type("Artifact", (), {"files": {"candidate.py": "not stored"}})(),
        model_name="small-python-coder",
        scaffold_name="inspect-plan-implement-test",
        provenance=RunProvenance(
            run_id="run-1",
            capability_ids_requested=("coding.execute",),
        ),
    )
    return TrajectoryRecord.from_results(
        rollout,
        EvaluationResult(
            task_id=task_id,
            passed=passed,
            reward=1.0 if passed else 0.0,
            checks={"pytest": passed},
            failure_class=None if passed else "TEST_FAILURE",
        ),
    )


def test_store_persists_and_round_trips_provenance(tmp_path: Path) -> None:
    store = GreenMemoryStore(tmp_path / "greenmemory.sqlite3")
    record = _record()

    record_id = store.append(record)

    assert store.count() == 1
    restored = store.get(record_id)
    assert restored == record
    assert restored is not None
    assert restored.provenance is not None
    assert restored.provenance.run_id == "run-1"
    assert "not stored" not in restored.to_json()


def test_store_is_idempotent_for_same_content(tmp_path: Path) -> None:
    store = GreenMemoryStore(tmp_path / "greenmemory.sqlite3")
    record = _record()

    first = store.append(record)
    second = store.append(record)

    assert first == second
    assert store.count() == 1


def test_store_supports_research_queries(tmp_path: Path) -> None:
    store = GreenMemoryStore(tmp_path / "greenmemory.sqlite3")
    store.append(_record("task-1", passed=True))
    store.append(_record("task-2", passed=False))

    assert len(store.find_by_run("run-1")) == 2
    assert len(store.find_by_task("task-2")) == 1
    failures = store.find_failures("TEST_FAILURE")
    assert len(failures) == 1
    assert failures[0].task_id == "task-2"
