"""Workspace, budget and policy intersection for GAIEP authorization."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from enum import StrEnum

from runtime.agent.authorization import authorize_action
from runtime.agent.contracts import (
    Action,
    ActionType,
    AuthorityScope,
    AuthorizationDecision,
    CapabilityRegistry,
    Decision,
    normalize_path,
)


class AuthorizationReason(StrEnum):
    AUTHORIZED = "authorized"
    CAPABILITY_DENIED = "capability_denied"
    TASK_POLICY_DENIED = "task_policy_denied"
    SKILL_DENIED = "skill_denied"
    WORKSPACE_DENIED = "workspace_denied"
    GLOBAL_POLICY_DENIED = "global_policy_denied"
    BUDGET_DENIED = "budget_denied"


def _require_utc(label: str, value: datetime) -> None:
    if value.utcoffset() != timedelta(0):
        raise ValueError(f"{label} must be timezone-aware UTC")


@dataclass(frozen=True)
class RuntimeBudget:
    action_limit: int
    actions_used: int = 0
    token_limit: int = 0
    tokens_used: int = 0
    child_budget_limit: int = 0
    child_budget_allocated: int = 0

    def __post_init__(self) -> None:
        values = (
            self.action_limit, self.actions_used, self.token_limit, self.tokens_used,
            self.child_budget_limit, self.child_budget_allocated,
        )
        if any(value < 0 for value in values):
            raise ValueError("budget values cannot be negative")
        if self.actions_used > self.action_limit:
            raise ValueError("actions_used cannot exceed action_limit")
        if self.tokens_used > self.token_limit:
            raise ValueError("tokens_used cannot exceed token_limit")
        if self.child_budget_allocated > self.child_budget_limit:
            raise ValueError("child allocation cannot exceed child budget")

    def can_consume(self, *, actions: int = 1, tokens: int = 0) -> bool:
        return (
            self.actions_used + actions <= self.action_limit
            and self.tokens_used + tokens <= self.token_limit
        )

    def consume(self, *, actions: int = 1, tokens: int = 0) -> RuntimeBudget:
        if not self.can_consume(actions=actions, tokens=tokens):
            raise ValueError("budget exceeded")
        return replace(
            self,
            actions_used=self.actions_used + actions,
            tokens_used=self.tokens_used + tokens,
        )

    def allocate_child(self, tokens: int) -> RuntimeBudget:
        if tokens < 0 or self.child_budget_allocated + tokens > self.child_budget_limit:
            raise ValueError("child budget exceeds parent remaining budget")
        return replace(self, child_budget_allocated=self.child_budget_allocated + tokens)


@dataclass(frozen=True)
class WorkspaceScope:
    workspace_id: str
    root: str
    readable_roots: tuple[str, ...]
    writable_roots: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "root", normalize_path(self.root))
        object.__setattr__(
            self,
            "readable_roots",
            tuple(sorted(normalize_path(path) for path in self.readable_roots)),
        )
        object.__setattr__(
            self,
            "writable_roots",
            tuple(sorted(normalize_path(path) for path in self.writable_roots)),
        )

    def allows(self, action: Action) -> bool:
        roots = (
            self.writable_roots
            if action.action_type is ActionType.FILE_WRITE
            else self.readable_roots
        )
        return any(
            action.resource == root or action.resource.startswith(root + "/")
            for root in roots
        )


@dataclass(frozen=True)
class TaskPolicy:
    policy_id: str
    allowed_capability_ids: tuple[str, ...]
    allowed_action_types: tuple[ActionType, ...]


@dataclass(frozen=True)
class SkillManifest:
    manifest_id: str
    allowed_capability_ids: tuple[str, ...]
    skill_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class GlobalPolicy:
    policy_id: str
    denied_capability_ids: tuple[str, ...] = ()
    denied_action_types: tuple[ActionType, ...] = ()


@dataclass(frozen=True)
class PolicyAuthorizationContext:
    registry: CapabilityRegistry
    authority: AuthorityScope
    workspace: WorkspaceScope
    budget: RuntimeBudget
    task_policy: TaskPolicy
    skill_manifest: SkillManifest
    global_policy: GlobalPolicy
    policy_version: str


def _decision(
    action: Action, decision: Decision, reason: AuthorizationReason
) -> AuthorizationDecision:
    return AuthorizationDecision(
        decision=decision,
        reason=reason.value,
        action_id=action.action_id,
        capability_id=action.capability_id,
    )


def authorize_with_policy(
    action: Action, context: PolicyAuthorizationContext
) -> AuthorizationDecision:
    base = authorize_action(registry=context.registry, authority=context.authority, action=action)
    if base.decision is Decision.DENY:
        return _decision(action, Decision.DENY, AuthorizationReason.CAPABILITY_DENIED)
    if action.capability_id not in context.task_policy.allowed_capability_ids:
        return _decision(action, Decision.DENY, AuthorizationReason.TASK_POLICY_DENIED)
    if action.action_type not in context.task_policy.allowed_action_types:
        return _decision(action, Decision.DENY, AuthorizationReason.TASK_POLICY_DENIED)
    if action.capability_id not in context.skill_manifest.allowed_capability_ids:
        return _decision(action, Decision.DENY, AuthorizationReason.SKILL_DENIED)
    if action.capability_id in context.global_policy.denied_capability_ids:
        return _decision(action, Decision.DENY, AuthorizationReason.GLOBAL_POLICY_DENIED)
    if action.action_type in context.global_policy.denied_action_types:
        return _decision(action, Decision.DENY, AuthorizationReason.GLOBAL_POLICY_DENIED)
    if not context.workspace.allows(action):
        return _decision(action, Decision.DENY, AuthorizationReason.WORKSPACE_DENIED)
    if not context.budget.can_consume(actions=1):
        return _decision(action, Decision.DENY, AuthorizationReason.BUDGET_DENIED)
    return _decision(action, Decision.ALLOW, AuthorizationReason.AUTHORIZED)
