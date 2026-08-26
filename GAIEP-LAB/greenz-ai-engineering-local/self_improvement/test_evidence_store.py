from pathlib import Path

from self_improvement.evaluation import EvaluationResult
from self_improvement.evidence_store import GreenMemoryStore
from self_improvement.provenance import ContextProvenance, RunProvenance
from self_improvement.rollout import RolloutResult
from self_improvement.trajectory import TrajectoryRecord


def _record(task_id: str = "task-1", passed: bool = True, run_id: str = "run-1") -> TrajectoryRecord:
    rollout = RolloutResult(
        task_id=task_id,
        artifact=type("Artifact", (), {"files": {"candidate.py": "not stored"}})(),
        model_name="small-python-coder",
        scaffold_name="inspect-plan-implement-test",
        provenance=RunProvenance(
            run_id=run_id,
            context=ContextProvenance("ctx-1", "context-hash-1"),
            skill_fingerprints=("skill-python",),
            capability_ids_requested=("coding.execute", "coding.inspect"),
            capability_ids_authorized=("coding.execute",),
            gateway_model="gaiep-gateway",
        ),
    )
    return TrajectoryRecord.from_results(
        rollout,
        EvaluationResult(
            task_id=task_id,
            passed=passed,
            reward=1.0 if passed else 0.0,
            checks={"pytest": passed, "ruff": passed},
            failure_class=None if passed else "test_failure",
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


def test_store_supports_structured_research_queries(tmp_path: Path) -> None:
    store = GreenMemoryStore(tmp_path / "greenmemory.sqlite3")
    store.append(_record("task-1", passed=True))
    store.append(_record("task-2", passed=False, run_id="run-2"))

    assert len(store.find_by_run("run-1")) == 1
    assert len(store.find_by_task("task-2")) == 1
    assert len(store.find_by_context_hash("context-hash-1")) == 2
    assert len(store.find_by_skill("skill-python")) == 2
    assert len(store.find_by_capability("coding.inspect")) == 2
    assert len(store.find_by_capability("coding.inspect", authorized_only=True)) == 0
    failures = store.find_failures("test_failure")
    assert len(failures) == 1
    assert failures[0].task_id == "task-2"
    fingerprint = failures[0]
    similar = store.find_similar_failures(fingerprint)
    assert similar == ()


def test_store_exposes_failure_fingerprint_and_summary(tmp_path: Path) -> None:
    store = GreenMemoryStore(tmp_path / "greenmemory.sqlite3")
    first = _record("task-1", passed=False)
    second = _record("task-2", passed=False, run_id="run-2")
    store.append(first)
    store.append(second)

    failure_fp = store.find_failures("test_failure")[0]
    matches = store.find_similar_failures(failure_fp)
    assert len(matches) == 1
    assert matches[0].task_id == "task-2"

    summary = store.summary()
    assert summary.total == 2
    assert summary.failed == 2
    assert summary.passed == 0
    assert summary.failure_classes == (("test_failure", 2),)


def test_store_integrity_and_export(tmp_path: Path) -> None:
    store = GreenMemoryStore(tmp_path / "greenmemory.sqlite3")
    store.append(_record())

    report = store.verify_integrity()
    assert report.passed
    assert report.checked == 1
    output = tmp_path / "export.jsonl"
    assert store.export_jsonl(output) == 1
    assert len(output.read_text(encoding="utf-8").splitlines()) == 1
