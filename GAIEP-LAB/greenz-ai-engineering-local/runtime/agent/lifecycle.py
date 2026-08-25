"""AgentRun lifecycle transition rules."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from runtime.agent.contracts import AgentRun, RunStatus

_ALLOWED_TRANSITIONS: dict[RunStatus, frozenset[RunStatus]] = {
    RunStatus.CREATED: frozenset({RunStatus.RUNNING, RunStatus.CANCELLED}),
    RunStatus.RUNNING: frozenset({
        RunStatus.WAITING,
        RunStatus.SUCCEEDED,
        RunStatus.FAILED,
        RunStatus.CANCELLED,
        RunStatus.TIMED_OUT,
        RunStatus.BLOCKED,
    }),
    RunStatus.WAITING: frozenset({RunStatus.RUNNING, RunStatus.CANCELLED, RunStatus.TIMED_OUT}),
    RunStatus.SUCCEEDED: frozenset(),
    RunStatus.FAILED: frozenset(),
    RunStatus.CANCELLED: frozenset(),
    RunStatus.TIMED_OUT: frozenset(),
    RunStatus.BLOCKED: frozenset(),
}
_TERMINAL = frozenset({
    RunStatus.SUCCEEDED,
    RunStatus.FAILED,
    RunStatus.CANCELLED,
    RunStatus.TIMED_OUT,
    RunStatus.BLOCKED,
})


class LifecycleError(ValueError):
    """Raised when an AgentRun lifecycle transition is invalid."""


def transition_run(run: AgentRun, status: RunStatus, *, at: datetime) -> AgentRun:
    if status not in _ALLOWED_TRANSITIONS[run.status]:
        raise LifecycleError(f"invalid AgentRun transition: {run.status} -> {status}")
    finished_at = at if status in _TERMINAL else None
    return replace(run, status=status, finished_at=finished_at)
