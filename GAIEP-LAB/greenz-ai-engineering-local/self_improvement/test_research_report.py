from pathlib import Path

from self_improvement.evidence_store import GreenMemoryStore, ResearchLineageEvent
from self_improvement.research_report import render_hypothesis_report, summarize_hypothesis


def test_research_report_summarizes_durable_lineage(tmp_path: Path) -> None:
    memory = GreenMemoryStore(tmp_path / "memory.sqlite3")
    event = ResearchLineageEvent.create(
        hypothesis_id="failure:abc",
        failure_fingerprint="abc",
        research_task_id="task-research",
        status="COMPLETED",
        source_evidence_ids=("evidence-1", "evidence-2"),
        experiment_run_id="run-1",
        result_evidence_id="evidence-3",
        created_at="2026-01-01T00:00:00+00:00",
    )
    memory.append_research_lineage_event(event)

    summary = summarize_hypothesis(memory, "failure:abc")
    assert summary is not None
    assert summary.source_evidence_ids == ("evidence-1", "evidence-2")
    assert summary.result_evidence_ids == ("evidence-3",)
    report = render_hypothesis_report(summary)
    assert "failure:abc" in report
    assert "candidate source" not in report.lower()


def test_research_report_missing_hypothesis_is_empty(tmp_path: Path) -> None:
    memory = GreenMemoryStore(tmp_path / "memory.sqlite3")
    assert summarize_hypothesis(memory, "missing") is None
