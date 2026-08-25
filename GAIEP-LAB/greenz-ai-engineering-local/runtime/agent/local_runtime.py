"""Minimal local runtime shell for GAIEP contract tests."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from runtime.agent.contracts import (
    Action,
    AuthorizationDecision,
    Decision,
    Observation,
    ObservationType,
)
from runtime.agent.events import RuntimeEvent, RuntimeEventType

Executor = Callable[[Action], Observation]


@dataclass
class LocalRuntime:
    executor: Executor
    events: list[RuntimeEvent] = field(default_factory=list)
    executed_actions: list[str] = field(default_factory=list)
    is_shutdown: bool = False

    def execute(self, action: Action, decision: AuthorizationDecision) -> Observation:
        now = datetime.now(UTC)
        self.events.append(RuntimeEvent(
            event_id=f"requested:{action.action_id}",
            run_id=action.run_id,
            event_type=RuntimeEventType.ACTION_REQUESTED,
            timestamp=now,
            action_id=action.action_id,
        ))
        self.events.append(RuntimeEvent(
            event_id=f"authorized:{action.action_id}",
            run_id=action.run_id,
            event_type=RuntimeEventType.AUTHORIZATION_EVALUATED,
            timestamp=now,
            action_id=action.action_id,
            payload={"decision": decision.decision.value, "reason": decision.reason},
        ))
        if self.is_shutdown:
            raise RuntimeError("runtime is shut down")
        if decision.decision is Decision.DENY:
            self.events.append(RuntimeEvent(
                event_id=f"denied:{action.action_id}",
                run_id=action.run_id,
                event_type=RuntimeEventType.ACTION_DENIED,
                timestamp=now,
                action_id=action.action_id,
                payload={"reason": decision.reason},
            ))
            return Observation(
                observation_id=f"denied:{action.action_id}",
                run_id=action.run_id,
                action_id=action.action_id,
                observation_type=ObservationType.TOOL_FAILED,
                occurred_at=now,
                outcome="denied",
            )
        try:
            self.executed_actions.append(action.action_id)
            observation = self.executor(action)
            self.events.append(RuntimeEvent(
                event_id=f"executed:{action.action_id}",
                run_id=action.run_id,
                event_type=RuntimeEventType.ACTION_EXECUTED,
                timestamp=now,
                action_id=action.action_id,
            ))
            self.events.append(RuntimeEvent(
                event_id=f"observed:{observation.observation_id}",
                run_id=action.run_id,
                event_type=RuntimeEventType.OBSERVATION_PRODUCED,
                timestamp=observation.occurred_at,
                action_id=action.action_id,
                payload_refs=observation.artifact_refs,
            ))
            return observation
        except Exception as exc:  # noqa: BLE001
            self.events.append(RuntimeEvent(
                event_id=f"failed:{action.action_id}",
                run_id=action.run_id,
                event_type=RuntimeEventType.ACTION_FAILED,
                timestamp=now,
                action_id=action.action_id,
                payload={"failure_class": type(exc).__name__},
            ))
            raise

    def shutdown(self) -> None:
        self.is_shutdown = True
