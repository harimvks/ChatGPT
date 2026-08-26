"""Persisted governed agent run provenance tests."""

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
from self_improvement.governed_agent_run import run_governed_agent_request
from self_improvement.trajectory_store import TrajectoryStore

_NOW = datetime(2026, 8, 26, 9, 0, tzinfo=UTC)


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


def _manifest() -> ContextManifest:
    return ContextManifest(
        manifest_id="ctx-real-run-1",
        run_id="run-real-1",
        schema_version="context-manifest-v1",
        profile_id="market-analysis",
        selected_items=(
            ContextItem(
                item_id="skill-context",
                kind=ContextItemKind.SKILL,
                source_ref="skills/market_read.md",
                token_estimate=12,
                mandatory=True,
                selection_reason=SelectionReason.MANDATORY,
                content_hash="hash-skill-context",
                redaction_checked=True,
            ),
        ),
        compression_records=(),
        budget=ContextBudget(
            input_token_limit=100,
            output_token_reserve=25,
            mandatory_token_estimate=12,
        ),
        created_at=_NOW,
    )


def _skill_disclosures():
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
    registry: CapabilityRegistry, *, allow_skill: bool = True
) -> PolicyAuthorizationContext:
    skill_caps = ("market.get_quote",) if allow_skill else ()
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
        request_id="req-real-1",
        run_id="run-real-1",
        capability_id="market.get_quote",
        capability_version="v1",
        arguments={"symbol": "NIFTY"},
        requested_at=_NOW,
        resource="greenz/market/get_quote",
    )


def test_governed_agent_run_persists_one_coherent_success_trace(tmp_path) -> None:
    registry = CapabilityRegistry((_capability(),))

    def resolver(action: Action, _arguments: object) -> Observation:
        return Observation(
            observation_id="obs-real-1",
            run_id=action.run_id,
            action_id=action.action_id,
            observation_type=ObservationType.CAPABILITY_RESULT,
            occurred_at=_NOW,
            outcome="success",
            artifact_refs=("artifact://real-run/quote",),
            evidence_refs=("evidence://real-run/quote",),
        )

    gateway = McpCapabilityGateway(
        registry=registry,
        policy_context=_policy(registry),
        runtime=LocalRuntime(lambda _action: pytest.fail("MCP must install resolver")),
        resolvers={"market.get_quote": resolver},
    )
    store = TrajectoryStore(tmp_path / "trajectory.jsonl")

    result = run_governed_agent_request(
        task_id="task-real-1",
        request=_request(),
        context_manifest=_manifest(),
        skill_disclosures=_skill_disclosures(),
        gateway=gateway,
        trajectory_store=store,
        model_name="small-python-coder",
        scaffold_name="inspect-plan-implement-test",
        policy_version="policy-v1",
        endpoint_model="qwen-local",
    )

    persisted = store.read_all()
    assert result.response_status is McpStatus.OK
    assert len(persisted) == 1
    record = persisted[0]
    assert record.provenance is not None
    assert record.provenance.run_id == "run-real-1"
    assert record.provenance.context is not None
    assert record.provenance.context.manifest_id == "ctx-real-run-1"
    assert record.provenance.context.context_hash == _manifest().context_hash
    assert record.provenance.skill_fingerprints == (_skill_disclosures()[0].fingerprint,)
    assert record.provenance.authorization[0].decision == "ALLOW"
    assert record.provenance.capability_ids_authorized == ("market.get_quote",)
    assert record.provenance.observation_refs == ("obs-real-1",)
    assert record.provenance.artifact_refs == ("artifact://real-run/quote",)
    assert record.provenance.evidence_refs == ("evidence://real-run/quote",)
    assert "raw" not in store.path.read_text(encoding="utf-8")


def test_governed_agent_run_persists_denial_without_execution(tmp_path) -> None:
    registry = CapabilityRegistry((_capability(),))
    gateway = McpCapabilityGateway(
        registry=registry,
        policy_context=_policy(registry, allow_skill=False),
        runtime=LocalRuntime(lambda _action: pytest.fail("denied request reached Runtime")),
        resolvers={"market.get_quote": lambda _action, _arguments: pytest.fail("denied")},
    )
    store = TrajectoryStore(tmp_path / "trajectory.jsonl")

    result = run_governed_agent_request(
        task_id="task-denied-1",
        request=_request(),
        context_manifest=_manifest(),
        skill_disclosures=_skill_disclosures(),
        gateway=gateway,
        trajectory_store=store,
        model_name="small-python-coder",
        scaffold_name="inspect-plan-implement-test",
        policy_version="policy-v1",
    )

    record = store.read_all()[0]
    assert result.response_status is McpStatus.UNAUTHORIZED
    assert record.provenance is not None
    assert record.provenance.authorization[0].decision == "DENY"
    assert record.provenance.authorization[0].reason == "skill_denied"
    assert record.provenance.observation_refs == ()
    assert record.provenance.capability_ids_authorized == ()
    assert gateway.runtime.executed_actions == []
