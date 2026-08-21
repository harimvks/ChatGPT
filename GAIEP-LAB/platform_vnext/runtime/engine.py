"""Minimal GAIEP Runtime VNext vertical-slice executor."""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from uuid import uuid4
from typing import Protocol

from platform_vnext.runtime.contracts import AgentRun, RunStatus
from platform_vnext.skills.contracts import GreenSkill
from platform_vnext.compat.platform_adapter import AdapterRequest, AdapterResponse, PlatformAdapter


@dataclass(frozen=True)
class EvidenceRecord:
    run_id: str
    event: str
    status: str
    details: tuple[tuple[str, str], ...] = ()


class ContextFactory(Protocol):
    def build(self, run: AgentRun, skill: GreenSkill):
        ...


@dataclass(frozen=True)
class RuntimeResult:
    run: AgentRun
    response: AdapterResponse
    evidence: tuple[EvidenceRecord, ...]


class RuntimeVNext:
    """Execute the smallest governed AgentRun path.

    This first slice intentionally delegates provider policy and model execution to the existing
    platform adapter. It does not yet execute arbitrary tools, mutate workspaces, or spawn children.
    """

    def __init__(self, *, adapter: PlatformAdapter, context_factory: ContextFactory) -> None:
        self._adapter = adapter
        self._context_factory = context_factory

    def execute(self, run: AgentRun, skill: GreenSkill, *, template: str) -> RuntimeResult:
        events: list[EvidenceRecord] = []
        current = replace(run, status=RunStatus.PLANNED)
        events.append(EvidenceRecord(current.run_id, "planned", current.status.value))

        if skill.skill_id not in current.task_policy.allowed_skills:
            raise PermissionError(f"skill {skill.skill_id!r} is not allowed by task policy")
        current = replace(current, status=RunStatus.AUTHORIZED)
        events.append(EvidenceRecord(current.run_id, "authorized", current.status.value))

        manifest = self._context_factory.build(current, skill)
        current = replace(current, status=RunStatus.CONTEXT_READY)
        events.append(
            EvidenceRecord(
                current.run_id,
                "context_ready",
                current.status.value,
                (("context_id", manifest.context.context_id), ("context_hash", manifest.context.content_hash)),
            )
        )

        current = replace(current, status=RunStatus.SKILL_READY)
        events.append(EvidenceRecord(current.run_id, "skill_ready", current.status.value, (("skill_id", skill.skill_id),)))

        current = replace(current, status=RunStatus.EXECUTING)
        events.append(EvidenceRecord(current.run_id, "executing", current.status.value))

        response = self._adapter.generate(
            AdapterRequest(
                capability_name=skill.name,
                capability_version=skill.version,
                capability_tag=skill.capability,
                template=template,
                context_manifest=manifest,
                context_id=manifest.context.context_id,
                context_hash=manifest.context.content_hash,
                classification=manifest.classification,
            )
        )

        current = replace(current, status=RunStatus.VALIDATING)
        events.append(
            EvidenceRecord(
                current.run_id,
                "validating",
                current.status.value,
                (("model", response.model), ("provider", response.provider_name)),
            )
        )

        # The first vertical slice validates execution metadata and a non-empty provider result.
        # Repository-specific tests/linters belong to the later write-capable skill executor.
        if not response.text.strip():
            raise ValueError("platform returned an empty response")

        current = replace(current, status=RunStatus.EVIDENCE_READY)
        events.append(EvidenceRecord(current.run_id, "evidence_ready", current.status.value))
        current = replace(current, status=RunStatus.GOVERNANCE)
        events.append(EvidenceRecord(current.run_id, "governance", current.status.value))
        current = replace(current, status=RunStatus.ACCEPTED)
        events.append(
            EvidenceRecord(
                current.run_id,
                "accepted",
                current.status.value,
                (("execution_id", response.execution_id or ""), ("failover", ",".join(response.failed_over_from))),
            )
        )
        return RuntimeResult(run=current, response=response, evidence=tuple(events))
