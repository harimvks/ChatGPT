"""Turn evaluation evidence into the next research-task candidates."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable

from .evaluation import EvaluationResult
from .fingerprint import failure_fingerprint
from .task_factory import EngineeringTask, TaskFactory
from .trajectory import TrajectoryRecord


@dataclass(frozen=True)
class FailureCluster:
    failure_class: str
    count: int
    task_ids: tuple[str, ...]


@dataclass(frozen=True)
class EvidenceFailureCluster:
    """Repeated failure mode with a deterministic evidence fingerprint."""

    failure_class: str
    fingerprint: str
    count: int
    task_ids: tuple[str, ...]
    model_names: tuple[str, ...]


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

    def cluster_trajectories(
        self, trajectories: Iterable[TrajectoryRecord]
    ) -> list[EvidenceFailureCluster]:
        """Cluster durable trajectories by generalized failure fingerprint."""
        grouped: dict[str, list[TrajectoryRecord]] = {}
        for trajectory in trajectories:
            fingerprint = failure_fingerprint(trajectory)
            if fingerprint:
                grouped.setdefault(fingerprint, []).append(trajectory)
        clusters: list[EvidenceFailureCluster] = []
        for fingerprint, records in grouped.items():
            first = records[0]
            clusters.append(
                EvidenceFailureCluster(
                    failure_class=first.failure_class or "unknown",
                    fingerprint=fingerprint,
                    count=len(records),
                    task_ids=tuple(sorted(record.task_id for record in records)),
                    model_names=tuple(sorted({record.model_name for record in records})),
                )
            )
        return sorted(clusters, key=lambda item: (-item.count, item.fingerprint))

    def propose_followups(
        self,
        tasks: Iterable[EngineeringTask],
        results: Iterable[EvaluationResult],
        *,
        limit: int = 10,
    ) -> list[EngineeringTask]:
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
            proposals.append(
                factory.from_seed(
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
                )
            )
        return proposals
