"""Executable staging harness for the proposed run_task ModelCall wiring.

This intentionally models only the dependency seam, not the production runner. It lets us
validate the feature-flag semantics before the patch is applied to the VPS checkout.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from runner.gateway_client import ChatResult
from runner.provenance_model_call import with_provenance
from runtime.artifact_hooks import ArtifactRegistrar
from runtime.artifact_refs import ArtifactReferenceIndex
from runtime.artifact_store import FileArtifactStore

ModelCall = Callable[[str, str], ChatResult]


@dataclass(frozen=True)
class ProvenanceSettings:
    enabled: bool = False
    fail_closed: bool = True
    artifact_root: str = "artifacts"


def build_model_call(
    default_model_call: ModelCall,
    *,
    settings: ProvenanceSettings,
    repo_root: Path,
    run_id: str,
) -> ModelCall:
    """Mirror the intended production call-site without importing run_task itself."""
    if not settings.enabled:
        return default_model_call

    registrar = ArtifactRegistrar(
        FileArtifactStore(repo_root / settings.artifact_root),
        ArtifactReferenceIndex(repo_root / settings.artifact_root / "index.db"),
    )
    return with_provenance(
        default_model_call,
        repo_root=repo_root,
        run_id=run_id,
        registrar=registrar,
    )
