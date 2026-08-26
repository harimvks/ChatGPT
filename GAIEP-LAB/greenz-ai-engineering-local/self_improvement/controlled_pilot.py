"""Reproducible, non-production fixture for the GAIEP 3x4 pilot matrix."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .evaluation import EvaluationResult
from .experiment import ExperimentArm, ExperimentPlan, build_small_model_pilot
from .provenance import RunProvenance
from .rollout import RolloutResult, RolloutRunner
from .task_factory import EngineeringTask, TaskFactory


@dataclass(frozen=True)
class ControlledPilotSpec:
    """Frozen task/arm definition for deterministic integration tests."""

    tasks: tuple[EngineeringTask, ...]
    plan: ExperimentPlan


def build_controlled_pilot() -> ControlledPilotSpec:
    """Return three representative tasks and the existing four pilot arms."""
    factory = TaskFactory()
    tasks = (
        factory.from_seed(
            task_type="implementation",
            title="Implement bounded parser helper",
            objective="Implement a deterministic Python parser helper with explicit validation.",
            acceptance=("pytest", "pyright"),
            constraints=("no external dependencies",),
            difficulty=2,
            source="controlled_pilot_v1",
        ),
        factory.from_seed(
            task_type="testing",
            title="Add regression tests for parser helper",
            objective="Add focused pytest coverage for valid, invalid, and boundary inputs.",
            acceptance=("pytest", "ruff"),
            constraints=("tests only",),
            difficulty=2,
            source="controlled_pilot_v1",
        ),
        factory.from_seed(
            task_type="refactor",
            title="Refactor validation path",
            objective="Refactor a small validation path while preserving observable behavior.",
            acceptance=("pytest", "pyright", "ruff"),
            constraints=("behavior preserving",),
            difficulty=3,
            source="controlled_pilot_v1",
        ),
    )
    plan = build_small_model_pilot([task.task_id for task in tasks])
    return ControlledPilotSpec(tasks=tasks, plan=plan)


class FixtureRolloutRunner:
    """Deterministic rollout fixture; never connects to a real model."""

    def __init__(
        self,
        arm: ExperimentArm,
        *,
        failure_selector: Callable[[EngineeringTask, ExperimentArm], bool],
    ) -> None:
        self._arm = arm
        self._failure_selector = failure_selector

    def run(self, task: EngineeringTask) -> RolloutResult:
        failed = self._failure_selector(task, self._arm)
        marker = "fixture_failure" if failed else "validated"
        return RolloutResult(
            task_id=task.task_id,
            artifact={"files": {"candidate.py": f"# {marker}\nvalue = 1\n"}},
            model_name=self._arm.model_name,
            scaffold_name=self._arm.scaffold_name,
            endpoint_model=f"fixture/{self._arm.model_name}",
            provenance=RunProvenance(run_id=f"fixture-{task.task_id}-{self._arm.model_name}"),
        )


def fixture_rollout_factory(
    *, failure_selector: Callable[[EngineeringTask, ExperimentArm], bool],
) -> Callable[[ExperimentArm], RolloutRunner]:
    """Build an injected rollout factory for tests; no model/provider access."""
    return lambda arm: FixtureRolloutRunner(arm, failure_selector=failure_selector)


def fixture_evaluator(_task: EngineeringTask, artifact: object) -> EvaluationResult:
    """Evaluate the fixture using an external-style check boundary."""
    files = getattr(artifact, "files", {})
    failed = "fixture_failure" in files.get("candidate.py", "")
    return EvaluationResult(
        task_id=_task.task_id,
        passed=not failed,
        reward=0.0 if failed else 1.0,
        checks={"pytest": not failed},
        failure_class="test_failure" if failed else None,
    )
