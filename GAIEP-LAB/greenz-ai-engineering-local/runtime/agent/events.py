"""Typed GAIEP runtime event model."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from runtime.agent.contracts import AuthorizationDecision, Decision


class RuntimeEventError(ValueError):
    """Raised when runtime event ordering or payload invariants are violated."""


class RuntimeEventType(StrEnum):
    ACTION_REQUESTED = "action.requested"
    AUTHORIZATION_EVALUATED = "authorization.evaluated"
    ACTION_DENIED = "action.denied"
    ACTION_EXECUTED = "action.executed"
    ACTION_FAILED = "action.failed"
    OBSERVATION_PRODUCED = "observation.produced"


def _require_non_empty(label: str, value: str) -> None:
    if not value.strip():
        raise RuntimeEventError(f"{label} cannot be empty")


def _require_utc(label: str, value: datetime) -> None:
    if value.utcoffset() != timedelta(0):
        raise RuntimeEventError(f"{label} must be timezone-aware UTC")


@dataclass(frozen=True)
class RuntimeEvent:
    event_id: str
    run_id: str
    event_type: RuntimeEventType
    timestamp: datetime
    schema_version: str = "runtime-event-v1"
    action_id: str | None = None
    parent_event_id: str | None = None
    artifact_ref: str | None = None
    payload_refs: tuple[str, ...] = ()
    payload: Mapping[str, str] | None = None

    def __post_init__(self) -> None:
        _require_non_empty("RuntimeEvent.event_id", self.event_id)
        _require_non_empty("RuntimeEvent.run_id", self.run_id)
        _require_non_empty("RuntimeEvent.schema_version", self.schema_version)
        _require_utc("RuntimeEvent.timestamp", self.timestamp)
        if self.action_id is not None:
            _require_non_empty("RuntimeEvent.action_id", self.action_id)
        if self.parent_event_id is not None:
            _require_non_empty("RuntimeEvent.parent_event_id", self.parent_event_id)
        if self.artifact_ref is not None:
            _require_non_empty("RuntimeEvent.artifact_ref", self.artifact_ref)
        if self.payload is not None and self.artifact_ref is None:
            joined = "".join(self.payload.values())
            if len(joined) > 4096:
                raise RuntimeEventError("large event payloads require artifact_ref")


def event_for_authorization(
    *, event_id: str, run_id: str, timestamp: datetime, decision: AuthorizationDecision
) -> RuntimeEvent:
    return RuntimeEvent(
        event_id=event_id,
        run_id=run_id,
        event_type=RuntimeEventType.AUTHORIZATION_EVALUATED,
        timestamp=timestamp,
        action_id=decision.action_id,
        payload={"decision": decision.decision.value, "reason": decision.reason},
    )


def validate_event_trace(events: tuple[RuntimeEvent, ...]) -> None:
    by_id: dict[str, RuntimeEvent] = {}
    auth_by_action: dict[str, AuthorizationDecision | Decision] = {}
    requested: set[str] = set()
    for event in events:
        if event.event_id in by_id:
            raise RuntimeEventError(f"duplicate event_id: {event.event_id}")
        by_id[event.event_id] = event
        if event.parent_event_id and event.parent_event_id not in by_id:
            raise RuntimeEventError("parent event must precede child event")
        if event.event_type is RuntimeEventType.ACTION_REQUESTED:
            if event.action_id is None:
                raise RuntimeEventError("ActionRequested requires action_id")
            requested.add(event.action_id)
        if event.event_type is RuntimeEventType.AUTHORIZATION_EVALUATED:
            if event.action_id is None or event.action_id not in requested:
                raise RuntimeEventError("authorization requires prior ActionRequested")
            value = (event.payload or {}).get("decision")
            auth_by_action[event.action_id] = Decision(value) if value else Decision.DENY
        if (
            event.event_type is RuntimeEventType.ACTION_EXECUTED
            and (
                event.action_id is None
                or auth_by_action.get(event.action_id) is not Decision.ALLOW
            )
        ):
            raise RuntimeEventError("ActionExecuted requires prior ALLOW authorization")
        if (
            event.event_type is RuntimeEventType.ACTION_DENIED
            and (
                event.action_id is None
                or auth_by_action.get(event.action_id) is not Decision.DENY
            )
        ):
            raise RuntimeEventError("ActionDenied requires prior DENY authorization")
