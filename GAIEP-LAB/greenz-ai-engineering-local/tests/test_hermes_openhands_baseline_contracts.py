"""Tests for Hermes/OpenHands-derived GAIEP baseline contract layers."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from runtime.agent.contracts import AgentRun, AuthorityScope, RunStatus
from runtime.memory.contracts import (
    CandidateMemory,
    GovernanceDecision,
    GreenMemoryRecord,
    MemoryStatus,
    MemoryValidationError,
)
from runtime.skills.contracts import (
    ApplicabilityRule,
    CertifiedSkillVersion,
    GreenSkill,
    GreenSkillRegistry,
    SkillStatus,
    SkillValidationError,
)
from runtime.subagents.contracts import (
    SubagentBoundary,
    SubagentHandle,
    SubagentValidationError,
)

_NOW = datetime(2026, 8, 25, 10, 0, tzinfo=UTC)


def _parent_authority() -> AuthorityScope:
    return AuthorityScope(
        scope_id="parent-auth",
        capability_ids=("engineering.implementation", "validation.local"),
        readable_roots=("src", "tests"),
        writable_roots=("src",),
        executable_commands=("pytest", "ruff"),
        network_allowed=False,
        max_child_runs=2,
        max_depth=1,
        token_budget=1000,
    )


def _child_authority() -> AuthorityScope:
    return AuthorityScope(
        scope_id="child-auth",
        capability_ids=("validation.local",),
        readable_roots=("tests",),
        writable_roots=(),
        executable_commands=("pytest",),
        network_allowed=False,
        max_child_runs=0,
        max_depth=0,
        token_budget=200,
    )


def test_greenskills_are_immutable_versioned_and_do_not_grant_authority() -> None:
    applicability = ApplicabilityRule(
        task_types=("implementation",),
        capability_ids=("engineering.implementation",),
        tags=("python",),
    )
    skill = GreenSkill(
        skill_id="skill-python-implementation",
        version="1.0.0",
        name="Python Implementation",
        procedure_ref="skills/python_implementation.md",
        applicability=applicability,
        status=SkillStatus.CERTIFIED,
        created_at=_NOW,
        required_capability_ids=("engineering.implementation",),
        evidence_refs=("CERT-SKILL-1",),
    )
    certified = CertifiedSkillVersion(
        skill=skill,
        certified_by="architecture-review",
        certification_ref="CERT-SKILL-1",
        certified_at=_NOW,
    )
    registry = GreenSkillRegistry((skill,))

    assert certified.skill is skill
    assert registry.applicable_to(
        task_type="implementation", capability_ids=("engineering.implementation",)
    ) == (skill,)
    assert registry.applicable_to(task_type="implementation", capability_ids=()) == ()

    with pytest.raises(FrozenInstanceError):
        skill.version = "1.0.1"  # type: ignore[misc]

    with pytest.raises(SkillValidationError, match="evidence"):
        GreenSkill(
            skill_id="skill-uncertified",
            version="1.0.0",
            name="Bad",
            procedure_ref="skills/bad.md",
            applicability=applicability,
            status=SkillStatus.CERTIFIED,
            created_at=_NOW,
        )


def test_greenmemory_requires_candidate_evidence_and_governed_promotion() -> None:
    candidate = CandidateMemory(
        candidate_id="mem-candidate-1",
        run_id="run-1",
        observation_id="obs-1",
        summary="This project validates generated code with pytest and ruff.",
        evidence_refs=("obs-1", "trajectory-1"),
        created_at=_NOW,
    )
    decision = GovernanceDecision(
        decision_id="gov-1",
        candidate_id="mem-candidate-1",
        status=MemoryStatus.APPROVED,
        decided_by="reviewer",
        decision_ref="GOV-1",
        decided_at=_NOW,
    )
    record = GreenMemoryRecord(
        memory_id="green-memory-1",
        candidate=candidate,
        governance=decision,
        tags=("validation",),
        promoted_at=_NOW,
    )

    assert record.candidate is candidate
    assert record.governance is decision

    with pytest.raises(MemoryValidationError, match="evidence"):
        CandidateMemory(
            candidate_id="mem-candidate-2",
            run_id="run-1",
            observation_id="obs-2",
            summary="No direct LLM durable memory.",
            evidence_refs=(),
            created_at=_NOW,
        )

    rejected = GovernanceDecision(
        decision_id="gov-2",
        candidate_id="mem-candidate-1",
        status=MemoryStatus.REJECTED,
        decided_by="reviewer",
        decision_ref="GOV-2",
        decided_at=_NOW,
    )
    with pytest.raises(MemoryValidationError, match="approved"):
        GreenMemoryRecord(
            memory_id="green-memory-2",
            candidate=candidate,
            governance=rejected,
            tags=("validation",),
            promoted_at=_NOW,
        )


def test_bounded_subagents_cannot_expand_authority_tools_context_or_budget() -> None:
    boundary = SubagentBoundary(
        parent_authority=_parent_authority(),
        child_authority=_child_authority(),
        parent_tool_ids=("pytest", "ruff"),
        child_tool_ids=("pytest",),
        parent_context_refs=("ctx-parent", "ctx-tests"),
        child_context_refs=("ctx-tests",),
        parent_budget_tokens=1000,
        child_budget_tokens=200,
    )
    child_run = AgentRun(
        run_id="child-run",
        task_id="TASK-1",
        capability="validation.local",
        parent_run_id="parent-run",
        authority_scope_id="child-auth",
        status=RunStatus.RUNNING,
        started_at=_NOW,
    )
    handle = SubagentHandle(
        handle_id="subagent-1",
        parent_run_id="parent-run",
        child_run=child_run,
        boundary=boundary,
        created_at=_NOW,
        checkpoint_ref="checkpoint-1",
    )

    assert handle.boundary is boundary

    with pytest.raises(SubagentValidationError, match="network"):
        SubagentBoundary(
            parent_authority=_parent_authority(),
            child_authority=AuthorityScope(
                scope_id="child-expanded",
                capability_ids=("validation.local",),
                network_allowed=True,
            ),
            parent_tool_ids=("pytest",),
            child_tool_ids=("pytest",),
            parent_context_refs=("ctx",),
            child_context_refs=("ctx",),
            parent_budget_tokens=100,
            child_budget_tokens=50,
        )

    with pytest.raises(SubagentValidationError, match="tools"):
        SubagentBoundary(
            parent_authority=_parent_authority(),
            child_authority=_child_authority(),
            parent_tool_ids=("pytest",),
            child_tool_ids=("pytest", "shell"),
            parent_context_refs=("ctx",),
            child_context_refs=("ctx",),
            parent_budget_tokens=100,
            child_budget_tokens=50,
        )

    with pytest.raises(SubagentValidationError, match="budget"):
        SubagentBoundary(
            parent_authority=_parent_authority(),
            child_authority=_child_authority(),
            parent_tool_ids=("pytest",),
            child_tool_ids=("pytest",),
            parent_context_refs=("ctx",),
            child_context_refs=("ctx",),
            parent_budget_tokens=100,
            child_budget_tokens=101,
        )
