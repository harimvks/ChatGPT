"""Compact read-only reporting over durable failure research lineage."""

from __future__ import annotations

from dataclasses import dataclass

from .evidence_store import GreenMemoryStore, ResearchLineageEvent


@dataclass(frozen=True)
class ResearchLineageSummary:
    """Deterministic summary for one hypothesis."""

    hypothesis_id: str
    failure_fingerprint: str
    statuses: tuple[str, ...]
    source_evidence_ids: tuple[str, ...]
    research_task_ids: tuple[str, ...]
    experiment_run_ids: tuple[str, ...]
    result_evidence_ids: tuple[str, ...]


def summarize_hypothesis(
    memory: GreenMemoryStore, hypothesis_id: str
) -> ResearchLineageSummary | None:
    """Return a read-only lineage summary for a hypothesis."""
    events = memory.find_research_lineage_by_hypothesis(hypothesis_id)
    if not events:
        return None
    return ResearchLineageSummary(
        hypothesis_id=hypothesis_id,
        failure_fingerprint=events[0].failure_fingerprint,
        statuses=tuple(event.status for event in events),
        source_evidence_ids=tuple(
            sorted({evidence_id for event in events for evidence_id in event.source_evidence_ids})
        ),
        research_task_ids=tuple(sorted({event.research_task_id for event in events})),
        experiment_run_ids=tuple(
            sorted({event.experiment_run_id for event in events if event.experiment_run_id})
        ),
        result_evidence_ids=tuple(
            sorted({event.result_evidence_id for event in events if event.result_evidence_id})
        ),
    )


def render_hypothesis_report(summary: ResearchLineageSummary) -> str:
    """Render a stable human-readable report without embedding candidate source."""
    lines = [
        f"Hypothesis: {summary.hypothesis_id}",
        f"Failure fingerprint: {summary.failure_fingerprint}",
        f"Statuses: {', '.join(summary.statuses)}",
        f"Source evidence: {', '.join(summary.source_evidence_ids) or '-'}",
        f"Research tasks: {', '.join(summary.research_task_ids) or '-'}",
        f"Experiment runs: {', '.join(summary.experiment_run_ids) or '-'}",
        f"Result evidence: {', '.join(summary.result_evidence_ids) or '-'}",
    ]
    return "\n".join(lines)
