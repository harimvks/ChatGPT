"""Agent/runtime boundary contracts for the GAIEP lab snapshot."""

from runtime.agent.authorization import authorize_action, child_authority_decision
from runtime.agent.contracts import (
    Action,
    ActionType,
    AgentRun,
    AuthorityScope,
    AuthorizationDecision,
    Capability,
    CapabilityRegistry,
    Decision,
    ModelCompletionEvidence,
    Observation,
    ObservationType,
    RunStatus,
)
from runtime.agent.events import (
    RuntimeEvent,
    RuntimeEventError,
    RuntimeEventType,
    validate_event_trace,
)
from runtime.agent.lifecycle import LifecycleError, transition_run
from runtime.agent.local_runtime import LocalRuntime
from runtime.agent.policy import (
    GlobalPolicy,
    PolicyAuthorizationContext,
    RuntimeBudget,
    SkillManifest,
    TaskPolicy,
    WorkspaceScope,
    authorize_with_policy,
)

__all__ = [
    "Action",
    "ActionType",
    "AgentRun",
    "AuthorityScope",
    "AuthorizationDecision",
    "Capability",
    "CapabilityRegistry",
    "Decision",
    "ModelCompletionEvidence",
    "Observation",
    "GlobalPolicy",
    "LifecycleError",
    "LocalRuntime",
    "ObservationType",
    "PolicyAuthorizationContext",
    "RunStatus",
    "RuntimeBudget",
    "RuntimeEvent",
    "RuntimeEventError",
    "RuntimeEventType",
    "SkillManifest",
    "TaskPolicy",
    "WorkspaceScope",
    "authorize_action",
    "authorize_with_policy",
    "child_authority_decision",
    "transition_run",
    "validate_event_trace",
]
