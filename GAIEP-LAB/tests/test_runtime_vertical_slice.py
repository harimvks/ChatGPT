from __future__ import annotations

from datetime import datetime, timezone

import pytest

from platform_vnext.compat.platform_adapter import AdapterResponse
from platform_vnext.runtime.contracts import AgentRun, ModelPolicy, RunStatus, TaskPolicy, WorkspaceScope
from platform_vnext.runtime.engine import RuntimeVNext
from platform_vnext.skills.contracts import GreenSkill, SkillStatus, SkillStep


class FakeContext:
    def __init__(self) -> None:
        from platform_vnext.context.manifest import AIRequestContext, ContextManifest

        payload = '{"task":"test"}'
        self.manifest = ContextManifest(
            context=AIRequestContext(
                context_id="ctx-vertical-1",
                schema_version="1.0.0",
                builder_name="test-builder",
                builder_version="1.0.0",
                capability_name="Python Implementation",
                capability_version="1.0.0",
                target_type="test",
                target_ref="vertical-slice",
                created_at=datetime.now(timezone.utc),
                content_hash="hash-vertical-1",
                payload=payload,
            ),
            classification="INTERNAL",
            redaction_checked=True,
        )

    def build(self, run, skill):
        return self.manifest


class FakeAdapter:
    def __init__(self) -> None:
        self.requests = []

    def generate(self, request):
        self.requests.append(request)
        return AdapterResponse(
            text="implementation response",
            model="certified-test-model",
            provider_name="test-provider",
            elapsed_seconds=0.01,
            execution_id="exec-1",
            failed_over_from=(),
        )


def make_run() -> AgentRun:
    return AgentRun(
        run_id="run-vertical-1",
        task_ref="task-vertical-1",
        workspace_scope=WorkspaceScope(root="/lab", mode="READ_ONLY"),
        task_policy=TaskPolicy(
            task_type="implementation",
            allowed_skills=frozenset({"GS-PY-001"}),
        ),
        model_policy=ModelPolicy(capability_tag="CODING"),
        created_at=datetime.now(timezone.utc),
    )


def make_skill(skill_id: str = "GS-PY-001") -> GreenSkill:
    return GreenSkill(
        skill_id=skill_id,
        name="Python Implementation" if skill_id == "GS-PY-001" else "Unauthorized",
        version="1.0.0",
        owner="greenz-ai-engineering" if skill_id == "GS-PY-001" else "test",
        capability="CODING",
        status=SkillStatus.ACTIVE,
        prerequisites=(),
        allowed_toolsets=(),
        expected_artifacts=(),
        validation_gates=(),
        evidence_requirements=(),
        procedure=(SkillStep(step_id="implement", purpose="perform implementation"),),
    )


def test_vertical_slice_reaches_accepted() -> None:
    adapter = FakeAdapter()
    result = RuntimeVNext(adapter=adapter, context_factory=FakeContext()).execute(
        make_run(), make_skill(), template="{{ payload }}"
    )

    assert result.run.status is RunStatus.ACCEPTED
    assert result.response.model == "certified-test-model"
    assert result.response.provider_name == "test-provider"
    assert result.evidence[-1].event == "accepted"
    assert [event.event for event in result.evidence] == [
        "planned",
        "authorized",
        "context_ready",
        "skill_ready",
        "executing",
        "validating",
        "evidence_ready",
        "governance",
        "accepted",
    ]
    assert len(adapter.requests) == 1


def test_vertical_slice_rejects_unauthorized_skill() -> None:
    adapter = FakeAdapter()
    with pytest.raises(PermissionError, match="not allowed"):
        RuntimeVNext(adapter=adapter, context_factory=FakeContext()).execute(
            make_run(), make_skill("GS-PY-999"), template="{{ payload }}"
        )
    assert not adapter.requests
