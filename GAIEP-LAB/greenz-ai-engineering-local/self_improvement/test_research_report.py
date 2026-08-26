from pathlib import Path

from self_improvement.evaluation import EvaluationResult
from self_improvement.evidence_store import GreenMemoryStore, ResearchLineageEvent
from self_improvement.provenance import RunProvenance
from self_improvement.research_report import render_hypothesis_report, summarize_hypothesis
from self_improvement.rollout import RolloutResult
from self_improvement.trajectory import TrajectoryRecord


def _record(task_id: str, *, run_id: str, passed: bool = False) -> TrajectoryRecord:
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
            passed=passed,
            reward=1.0 if passed else 0.0,
            checks={"pytest": passed},
            failure_class=None if passed else "test_failure",
        ),
    )


def test_research_report_summarizes_durable_lineage(tmp_path: Path) -> None:
    memory = GreenMemoryStore(tmp_path / "memory.sqlite3")
    source_1 = memory.append(_record("task-1", run_id="run-1"))
    source_2 = memory.append(_record("task-2", run_id="run-2"))
    result = memory.append(_record("task-result", run_id="run-3", passed=True))
    event = ResearchLineageEvent.create(
        hypothesis_id="failure:abc",
        failure_fingerprint="abc",
        research_task_id="task-research",
        status="COMPLETED",
        source_evidence_ids=(source_1, source_2),
        experiment_run_id="run-1",
        result_evidence_id=result,
        created_at="2026-01-01T00:00:00+00:00",
    )
    memory.append_research_lineage_event(event)

    summary = summarize_hypothesis(memory, "failure:abc")
    assert summary is not None
    assert summary.source_evidence_ids == tuple(sorted((source_1, source_2)))
    assert summary.result_evidence_ids == (result,)
    report = render_hypothesis_report(summary)
    assert "failure:abc" in report
    assert "candidate source" not in report.lower()


def test_research_report_missing_hypothesis_is_empty(tmp_path: Path) -> None:
    memory = GreenMemoryStore(tmp_path / "memory.sqlite3")
    assert summarize_hypothesis(memory, "missing") is None
