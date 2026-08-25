"""Pure bounded subagent contracts.

Subagents are isolated child runs. They cannot expand authority, tools, context,
or budgets beyond the parent envelope.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from runtime.agent.authorization import child_authority_decision
from runtime.agent.contracts import AgentRun, AuthorityScope, Decision


class SubagentValidationError(ValueError):
    """Raised when a subagent boundary invariant is violated."""


def _require_non_empty(label: str, value: str) -> None:
    if not value.strip():
        raise SubagentValidationError(f"{label} cannot be empty")


def _require_utc(label: str, value: datetime) -> None:
    if value.utcoffset() != timedelta(0):
        raise SubagentValidationError(f"{label} must be timezone-aware UTC")


def _subset(label: str, child: tuple[str, ...], parent: tuple[str, ...]) -> None:
    if not set(child).issubset(parent):
        raise SubagentValidationError(f"child {label} exceeds parent {label}")


@dataclass(frozen=True)
class SubagentBoundary:
    parent_authority: AuthorityScope
    child_authority: AuthorityScope
    parent_tool_ids: tuple[str, ...]
    child_tool_ids: tuple[str, ...]
    parent_context_refs: tuple[str, ...]
    child_context_refs: tuple[str, ...]
    parent_budget_tokens: int
    child_budget_tokens: int

    def __post_init__(self) -> None:
        if self.parent_budget_tokens < 0 or self.child_budget_tokens < 0:
            raise SubagentValidationError("subagent budgets cannot be negative")
        if self.child_budget_tokens > self.parent_budget_tokens:
            raise SubagentValidationError("child budget exceeds parent budget")
        decision = child_authority_decision(self.parent_authority, self.child_authority)
        if decision.decision is not Decision.ALLOW:
            raise SubagentValidationError(decision.reason)
        _subset("tools", self.child_tool_ids, self.parent_tool_ids)
        _subset("context", self.child_context_refs, self.parent_context_refs)


@dataclass(frozen=True)
class SubagentHandle:
    handle_id: str
    parent_run_id: str
    child_run: AgentRun
    boundary: SubagentBoundary
    created_at: datetime
    checkpoint_ref: str | None = None

    def __post_init__(self) -> None:
        _require_non_empty("SubagentHandle.handle_id", self.handle_id)
        _require_non_empty("SubagentHandle.parent_run_id", self.parent_run_id)
        _require_utc("SubagentHandle.created_at", self.created_at)
        if self.child_run.parent_run_id != self.parent_run_id:
            raise SubagentValidationError("child AgentRun must reference parent run")
        if self.checkpoint_ref is not None:
            _require_non_empty("SubagentHandle.checkpoint_ref", self.checkpoint_ref)


def validate_subagent_boundary(boundary: SubagentBoundary) -> SubagentBoundary:
    return boundary
