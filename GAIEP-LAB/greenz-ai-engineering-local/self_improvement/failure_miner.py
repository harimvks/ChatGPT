"""Turn evaluation evidence into the next research-task candidates."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable

from .evaluation import EvaluationResult
from .task_factory import EngineeringTask, TaskFactory


@dataclass(frozen=True)
class FailureCluster:
    failure_class: str
    count: int
    task_ids: tuple[str, ...]


class FailureMiner:
    """Mine repeated externally-observed failures without changing models."""

    def cluster(self, results: Iterable[EvaluationResult]) -> list[FailureCluster]:
        grouped: dict[str, list[str]] = {}
        for result in results:
            if result.failure_class:
                grouped.setdefault(result.failure_class, []).append(result.task_id)
        return [
            FailureCluster(name, len(ids), tuple(ids))
            for name, ids in sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0]))
        ]

    def propose_followups(self, tasks: Iterable[EngineeringTask],
                         results: Iterable[EvaluationResult], *, limit: int = 10) -> list[EngineeringTask]:
        by_id = {task.task_id: task for task in tasks}
        failures = [result for result in results if result.failure_class and result.task_id in by_id]
        counts = Counter(result.failure_class for result in failures)
        factory = TaskFactory()
        proposals: list[EngineeringTask] = []
        for result in failures:
            if len(proposals) >= limit:
                break
            original = by_id[result.task_id]
            failure = result.failure_class or "unknown"
            proposals.append(factory.from_seed(
                task_type=original.task_type,
                title=f"Targeted follow-up: {failure}",
                objective=(
                    f"Re-solve the original task while explicitly addressing the observed "
                    f"{failure}; this is a research follow-up, not a production task."
                ),
                repository_path=original.repository_path,
                acceptance=original.acceptance,
                constraints=(*original.constraints, f"derived_from={original.task_id}"),
                difficulty=min(5, original.difficulty + 1),
                source="failure_mining",
            ))
        return proposals
