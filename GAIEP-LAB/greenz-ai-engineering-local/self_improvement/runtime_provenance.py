"""Build RunProvenance from governed Runtime/MCP request results."""

from __future__ import annotations

from runtime.agent.events import RuntimeEvent, RuntimeEventType
from runtime.context.contracts import ContextManifest
from runtime.mcp.gateway import McpRequest, McpResponse, McpStatus
from runtime.skills.contracts import SkillDisclosure

from .provenance import AuthorizationProvenance, ContextProvenance, RunProvenance


def provenance_from_mcp_result(
    *,
    request: McpRequest,
    response: McpResponse,
    events: tuple[RuntimeEvent, ...],
    context_manifest: ContextManifest | None = None,
    skill_disclosures: tuple[SkillDisclosure, ...] = (),
    policy_version: str | None = None,
    gateway_model: str | None = None,
    gateway_endpoint_model: str | None = None,
) -> RunProvenance:
    """Create reference-only trajectory provenance from the actual governed path."""
    authorization = tuple(
        AuthorizationProvenance(
            decision_ref=event.event_id,
            decision=(event.payload or {}).get("decision", "DENY"),
            reason=(event.payload or {}).get("reason", response.error or "unknown"),
            capability_id=(event.payload or {}).get("capability_id", request.capability_id),
            capability_version=(event.payload or {}).get(
                "capability_version", request.capability_version
            ),
            policy_version=policy_version,
        )
        for event in events
        if event.event_type is RuntimeEventType.AUTHORIZATION_EVALUATED
        and event.action_id == request.request_id
    )
    observation_refs = (
        (response.observation.observation_id,)
        if response.status is McpStatus.OK and response.observation is not None
        else ()
    )
    authorized_ids = (request.capability_id,) if response.status is McpStatus.OK else ()
    return RunProvenance(
        run_id=request.run_id,
        context=(
            ContextProvenance(
                manifest_id=context_manifest.manifest_id,
                context_hash=context_manifest.context_hash or context_manifest.compute_hash(),
            )
            if context_manifest is not None
            else None
        ),
        skill_fingerprints=tuple(
            disclosure.fingerprint for disclosure in skill_disclosures
        ),
        authorization=authorization,
        observation_refs=observation_refs,
        artifact_refs=response.artifact_refs,
        evidence_refs=response.evidence_refs,
        gateway_model=gateway_model,
        gateway_endpoint_model=gateway_endpoint_model,
        capability_ids_requested=(request.capability_id,),
        capability_ids_authorized=authorized_ids,
        policy_decision_refs=tuple(item.decision_ref for item in authorization),
        started_at_ref=f"mcp-requested:{request.request_id}",
        finished_at_ref=(
            f"observation:{response.observation.observation_id}"
            if response.observation is not None
            else f"mcp-response:{response.status.value}"
        ),
    )
