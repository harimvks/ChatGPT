"""Read-only GreenZ capability catalog for the lab snapshot.

The current ChatGPT lab checkout does not include authoritative GreenZ domain
interfaces for market, measurement, forecast, strategy, risk, or portfolio data.
The catalog therefore declares the stable capability identities and schemas, but
marks each capability unavailable until it can be bound to the real production
interface.
"""

from __future__ import annotations

from runtime.agent.contracts import (
    ActionType,
    Capability,
    CapabilityAccessMode,
    CapabilityRegistry,
    CapabilityRiskClass,
    CapabilityRuntime,
)

READ_ONLY_CAPABILITY_IDS = (
    "market.get_snapshot",
    "market.get_quote",
    "market.get_candles",
    "measurements.get_snapshot",
    "measurements.get_breadth",
    "measurements.get_options_state",
    "forecast.get_current",
    "forecast.get_history",
    "strategy.get_state",
    "risk.get_state",
    "portfolio.get_positions",
)

FUTURE_ACTION_CAPABILITY_IDS = (
    "trade.submit",
    "trade.cancel",
    "trade.modify",
    "trade.flatten",
)

_SCHEMA_PREFIX = "schema:gaiep.greenz"
_MISSING_SOURCE = "authoritative GreenZ domain interface is absent from this ChatGPT lab snapshot"


def _read_capability(capability_id: str) -> Capability:
    return Capability(
        capability_id=capability_id,
        version="v1",
        description=f"Read-only GreenZ domain capability {capability_id}",
        action_types=(ActionType.CAPABILITY_READ,),
        resource_patterns=(f"greenz/{capability_id.replace('.', '/')}",),
        requires_evidence=True,
        access_mode=CapabilityAccessMode.READ,
        risk_class=CapabilityRiskClass.LOW,
        required_scopes=("greenz.read",),
        allowed_runtime=(CapabilityRuntime.UNAVAILABLE,),
        provenance_required=True,
        audit_required=True,
        input_schema_ref=f"{_SCHEMA_PREFIX}.{capability_id}.input.v1",
        output_schema_ref=f"{_SCHEMA_PREFIX}.{capability_id}.output.v1",
        authoritative_source="GreenZ production domain API",
        freshness="source-defined; fail closed when stale or unavailable",
        point_in_time="request timestamp must be preserved by authoritative source",
        unavailable_reason=_MISSING_SOURCE,
    )


def _forbidden_action(capability_id: str) -> Capability:
    return Capability(
        capability_id=capability_id,
        version="v1",
        description=f"Future trading action capability {capability_id}; forbidden in this phase",
        action_types=(ActionType.TOOL_CALL,),
        resource_patterns=(f"greenz/{capability_id.replace('.', '/')}",),
        requires_evidence=True,
        access_mode=CapabilityAccessMode.ACTION,
        risk_class=CapabilityRiskClass.FORBIDDEN,
        required_scopes=("greenz.trade",),
        allowed_runtime=(CapabilityRuntime.UNAVAILABLE,),
        provenance_required=True,
        audit_required=True,
        input_schema_ref=f"{_SCHEMA_PREFIX}.{capability_id}.input.v1",
        output_schema_ref=f"{_SCHEMA_PREFIX}.{capability_id}.output.v1",
        authoritative_source="not implemented",
        freshness="not available",
        point_in_time="not available",
        unavailable_reason=(
            "broker execution and trading actions are explicitly prohibited in this phase"
        ),
    )


def greenz_read_only_catalog() -> CapabilityRegistry:
    capabilities = tuple(
        _read_capability(capability_id) for capability_id in READ_ONLY_CAPABILITY_IDS
    )
    forbidden = tuple(
        _forbidden_action(capability_id) for capability_id in FUTURE_ACTION_CAPABILITY_IDS
    )
    return CapabilityRegistry((*capabilities, *forbidden), registry_version="greenz-readonly-v1")
