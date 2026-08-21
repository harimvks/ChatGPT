"""Gate C smoke runner for a real GreenZ Gateway execution.

This is intentionally read-only: it invokes the existing Gateway and prints normalized evidence;
it never writes to a GreenZ repository and never calls a provider directly.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from uuid import uuid4

from platform_vnext.compat.platform_adapter import AdapterRequest, PlatformAdapter
from platform_vnext.context.manifest import AIRequestContext, ContextManifest
from platform_vnext.integration.existing_gateway_bootstrap import build_existing_gateway
from platform_vnext.runtime.contracts import AgentRun, ModelPolicy, RunStatus, TaskPolicy, WorkspaceScope
from platform_vnext.runtime.engine import RuntimeVNext
from platform_vnext.skills.contracts import GreenSkill, SkillStatus, SkillStep


@dataclass(frozen=True)
class StaticContextFactory:
    capability: str
    payload: str

    def build(self, run: AgentRun, skill: GreenSkill) -> ContextManifest:
        created = datetime.now(UTC)
        digest = hashlib.sha256(self.payload.encode("utf-8")).hexdigest()
        context = AIRequestContext(
            context_id=f"ctx-{run.run_id}",
            schema_version="v1",
            builder_name="GateCSmokeContextBuilder",
            builder_version="1",
            capability_name=self.capability,
            capability_version=skill.version,
            target_type="smoke",
            target_ref=run.task_ref,
            created_at=created,
            content_hash=digest,
            payload=self.payload,
        )
        return ContextManifest(context=context, classification="ARCHITECTURE", redaction_checked=True)


class AdapterProxy:
    def __init__(self, adapter: PlatformAdapter) -> None:
        self._adapter = adapter

    def generate(self, request):
        return self._adapter.generate(request)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--certifications", type=Path, required=True)
    parser.add_argument("--engineering-path", type=Path, required=True)
    parser.add_argument("--platform-path", type=Path, required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    parser.add_argument("--capability", default="CODING")
    parser.add_argument("--template", default="{{payload}}")
    parser.add_argument("--payload", default="Return a one-line confirmation that the Gateway smoke test reached the provider.")
    args = parser.parse_args()

    import sys

    sys.path.insert(0, str(args.engineering_path))
    sys.path.insert(0, str(args.platform_path))

    runtime = build_existing_gateway(
        registry_path=args.registry,
        certifications_dir=args.certifications,
        base_url=args.base_url,
    )

    run = AgentRun(
        run_id=f"smoke-{uuid4().hex}",
        task_ref="phase9-gateway-smoke",
        workspace_scope=WorkspaceScope(root=str(args.engineering_path), mode="READ_ONLY"),
        task_policy=TaskPolicy(
            task_type="READ_ONLY_SMOKE",
            allowed_skills=frozenset({"GS-GATEWAY-SMOKE"}),
            allow_write=False,
            allow_network=False,
            allow_subagents=False,
        ),
        model_policy=ModelPolicy(capability_tag=args.capability),
        status=RunStatus.REQUESTED,
    )
    skill = GreenSkill(
        skill_id="GS-GATEWAY-SMOKE",
        name="Gateway Read-Only Smoke",
        version="1.0",
        owner="GAIEP-LAB",
        capability=args.capability,
        status=SkillStatus.ACTIVE,
        procedure=(SkillStep("smoke", "Invoke the existing GreenZ Gateway without mutation"),),
    )

    class ContextAdapter:
        def __init__(self, adapter: PlatformAdapter) -> None:
            self._adapter = adapter

        def generate(self, request):
            return self._adapter.generate(request)

    result = RuntimeVNext(
        adapter=ContextAdapter(runtime.adapter),
        context_factory=StaticContextFactory(args.capability, args.payload),
    ).execute(run, skill, template=args.template)

    print(json.dumps({
        "status": result.run.status.value,
        "run_id": result.run.run_id,
        "model": result.response.model,
        "provider": result.response.provider_name,
        "elapsed_seconds": result.response.elapsed_seconds,
        "execution_id": result.response.execution_id,
        "failed_over_from": list(result.response.failed_over_from),
        "context_hash": result.evidence[2].details[1][1],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
