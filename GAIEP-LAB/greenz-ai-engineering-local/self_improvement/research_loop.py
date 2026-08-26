"""Deterministic failure-to-research proposal loop for GAIEP."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .evidence_store import GreenMemoryStore
from .failure_miner import EvidenceFailureCluster, FailureMiner
from .task_factory import EngineeringTask, TaskFactory
from .trajectory import TrajectoryRecord


@dataclass(frozen=True)
class ResearchHypothesis:
    """A bounded, evidence-linked hypothesis for follow-up research."""

    hypothesis_id: str
    failure_fingerprint: str
    failure_class: str
    statement: str
    evidence_record_ids: tuple[str, ...]
    source_task_ids: tuple[str, ...]


@dataclass(frozen=True)
class ResearchProposal:
    """A proposed experiment task; never an execution instruction."""

    hypothesis: ResearchHypothesis
    task: EngineeringTask


class FailureResearchLoop:
    """Turn durable recurring failures into bounded research proposals."""

    def __init__(self, memory: GreenMemoryStore) -> None:
        self._memory = memory
        self._miner = FailureMiner()
        self._factory = TaskFactory()

    def discover(self, *, minimum_count: int = 2) -> tuple[EvidenceFailureCluster, ...]:
        """Return recurring failure clusters above the requested evidence threshold."""
        clusters = self._miner.cluster_trajectories(self._memory.find_failures())
        return tuple(cluster for cluster in clusters if cluster.count >= minimum_count)

    def propose(
        self,
        tasks: Iterable[EngineeringTask],
        *,
        minimum_count: int = 2,
        limit: int = 10,
    ) -> tuple[ResearchProposal, ...]:
        """Create deterministic research proposals from recurring evidence.

        This method only creates research objects. It never executes, authorizes,
        routes, promotes, or mutates production artifacts.
        """
        task_by_id = {task.task_id: task for task in tasks}
        proposals: list[ResearchProposal] = []
        for cluster in self.discover(minimum_count=minimum_count):
            if len(proposals) >= limit:
                break
            records = self._memory.find_by_failure_fingerprint(cluster.fingerprint)
            evidence_ids = tuple(
                _record_id(record) for record in records
            )
            source_tasks = tuple(sorted({record.task_id for record in records}))
            base = next((task_by_id[task_id] for task_id in source_tasks if task_id in task_by_id), None)
            if base is None:
                continue
            hypothesis = ResearchHypothesis(
                hypothesis_id=f"failure:{cluster.fingerprint}",
                failure_fingerprint=cluster.fingerprint,
                failure_class=cluster.failure_class,
                statement=(
                    f"Investigate and reduce recurring {cluster.failure_class} failures "
                    f"represented by evidence fingerprint {cluster.fingerprint}."
                ),
                evidence_record_ids=evidence_ids,
                source_task_ids=source_tasks,
            )
            task = self._factory.from_seed(
                task_type=base.task_type,
                title=f"Research: {cluster.failure_class}",
                objective=hypothesis.statement,
                repository_path=base.repository_path,
                acceptance=base.acceptance,
                constraints=(*base.constraints, f"research_hypothesis={hypothesis.hypothesis_id}"),
                difficulty=min(5, base.difficulty + 1),
                source="failure_research_loop",
            )
            proposals.append(ResearchProposal(hypothesis, task))
        return tuple(proposals)


def _record_id(record: TrajectoryRecord) -> str:
    import hashlib

    return hashlib.sha256(record.to_json().encode("utf-8")).hexdigest()
