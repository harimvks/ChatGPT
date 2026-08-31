"""Controlled experiment definitions for small-model GAIEP research."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExperimentArm:
    model_name: str
    scaffold_name: str


@dataclass(frozen=True)
class ExperimentPlan:
    name: str
    task_ids: tuple[str, ...]
    arms: tuple[ExperimentArm, ...]

    def matrix_size(self) -> int:
        return len(self.task_ids) * len(self.arms)


def build_small_model_pilot(task_ids: list[str]) -> ExperimentPlan:
    """Create a reproducible pilot without hard-coding a provider/model endpoint."""
    arms = (
        ExperimentArm("small-python-coder", "inspect-plan-implement-test"),
        ExperimentArm("small-python-coder", "inspect-implement-test"),
        ExperimentArm("qwen3.6-27b", "inspect-plan-implement-test"),
        ExperimentArm("qwen3.6-27b", "inspect-implement-test"),
    )
    return ExperimentPlan(
        name="gaiep-small-python-pilot-v0",
        task_ids=tuple(task_ids),
        arms=arms,
    )
