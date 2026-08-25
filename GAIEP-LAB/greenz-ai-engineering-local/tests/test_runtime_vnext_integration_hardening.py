"""Integration-hardening tests for Runtime VNext lab contracts."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from runtime.agent.contracts import (
    Action,
    ActionType,
    AuthorityScope,
    AuthorizationDecision,
    Capability,
    CapabilityRegistry,
    Decision,
    ModelCompletionEvidence,
    Observation,
    ObservationType,
)
from runtime.agent.events import RuntimeEventError, RuntimeEventType, validate_event_trace
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
from runtime.subagents.contracts import SubagentBoundary, SubagentValidationError

_NOW = datetime(2026, 8, 25, 12, 0, tzinfo=UTC)


def _registry() -> CapabilityRegistry:
    return CapabilityRegistry((
        Capability(
            capability_id="model.gateway",
            action_types=(ActionType.MODEL_REQUEST,),
            resource_patterns=("gateway/**",),
            requires_evidence=True,
        ),
        Capability(
            capability_id="dev.files",
            action_types=(ActionType.FILE_READ, ActionType.FILE_WRITE),
            resource_patterns=("src/**",),
            requires_evidence=True,
        ),
    ))


def _context(*, budget: RuntimeBudget | None = None) -> PolicyAuthorizationContext:
    return PolicyAuthorizationContext(
        registry=_registry(),
        authority=AuthorityScope(
            scope_id="auth",
            capability_ids=("dev.files", "model.gateway"),
            readable_roots=("gateway", "src"),
            writable_roots=("src",),
            executable_commands=(),
            token_budget=200,
        ),
        workspace=WorkspaceScope(
            workspace_id="ws",
            root="repo",
            readable_roots=("gateway", "src"),
            writable_roots=("src",),
        ),
        budget=budget or RuntimeBudget(action_limit=3, token_limit=200, child_budget_limit=50),
        task_policy=TaskPolicy(
            policy_id="task",
            allowed_capability_ids=("dev.files", "model.gateway"),
            allowed_action_types=(
                ActionType.FILE_READ,
                ActionType.FILE_WRITE,
                ActionType.MODEL_REQUEST,
            ),
        ),
        skill_manifest=SkillManifest(
            manifest_id="skills",
            allowed_capability_ids=("dev.files", "model.gateway"),
        ),
        global_policy=GlobalPolicy(policy_id="global"),
        policy_version="policy-v1",
    )


def _model_action(action_id: str = "model-1") -> Action:
    return Action(
        action_id=action_id,
        run_id="run-1",
        action_type=ActionType.MODEL_REQUEST,
        capability_id="model.gateway",
        resource="gateway/coding",
        requested_at=_NOW,
        payload_ref="prompt-ref-1",
    )


def test_authorized_gateway_execution_joins_runtime_event_to_model_provenance() -> None:
    calls: list[str] = []

    def gateway_executor(action: Action) -> Observation:
        calls.append(action.action_id)
        evidence = ModelCompletionEvidence(
            response_log_id="RL-1",
            execution_id="exec-1",
            context_id="ctx-1",
            context_hash="ctx-hash",
            artifact_ref="artifacts/RL-1.txt",
        )
        return Observation(
            observation_id="obs-1",
            run_id=action.run_id,
            action_id=action.action_id,
            observation_type=ObservationType.MODEL_COMPLETED,
            occurred_at=_NOW,
            outcome="success",
            artifact_refs=(evidence.artifact_ref,),
            evidence_refs=(evidence.response_log_id, evidence.execution_id),
            model_evidence=evidence,
        )

    action = _model_action()
    decision = authorize_with_policy(action, _context())
    runtime = LocalRuntime(gateway_executor)
    observation = runtime.execute(action, decision)

    assert calls == ["model-1"]
    assert observation.model_evidence is not None
    assert observation.run_id == runtime.events[-1].run_id == "run-1"
    assert observation.model_evidence.execution_id in observation.evidence_refs
    assert observation.model_evidence.artifact_ref in runtime.events[-1].payload_refs
    validate_event_trace(tuple(runtime.events))


def test_action_denied_produces_no_gateway_or_provider_invocation() -> None:
    def gateway_executor(_action: Action) -> Observation:
        raise AssertionError("denied action reached provider")

    action = _model_action()
    decision = AuthorizationDecision(
        decision=Decision.DENY,
        reason="global_policy_denied",
        action_id=action.action_id,
        capability_id=action.capability_id,
    )
    runtime = LocalRuntime(gateway_executor)
    observation = runtime.execute(action, decision)

    assert observation.outcome == "denied"
    assert runtime.executed_actions == []
    assert runtime.events[-1].event_type is RuntimeEventType.ACTION_DENIED
    validate_event_trace(tuple(runtime.events))


def test_gateway_failure_does_not_emit_action_executed_or_observation_produced() -> None:
    def gateway_executor(_action: Action) -> Observation:
        raise RuntimeError("provider unavailable")

    action = _model_action()
    runtime = LocalRuntime(gateway_executor)
    with pytest.raises(RuntimeError):
        runtime.execute(action, authorize_with_policy(action, _context()))

    event_types = tuple(event.event_type for event in runtime.events)
    assert RuntimeEventType.ACTION_FAILED in event_types
    assert RuntimeEventType.ACTION_EXECUTED not in event_types
    assert RuntimeEventType.OBSERVATION_PRODUCED not in event_types


def test_shutdown_records_failure_without_orphaned_execution_state() -> None:
    def gateway_executor(_action: Action) -> Observation:
        raise AssertionError("shutdown runtime reached provider")

    action = _model_action()
    runtime = LocalRuntime(gateway_executor)
    runtime.shutdown()

    with pytest.raises(RuntimeError, match="shut down"):
        runtime.execute(action, authorize_with_policy(action, _context()))

    event_types = tuple(event.event_type for event in runtime.events)
    assert event_types[-1] is RuntimeEventType.ACTION_FAILED
    failure_payload = runtime.events[-1].payload
    assert failure_payload is not None
    assert failure_payload["failure_class"] == "RuntimeShutdown"
    assert RuntimeEventType.ACTION_EXECUTED not in event_types
    assert RuntimeEventType.OBSERVATION_PRODUCED not in event_types
    assert runtime.executed_actions == []
    validate_event_trace(tuple(runtime.events))


def test_large_model_outputs_must_use_artifact_refs_not_event_payload_duplication() -> None:
    with pytest.raises(RuntimeEventError, match="artifact_ref"):
        from runtime.agent.events import RuntimeEvent

        RuntimeEvent(
            event_id="evt-large",
            run_id="run-1",
            event_type=RuntimeEventType.OBSERVATION_PRODUCED,
            timestamp=_NOW,
            payload={"model_output": "x" * 4097},
        )


def test_runtime_budget_and_workspace_are_enforced_before_execution() -> None:
    action = Action(
        action_id="write-1",
        run_id="run-1",
        action_type=ActionType.FILE_WRITE,
        capability_id="dev.files",
        resource="src/a.py",
        requested_at=_NOW,
    )
    budget_denied = authorize_with_policy(
        action, _context(budget=RuntimeBudget(action_limit=1, actions_used=1, token_limit=10))
    )
    assert budget_denied.decision is Decision.DENY
    assert budget_denied.reason == "budget_denied"

    outside_workspace = Action(
        action_id="write-2",
        run_id="run-1",
        action_type=ActionType.FILE_WRITE,
        capability_id="dev.files",
        resource="tests/a.py",
        requested_at=_NOW,
    )
    workspace_denied = authorize_with_policy(outside_workspace, _context())
    assert workspace_denied.decision is Decision.DENY
    assert workspace_denied.reason in {"capability_denied", "workspace_denied"}


def test_parent_child_authority_runtime_and_budget_escalation_are_rejected() -> None:
    parent = AuthorityScope(
        scope_id="parent",
        capability_ids=("dev.files",),
        readable_roots=("src",),
        writable_roots=("src",),
        executable_commands=(),
        network_allowed=False,
        max_child_runs=1,
        max_depth=1,
        token_budget=100,
    )
    child = AuthorityScope(
        scope_id="child",
        capability_ids=("dev.files", "model.gateway"),
        readable_roots=("src",),
        writable_roots=("src",),
        executable_commands=(),
        network_allowed=False,
        max_child_runs=0,
        max_depth=0,
        token_budget=50,
    )

    with pytest.raises(SubagentValidationError, match="capabilities"):
        SubagentBoundary(
            parent_authority=parent,
            child_authority=child,
            parent_tool_ids=("read",),
            child_tool_ids=("read",),
            parent_context_refs=("ctx",),
            child_context_refs=("ctx",),
            parent_budget_tokens=100,
            child_budget_tokens=50,
        )

    with pytest.raises(SubagentValidationError, match="budget"):
        SubagentBoundary(
            parent_authority=parent,
            child_authority=AuthorityScope(
                scope_id="child",
                capability_ids=("dev.files",),
                readable_roots=("src",),
                writable_roots=("src",),
                token_budget=50,
            ),
            parent_tool_ids=("read",),
            child_tool_ids=("read",),
            parent_context_refs=("ctx",),
            child_context_refs=("ctx",),
            parent_budget_tokens=100,
            child_budget_tokens=101,
        )
