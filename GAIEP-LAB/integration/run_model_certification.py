"""Operator entrypoint for a local GS-PY-001 certification run.

This command intentionally stops at the governed deployment callback. The callback must be wired
by the local environment to the existing GreenZ Gateway; no direct provider call is implemented
here and no upstream repository is modified.
"""
from __future__ import annotations

import argparse
import json

from platform_vnext.certification.local_deployment import (
    DeploymentIdentity,
    LocalDeploymentCertificationAdapter,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--provider", default="ollama")
    parser.add_argument("--runtime-version", required=True)
    parser.add_argument("--digest")
    parser.add_argument("--quantization")
    parser.add_argument("--hardware")
    args = parser.parse_args()

    def execute(_case):
        raise RuntimeError(
            "Local GreenZ Gateway callback is not wired. Connect this callback to the existing "
            "CertifiedProviderRegistry/Gateway path before running certification."
        )

    run = LocalDeploymentCertificationAdapter(
        DeploymentIdentity(
            model_id=args.model,
            provider=args.provider,
            runtime_version=args.runtime_version,
            artifact_digest=args.digest,
            quantization=args.quantization,
            hardware=args.hardware,
        ),
        execute,
    ).run()

    print(json.dumps({
        "model": run.identity.model_id,
        "provider": run.identity.provider,
        "runtime_version": run.identity.runtime_version,
        "status": "GATEWAY_CALLBACK_REQUIRED",
        "cases": len(run.report.cases),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
