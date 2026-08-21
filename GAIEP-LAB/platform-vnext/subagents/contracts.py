from dataclasses import dataclass
from enum import StrEnum

from ..runtime.contracts import TaskPolicy, WorkspaceScope


class SubagentStatus(StrEnum):
    REQUESTED = "REQUESTED"
    AUTHORIZED = "AUTHORIZED"
    RUNNING = "RUNNING"
    CHECKPOINTED = "CHECKPOINTED"
    VALIDATING = "VALIDATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True)
class SubagentRequest:
    parent_run_id: str
    task_ref: str
    skill_ref: str
    workspace_scope: WorkspaceScope
    task_policy: TaskPolicy
    model_policy_ref: str
    token_budget: int
    max_steps: int
    timeout_seconds: int
    depth: int = 1

    def __post_init__(self) -> None:
        if not self.parent_run_id.strip() or not self.task_ref.strip():
            raise ValueError("parent_run_id and task_ref cannot be empty")
        if self.depth < 1:
            raise ValueError("subagent depth must be >= 1")
        if min(self.token_budget, self.max_steps, self.timeout_seconds) < 1:
            raise ValueError("subagent resource budgets must be positive")
        if self.task_policy.allow_subagents:
            raise ValueError("child task policy cannot enable recursive subagents")


@dataclass(frozen=True)
class SubagentHandle:
    subagent_id: str
    parent_run_id: str
    task_ref: str
    status: SubagentStatus
    depth: int


@dataclass(frozen=True)
class SubagentResult:
    subagent_id: str
    status: SubagentStatus
    artifact_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    validation_refs: tuple[str, ...] = ()
    failure_refs: tuple[str, ...] = ()
    resource_usage_ref: str | None = None
