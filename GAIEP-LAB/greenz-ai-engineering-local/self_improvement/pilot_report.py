"""Summarize pilot trajectories without inspecting candidate source."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass

from .pilot_runner import PilotTrialResult


@dataclass(frozen=True)
class ArmSummary:
    model_name: str
    scaffold_name: str
    trials: int
    passes: int
    pass_rate: float
    mean_reward: float
    mean_latency_s: float | None


def summarize(trials: Iterable[PilotTrialResult]) -> list[ArmSummary]:
    groups: dict[tuple[str, str], list[PilotTrialResult]] = defaultdict(list)
    for trial in trials:
        groups[(trial.arm.model_name, trial.arm.scaffold_name)].append(trial)

    summaries: list[ArmSummary] = []
    for (model, scaffold), group in sorted(groups.items()):
        passes = sum(trial.trajectory.passed for trial in group)
        latencies = [
            trial.trajectory.latency_s
            for trial in group
            if trial.trajectory.latency_s is not None
        ]
        summaries.append(
            ArmSummary(
                model_name=model,
                scaffold_name=scaffold,
                trials=len(group),
                passes=passes,
                pass_rate=passes / len(group),
                mean_reward=sum(t.trajectory.reward for t in group) / len(group),
                mean_latency_s=sum(latencies) / len(latencies) if latencies else None,
            )
        )
    return summaries


def failure_classes(trials: Iterable[PilotTrialResult]) -> Counter[str]:
    return Counter(
        trial.trajectory.failure_class or "passed"
        for trial in trials
    )


def to_markdown(trials: Iterable[PilotTrialResult]) -> str:
    trial_list = list(trials)
    rows = summarize(trial_list)
    failures = failure_classes(trial_list)
    lines = [
        "# GAIEP Pilot Report",
        "",
        f"Trials completed: {len(trial_list)}",
        "",
        "| Model | Scaffold | Trials | Passes | Pass rate | Mean reward | Mean latency s |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        latency = "n/a" if row.mean_latency_s is None else f"{row.mean_latency_s:.3f}"
        lines.append(
            f"| {row.model_name} | {row.scaffold_name} | {row.trials} | "
            f"{row.passes} | {row.pass_rate:.1%} | {row.mean_reward:.3f} | {latency} |"
        )
    lines.extend(["", "## Failure Classes", ""])
    for name, count in sorted(failures.items()):
        lines.append(f"- {name}: {count}")
    return "\n".join(lines) + "\n"
