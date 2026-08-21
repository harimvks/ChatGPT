"""Local integration harness for the GAIEP VNext vertical slice.

Run this from an environment where the pinned greenz-ai-platform source is importable. The
harness intentionally does not start Ollama or select a model itself; the existing platform
composition root remains responsible for registry, certification, policy, Gateway, and provider
construction.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import sys
from pathlib import Path


EXPECTED_PLATFORM_COMMIT = "3776af2704b5b2cc9f6629239c43d8fe3d48d241"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run GAIEP VNext against the real platform")
    parser.add_argument("--platform-root", type=Path, required=True)
    parser.add_argument("--capability-name", required=True)
    parser.add_argument("--capability-version", required=True)
    parser.add_argument("--capability-tag", required=True)
    parser.add_argument("--template", required=True)
    parser.add_argument("--context-id", default="gaiep-real-integration")
    parser.add_argument("--target-type", default="integration-test")
    parser.add_argument("--target-ref", default="gaiep-runtime-vnext")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    platform_root = args.platform_root.resolve()
    if not platform_root.exists():
        raise SystemExit(f"platform root does not exist: {platform_root}")

    sys.path.insert(0, str(platform_root))

    try:
        from context.builder import ContextBuilderBase
        from gateway.gateway import Gateway
    except ImportError as exc:
        raise SystemExit(
            "Unable to import greenz-ai-platform from --platform-root. "
            "Run this harness from the environment containing the pinned platform source."
        ) from exc

    # Import check is deliberately explicit. Construction of the actual Gateway depends on the
    # deployment's existing composition root and certified registry; the harness must not invent
    # one. Operators should wire that composition in the adapter integration module for their
    # environment rather than bypassing certification.
    result = {
        "harness": "gaiep-real-platform",
        "platform_root": str(platform_root),
        "expected_platform_commit": EXPECTED_PLATFORM_COMMIT,
        "imports": {
            "ContextBuilderBase": f"{ContextBuilderBase.__module__}.{ContextBuilderBase.__name__}",
            "Gateway": f"{Gateway.__module__}.{Gateway.__name__}",
        },
        "request": {
            "capability_name": args.capability_name,
            "capability_version": args.capability_version,
            "capability_tag": args.capability_tag,
            "context_id": args.context_id,
            "target_type": args.target_type,
            "target_ref": args.target_ref,
            "template": args.template,
        },
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "status": "PLATFORM_IMPORTS_VERIFIED",
        "next": "Wire the deployment's existing certified Gateway composition root; do not construct a parallel registry or provider here.",
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
