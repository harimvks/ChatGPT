"""Runtime boundary protocol for GAIEP Agent Core.

This is intentionally a contract, not an implementation loop.
"""

from __future__ import annotations

from typing import Protocol

from runtime.agent.contracts import Action, AgentRun, AuthorizationDecision, Observation


class Runtime(Protocol):
    """Minimal boundary an Agent Core can rely on without owning execution machinery."""

    def start_run(self, run: AgentRun) -> AgentRun:
        """Register or transition a run into execution."""
        ...

    def authorize(self, action: Action) -> AuthorizationDecision:
        """Authorize an action before execution."""
        ...

    def observe(self, observation: Observation) -> None:
        """Record an observable result or failure."""
        ...
