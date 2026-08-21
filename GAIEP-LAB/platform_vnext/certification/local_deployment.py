"""Deployment adapter boundary for running the fixed corpus against a real local model.

The adapter is intentionally provider-neutral. A caller supplies a governed case executor that
already knows how to invoke the existing GreenZ Gateway. This module adds run metadata and keeps
certification output separate from the upstream ledger until explicitly promoted.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from .corpus_runner import GreenZCorpusRunner
from .model_certification import CertificationCase, ModelCertificationReport


@dataclass(frozen=True)
class DeploymentIdentity:
    model_id: str
    provider: str
    runtime_version: str
    artifact_digest: str | None = None
    quantization: str | None = None
    hardware: str | None = None


@dataclass(frozen=True)
class LocalCertificationRun:
    identity: DeploymentIdentity
    started_at: datetime
    report: ModelCertificationReport


class LocalDeploymentCertificationAdapter:
    def __init__(
        self,
        identity: DeploymentIdentity,
        executor: Callable[[CertificationCase], tuple[bool, tuple[tuple[str, bool], ...], str | None]],
    ) -> None:
        self.identity = identity
        self._runner = GreenZCorpusRunner(executor)

    def run(self) -> LocalCertificationRun:
        started = datetime.now(timezone.utc)
        report = self._runner.run(model_id=self.identity.model_id)
        return LocalCertificationRun(identity=self.identity, started_at=started, report=report)
