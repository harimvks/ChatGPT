"""Phase-1 tests for GAIEP Agent/Runtime boundary contracts."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta

import pytest

from runtime.agent.authorization import authorize_action, child_authority_decision
from runtime.agent.contracts import (
    Action,
    ActionType,
    AgentRun,
    AuthorityScope,
    Capability,
    CapabilityRegistry,
    Decision,
    ModelCompletionEvidence,
    Observation,
    ObservationType,
    RunStatus,
)

_NOW = datetime(2026, 8, 24, 10, 0, tzinfo=UTC)


def _registry() -> CapabilityRegistry:
    return CapabilityRegistry(
        capabilities=(
            Capability(
                capability_id="engineering.implementation",
                action_types=(
                    ActionType.MODEL_REQUEST,
                    ActionType.FILE_READ,
                    ActionType.FILE_WRITE,
                ),
                resource_patterns=("src/**", "tests/**", "model/**"),
                requires_evidence=True,
            ),
            Capability(
                capability_id="validation.local",
                action_types=(ActionType.VALIDATION,),
                resource_patterns=("tests/**",),
            ),
        )
    )


def _authority() -> AuthorityScope:
    return AuthorityScope(
        scope_id="auth-root",
        capability_ids=("engineering.implementation", "validation.local"),
        readable_roots=("src", "tests"),
        writable_roots=("src", "tests"),
        executable_commands=("pytest", "ruff", "pyright"),
        network_allowed=False,
        max_child_runs=2,
        max_depth=1,
        token_budget=1000,
    )


def test_agent_run_rejects_empty_ids_and_naive_timestamps() -> None:
    with pytest.raises(ValueError, match="run_id"):
        AgentRun(
            run_id="",
            task_id="TASK-1",
            capability="engineering.implementation",
            parent_run_id=None,
            authority_scope_id="auth-root",
            status=RunStatus.CREATED,
            started_at=_NOW,
        )

    with pytest.raises(ValueError, match="timezone-aware UTC"):
        AgentRun(
            run_id="run-1",
            task_id="TASK-1",
            capability="engineering.implementation",
            parent_run_id=None,
            authority_scope_id="auth-root",
            status=RunStatus.CREATED,
            started_at=datetime(2026, 8, 24, 10, 0),
        )


def test_agent_run_identity_is_immutable_and_terminal_state_requires_finish() -> None:
    run = AgentRun(
        run_id="run-1",
        task_id="TASK-1",
        capability="engineering.implementation",
        parent_run_id=None,
        authority_scope_id="auth-root",
        status=RunStatus.RUNNING,
        started_at=_NOW,
    )

    with pytest.raises(FrozenInstanceError):
        run.status = RunStatus.SUCCEEDED  # type: ignore[misc]

    with pytest.raises(ValueError, match="terminal"):
        AgentRun(
            run_id="run-2",
            task_id="TASK-1",
            capability="engineering.implementation",
            parent_run_id=None,
            authority_scope_id="auth-root",
            status=RunStatus.SUCCEEDED,
            started_at=_NOW,
        )

    with pytest.raises(ValueError, match="cannot precede"):
        AgentRun(
            run_id="run-3",
            task_id="TASK-1",
            capability="engineering.implementation",
            parent_run_id=None,
            authority_scope_id="auth-root",
            status=RunStatus.FAILED,
            started_at=_NOW,
            finished_at=_NOW - timedelta(seconds=1),
        )


def test_authorization_allows_registered_capability_action_and_resource() -> None:
    action = Action(
        action_id="act-1",
        run_id="run-1",
        action_type=ActionType.FILE_WRITE,
        capability_id="engineering.implementation",
        resource="src/runtime/foo.py",
        requested_at=_NOW,
    )

    decision = authorize_action(registry=_registry(), authority=_authority(), action=action)

    assert decision.decision is Decision.ALLOW
    assert decision.reason == "authorized"


def test_authorization_denies_unknown_ungranted_wrong_type_and_wrong_resource() -> None:
    registry = _registry()
    authority = _authority()

    unknown = Action(
        action_id="act-unknown",
        run_id="run-1",
        action_type=ActionType.FILE_READ,
        capability_id="missing",
        resource="src/a.py",
        requested_at=_NOW,
    )
    decision = authorize_action(registry=registry, authority=authority, action=unknown)
    assert decision.decision is Decision.DENY

    ungranted = Action(
        action_id="act-ungranted",
        run_id="run-1",
        action_type=ActionType.FILE_READ,
        capability_id="engineering.implementation",
        resource="src/a.py",
        requested_at=_NOW,
    )
    reduced = AuthorityScope(scope_id="reduced", capability_ids=("validation.local",))
    decision = authorize_action(registry=registry, authority=reduced, action=ungranted)
    assert decision.decision is Decision.DENY

    wrong_type = Action(
        action_id="act-type",
        run_id="run-1",
        action_type=ActionType.FILE_WRITE,
        capability_id="validation.local",
        resource="tests/test_a.py",
        requested_at=_NOW,
    )
    decision = authorize_action(registry=registry, authority=authority, action=wrong_type)
    assert decision.decision is Decision.DENY

    wrong_resource = Action(
        action_id="act-resource",
        run_id="run-1",
        action_type=ActionType.FILE_WRITE,
        capability_id="engineering.implementation",
        resource="prod/secrets.py",
        requested_at=_NOW,
    )
    decision = authorize_action(registry=registry, authority=authority, action=wrong_resource)
    assert decision.decision is Decision.DENY


def test_child_authority_must_be_subset_of_parent_authority() -> None:
    parent = _authority()
    child = AuthorityScope(
        scope_id="auth-child",
        capability_ids=("validation.local",),
        readable_roots=("tests",),
        writable_roots=("tests",),
        executable_commands=("pytest",),
        network_allowed=False,
        max_child_runs=1,
        max_depth=0,
        token_budget=500,
    )

    assert child_authority_decision(parent, child).decision is Decision.ALLOW

    expanded = AuthorityScope(
        scope_id="auth-expanded",
        capability_ids=("validation.local",),
        readable_roots=("tests",),
        writable_roots=("tests",),
        executable_commands=("pytest",),
        network_allowed=True,
        max_child_runs=1,
        max_depth=0,
        token_budget=500,
    )
    decision = child_authority_decision(parent, expanded)
    assert decision.decision is Decision.DENY
    assert "network" in decision.reason


def test_authority_rejects_path_traversal_and_duplicate_capabilities() -> None:
    with pytest.raises(ValueError, match="duplicates"):
        AuthorityScope(scope_id="auth", capability_ids=("a", "a"))

    with pytest.raises(ValueError, match="escapes"):
        AuthorityScope(scope_id="auth", capability_ids=("a",), readable_roots=("../outside",))


def test_model_completed_observation_requires_existing_provenance_reference() -> None:
    evidence = ModelCompletionEvidence(
        response_log_id="RL-123",
        execution_id="exec-123",
        context_id="ctx-123",
        context_hash="hash-123",
        artifact_ref="corrections/artifacts/RL-123.txt",
    )
    observation = Observation(
        observation_id="obs-1",
        run_id="run-1",
        action_id="act-1",
        observation_type=ObservationType.MODEL_COMPLETED,
        occurred_at=_NOW,
        outcome="success",
        evidence_refs=("RL-123",),
        model_evidence=evidence,
    )

    assert observation.model_evidence is evidence
    assert observation.evidence_refs == ("RL-123",)

    with pytest.raises(ValueError, match="ModelCompletionEvidence"):
        Observation(
            observation_id="obs-2",
            run_id="run-1",
            action_id="act-1",
            observation_type=ObservationType.MODEL_COMPLETED,
            occurred_at=_NOW,
            outcome="success",
        )
