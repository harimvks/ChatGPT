"""Bridge for using an existing GreenZ AI Platform ContextBuilderBase instance."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Protocol

from platform_vnext.runtime.contracts import AgentRun
from platform_vnext.skills.contracts import GreenSkill


class PlatformContextBuilder(Protocol):
    """The subset of the upstream ContextBuilderBase contract VNext requires."""

    def build(
        self,
        *,
        context_id: str,
        target_type: str,
        target_ref: str,
        created_at: datetime,
    ) -> Any:
        ...


class PlatformContextFactory:
    """Adapt an instantiated upstream context builder to the VNext ContextFactory protocol.

    The upstream builder remains responsible for deterministic serialization, payload budgeting,
    forbidden-content scanning, hashing, classification, and the ContextManifest construction.
    VNext only supplies execution identity and target metadata.
    """

    def __init__(self, builder: PlatformContextBuilder) -> None:
        self._builder = builder

    def build(self, run: AgentRun, skill: GreenSkill) -> Any:
        return self._builder.build(
            context_id=f"{run.run_id}:context",
            target_type=skill.capability,
            target_ref=run.task_ref,
            created_at=datetime.now(timezone.utc),
        )
