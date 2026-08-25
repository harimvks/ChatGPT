"""Concrete GAIEP pilot execution coordinator.

This module binds the research framework to local evidence when supplied, while
failing closed if the actual Gateway ModelCall or certification corpus is absent.
It does not own model routing and does not fabricate pilot results.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from .artifact import CandidateArtifact
from .corpus_adapter import load_certifications
from .experiment import ExperimentArm, build_small_model_pilot
from .experiment_config import ModelBinding, load_model_binding
from .gateway_rollout import GatewayResearchRollout, ModelCall
from .pilot_manifest import PilotManifest
from .pilot_preflight import assert_preflight, check_required_environment
from .pilot_runner import PilotRunner, PilotTrialResult
from .pilot_task_selection import corpus_version_for_manifest, select_pilot_tasks
from .rollout import RolloutRunner
from .sandbox_evaluation import SandboxEvaluator
from .task_factory import EngineeringTask
from .trajectory_store import TrajectoryStore


@dataclass(frozen=True)
class PilotExecutionPlan:
    manifest: PilotManifest
    tasks: tuple[EngineeringTask, ...]
    model_bindings: tuple[ModelBinding, ...]
    source_case_ids: tuple[str, ...]


def build_execution_plan(certification_paths: Iterable[Path]) -> PilotExecutionPlan:
    records = load_certifications(certification_paths)
    selected = select_pilot_tasks(records)
    tasks = tuple(item.task for item in selected)
    plan = build_small_model_pilot([task.task_id for task in tasks])
    manifest = PilotManifest.from_plan(
        plan,
        corpus_version=corpus_version_for_manifest(selected),
        source_case_ids=tuple(item.source_case_id for item in selected),
    )
    checks = check_required_environment(tuple({arm.model_name for arm in manifest.arms}))
    assert_preflight(checks)
    bindings = tuple(
        load_model_binding(name) for name in sorted({arm.model_name for arm in manifest.arms})
    )
    return PilotExecutionPlan(
        manifest=manifest,
        tasks=tasks,
        model_bindings=bindings,
        source_case_ids=tuple(item.source_case_id for item in selected),
    )


def make_gateway_rollout_factory(
    *, model_call_factory: Callable[[ModelBinding], ModelCall], bindings: Iterable[ModelBinding]
) -> Callable[[ExperimentArm], RolloutRunner]:
    binding_map = {binding.logical_name: binding for binding in bindings}

    def factory(arm: ExperimentArm) -> RolloutRunner:
        model_name = arm.model_name
        scaffold_name = arm.scaffold_name
        binding = binding_map[model_name]
        return GatewayResearchRollout(
            model_call_factory(binding),
            model_name=model_name,
            endpoint_model=binding.endpoint_model,
            scaffold_name=scaffold_name,
        )

    return factory


def run_pilot(
    *,
    certification_paths: Iterable[Path],
    model_call_factory: Callable[[ModelBinding], ModelCall],
    evaluator: SandboxEvaluator,
    trajectory_path: Path,
) -> tuple[PilotExecutionPlan, tuple[PilotTrialResult, ...]]:
    execution_plan = build_execution_plan(certification_paths)
    store = TrajectoryStore(trajectory_path)
    runner = PilotRunner(
        make_gateway_rollout_factory(
            model_call_factory=model_call_factory,
            bindings=execution_plan.model_bindings,
        ),
        lambda task, artifact: evaluator.evaluate(task, cast(CandidateArtifact, artifact)).evaluation,
        store,
    )
    results = runner.run(
        execution_plan.manifest,
        execution_plan.tasks,
        completed_keys=store.completed_keys(),
    )
    return execution_plan, tuple(results)
