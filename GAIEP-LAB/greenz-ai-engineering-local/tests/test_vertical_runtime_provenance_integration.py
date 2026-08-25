"""Vertical Context/Skills -> MCP Gateway -> Runtime -> RunProvenance tests."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from runtime.agent.contracts import (
    Action,
    ActionType,
    AuthorityScope,
    Capability,
    CapabilityAccessMode,
    CapabilityRegistry,
    CapabilityRiskClass,
    CapabilityRuntime,
    Observation,
    ObservationType,
)
from runtime.agent.local_runtime import LocalRuntime
from runtime.agent.policy import (
    GlobalPolicy,
    PolicyAuthorizationContext,
    RuntimeBudget,
    SkillManifest,
    TaskPolicy,
    WorkspaceScope,
)
from runtime.context.contracts import (
    ContextBudget,
    ContextItem,
    ContextItemKind,
    ContextManifest,
    SelectionReason,
)
from runtime.mcp.gateway import McpCapabilityGateway, McpRequest, McpStatus
from runtime.skills.contracts import (
    ApplicabilityRule,
    GreenSkill,
    GreenSkillRegistry,
    SkillStatus,
)
from self_improvement.evaluation import EvaluationResult
from self_improvement.rollout import RolloutResult
from self_improvement.runtime_provenance import provenance_from_mcp_result
from self_improvement.trajectory import TrajectoryRecord

_NOW = datetime(2026, 8, 25, 14, 0, tzinfo=UTC)


def _capability() -> Capability:
    return Capability(
        capability_id="market.get_quote",
        version="v1",
        description="read market quote",
        action_types=(ActionType.CAPABILITY_READ,),
        resource_patterns=("greenz/market/get_quote",),
        requires_evidence=True,
        access_mode=CapabilityAccessMode.READ,
        risk_class=CapabilityRiskClass.LOW,
        required_scopes=("greenz.read",),
        allowed_runtime=(CapabilityRuntime.MCP_READ_ONLY,),
        provenance_required=True,
        audit_required=True,
        input_schema_ref="schema:quote.input.v1",
        output_schema_ref="schema:quote.output.v1",
    )


def _context_manifest() -> ContextManifest:
    item = ContextItem(
        item_id="ctx-skill",
        kind=ContextItemKind.SKILL,
        source_ref="skills/market_read.md",
        token_estimate=12,
        mandatory=True,
        selection_reason=SelectionReason.MANDATORY,
        content_hash="hash-skill-source",
        redaction_checked=True,
    )
    return ContextManifest(
        manifest_id="ctx-manifest-1",
        run_id="run-1",
        schema_version="context-manifest-v1",
        profile_id="market-analysis",
        selected_items=(item,),
        compression_records=(),
        budget=ContextBudget(
            input_token_limit=100,
            output_token_reserve=25,
            mandatory_token_estimate=12,
        ),
        created_at=_NOW,
    )


def _skill_disclosure():
    skill = GreenSkill(
        skill_id="skill-market-read",
        version="1.0.0",
        name="Market Read",
        procedure_ref="skills/market_read.md",
        applicability=ApplicabilityRule(
            task_types=("market-analysis",),
            capability_ids=("market.get_quote",),
        ),
        status=SkillStatus.CERTIFIED,
        created_at=_NOW,
        required_capability_ids=("market.get_quote",),
        evidence_refs=("cert://skill-market-read",),
        context_refs=("skills/market_read.md",),
    )
    return GreenSkillRegistry((skill,)).disclose(
        task_type="market-analysis",
        capability_ids=("market.get_quote",),
        max_context_refs=1,
    )


def _policy(
    registry: CapabilityRegistry, *, skill_allowed: bool = True
) -> PolicyAuthorizationContext:
    skill_caps = ("market.get_quote",) if skill_allowed else ()
    return PolicyAuthorizationContext(
        registry=registry,
        authority=AuthorityScope(
            scope_id="auth",
            capability_ids=("market.get_quote",),
            readable_roots=("greenz",),
            writable_roots=(),
            token_budget=100,
        ),
        workspace=WorkspaceScope(
            workspace_id="ws",
            root="repo",
            readable_roots=("greenz",),
            writable_roots=(),
        ),
        budget=RuntimeBudget(action_limit=1, token_limit=100),
        task_policy=TaskPolicy(
            policy_id="task",
            allowed_capability_ids=("market.get_quote",),
            allowed_action_types=(ActionType.CAPABILITY_READ,),
        ),
        skill_manifest=SkillManifest(manifest_id="skills", allowed_capability_ids=skill_caps),
        global_policy=GlobalPolicy(policy_id="global"),
        policy_version="policy-v1",
    )


def _request() -> McpRequest:
    return McpRequest(
        request_id="req-1",
        run_id="run-1",
        capability_id="market.get_quote",
        capability_version="v1",
        arguments={"symbol": "NIFTY"},
        requested_at=_NOW,
        resource="greenz/market/get_quote",
    )


def test_vertical_success_produces_actual_context_skill_auth_observation_provenance() -> None:
    registry = CapabilityRegistry((_capability(),))

    def resolver(action: Action, _arguments: object) -> Observation:
        return Observation(
            observation_id="obs-quote-1",
            run_id=action.run_id,
            action_id=action.action_id,
            observation_type=ObservationType.CAPABILITY_RESULT,
            occurred_at=_NOW,
            outcome="success",
            artifact_refs=("artifact://quote/req-1",),
            evidence_refs=("evidence://quote/req-1",),
        )

    gateway = McpCapabilityGateway(
        registry=registry,
        policy_context=_policy(registry),
        runtime=LocalRuntime(lambda _action: pytest.fail("resolver must be installed by MCP")),
        resolvers={"market.get_quote": resolver},
    )
    request = _request()
    response = gateway.handle(request)
    provenance = provenance_from_mcp_result(
        request=request,
        response=response,
        events=tuple(gateway.events),
        context_manifest=_context_manifest(),
        skill_disclosures=_skill_disclosure(),
        policy_version="policy-v1",
        gateway_model="small-python-coder",
        gateway_endpoint_model="qwen-local",
    )

    assert response.status is McpStatus.OK
    assert provenance.context is not None
    assert provenance.context.manifest_id == "ctx-manifest-1"
    assert provenance.context.context_hash == _context_manifest().context_hash
    assert provenance.skill_fingerprints == (_skill_disclosure()[0].fingerprint,)
    assert provenance.authorization[0].decision == "ALLOW"
    assert provenance.authorization[0].reason == "authorized"
    assert provenance.capability_ids_requested == ("market.get_quote",)
    assert provenance.capability_ids_authorized == ("market.get_quote",)
    assert provenance.observation_refs == ("obs-quote-1",)
    assert provenance.artifact_refs == ("artifact://quote/req-1",)
    assert provenance.evidence_refs == ("evidence://quote/req-1",)

    rollout = RolloutResult(
        task_id="task-1",
        artifact=type("Artifact", (), {"files": {"candidate.py": "raw candidate"}})(),
        model_name="small-python-coder",
        scaffold_name="inspect-plan-implement-test",
        provenance=provenance,
    )
    trajectory = TrajectoryRecord.from_results(
        rollout,
        EvaluationResult(task_id="task-1", passed=True, reward=1.0, checks={"pytest": True}),
    )
    assert trajectory.provenance == provenance
    assert "raw candidate" not in trajectory.to_json()


def test_vertical_denial_records_authorization_without_runtime_observation() -> None:
    registry = CapabilityRegistry((_capability(),))
    gateway = McpCapabilityGateway(
        registry=registry,
        policy_context=_policy(registry, skill_allowed=False),
        runtime=LocalRuntime(lambda _action: pytest.fail("denied request reached Runtime")),
        resolvers={"market.get_quote": lambda _action, _arguments: pytest.fail("denied")},
    )
    request = _request()
    response = gateway.handle(request)
    provenance = provenance_from_mcp_result(
        request=request,
        response=response,
        events=tuple(gateway.events),
        context_manifest=_context_manifest(),
        skill_disclosures=_skill_disclosure(),
        policy_version="policy-v1",
    )

    assert response.status is McpStatus.UNAUTHORIZED
    assert provenance.authorization[0].decision == "DENY"
    assert provenance.authorization[0].reason == "skill_denied"
    assert provenance.capability_ids_requested == ("market.get_quote",)
    assert provenance.capability_ids_authorized == ()
    assert provenance.observation_refs == ()
    assert gateway.runtime.executed_actions == []
