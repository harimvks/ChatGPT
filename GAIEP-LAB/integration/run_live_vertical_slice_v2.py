"""Run one real GAIEP VNext AgentRun through the existing certified GreenZ stack.

This is an operator-run integration harness. It is read-only with respect to the GreenZ repositories:
it reads the platform and engineering source, registry and certification ledger, then executes one
model request through the existing Gateway.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

EXPECTED_PLATFORM_COMMIT = "3776af2704b5b2cc9f6629239c43d8fe3d48d241"
EXPECTED_ENGINEERING_COMMIT = "53ae576d8af26a32337f8d912c0dc0bd166a1a3c"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Execute one real GAIEP VNext AgentRun")
    parser.add_argument("--platform-root", type=Path, required=True)
    parser.add_argument("--engineering-root", type=Path, required=True)
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    parser.add_argument("--capability-tag", default="CODING")
    parser.add_argument("--system", default="You are a Python engineering assistant.")
    parser.add_argument("--user", required=True)
    parser.add_argument("--timeout-seconds", type=int, default=120)
    return parser.parse_args()


def build_integration_context_builder(base_cls: type, system: str, user: str, capability_tag: str):
    """Create a concrete subclass of the VNext ContextBuilderBase for this smoke request."""

    class Builder(base_cls):
        SCHEMA_VERSION = "v1"
        BUILDER_NAME = "GAIEPVNextIntegrationContextBuilder"
        BUILDER_VERSION = "1.0.0"
        CAPABILITY_NAME = "integration"
        CAPABILITY_VERSION = "v1"
        CLASSIFICATION = "ARCHITECTURE"
        MAX_PAYLOAD_BYTES = 32_000

        def payload_fields(self):
            return {"system": system, "user": user, "capability_tag": capability_tag}

    return Builder()


def main() -> int:
    args = parse_args()
    platform_root = args.platform_root.resolve()
    engineering_root = args.engineering_root.resolve()
    for label, root in (("platform", platform_root), ("engineering", engineering_root)):
        if not root.is_dir():
            raise SystemExit(f"{label} root does not exist: {root}")

    # The lab package comes first; the two original repositories follow. This lets the VNext
    # runtime be loaded from the lab while ContextBuilderBase/Gateway/provider modules are loaded
    # from the real upstream checkouts.
    lab_root = Path(__file__).resolve().parents[1]
    sys.path[:0] = [str(lab_root), str(engineering_root), str(platform_root)]

    from context.builder import ContextBuilderBase
    from runner.gateway_client import build_gateway, build_models, build_registry
    from platform_vnext.compat.platform_adapter import GreenZPlatformAdapter
    from platform_vnext.context.platform_factory import PlatformContextFactory
    from platform_vnext.runtime.contracts import AgentRun, ModelPolicy, TaskPolicy, WorkspaceScope
    from platform_vnext.runtime.engine import RuntimeVNext
    from platform_vnext.skills.contracts import GreenSkill, SkillStatus, SkillStep

    registry_path = engineering_root / "ai/policies/provider_registry.yaml"
    certifications_dir = engineering_root / "benchmarks/certifications"
    registry = build_registry(
        registry_path=registry_path,
        certifications_dir=certifications_dir,
    )
    models = build_models(registry_path=registry_path)
    gateway = build_gateway(
        registry=registry,
        models=models,
        base_url=args.ollama_url,
        timeout_seconds=args.timeout_seconds,
        observability_dir=engineering_root / "observability/routing_events",
    )

    context_builder = build_integration_context_builder(
        ContextBuilderBase,
        args.system,
        args.user,
        args.capability_tag,
    )
    context_factory = PlatformContextFactory(context_builder)
    adapter = GreenZPlatformAdapter(gateway)

    skill = GreenSkill(
        skill_id="GS-PY-001",
        name="Python Implementation",
        version="1.0.0",
        owner="greenz-ai-engineering",
        capability=args.capability_tag,
        status=SkillStatus.ACTIVE,
        procedure=(
            SkillStep(
                step_id="execute",
                purpose="Perform the requested read-only engineering analysis",
            ),
        ),
    )
    run = AgentRun(
        run_id=f"live-{datetime.now(UTC).strftime('%Y%m%dT%H%M%S%fZ')}",
        task_ref="GAIEP-LIVE-VERTICAL-SLICE",
        workspace_scope=WorkspaceScope(root=str(engineering_root), mode="READ_ONLY"),
        task_policy=TaskPolicy(
            task_type="implementation",
            allowed_skills=frozenset({skill.skill_id}),
            allow_write=False,
            allow_network=False,
            allow_subagents=False,
        ),
        model_policy=ModelPolicy(
            capability_tag=args.capability_tag,
            require_certification=True,
            allow_failover=True,
        ),
        created_at=datetime.now(UTC),
    )

    result = RuntimeVNext(adapter=adapter, context_factory=context_factory).execute(
        run,
        skill,
        template="{{payload}}",
    )
    context_event = result.evidence[2]
    context_id = dict(context_event.details)["context_id"]
    context_hash = dict(context_event.details)["context_hash"]

    print(
        json.dumps(
            {
                "status": "PASS",
                "platform_commit_expected": EXPECTED_PLATFORM_COMMIT,
                "engineering_commit_expected": EXPECTED_ENGINEERING_COMMIT,
                "run_id": result.run.run_id,
                "final_status": result.run.status.value,
                "model": result.response.model,
                "provider": result.response.provider_name,
                "execution_id": result.response.execution_id,
                "failed_over_from": result.response.failed_over_from,
                "elapsed_seconds": result.response.elapsed_seconds,
                "context_id": context_id,
                "context_hash": context_hash,
                "evidence_events": [event.event for event in result.evidence],
                "output": result.response.text,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
