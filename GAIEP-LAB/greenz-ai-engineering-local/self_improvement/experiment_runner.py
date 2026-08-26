"""Execute a controlled experiment matrix through injected GAIEP boundaries."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from .artifact import normalize_artifact
from .evaluation import EvaluationResult
from .evidence_store import GreenMemoryStore
from .experiment import ExperimentArm, ExperimentPlan
from .rollout import RolloutRunner
from .task_factory import EngineeringTask
from .trajectory import TrajectoryRecord


@dataclass(frozen=True)
class ExperimentTrial:
    task_id: str
    arm: ExperimentArm
    trajectory: TrajectoryRecord


class ExperimentRunner:
    """Run model/scaffold arms without owning routing or promotion decisions."""

    def __init__(
        self,
        rollout_factory: Callable[[ExperimentArm], RolloutRunner],
        evaluate: Callable[[EngineeringTask, object], EvaluationResult],
        evidence_store: GreenMemoryStore | None = None,
    ) -> None:
        self._rollout_factory = rollout_factory
        self._evaluate = evaluate
        self._evidence_store = evidence_store

    def run(self, plan: ExperimentPlan, tasks: Iterable[EngineeringTask]) -> list[ExperimentTrial]:
        task_map = {task.task_id: task for task in tasks}
        trials: list[ExperimentTrial] = []
        for task_id in plan.task_ids:
            task = task_map[task_id]
            for arm in plan.arms:
                rollout = self._rollout_factory(arm).run(task)
                artifact = normalize_artifact(rollout.artifact)
                evaluation = self._evaluate(task, artifact)
                normalized_rollout = rollout.__class__(
                    task_id=rollout.task_id,
                    artifact=artifact,
                    model_name=rollout.model_name,
                    scaffold_name=rollout.scaffold_name,
                    endpoint_model=rollout.endpoint_model,
                    latency_s=rollout.latency_s,
                    usage=rollout.usage,
                    provenance=rollout.provenance,
                )
                trajectory = TrajectoryRecord.from_results(normalized_rollout, evaluation)
                if self._evidence_store is not None:
                    self._evidence_store.append(trajectory)
                trials.append(
                    ExperimentTrial(
                        task_id=task_id,
                        arm=arm,
                        trajectory=trajectory,
                    )
                )
        return trials
