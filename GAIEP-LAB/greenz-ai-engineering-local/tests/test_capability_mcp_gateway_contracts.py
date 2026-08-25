"""Capability Registry and read-only MCP gateway contract tests."""

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
from runtime.agent.events import RuntimeEventType
from runtime.agent.local_runtime import LocalRuntime
from runtime.agent.policy import (
    GlobalPolicy,
    PolicyAuthorizationContext,
    RuntimeBudget,
    SkillManifest,
    TaskPolicy,
    WorkspaceScope,
)
from runtime.capabilities.greenz_catalog import (
    FUTURE_ACTION_CAPABILITY_IDS,
    READ_ONLY_CAPABILITY_IDS,
    greenz_read_only_catalog,
)
from runtime.mcp.gateway import McpCapabilityGateway, McpRequest, McpStatus

_NOW = datetime(2026, 8, 25, 12, 0, tzinfo=UTC)


def _read_capability(capability_id: str = "market.get_quote", version: str = "v1") -> Capability:
    return Capability(
        capability_id=capability_id,
        version=version,
        description="read quote",
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
        authoritative_source="test domain adapter",
        freshness="point-in-time test fixture",
        point_in_time="requested_at",
    )


def _registry(*capabilities: Capability) -> CapabilityRegistry:
    return CapabilityRegistry(
        capabilities or (_read_capability(),), registry_version="test-registry-v1"
    )


def _context(
    registry: CapabilityRegistry,
    *,
    task_caps: tuple[str, ...] = ("market.get_quote",),
    skill_caps: tuple[str, ...] = ("market.get_quote",),
    readable_roots: tuple[str, ...] = ("greenz",),
    action_limit: int = 3,
) -> PolicyAuthorizationContext:
    return PolicyAuthorizationContext(
        registry=registry,
        authority=AuthorityScope(
            scope_id="auth",
            capability_ids=task_caps,
            readable_roots=readable_roots,
            writable_roots=(),
            token_budget=100,
        ),
        workspace=WorkspaceScope(
            workspace_id="ws",
            root="repo",
            readable_roots=readable_roots,
            writable_roots=(),
        ),
        budget=RuntimeBudget(action_limit=action_limit, token_limit=100),
        task_policy=TaskPolicy(
            policy_id="task",
            allowed_capability_ids=task_caps,
            allowed_action_types=(ActionType.CAPABILITY_READ,),
        ),
        skill_manifest=SkillManifest(manifest_id="skills", allowed_capability_ids=skill_caps),
        global_policy=GlobalPolicy(policy_id="global"),
        policy_version="policy-v1",
    )


def _request(
    capability_id: str = "market.get_quote",
    version: str = "v1",
    resource: str = "greenz/market/get_quote",
) -> McpRequest:
    return McpRequest(
        request_id="req-1",
        run_id="run-1",
        capability_id=capability_id,
        capability_version=version,
        arguments={"symbol": "NIFTY"},
        requested_at=_NOW,
        resource=resource,
    )


def _gateway(
    registry: CapabilityRegistry,
    *,
    context: PolicyAuthorizationContext | None = None,
    resolver_called: list[str] | None = None,
) -> McpCapabilityGateway:
    calls = resolver_called if resolver_called is not None else []

    def resolver(action: Action, arguments: object) -> Observation:
        calls.append(action.action_id)
        return Observation(
            observation_id="obs-1",
            run_id=action.run_id,
            action_id=action.action_id,
            observation_type=ObservationType.CAPABILITY_RESULT,
            occurred_at=_NOW,
            outcome="success",
            artifact_refs=("artifact://quote/req-1",),
            evidence_refs=("evidence://quote/req-1",),
        )

    runtime = LocalRuntime(lambda _action: pytest.fail("MCP must install authorized resolver"))
    return McpCapabilityGateway(
        registry=registry,
        policy_context=context or _context(registry),
        runtime=runtime,
        resolvers={"market.get_quote": resolver},
    )


def test_capability_registry_registers_versions_and_enumerates_deterministically() -> None:
    cap_v1 = _read_capability("market.get_quote", "v1")
    cap_v2 = _read_capability("market.get_quote", "v2")
    other = _read_capability("risk.get_state", "v1")

    registry = CapabilityRegistry((other, cap_v2), registry_version="r1").register(cap_v1)

    assert registry.get("market.get_quote", "v1") == cap_v1
    assert registry.get("market.get_quote", "missing") is None
    assert tuple(cap.identity for cap in registry.enumerate()) == (
        ("market.get_quote", "v1"),
        ("market.get_quote", "v2"),
        ("risk.get_state", "v1"),
    )
    with pytest.raises(ValueError, match="duplicate capability identities"):
        CapabilityRegistry((cap_v1, cap_v1))
    with pytest.raises(ValueError, match="version"):
        _read_capability(version="")


def test_greenz_catalog_is_read_only_unavailable_and_future_actions_forbidden() -> None:
    registry = greenz_read_only_catalog()

    assert tuple(cap.capability_id for cap in registry.enumerate()) == tuple(
        sorted((*READ_ONLY_CAPABILITY_IDS, *FUTURE_ACTION_CAPABILITY_IDS))
    )
    quote = registry.require("market.get_quote", "v1")
    assert quote.access_mode is CapabilityAccessMode.READ
    assert CapabilityRuntime.UNAVAILABLE in quote.allowed_runtime
    assert quote.provenance_required is True
    trade = registry.require("trade.submit", "v1")
    assert trade.risk_class is CapabilityRiskClass.FORBIDDEN
    assert CapabilityRuntime.UNAVAILABLE in trade.allowed_runtime


def test_authorized_read_mcp_request_executes_through_runtime_with_evidence() -> None:
    registry = _registry()
    calls: list[str] = []
    gateway = _gateway(registry, resolver_called=calls)

    response = gateway.handle(_request())

    assert response.status is McpStatus.OK
    assert response.observation is not None
    assert response.run_id == response.observation.run_id == "run-1"
    assert response.artifact_refs == ("artifact://quote/req-1",)
    assert response.evidence_refs == ("evidence://quote/req-1",)
    assert calls == ["req-1"]
    runtime_event_types = tuple(event.event_type for event in gateway.runtime.events)
    assert RuntimeEventType.ACTION_EXECUTED in runtime_event_types
    assert RuntimeEventType.OBSERVATION_PRODUCED in runtime_event_types


def test_unknown_malformed_version_and_unavailable_requests_fail_closed() -> None:
    registry = _registry()
    calls: list[str] = []
    gateway = _gateway(registry, resolver_called=calls)

    unknown = gateway.handle(_request(capability_id="market.unknown"))
    mismatch = gateway.handle(_request(version="v2"))
    unavailable_gateway = _gateway(greenz_read_only_catalog(), resolver_called=calls)
    unavailable = unavailable_gateway.handle(_request())

    assert unknown.status is McpStatus.UNKNOWN_CAPABILITY
    assert mismatch.status is McpStatus.UNAUTHORIZED
    assert unavailable.status is McpStatus.UNAVAILABLE
    assert calls == []
    with pytest.raises(ValueError, match="reserved"):
        McpRequest(
            request_id="bad",
            run_id="run-1",
            capability_id="market.get_quote",
            capability_version="v1",
            arguments={"__python__": "exec('bad')"},
            requested_at=_NOW,
        )


def test_policy_skill_workspace_and_budget_denials_prevent_runtime_execution() -> None:
    registry = _registry()
    cases = (
        _context(registry, task_caps=()),
        _context(registry, skill_caps=()),
        _context(registry, readable_roots=("portfolio",)),
        _context(registry, action_limit=0),
    )
    for context in cases:
        calls: list[str] = []
        gateway = _gateway(registry, context=context, resolver_called=calls)
        response = gateway.handle(_request())
        assert response.status is McpStatus.UNAUTHORIZED
        assert calls == []
        assert gateway.runtime.executed_actions == []


def test_mcp_cannot_execute_forbidden_operations_or_bypass_runtime_authorization() -> None:
    registry = _registry(_read_capability(), _read_capability("trade.submit", "v1"))
    calls: list[str] = []
    gateway = _gateway(registry, resolver_called=calls)

    response = gateway.handle(
        _request(capability_id="trade.submit", resource="greenz/trade/submit")
    )

    assert response.status is McpStatus.UNAUTHORIZED
    assert calls == []
    assert gateway.runtime.executed_actions == []
    assert all("/Users/" not in (event.payload or {}).get("reason", "") for event in gateway.events)


def test_execution_failure_and_large_inline_outputs_fail_closed_without_success() -> None:
    registry = _registry()

    def failing_resolver(_action: Action, _arguments: object) -> Observation:
        raise RuntimeError("SECRET_TOKEN=/Users/private")

    runtime = LocalRuntime(lambda _action: pytest.fail("MCP must install resolver"))
    gateway = McpCapabilityGateway(
        registry=registry,
        policy_context=_context(registry),
        runtime=runtime,
        resolvers={"market.get_quote": failing_resolver},
    )
    failed = gateway.handle(_request())
    assert failed.status is McpStatus.EXECUTION_FAILED
    assert failed.error == "request could not be completed"
    assert RuntimeEventType.ACTION_EXECUTED not in tuple(
        event.event_type for event in runtime.events
    )

    def large_resolver(action: Action, _arguments: object) -> Observation:
        return Observation(
            observation_id="obs-large",
            run_id=action.run_id,
            action_id=action.action_id,
            observation_type=ObservationType.CAPABILITY_RESULT,
            occurred_at=_NOW,
            outcome="success",
            evidence_refs=("x" * 4097,),
        )

    large_gateway = McpCapabilityGateway(
        registry=registry,
        policy_context=_context(registry),
        runtime=LocalRuntime(lambda _action: pytest.fail("MCP must install resolver")),
        resolvers={"market.get_quote": large_resolver},
    )
    large = large_gateway.handle(_request())
    assert large.status is McpStatus.INVALID_REQUEST
    assert large.observation is None
