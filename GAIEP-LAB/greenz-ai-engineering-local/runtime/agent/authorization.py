"""Deterministic authorization helpers for GAIEP runtime actions."""

from __future__ import annotations

from datetime import UTC, datetime
from fnmatch import fnmatchcase

from runtime.agent.contracts import (
    Action,
    ActionType,
    AuthorityScope,
    AuthorizationDecision,
    CapabilityRegistry,
    Decision,
)


def _decision(action: Action, decision: Decision, reason: str) -> AuthorizationDecision:
    return AuthorizationDecision(
        decision=decision,
        reason=reason,
        action_id=action.action_id,
        capability_id=action.capability_id,
    )


def authorize_action(
    *, registry: CapabilityRegistry, authority: AuthorityScope, action: Action
) -> AuthorizationDecision:
    """Authorize one action without side effects or hidden state."""
    capability = registry.get(action.capability_id)
    if capability is None:
        return _decision(action, Decision.DENY, "capability is not registered")
    if action.capability_id not in authority.capability_ids:
        return _decision(action, Decision.DENY, "capability is not in the authority scope")
    if action.action_type not in capability.action_types:
        return _decision(action, Decision.DENY, "action type is not allowed by capability")
    if not any(fnmatchcase(action.resource, pattern) for pattern in capability.resource_patterns):
        return _decision(action, Decision.DENY, "resource is outside capability patterns")
    return _decision(action, Decision.ALLOW, "authorized")


def child_authority_decision(
    parent: AuthorityScope, child: AuthorityScope
) -> AuthorizationDecision:
    """Verify ChildAuthority is a subset of ParentAuthority."""
    probe = Action(
        action_id=f"child-authority:{child.scope_id}",
        run_id=parent.scope_id,
        action_type=ActionType.CHILD_RUN,
        capability_id="child_authority",
        resource=child.scope_id,
        requested_at=datetime.now(UTC),
    )
    failures: list[str] = []
    if not set(child.capability_ids).issubset(parent.capability_ids):
        failures.append("capabilities")
    if not set(child.readable_roots).issubset(parent.readable_roots):
        failures.append("readable_roots")
    if not set(child.writable_roots).issubset(parent.writable_roots):
        failures.append("writable_roots")
    if not set(child.executable_commands).issubset(parent.executable_commands):
        failures.append("executable_commands")
    if child.network_allowed and not parent.network_allowed:
        failures.append("network")
    if child.max_child_runs > parent.max_child_runs:
        failures.append("max_child_runs")
    if child.max_depth > parent.max_depth:
        failures.append("max_depth")
    if child.token_budget > parent.token_budget:
        failures.append("token_budget")
    if failures:
        return AuthorizationDecision(
            decision=Decision.DENY,
            reason="child authority exceeds parent: " + ", ".join(sorted(failures)),
            action_id=probe.action_id,
            capability_id=probe.capability_id,
        )
    return AuthorizationDecision(
        decision=Decision.ALLOW,
        reason="child authority is subset of parent authority",
        action_id=probe.action_id,
        capability_id=probe.capability_id,
    )
