from datetime import UTC, datetime

import pytest

from platform_vnext.context import ContextBuilderBase
from platform_vnext.runtime.contracts import (
    AgentRun,
    ModelPolicy,
    TaskPolicy,
    WorkspaceScope,
    derive_child_policy,
)
from platform_vnext.skills.contracts import GreenSkill, SkillStatus, SkillStep
from platform_vnext.subagents.contracts import SubagentRequest


class ExampleBuilder(ContextBuilderBase):
    SCHEMA_VERSION = "1"
    BUILDER_NAME = "ExampleBuilder"
    BUILDER_VERSION = "1"
    CAPABILITY_NAME = "TEST"
    CAPABILITY_VERSION = "1"
    CLASSIFICATION = "INTERNAL"
    MAX_PAYLOAD_BYTES = 1024

    def payload_fields(self):
        return {"b": 2, "a": 1}


def make_run() -> AgentRun:
    return AgentRun(
        run_id="run-1",
        task_ref="task-1",
        workspace_scope=WorkspaceScope(root="/lab", mode="READ_WRITE"),
        task_policy=TaskPolicy(
            task_type="implementation",
            allowed_tools=frozenset({"READ_SOURCE", "WRITE_WORKSPACE"}),
            allowed_skills=frozenset({"GS-PY-001"}),
            allow_write=True,
            allow_network=False,
            allow_subagents=True,
        ),
        model_policy=ModelPolicy(capability_tag="CODING"),
        child_budget_tokens=1000,
        child_budget_count=1,
        max_subagent_depth=1,
    )


def test_context_is_deterministic_and_redaction_checked():
    now = datetime.now(UTC)
    first = ExampleBuilder().build(context_id="ctx-1", target_type="test", target_ref="1", created_at=now)
    second = ExampleBuilder().build(context_id="ctx-2", target_type="test", target_ref="1", created_at=now)
    assert first.context.payload == '{"a": 1, "b": 2}'
    assert first.context.content_hash == second.context.content_hash
    assert first.redaction_checked is True
    assert first.classification == "INTERNAL"


def test_context_fails_closed_on_budget():
    class TinyBuilder(ExampleBuilder):
        MAX_PAYLOAD_BYTES = 4

    with pytest.raises(ValueError, match="exceeds budget"):
        TinyBuilder().build(
            context_id="ctx-1", target_type="test", target_ref="1", created_at=datetime.now(UTC)
        )


def test_context_rejects_credential_like_value():
    class SecretBuilder(ExampleBuilder):
        def payload_fields(self):
            return {"api_key": "abcdefgh12345678"}

    with pytest.raises(ValueError, match="forbidden"):
        SecretBuilder().build(
            context_id="ctx-1", target_type="test", target_ref="1", created_at=datetime.now(UTC)
        )


def test_child_policy_cannot_expand_authority():
    child = derive_child_policy(make_run(), allow_write=True)
    assert child.allowed_tools == frozenset({"READ_SOURCE", "WRITE_WORKSPACE"})
    assert child.allow_write is True
    assert child.allow_subagents is False


def test_subagent_request_rejects_recursive_policy():
    parent = make_run()
    with pytest.raises(ValueError, match="recursive"):
        SubagentRequest(
            parent_run_id=parent.run_id,
            task_ref="child",
            skill_ref="GS-PY-001",
            workspace_scope=parent.workspace_scope,
            task_policy=TaskPolicy(task_type="review", allow_subagents=True),
            model_policy_ref="coding",
            token_budget=100,
            max_steps=5,
            timeout_seconds=30,
        )


def test_skill_requires_procedure():
    with pytest.raises(ValueError, match="at least one"):
        GreenSkill(
            skill_id="GS-X",
            name="Bad",
            version="1",
            owner="test",
            capability="CODING",
            status=SkillStatus.ACTIVE,
            procedure=(),
        )


def test_skill_step_has_positive_attempt_budget():
    with pytest.raises(ValueError, match="max_attempts"):
        SkillStep(step_id="x", purpose="x", max_attempts=0)
