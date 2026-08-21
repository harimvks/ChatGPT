from __future__ import annotations

from datetime import datetime, timezone

from platform_vnext.context.platform_factory import PlatformContextFactory


class FakePlatformBuilder:
    def __init__(self) -> None:
        self.calls = []

    def build(self, *, context_id, target_type, target_ref, created_at):
        self.calls.append((context_id, target_type, target_ref, created_at))
        return {"context_id": context_id, "classification": "INTERNAL"}


class Run:
    run_id = "run-123"
    task_ref = "task-456"


class Skill:
    capability = "CODING"


def test_factory_delegates_context_policy_to_platform_builder() -> None:
    builder = FakePlatformBuilder()
    factory = PlatformContextFactory(builder)

    result = factory.build(Run(), Skill())

    assert result["context_id"] == "run-123:context"
    assert builder.calls
    context_id, target_type, target_ref, created_at = builder.calls[0]
    assert context_id == "run-123:context"
    assert target_type == "CODING"
    assert target_ref == "task-456"
    assert created_at.tzinfo is timezone.utc
