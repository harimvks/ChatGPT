"""Resumable execution coordinator for the GAIEP pilot."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime, timezone

from .artifact import normalize_artifact
from .evaluation import EvaluationResult
from .experiment import ExperimentArm
from .pilot_manifest import PilotManifest
from .rollout import RolloutResult, RolloutRunner
from .task_factory import EngineeringTask
from .trajectory import TrajectoryRecord
from .trajectory_store import TrajectoryStore


@dataclass(frozen=True)
class PilotTrialResult:
    task_id: str
    arm: ExperimentArm
    started_at: str
    finished_at: str
    trajectory: TrajectoryRecord


class PilotRunner:
    """Execute every manifest cell and continue after individual trial failures."""

    def __init__(
        self,
        rollout_factory: Callable[[ExperimentArm], RolloutRunner],
        evaluate: Callable[[EngineeringTask, object], EvaluationResult],
        store: TrajectoryStore,
    ) -> None:
        self._rollout_factory = rollout_factory
        self._evaluate = evaluate
        self._store = store

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def run(
        self,
        manifest: PilotManifest,
        tasks: Iterable[EngineeringTask],
        *,
        completed_keys: set[tuple[str, str, str]] | None = None,
    ) -> list[PilotTrialResult]:
        task_map = {task.task_id: task for task in tasks}
        missing = [task_id for task_id in manifest.task_ids if task_id not in task_map]
        if missing:
            raise ValueError(f"manifest tasks unavailable: {missing}")

        completed = completed_keys or set()
        results: list[PilotTrialResult] = []
        for task_id in manifest.task_ids:
            task = task_map[task_id]
            for arm in manifest.arms:
                key = (task_id, arm.model_name, arm.scaffold_name)
                if key in completed:
                    continue
                started = self._now()
                try:
                    rollout = self._rollout_factory(arm).run(task)
                    artifact = normalize_artifact(rollout.artifact)
                    evaluation = self._evaluate(task, artifact)
                    trajectory = TrajectoryRecord.from_results(
                        RolloutResult(
                            task_id=rollout.task_id,
                            artifact=artifact,
                            model_name=rollout.model_name,
                            scaffold_name=rollout.scaffold_name,
                            endpoint_model=rollout.endpoint_model,
                            latency_s=rollout.latency_s,
                            usage=rollout.usage,
                        ),
                        evaluation,
                    )
                except Exception as exc:  # noqa: BLE001
                    trajectory = TrajectoryRecord(
                        task_id=task_id,
                        model_name=arm.model_name,
                        scaffold_name=arm.scaffold_name,
                        artifact_files=(),
                        passed=False,
                        reward=0.0,
                        checks=(("runner_exception", False),),
                        failure_class=type(exc).__name__,
                    )
                finished = self._now()
                self._store.append(trajectory)
                results.append(
                    PilotTrialResult(
                        task_id=task_id,
                        arm=arm,
                        started_at=started,
                        finished_at=finished,
                        trajectory=trajectory,
                    )
                )
        return results
