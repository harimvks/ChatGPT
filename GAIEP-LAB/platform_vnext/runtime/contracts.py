from dataclasses import dataclass, field
from enum import StrEnum
from datetime import datetime


class RunStatus(StrEnum):
    REQUESTED = "REQUESTED"
    PLANNED = "PLANNED"
    AUTHORIZED = "AUTHORIZED"
    CONTEXT_READY = "CONTEXT_READY"
    SKILL_READY = "SKILL_READY"
    EXECUTING = "EXECUTING"
    VALIDATING = "VALIDATING"
    EVIDENCE_READY = "EVIDENCE_READY"
    GOVERNANCE = "GOVERNANCE"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    ESCALATED = "ESCALATED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True)
class WorkspaceScope:
    root: str
    mode: str
    allowed_paths: tuple[str, ...] = ()
    forbidden_paths: tuple[str, ...] = ()


@dataclass(frozen=True)
class TaskPolicy:
    task_type: str
    allowed_tools: frozenset[str] = frozenset()
    allowed_skills: frozenset[str] = frozenset()
    allow_write: bool = False
    allow_network: bool = False
    allow_subagents: bool = False
    approval_required: bool = False


@dataclass(frozen=True)
class ModelPolicy:
    capability_tag: str
    eligible_deployments: tuple[str, ...] = ()
    require_certification: bool = True
    allow_failover: bool = True


@dataclass(frozen=True)
class AgentRun:
    run_id: str
    task_ref: str
    workspace_scope: WorkspaceScope
    task_policy: TaskPolicy
    model_policy: ModelPolicy
    status: RunStatus = RunStatus.REQUESTED
    parent_run_id: str | None = None
    child_budget_tokens: int = 0
    child_budget_count: int = 0
    max_subagent_depth: int = 0
    metadata: dict[str, str] = field(default_factory=dict)
    created_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.run_id.strip() or not self.task_ref.strip():
            raise ValueError("run_id and task_ref cannot be empty")
        if min(self.child_budget_tokens, self.child_budget_count, self.max_subagent_depth) < 0:
            raise ValueError("child budgets/depth cannot be negative")


def derive_child_policy(parent: AgentRun, *, allow_write: bool = False) -> TaskPolicy:
    return TaskPolicy(
        task_type=parent.task_policy.task_type,
        allowed_tools=parent.task_policy.allowed_tools,
        allowed_skills=parent.task_policy.allowed_skills,
        allow_write=allow_write and parent.task_policy.allow_write,
        allow_network=parent.task_policy.allow_network,
        allow_subagents=False,
        approval_required=parent.task_policy.approval_required,
    )
