from datetime import datetime, timezone

from platform_vnext.runtime.contracts import AgentRun, ModelPolicy, TaskPolicy, WorkspaceScope
from platform_vnext.runtime.engine import RuntimeVNext
from platform_vnext.compat.platform_adapter import AdapterResponse
from platform_vnext.skills.contracts import GreenSkill, SkillStatus
from platform_vnext.subagents.contracts import SubagentRequest
from platform_vnext.subagents.runtime_worker import RuntimeSubagentWorker


class Context:
    def build(self, run, skill):
        from platform_vnext.context.manifest import AIRequestContext, ContextManifest
        context = AIRequestContext(
            context_id="child-context",
            schema_version="1.0.0",
            builder_name="test",
            builder_version="1.0.0",
            capability_name=skill.name,
            capability_version=skill.version,
            target_type="subagent",
            target_ref=run.task_ref,
            created_at=datetime.now(timezone.utc),
            content_hash="child-hash",
            payload='{"payload":"test"}',
        )
        return ContextManifest(context=context, classification="INTERNAL", redaction_checked=True)


class Adapter:
    def generate(self, request):
        assert request.capability_tag == "CODING"
        return AdapterResponse("child answer", "certified-model", "local", 0.1, "exec-child", ())


def skill():
    return GreenSkill(
        skill_id="GS-CHILD",
        name="Child Skill",
        version="1.0.0",
        owner="test",
        capability="CODING",
        status=SkillStatus.ACTIVE,
        prerequisites=(),
        allowed_toolsets=(),
        expected_artifacts=(),
        validation_gates=(),
        evidence_requirements=(),
        procedure=(),
    )


def test_runtime_subagent_reuses_primary_runtime():
    runtime = RuntimeVNext(adapter=Adapter(), context_factory=Context())
    worker = RuntimeSubagentWorker(runtime=runtime, skill_resolver=lambda ref: skill() if ref == "GS-CHILD" else None)
    request = SubagentRequest(
        parent_run_id="parent",
        task_ref="child",
        skill_ref="GS-CHILD",
        workspace_scope=WorkspaceScope(root="/tmp", mode="read-only"),
        task_policy=TaskPolicy(task_type="research"),
        model_policy_ref="CODING",
        token_budget=100,
        max_steps=2,
        timeout_seconds=10,
        depth=1,
    )
    result = worker.worker().run(request)
    assert result.status.value == "COMPLETED"
    assert "model:certified-model" in result.artifact_refs
    assert "execution:exec-child" in result.evidence_refs
