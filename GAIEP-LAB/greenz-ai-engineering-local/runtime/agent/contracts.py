"""Pure GAIEP agent/runtime contracts.

These dataclasses describe immutable runtime identity, actions, observations,
capabilities, authority and provenance references. They deliberately perform no
filesystem, Gateway, provider, or artifact-store I/O.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from pathlib import PurePosixPath


class RunStatus(StrEnum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMED_OUT = "TIMED_OUT"
    BLOCKED = "BLOCKED"


_TERMINAL_STATUSES = frozenset({
    RunStatus.SUCCEEDED,
    RunStatus.FAILED,
    RunStatus.CANCELLED,
    RunStatus.TIMED_OUT,
    RunStatus.BLOCKED,
})


class ActionType(StrEnum):
    MODEL_REQUEST = "model.request"
    TOOL_CALL = "tool.call"
    FILE_READ = "file.read"
    FILE_WRITE = "file.write"
    VALIDATION = "validation.run"
    CHECKPOINT = "checkpoint.create"
    CHILD_RUN = "child.run"


class ObservationType(StrEnum):
    MODEL_COMPLETED = "model.completed"
    MODEL_FAILED = "model.failed"
    TOOL_RESULT = "tool.result"
    TOOL_FAILED = "tool.failed"
    FILE_READ = "file.read"
    FILE_WRITTEN = "file.write"
    VALIDATION_COMPLETED = "validation.completed"
    CHECKPOINT_CREATED = "checkpoint.created"
    CHILD_COMPLETED = "child.completed"
    CHILD_FAILED = "child.failed"


class Decision(StrEnum):
    ALLOW = "ALLOW"
    DENY = "DENY"


def _require_non_empty(label: str, value: str) -> None:
    if not value.strip():
        raise ValueError(f"{label} cannot be empty")


def _require_utc(label: str, value: datetime) -> None:
    if value.utcoffset() != timedelta(0):
        raise ValueError(f"{label} must be timezone-aware UTC")


def _dedupe_sorted(values: tuple[str, ...], *, label: str) -> tuple[str, ...]:
    cleaned = tuple(str(value).strip() for value in values if str(value).strip())
    if len(set(cleaned)) != len(cleaned):
        raise ValueError(f"{label} cannot contain duplicates")
    return tuple(sorted(cleaned))


def normalize_path(path: str) -> str:
    _require_non_empty("path", path)
    normalized = str(PurePosixPath(path.replace("\\", "/")))
    if normalized in {".", ""} or normalized.startswith("../") or "/../" in normalized:
        raise ValueError(f"path escapes the authority envelope: {path!r}")
    return normalized.lstrip("/")


@dataclass(frozen=True)
class AgentRun:
    run_id: str
    task_id: str
    capability: str
    parent_run_id: str | None
    authority_scope_id: str
    status: RunStatus
    started_at: datetime
    finished_at: datetime | None = None
    context_manifest_id: str | None = None
    tool_manifest_id: str | None = None
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_non_empty("AgentRun.run_id", self.run_id)
        _require_non_empty("AgentRun.task_id", self.task_id)
        _require_non_empty("AgentRun.capability", self.capability)
        _require_non_empty("AgentRun.authority_scope_id", self.authority_scope_id)
        if self.parent_run_id is not None:
            _require_non_empty("AgentRun.parent_run_id", self.parent_run_id)
        _require_utc("AgentRun.started_at", self.started_at)
        if self.finished_at is not None:
            _require_utc("AgentRun.finished_at", self.finished_at)
            if self.finished_at < self.started_at:
                raise ValueError("AgentRun.finished_at cannot precede started_at")
        if self.status in _TERMINAL_STATUSES and self.finished_at is None:
            raise ValueError("terminal AgentRun status requires finished_at")
        if self.status not in _TERMINAL_STATUSES and self.finished_at is not None:
            raise ValueError("non-terminal AgentRun status cannot have finished_at")
        object.__setattr__(
            self,
            "evidence_refs",
            _dedupe_sorted(self.evidence_refs, label="AgentRun.evidence_refs"),
        )


@dataclass(frozen=True)
class AuthorityScope:
    scope_id: str
    capability_ids: tuple[str, ...]
    readable_roots: tuple[str, ...] = ()
    writable_roots: tuple[str, ...] = ()
    executable_commands: tuple[str, ...] = ()
    network_allowed: bool = False
    max_child_runs: int = 0
    max_depth: int = 0
    token_budget: int = 0

    def __post_init__(self) -> None:
        _require_non_empty("AuthorityScope.scope_id", self.scope_id)
        if self.max_child_runs < 0 or self.max_depth < 0 or self.token_budget < 0:
            raise ValueError("authority limits cannot be negative")
        object.__setattr__(
            self, "capability_ids", _dedupe_sorted(self.capability_ids, label="capability_ids")
        )
        object.__setattr__(
            self,
            "readable_roots",
            tuple(sorted(normalize_path(path) for path in self.readable_roots)),
        )
        object.__setattr__(
            self,
            "writable_roots",
            tuple(sorted(normalize_path(path) for path in self.writable_roots)),
        )
        object.__setattr__(
            self, "executable_commands", _dedupe_sorted(self.executable_commands, label="commands")
        )


@dataclass(frozen=True)
class Capability:
    capability_id: str
    action_types: tuple[ActionType, ...]
    resource_patterns: tuple[str, ...]
    requires_evidence: bool = False

    def __post_init__(self) -> None:
        _require_non_empty("Capability.capability_id", self.capability_id)
        if not self.action_types:
            raise ValueError("Capability.action_types cannot be empty")
        if not self.resource_patterns:
            raise ValueError("Capability.resource_patterns cannot be empty")
        if len(set(self.action_types)) != len(self.action_types):
            raise ValueError("Capability.action_types cannot contain duplicates")
        object.__setattr__(
            self,
            "resource_patterns",
            _dedupe_sorted(self.resource_patterns, label="resource_patterns"),
        )


@dataclass(frozen=True)
class CapabilityRegistry:
    capabilities: tuple[Capability, ...]

    def __post_init__(self) -> None:
        ids = tuple(cap.capability_id for cap in self.capabilities)
        if len(set(ids)) != len(ids):
            raise ValueError("CapabilityRegistry cannot contain duplicate capability IDs")

    def get(self, capability_id: str) -> Capability | None:
        for capability in self.capabilities:
            if capability.capability_id == capability_id:
                return capability
        return None


@dataclass(frozen=True)
class Action:
    action_id: str
    run_id: str
    action_type: ActionType
    capability_id: str
    resource: str
    requested_at: datetime
    payload_ref: str | None = None

    def __post_init__(self) -> None:
        _require_non_empty("Action.action_id", self.action_id)
        _require_non_empty("Action.run_id", self.run_id)
        _require_non_empty("Action.capability_id", self.capability_id)
        object.__setattr__(self, "resource", normalize_path(self.resource))
        _require_utc("Action.requested_at", self.requested_at)
        if self.payload_ref is not None:
            _require_non_empty("Action.payload_ref", self.payload_ref)


@dataclass(frozen=True)
class AuthorizationDecision:
    decision: Decision
    reason: str
    action_id: str
    capability_id: str

    def __post_init__(self) -> None:
        _require_non_empty("AuthorizationDecision.reason", self.reason)
        _require_non_empty("AuthorizationDecision.action_id", self.action_id)
        _require_non_empty("AuthorizationDecision.capability_id", self.capability_id)


@dataclass(frozen=True)
class ModelCompletionEvidence:
    response_log_id: str
    execution_id: str
    context_id: str
    context_hash: str
    artifact_ref: str

    def __post_init__(self) -> None:
        _require_non_empty("ModelCompletionEvidence.response_log_id", self.response_log_id)
        _require_non_empty("ModelCompletionEvidence.execution_id", self.execution_id)
        _require_non_empty("ModelCompletionEvidence.context_id", self.context_id)
        _require_non_empty("ModelCompletionEvidence.context_hash", self.context_hash)
        _require_non_empty("ModelCompletionEvidence.artifact_ref", self.artifact_ref)


@dataclass(frozen=True)
class Observation:
    observation_id: str
    run_id: str
    action_id: str
    observation_type: ObservationType
    occurred_at: datetime
    outcome: str
    artifact_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    model_evidence: ModelCompletionEvidence | None = None

    def __post_init__(self) -> None:
        _require_non_empty("Observation.observation_id", self.observation_id)
        _require_non_empty("Observation.run_id", self.run_id)
        _require_non_empty("Observation.action_id", self.action_id)
        _require_non_empty("Observation.outcome", self.outcome)
        _require_utc("Observation.occurred_at", self.occurred_at)
        object.__setattr__(
            self, "artifact_refs", _dedupe_sorted(self.artifact_refs, label="artifact_refs")
        )
        object.__setattr__(
            self, "evidence_refs", _dedupe_sorted(self.evidence_refs, label="evidence_refs")
        )
        if self.observation_type is ObservationType.MODEL_COMPLETED and self.model_evidence is None:
            raise ValueError("model.completed observations require ModelCompletionEvidence")
