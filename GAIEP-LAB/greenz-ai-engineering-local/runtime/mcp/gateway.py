"""Read-only MCP transport adapter for capability-authorized Runtime execution."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from runtime.agent.contracts import (
    Action,
    ActionType,
    CapabilityAccessMode,
    CapabilityRegistry,
    CapabilityRuntime,
    Decision,
    Observation,
)
from runtime.agent.events import RuntimeEvent, RuntimeEventType
from runtime.agent.local_runtime import LocalRuntime
from runtime.agent.policy import PolicyAuthorizationContext, authorize_with_policy

CapabilityResolver = Callable[[Action, Mapping[str, str]], Observation]

_MAX_INLINE_RESULT_CHARS = 4096
_DENIED_STATUSES = {"unauthorized", "unknown_capability", "invalid_request", "unavailable"}
_FORBIDDEN_CAPABILITY_PREFIXES = ("trade.",)


class McpStatus(StrEnum):
    OK = "ok"
    UNKNOWN_CAPABILITY = "unknown_capability"
    INVALID_REQUEST = "invalid_request"
    UNAUTHORIZED = "unauthorized"
    UNAVAILABLE = "unavailable"
    EXECUTION_FAILED = "execution_failure"


class McpGatewayError(ValueError):
    """Raised for malformed MCP gateway construction."""


def _clean_error(message: str) -> str:
    forbidden = ("/Users/", "SECRET", "TOKEN", "KEY=", "PASSWORD")
    if any(part in message for part in forbidden):
        return "request could not be completed"
    return message


def _require_non_empty(label: str, value: str) -> None:
    if not value.strip():
        raise ValueError(f"{label} cannot be empty")


@dataclass(frozen=True)
class McpRequest:
    request_id: str
    run_id: str
    capability_id: str
    capability_version: str
    arguments: Mapping[str, str]
    requested_at: datetime
    resource: str | None = None

    def __post_init__(self) -> None:
        _require_non_empty("McpRequest.request_id", self.request_id)
        _require_non_empty("McpRequest.run_id", self.run_id)
        _require_non_empty("McpRequest.capability_id", self.capability_id)
        _require_non_empty("McpRequest.capability_version", self.capability_version)
        if self.requested_at.utcoffset() != datetime.now(UTC).utcoffset():
            raise ValueError("McpRequest.requested_at must be timezone-aware UTC")
        if any(not key.strip() for key in self.arguments):
            raise ValueError("McpRequest.arguments cannot contain empty keys")
        if any(key.startswith("__") for key in self.arguments):
            raise ValueError("MCP request cannot use reserved argument keys")
        if self.resource is not None:
            _require_non_empty("McpRequest.resource", self.resource)


@dataclass(frozen=True)
class McpResponse:
    request_id: str
    run_id: str
    capability_id: str
    capability_version: str
    status: McpStatus
    observation: Observation | None = None
    artifact_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    error: str | None = None

    @property
    def is_success(self) -> bool:
        return self.status is McpStatus.OK


class McpCapabilityGateway:
    """Translate MCP requests into authorized Runtime actions.

    The gateway is transport glue only: it performs capability resolution, delegates
    policy decisions to Runtime VNext authorization, and calls Runtime only after
    an ALLOW decision for an available read-only capability.
    """

    def __init__(
        self,
        *,
        registry: CapabilityRegistry,
        policy_context: PolicyAuthorizationContext,
        runtime: LocalRuntime,
        resolvers: Mapping[str, CapabilityResolver],
    ) -> None:
        if policy_context.registry is not registry:
            raise McpGatewayError("MCP gateway must use the policy context registry")
        self.registry = registry
        self.policy_context = policy_context
        self.runtime = runtime
        self.resolvers = dict(resolvers)
        self.events: list[RuntimeEvent] = []

    def handle(self, request: McpRequest) -> McpResponse:
        requested = RuntimeEvent(
            event_id=f"mcp-requested:{request.request_id}",
            run_id=request.run_id,
            event_type=RuntimeEventType.ACTION_REQUESTED,
            timestamp=request.requested_at,
            action_id=request.request_id,
            payload={
                "transport": "mcp",
                "capability_id": request.capability_id,
                "capability_version": request.capability_version,
            },
        )
        self.events.append(requested)
        try:
            return self._handle_checked(request)
        except Exception as exc:  # noqa: BLE001
            self.events.append(RuntimeEvent(
                event_id=f"mcp-failed:{request.request_id}",
                run_id=request.run_id,
                event_type=RuntimeEventType.ACTION_FAILED,
                timestamp=request.requested_at,
                action_id=request.request_id,
                parent_event_id=requested.event_id,
                payload={"failure_class": type(exc).__name__},
            ))
            return self._response(request, McpStatus.EXECUTION_FAILED, error=_clean_error(str(exc)))

    def _handle_checked(self, request: McpRequest) -> McpResponse:
        if request.capability_id.startswith(_FORBIDDEN_CAPABILITY_PREFIXES):
            return self._deny(
                request, McpStatus.UNAUTHORIZED, "future action capabilities are forbidden"
            )
        capability = self.registry.get(request.capability_id, request.capability_version)
        if capability is None:
            status = (
                McpStatus.UNKNOWN_CAPABILITY
                if self.registry.get(request.capability_id) is None
                else McpStatus.UNAUTHORIZED
            )
            return self._deny(request, status, "unknown capability or version")
        if capability.access_mode is not CapabilityAccessMode.READ:
            return self._deny(request, McpStatus.UNAUTHORIZED, "unsupported capability access mode")
        if CapabilityRuntime.MCP_READ_ONLY not in capability.allowed_runtime:
            return self._deny(
                request,
                McpStatus.UNAVAILABLE,
                capability.unavailable_reason or "capability is unavailable over MCP",
            )
        if request.capability_id not in self.resolvers:
            return self._deny(request, McpStatus.UNAVAILABLE, "capability resolver is unavailable")
        action = Action(
            action_id=request.request_id,
            run_id=request.run_id,
            action_type=ActionType.CAPABILITY_READ,
            capability_id=request.capability_id,
            resource=request.resource or capability.resource_patterns[0].rstrip("*"),
            requested_at=request.requested_at,
            payload_ref=f"mcp:{request.request_id}:arguments",
        )
        decision = authorize_with_policy(action, self.policy_context)
        self.events.append(RuntimeEvent(
            event_id=f"mcp-authorized:{request.request_id}",
            run_id=request.run_id,
            event_type=RuntimeEventType.AUTHORIZATION_EVALUATED,
            timestamp=request.requested_at,
            action_id=request.request_id,
            parent_event_id=f"mcp-requested:{request.request_id}",
            payload={
                "decision": decision.decision.value,
                "reason": decision.reason,
                "capability_id": request.capability_id,
                "capability_version": request.capability_version,
            },
        ))
        if decision.decision is Decision.DENY:
            self.events.append(RuntimeEvent(
                event_id=f"mcp-denied:{request.request_id}",
                run_id=request.run_id,
                event_type=RuntimeEventType.ACTION_DENIED,
                timestamp=request.requested_at,
                action_id=request.request_id,
                parent_event_id=f"mcp-authorized:{request.request_id}",
                payload={"reason": decision.reason},
            ))
            return self._response(request, McpStatus.UNAUTHORIZED, error=decision.reason)

        resolver = self.resolvers[request.capability_id]

        def executor(action: Action) -> Observation:
            return resolver(action, request.arguments)

        original_executor = self.runtime.executor
        self.runtime.executor = executor
        try:
            observation = self.runtime.execute(action, decision)
        finally:
            self.runtime.executor = original_executor
        if self._inline_payload_too_large(observation):
            return self._deny(
                request, McpStatus.INVALID_REQUEST, "large responses require artifact refs"
            )
        return self._response(
            request,
            McpStatus.OK,
            observation=observation,
            artifact_refs=observation.artifact_refs,
            evidence_refs=observation.evidence_refs,
        )

    def _deny(self, request: McpRequest, status: McpStatus, reason: str) -> McpResponse:
        event_type = (
            RuntimeEventType.ACTION_DENIED
            if status.value in _DENIED_STATUSES
            else RuntimeEventType.ACTION_FAILED
        )
        self.events.append(RuntimeEvent(
            event_id=f"mcp-denied:{request.request_id}:{len(self.events)}",
            run_id=request.run_id,
            event_type=event_type,
            timestamp=request.requested_at,
            action_id=request.request_id,
            payload={"reason": _clean_error(reason)},
        ))
        return self._response(request, status, error=_clean_error(reason))

    def _response(
        self,
        request: McpRequest,
        status: McpStatus,
        *,
        observation: Observation | None = None,
        artifact_refs: tuple[str, ...] = (),
        evidence_refs: tuple[str, ...] = (),
        error: str | None = None,
    ) -> McpResponse:
        return McpResponse(
            request_id=request.request_id,
            run_id=request.run_id,
            capability_id=request.capability_id,
            capability_version=request.capability_version,
            status=status,
            observation=observation,
            artifact_refs=artifact_refs,
            evidence_refs=evidence_refs,
            error=_clean_error(error) if error else None,
        )

    @staticmethod
    def _inline_payload_too_large(observation: Observation) -> bool:
        inline = "".join(observation.evidence_refs)
        return len(inline) > _MAX_INLINE_RESULT_CHARS and not observation.artifact_refs
