"""Evidence-first closed-loop orchestration for GAIEP research."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .evaluation import EvaluationResult, EvaluationRunner
from .failure_miner import FailureMiner
from .rollout import ResearchRolloutRunner
from .task_factory import EngineeringTask


@dataclass(frozen=True)
class ResearchRun:
    rollout_task_id: str
    model_name: str
    scaffold_name: str
    evaluation: EvaluationResult


class SelfImprovementLoop:
    """Run task -> rollout -> external evidence -> failure mining.

    This orchestrator deliberately stops before training, routing mutation, or
    promotion. The caller owns persistence and any human approval boundary.
    """

    def __init__(self, rollout: ResearchRolloutRunner, evaluator: EvaluationRunner,
                 failure_miner: FailureMiner | None = None) -> None:
        self._rollout = rollout
        self._evaluator = evaluator
        self._failure_miner = failure_miner or FailureMiner()

    def run_task(self, task: EngineeringTask) -> ResearchRun:
        result = self._rollout.run(task)
        evaluation = self._evaluator.evaluate(task, result.artifact)
        return ResearchRun(
            rollout_task_id=result.task_id,
            model_name=result.model_name,
            scaffold_name=result.scaffold_name,
            evaluation=evaluation,
        )

    def propose_followups(self, tasks: Iterable[EngineeringTask],
                          runs: Iterable[ResearchRun], *, limit: int = 10) -> list[EngineeringTask]:
        results = [run.evaluation for run in runs]
        return self._failure_miner.propose_followups(tasks, results, limit=limit)
