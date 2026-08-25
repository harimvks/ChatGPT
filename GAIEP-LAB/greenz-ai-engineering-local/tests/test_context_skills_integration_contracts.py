"""ContextEngine and GreenSkills integration tests."""

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
    Decision,
)
from runtime.agent.policy import (
    GlobalPolicy,
    PolicyAuthorizationContext,
    RuntimeBudget,
    SkillManifest,
    TaskPolicy,
    WorkspaceScope,
    authorize_with_policy,
)
from runtime.context.contracts import (
    ContextBudget,
    ContextItem,
    ContextItemKind,
    ContextProfile,
    ContextValidationError,
    SelectionReason,
)
from runtime.context.engine import ContextBuildRequest, DeterministicContextEngine
from runtime.skills.contracts import (
    ApplicabilityRule,
    GreenSkill,
    GreenSkillRegistry,
    SkillStatus,
    SkillValidationError,
)

_NOW = datetime(2026, 8, 25, 13, 0, tzinfo=UTC)


def _item(item_id: str, tokens: int, *, mandatory: bool = False) -> ContextItem:
    return ContextItem(
        item_id=item_id,
        kind=ContextItemKind.SKILL if item_id.startswith("skill") else ContextItemKind.SOURCE,
        source_ref=f"context/{item_id}.md",
        token_estimate=tokens,
        mandatory=mandatory,
        selection_reason=(
            SelectionReason.MANDATORY if mandatory else SelectionReason.SUPPORTING_CONTEXT
        ),
        content_hash=f"hash-{item_id}",
        redaction_checked=True,
    )


def _skill(capability_ids: tuple[str, ...] = ("market.get_quote",)) -> GreenSkill:
    return GreenSkill(
        skill_id="skill-market-read",
        version="1.0.0",
        name="Market Read",
        procedure_ref="skills/market_read.md",
        applicability=ApplicabilityRule(
            task_types=("market-analysis",),
            capability_ids=capability_ids,
            tags=("market",),
        ),
        status=SkillStatus.CERTIFIED,
        created_at=_NOW,
        required_capability_ids=capability_ids,
        evidence_refs=("cert://skill-market-read",),
        context_refs=("context/quote.md", "context/breadth.md"),
    )


def _registry() -> CapabilityRegistry:
    return CapabilityRegistry((
        Capability(
            capability_id="market.get_quote",
            version="v1",
            description="market quote read",
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
        ),
    ))


def _policy(skill_caps: tuple[str, ...]) -> PolicyAuthorizationContext:
    registry = _registry()
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


def test_context_engine_selects_budgeted_manifest_deterministically() -> None:
    engine = DeterministicContextEngine()
    request = ContextBuildRequest(
        run_id="run-1",
        manifest_id="ctx-1",
        profile=ContextProfile(
            profile_id="market-analysis",
            engine_version="context-v2",
            allowed_kinds=(ContextItemKind.SOURCE, ContextItemKind.SKILL),
            max_items=3,
        ),
        budget=ContextBudget(input_token_limit=100, output_token_reserve=40),
        items=(
            _item("optional-large", 70),
            _item("mandatory", 20, mandatory=True),
            _item("skill-read", 15),
            _item("optional-small", 10),
        ),
        created_at=_NOW,
    )

    manifest_a = engine.build(request)
    manifest_b = engine.build(request)

    assert manifest_a.context_hash == manifest_b.context_hash
    assert tuple(item.item_id for item in manifest_a.selected_items) == (
        "mandatory",
        "optional-small",
        "skill-read",
    )
    assert manifest_a.budget.total_token_estimate == 45


def test_context_engine_compacts_only_optional_context() -> None:
    engine = DeterministicContextEngine()
    record = engine.compact_optional(
        item=_item("optional", 50), after_tokens=20, content_hash_after="hash-after"
    )

    assert record.before_tokens == 50
    assert record.after_tokens == 20
    with pytest.raises(ContextValidationError, match="mandatory"):
        engine.compact_optional(
            item=_item("mandatory", 50, mandatory=True),
            after_tokens=20,
            content_hash_after="hash-after",
        )


def test_skill_fingerprint_and_progressive_disclosure_are_deterministic() -> None:
    skill = _skill()
    registry = GreenSkillRegistry((skill,))

    disclosures = registry.disclose(
        task_type="market-analysis",
        capability_ids=("market.get_quote",),
        max_context_refs=1,
    )

    assert disclosures[0].context_refs == ("context/breadth.md",)
    assert disclosures[0].capability_ids == ("market.get_quote",)
    assert disclosures[0].fingerprint == skill.compute_fingerprint()
    with pytest.raises(SkillValidationError, match="fingerprint"):
        GreenSkill(
            skill_id=skill.skill_id,
            version=skill.version,
            name=skill.name,
            procedure_ref=skill.procedure_ref,
            applicability=skill.applicability,
            status=skill.status,
            created_at=skill.created_at,
            required_capability_ids=skill.required_capability_ids,
            evidence_refs=skill.evidence_refs,
            context_refs=skill.context_refs,
            fingerprint="wrong",
        )


def test_skills_influence_requests_but_cannot_bypass_authorization() -> None:
    skill = _skill(("market.get_quote",))
    assert GreenSkillRegistry((skill,)).applicable_to(
        task_type="market-analysis", capability_ids=("market.get_quote",)
    ) == (skill,)
    action = Action(
        action_id="read-1",
        run_id="run-1",
        action_type=ActionType.CAPABILITY_READ,
        capability_id="market.get_quote",
        resource="greenz/market/get_quote",
        requested_at=_NOW,
    )

    denied = authorize_with_policy(action, _policy(skill_caps=()))
    allowed = authorize_with_policy(action, _policy(skill_caps=("market.get_quote",)))

    assert denied.decision is Decision.DENY
    assert denied.reason == "skill_denied"
    assert allowed.decision is Decision.ALLOW
