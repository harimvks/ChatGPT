"""Persist a governed GAIEP agent request as self-improvement trajectory evidence."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from runtime.context.contracts import ContextManifest
from runtime.mcp.gateway import McpCapabilityGateway, McpRequest, McpStatus
from runtime.skills.contracts import SkillDisclosure

from .artifact import CandidateArtifact
from .evaluation import EvaluationResult
from .rollout import RolloutResult
from .runtime_provenance import provenance_from_mcp_result
from .trajectory import TrajectoryRecord
from .trajectory_store import TrajectoryStore


@dataclass(frozen=True)
class GovernedAgentRunResult:
    response_status: McpStatus
    rollout: RolloutResult
    evaluation: EvaluationResult
    trajectory: TrajectoryRecord
    trajectory_path: Path


def run_governed_agent_request(
    *,
    task_id: str,
    request: McpRequest,
    context_manifest: ContextManifest,
    skill_disclosures: tuple[SkillDisclosure, ...],
    gateway: McpCapabilityGateway,
    trajectory_store: TrajectoryStore,
    model_name: str,
    scaffold_name: str,
    policy_version: str,
    endpoint_model: str | None = None,
) -> GovernedAgentRunResult:
    """Execute one governed request and persist reference-only trajectory metadata.

    This function is orchestration glue: it does not authorize, execute, route models,
    or call providers directly. The supplied MCP gateway owns the authorized Runtime
    path, and this function records the resulting observation/evidence references.
    """
    response = gateway.handle(request)
    provenance = provenance_from_mcp_result(
        request=request,
        response=response,
        events=tuple(gateway.events),
        context_manifest=context_manifest,
        skill_disclosures=skill_disclosures,
        policy_version=policy_version,
        gateway_model=model_name,
        gateway_endpoint_model=endpoint_model,
    )
    artifact = CandidateArtifact(files={})
    rollout = RolloutResult(
        task_id=task_id,
        artifact=artifact,
        model_name=model_name,
        scaffold_name=scaffold_name,
        endpoint_model=endpoint_model,
        provenance=provenance,
    )
    evaluation = EvaluationResult(
        task_id=task_id,
        passed=response.status is McpStatus.OK,
        reward=1.0 if response.status is McpStatus.OK else 0.0,
        checks={"authorized_runtime_path": response.status is McpStatus.OK},
        failure_class=None if response.status is McpStatus.OK else response.status.value,
    )
    trajectory = TrajectoryRecord.from_results(rollout, evaluation)
    trajectory_store.append(trajectory)
    return GovernedAgentRunResult(
        response_status=response.status,
        rollout=rollout,
        evaluation=evaluation,
        trajectory=trajectory,
        trajectory_path=trajectory_store.path,
    )
