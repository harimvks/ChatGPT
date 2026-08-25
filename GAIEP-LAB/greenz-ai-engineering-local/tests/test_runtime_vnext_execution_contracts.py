"""Execution-boundary tests for the GAIEP/OpenHands Runtime VNext handoff."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from runtime.agent.contracts import (
    Action,
    ActionType,
    AgentRun,
    AuthorityScope,
    Capability,
    CapabilityRegistry,
    Decision,
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

_NOW = datetime(2026, 8, 25, 11, 0, tzinfo=UTC)


def _registry() -> CapabilityRegistry:
    return CapabilityRegistry((
        Capability(
            capability_id="engineering.read",
            action_types=(ActionType.FILE_READ,),
            resource_patterns=("src/**", "tests/**"),
            requires_evidence=True,
        ),
        Capability(
            capability_id="engineering.write",
            action_types=(ActionType.FILE_WRITE,),
            resource_patterns=("src/**", "tests/**"),
            requires_evidence=True,
        ),
    ))


def _context(*, budget: RuntimeBudget | None = None) -> PolicyAuthorizationContext:
    return PolicyAuthorizationContext(
        registry=_registry(),
        authority=AuthorityScope(
            scope_id="auth",
            capability_ids=("engineering.read", "engineering.write"),
            readable_roots=("src", "tests"),
            writable_roots=("src",),
            token_budget=100,
        ),
        workspace=WorkspaceScope(
            workspace_id="workspace",
            root="repo",
            readable_roots=("src", "tests"),
            writable_roots=("src",),
        ),
        budget=budget or RuntimeBudget(action_limit=2, token_limit=100, child_budget_limit=50),
        task_policy=TaskPolicy(
            policy_id="task",
            allowed_capability_ids=("engineering.read", "engineering.write"),
            allowed_action_types=(ActionType.FILE_READ, ActionType.FILE_WRITE),
        ),
        skill_manifest=SkillManifest(
            manifest_id="skills",
            allowed_capability_ids=("engineering.read", "engineering.write"),
        ),
        global_policy=GlobalPolicy(policy_id="global"),
        policy_version="policy-v1",
    )


def _action(action_type: ActionType = ActionType.FILE_WRITE, resource: str = "src/a.py") -> Action:
    return Action(
        action_id="act-1",
        run_id="run-1",
        action_type=action_type,
        capability_id=(
            "engineering.write" if action_type is ActionType.FILE_WRITE else "engineering.read"
        ),
        resource=resource,
        requested_at=_NOW,
    )


def test_lifecycle_rejects_invalid_and_terminal_transitions() -> None:
    run = AgentRun(
        run_id="run-1",
        task_id="TASK-1",
        capability="engineering.write",
        parent_run_id=None,
        authority_scope_id="auth",
        status=RunStatus.CREATED,
        started_at=_NOW,
    )
    running = transition_run(run, RunStatus.RUNNING, at=_NOW)
    done = transition_run(running, RunStatus.SUCCEEDED, at=_NOW)

    assert done.finished_at == _NOW
    with pytest.raises(LifecycleError):
        transition_run(done, RunStatus.RUNNING, at=_NOW)
    with pytest.raises(LifecycleError):
        transition_run(run, RunStatus.SUCCEEDED, at=_NOW)


def test_authorization_intersection_denies_policy_workspace_global_and_budget() -> None:
    assert authorize_with_policy(_action(), _context()).decision is Decision.ALLOW

    base_context = _context()
    task_denied = base_context.__class__(
        **{
            **base_context.__dict__,
            "task_policy": TaskPolicy(
                "task", ("engineering.read",), (ActionType.FILE_READ,)
            ),
        }
    )
    assert authorize_with_policy(_action(), task_denied).reason == "task_policy_denied"

    workspace_denied = _action(resource="tests/test_a.py")
    assert authorize_with_policy(workspace_denied, _context()).reason == "workspace_denied"

    base_context = _context()
    global_denied = base_context.__class__(
        **{
            **base_context.__dict__,
            "global_policy": GlobalPolicy("global", ("engineering.write",)),
        }
    )
    assert authorize_with_policy(_action(), global_denied).reason == "global_policy_denied"

    assert authorize_with_policy(
        _action(), _context(budget=RuntimeBudget(action_limit=1, actions_used=1, token_limit=1))
    ).reason == "budget_denied"


def test_budget_consumption_and_child_allocation_are_deterministic() -> None:
    budget = RuntimeBudget(action_limit=2, token_limit=10, child_budget_limit=5)

    assert budget.consume(actions=1, tokens=10).tokens_used == 10
    assert budget.allocate_child(5).child_budget_allocated == 5
    with pytest.raises(ValueError, match="budget exceeded"):
        budget.consume(actions=3)
    with pytest.raises(ValueError, match="child budget"):
        budget.allocate_child(6)


def test_event_trace_requires_authorization_before_execution_and_refs_large_payloads() -> None:
    requested = RuntimeEvent(
        "evt-1", "run-1", RuntimeEventType.ACTION_REQUESTED, _NOW, action_id="act-1"
    )
    authorized = RuntimeEvent(
        "evt-2",
        "run-1",
        RuntimeEventType.AUTHORIZATION_EVALUATED,
        _NOW,
        action_id="act-1",
        parent_event_id="evt-1",
        payload={"decision": "ALLOW", "reason": "authorized"},
    )
    executed = RuntimeEvent(
        "evt-3",
        "run-1",
        RuntimeEventType.ACTION_EXECUTED,
        _NOW,
        action_id="act-1",
        parent_event_id="evt-2",
    )

    validate_event_trace((requested, authorized, executed))
    executed_without_auth = RuntimeEvent(
        "evt-4", "run-1", RuntimeEventType.ACTION_EXECUTED, _NOW, action_id="act-1"
    )
    with pytest.raises(RuntimeEventError, match="prior ALLOW"):
        validate_event_trace((requested, executed_without_auth))
    with pytest.raises(RuntimeEventError, match="large event payloads"):
        RuntimeEvent(
            "evt-large",
            "run-1",
            RuntimeEventType.OBSERVATION_PRODUCED,
            _NOW,
            payload={"output": "x" * 4097},
        )


def test_local_runtime_never_executes_denied_actions_and_records_observations() -> None:
    calls: list[str] = []

    def executor(action: Action) -> Observation:
        calls.append(action.action_id)
        return Observation(
            observation_id="obs-1",
            run_id=action.run_id,
            action_id=action.action_id,
            observation_type=ObservationType.FILE_WRITTEN,
            occurred_at=_NOW,
            outcome="ok",
            artifact_refs=("artifact-1",),
        )

    runtime = LocalRuntime(executor)
    action = _action()
    allowed = authorize_with_policy(action, _context())
    observed = runtime.execute(action, allowed)

    assert observed.outcome == "ok"
    assert calls == ["act-1"]
    assert runtime.executed_actions == ["act-1"]

    denied = authorize_with_policy(_action(resource="tests/test_a.py"), _context())
    denial_observation = runtime.execute(_action(resource="tests/test_a.py"), denied)

    assert denial_observation.outcome == "denied"
    assert calls == ["act-1"]
    assert runtime.executed_actions == ["act-1"]


def test_local_runtime_failure_produces_action_failed_event() -> None:
    def executor(_action: Action) -> Observation:
        raise RuntimeError("boom")

    runtime = LocalRuntime(executor)
    with pytest.raises(RuntimeError):
        runtime.execute(_action(), authorize_with_policy(_action(), _context()))

    assert runtime.events[-1].event_type is RuntimeEventType.ACTION_FAILED


def test_workspace_blocks_path_traversal_before_runtime() -> None:
    with pytest.raises(ValueError, match="escapes"):
        _action(resource="../outside.py")
