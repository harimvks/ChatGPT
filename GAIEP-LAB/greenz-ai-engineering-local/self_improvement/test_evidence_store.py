import hashlib
import sqlite3
from pathlib import Path

from self_improvement.evaluation import EvaluationResult
from self_improvement.evidence_store import GreenMemoryStore
from self_improvement.provenance import (
    AuthorizationProvenance,
    ContextProvenance,
    RunProvenance,
)
from self_improvement.rollout import RolloutResult
from self_improvement.trajectory import TrajectoryRecord


def _record(
    task_id: str = "task-1", passed: bool = True, run_id: str = "run-1"
) -> TrajectoryRecord:
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
    assert store.find_similar_failures(failures[0]) == ()


def test_store_exposes_failure_fingerprint_and_summary(tmp_path: Path) -> None:
    store = GreenMemoryStore(tmp_path / "greenmemory.sqlite3")
    store.append(_record("task-1", passed=False))
    store.append(_record("task-2", passed=False, run_id="run-2"))

    failure_record = store.find_failures("test_failure")[0]
    matches = store.find_similar_failures(failure_record)
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


def test_store_detects_tampered_trajectory_payload(tmp_path: Path) -> None:
    path = tmp_path / "greenmemory.sqlite3"
    store = GreenMemoryStore(path)
    record_id = store.append(_record())

    with sqlite3.connect(path) as connection:
        connection.execute(
            "UPDATE evidence_records SET trajectory_json = ? WHERE record_id = ?",
            ('{"tampered": true}', record_id),
        )

    report = store.verify_integrity()
    assert not report.passed
    assert report.checked == 1
    assert report.invalid_record_ids == (record_id,)


def test_store_migrates_v1_schema_and_backfills_lineage(tmp_path: Path) -> None:
    path = tmp_path / "greenmemory.sqlite3"
    record = _record()
    payload = record.to_json()
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()

    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE evidence_records (
                record_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                run_id TEXT,
                task_id TEXT NOT NULL,
                model_name TEXT NOT NULL,
                scaffold_name TEXT NOT NULL,
                passed INTEGER NOT NULL,
                reward REAL NOT NULL,
                failure_class TEXT,
                trajectory_json TEXT NOT NULL,
                content_hash TEXT NOT NULL UNIQUE
            );
            """
        )
        connection.execute(
            "INSERT INTO evidence_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                digest,
                "2026-01-01T00:00:00+00:00",
                "run-1",
                record.task_id,
                record.model_name,
                record.scaffold_name,
                int(record.passed),
                record.reward,
                record.failure_class,
                payload,
                digest,
            ),
        )

    migrated = GreenMemoryStore(path)
    assert migrated.count() == 1
    assert len(migrated.find_by_context_hash("context-hash-1")) == 1
    assert len(migrated.find_by_skill("skill-python")) == 1
    assert len(migrated.find_by_capability("coding.execute", authorized_only=True)) == 1
    assert len(migrated.find_by_capability("coding.inspect", authorized_only=True)) == 0
    with sqlite3.connect(path) as connection:
        version = connection.execute(
            "SELECT value FROM metadata WHERE key = 'schema_version'"
        ).fetchone()[0]
    assert version == "2"


def test_denied_authorization_is_stored_but_not_marked_authorized(tmp_path: Path) -> None:
    path = tmp_path / "greenmemory.sqlite3"
    store = GreenMemoryStore(path)
    rollout = RolloutResult(
        task_id="denied-task",
        artifact=type("Artifact", (), {"files": {}})(),
        model_name="small-python-coder",
        scaffold_name="inspect-plan-implement-test",
        provenance=RunProvenance(
            run_id="run-denied",
            capability_ids_requested=("coding.execute",),
            authorization=(
                AuthorizationProvenance(
                    decision_ref="decision-1",
                    decision="DENY",
                    reason="capability not authorized",
                    capability_id="coding.execute",
                ),
            ),
        ),
    )
    record = TrajectoryRecord.from_results(
        rollout,
        EvaluationResult(
            task_id="denied-task",
            passed=False,
            reward=0.0,
            checks={"pytest": False},
            failure_class="authorization_failure",
        ),
    )

    store.append(record)

    assert len(store.find_by_capability("coding.execute")) == 1
    assert len(store.find_by_capability("coding.execute", authorized_only=True)) == 0


def test_repeated_append_does_not_duplicate_lineage_rows(tmp_path: Path) -> None:
    path = tmp_path / "greenmemory.sqlite3"
    store = GreenMemoryStore(path)
    record = _record()
    record_id = store.append(record)
    assert store.append(record) == record_id

    with sqlite3.connect(path) as connection:
        skill_count = connection.execute(
            "SELECT COUNT(*) FROM evidence_skills WHERE record_id = ?",
            (record_id,),
        ).fetchone()[0]
        capability_count = connection.execute(
            "SELECT COUNT(*) FROM evidence_capabilities WHERE record_id = ?",
            (record_id,),
        ).fetchone()[0]

    assert skill_count == 1
    assert capability_count == 2
