"""Optional runner-side provenance wrapper for the Gateway ModelCall.

This file is staged here for later VPS integration. It deliberately does not modify the
production runner until the exact source checkout is available for a surgical patch.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from runner.gateway_client import ChatResult
from runner.model_provenance_integration import build_artifact_registrar, persist_chat_result
from runtime.artifact_hooks import ArtifactRegistrar

ModelCall = Callable[[str, str], ChatResult]


def with_provenance(
    model_call: ModelCall,
    *,
    repo_root: Path,
    run_id: str,
    registrar: ArtifactRegistrar | None = None,
    protected: bool = False,
) -> ModelCall:
    """Wrap an existing ModelCall without changing its return value.

    A successful Gateway response is persisted through the GAIEP artifact/provenance layer.
    Provider exceptions propagate unchanged; provenance persistence failures also propagate so
    the governed path cannot silently claim an auditable completion that was not recorded.
    """
    artifact_registrar = registrar or build_artifact_registrar(repo_root=repo_root)

    def call(system: str, user: str) -> ChatResult:
        result = model_call(system, user)
        persist_chat_result(
            artifact_registrar,
            result=result,
            run_id=run_id,
            request_id=result.execution_id,
            protected=protected,
            at=datetime.now(UTC),
        )
        return result

    return call
