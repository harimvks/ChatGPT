"""Deterministic failure-to-research proposal loop for GAIEP."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from .evidence_store import GreenMemoryStore, ResearchLineageEvent
from .experiment import ExperimentArm, ExperimentPlan
from .experiment_runner import ExperimentRunner
from .failure_miner import EvidenceFailureCluster, FailureMiner
from .task_factory import EngineeringTask, TaskFactory


class ResearchProposalStatus(StrEnum):
    """Explicit lifecycle states for failure-research proposals."""

    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    SUBMITTED = "SUBMITTED"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


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
    status: ResearchProposalStatus = ResearchProposalStatus.PROPOSED


@dataclass(frozen=True)
class ResearchSubmissionRecord:
    """Result of an explicit caller-driven proposal submission."""

    proposal_id: str
    hypothesis_id: str
    task_id: str
    evidence_record_ids: tuple[str, ...]
    submitted_at: str
    status: ResearchProposalStatus
    experiment_run_id: str | None = None
    result_evidence_ids: tuple[str, ...] = ()


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
            evidence_ids = tuple(self._memory.record_id_for(record) for record in records)
            source_tasks = tuple(sorted({record.task_id for record in records}))
            base = next(
                (task_by_id[task_id] for task_id in source_tasks if task_id in task_by_id), None
            )
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
            proposal = ResearchProposal(hypothesis, task)
            self._memory.append_research_lineage_event(
                ResearchLineageEvent.create(
                    hypothesis_id=hypothesis.hypothesis_id,
                    failure_fingerprint=hypothesis.failure_fingerprint,
                    research_task_id=task.task_id,
                    status=proposal.status.value,
                    source_evidence_ids=evidence_ids,
                )
            )
            proposals.append(proposal)
        return tuple(proposals)


class ResearchSubmissionAdapter:
    """Submit externally approved proposals to the controlled experiment runner."""

    def __init__(self, memory: GreenMemoryStore) -> None:
        self._memory = memory

    def reject(
        self,
        proposal: ResearchProposal,
        *,
        rejected_by: str,
        rejected_at: datetime | None = None,
    ) -> ResearchSubmissionRecord:
        if not rejected_by.strip():
            raise ValueError("rejected_by is required")
        timestamp = _timestamp(rejected_at)
        self._append_lineage(proposal, ResearchProposalStatus.REJECTED, created_at=timestamp)
        return ResearchSubmissionRecord(
            proposal_id=proposal.task.task_id,
            hypothesis_id=proposal.hypothesis.hypothesis_id,
            task_id=proposal.task.task_id,
            evidence_record_ids=proposal.hypothesis.evidence_record_ids,
            submitted_at=timestamp,
            status=ResearchProposalStatus.REJECTED,
        )

    def submit(
        self,
        proposal: ResearchProposal,
        *,
        approved_by: str,
        runner: ExperimentRunner,
        arm: ExperimentArm,
        experiment_run_id: str,
        submitted_at: datetime | None = None,
    ) -> ResearchSubmissionRecord:
        """Run a proposal only after explicit external approval is supplied."""
        if not approved_by.strip():
            raise ValueError("approved_by is required before proposal submission")
        if not experiment_run_id.strip():
            raise ValueError("experiment_run_id is required")
        timestamp = _timestamp(submitted_at)
        self._append_lineage(proposal, ResearchProposalStatus.APPROVED, created_at=timestamp)
        self._append_lineage(
            proposal,
            ResearchProposalStatus.SUBMITTED,
            experiment_run_id=experiment_run_id,
            created_at=timestamp,
        )
        plan = ExperimentPlan(
            name=experiment_run_id,
            task_ids=(proposal.task.task_id,),
            arms=(arm,),
        )
        try:
            trials = runner.run(plan, [proposal.task])
        except Exception:
            self._append_lineage(
                proposal,
                ResearchProposalStatus.FAILED,
                experiment_run_id=experiment_run_id,
                created_at=timestamp,
            )
            raise
        result_ids = tuple(self._memory.append(trial.trajectory) for trial in trials)
        status = ResearchProposalStatus.COMPLETED
        for result_id in result_ids:
            self._append_lineage(
                proposal,
                status,
                experiment_run_id=experiment_run_id,
                result_evidence_id=result_id,
                created_at=timestamp,
            )
        return ResearchSubmissionRecord(
            proposal_id=proposal.task.task_id,
            hypothesis_id=proposal.hypothesis.hypothesis_id,
            task_id=proposal.task.task_id,
            evidence_record_ids=proposal.hypothesis.evidence_record_ids,
            submitted_at=timestamp,
            status=status,
            experiment_run_id=experiment_run_id,
            result_evidence_ids=result_ids,
        )

    def _append_lineage(
        self,
        proposal: ResearchProposal,
        status: ResearchProposalStatus,
        *,
        experiment_run_id: str | None = None,
        result_evidence_id: str | None = None,
        created_at: str,
    ) -> str:
        return self._memory.append_research_lineage_event(
            ResearchLineageEvent.create(
                hypothesis_id=proposal.hypothesis.hypothesis_id,
                failure_fingerprint=proposal.hypothesis.failure_fingerprint,
                research_task_id=proposal.task.task_id,
                status=status.value,
                source_evidence_ids=proposal.hypothesis.evidence_record_ids,
                experiment_run_id=experiment_run_id,
                result_evidence_id=result_evidence_id,
                created_at=created_at,
            )
        )


def _timestamp(value: datetime | None = None) -> str:
    current = value or datetime.now(UTC)
    if current.tzinfo is None or current.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return current.astimezone(UTC).isoformat()
