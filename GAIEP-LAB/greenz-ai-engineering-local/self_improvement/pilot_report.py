"""Summarize pilot trajectories without inspecting candidate source."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

from .pilot_runner import PilotTrialResult


@dataclass(frozen=True)
class ArmSummary:
    model_name: str
    scaffold_name: str
    trials: int
    passes: int
    pass_rate: float
    mean_reward: float


def summarize(trials: Iterable[PilotTrialResult]) -> list[ArmSummary]:
    groups: dict[tuple[str, str], list[PilotTrialResult]] = defaultdict(list)
    for trial in trials:
        groups[(trial.arm.model_name, trial.arm.scaffold_name)].append(trial)

    summaries: list[ArmSummary] = []
    for (model, scaffold), group in sorted(groups.items()):
        passes = sum(trial.trajectory.passed for trial in group)
        summaries.append(
            ArmSummary(
                model_name=model,
                scaffold_name=scaffold,
                trials=len(group),
                passes=passes,
                pass_rate=passes / len(group),
                mean_reward=sum(t.trajectory.reward for t in group) / len(group),
            )
        )
    return summaries


def to_markdown(trials: Iterable[PilotTrialResult]) -> str:
    rows = summarize(trials)
    lines = [
        "# GAIEP Pilot Report",
        "",
        "| Model | Scaffold | Trials | Passes | Pass rate | Mean reward |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row.model_name} | {row.scaffold_name} | {row.trials} | "
            f"{row.passes} | {row.pass_rate:.1%} | {row.mean_reward:.3f} |"
        )
    return "\n".join(lines) + "\n"
