"""Evidence-backed task selection for the first GAIEP self-improvement pilot."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .corpus_adapter import CertificationRecord
from .pilot_manifest import freeze_task_ids
from .task_factory import EngineeringTask, TaskFactory


@dataclass(frozen=True)
class SelectedPilotTask:
    behavior: str
    source_case_id: str
    task: EngineeringTask


_BEHAVIOR_KEYWORDS = {
    "isolated_implementation": ("implementation", "isolated", "single-file", "feature"),
    "test_oriented_implementation": ("test", "pytest", "coverage", "regression"),
    "integration_refactor_behavior": ("integration", "refactor", "adapter", "boundary"),
}
_BEHAVIOR_PRIORITY = (
    "test_oriented_implementation",
    "integration_refactor_behavior",
    "isolated_implementation",
)


def _haystack(record: CertificationRecord) -> str:
    return " ".join(
        str(value or "")
        for value in (
            record.capability,
            record.benchmark_id,
            record.certification_id,
            record.detail,
        )
    ).lower()


def classify_behavior(record: CertificationRecord) -> str | None:
    text = _haystack(record)
    if "implementation" not in text and "coding" not in text and "refactor" not in text:
        return None
    for behavior in _BEHAVIOR_PRIORITY:
        keywords = _BEHAVIOR_KEYWORDS[behavior]
        if any(keyword in text for keyword in keywords):
            return behavior
    return None


def implementation_task_from_certification(
    record: CertificationRecord, *, behavior: str
) -> EngineeringTask:
    factory = TaskFactory()
    return factory.from_seed(
        task_type="implementation" if behavior != "integration_refactor_behavior" else "refactor",
        title=f"Pilot case: {record.benchmark_id}",
        objective=(
            "Complete the implementation-oriented certification case using only the "
            f"recorded evidence for {record.benchmark_id}. Preserve behavior and pass "
            "the external validation gates."
        ),
        source="certification_corpus",
        difficulty=3,
        acceptance=("pytest", "ruff", "pyright"),
        constraints=(
            f"source_case_id={record.certification_id}",
            f"corpus_version={record.corpus_version}",
            f"behavior={behavior}",
            "research_only=true",
            "no_production_mutation=true",
        ),
    )


def select_pilot_tasks(records: Iterable[CertificationRecord]) -> tuple[SelectedPilotTask, ...]:
    """Select exactly one evidence-backed task for each required behavior."""
    by_behavior: dict[str, SelectedPilotTask] = {}
    for record in sorted(records, key=lambda item: item.certification_id):
        behavior = classify_behavior(record)
        if behavior is None or behavior in by_behavior:
            continue
        by_behavior[behavior] = SelectedPilotTask(
            behavior=behavior,
            source_case_id=record.certification_id,
            task=implementation_task_from_certification(record, behavior=behavior),
        )

    missing = [behavior for behavior in _BEHAVIOR_KEYWORDS if behavior not in by_behavior]
    if missing:
        raise RuntimeError(
            "fewer than three suitable implementation pilot cases; missing: "
            + ", ".join(missing)
        )

    selected = tuple(by_behavior[behavior] for behavior in _BEHAVIOR_KEYWORDS)
    freeze_task_ids([item.task.task_id for item in selected], expected=3)
    return selected


def corpus_version_for_manifest(selected: Iterable[SelectedPilotTask]) -> str:
    versions = sorted(
        {
            constraint.split("=", 1)[1]
            for item in selected
            for constraint in item.task.constraints
            if constraint.startswith("corpus_version=")
        }
    )
    if not versions:
        return "unknown"
    return "+".join(versions)
