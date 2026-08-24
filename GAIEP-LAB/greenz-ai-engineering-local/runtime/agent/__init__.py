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
    "ObservationType",
    "RunStatus",
    "authorize_action",
    "child_authority_decision",
]
