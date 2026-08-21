"""Run the existing GreenZ engineering certification references through the adapter."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .greenZ_corpus import GREENZ_ENGINEERING_CORPUS, GreenZCorpusReference
from .model_certification import CertificationCase, ModelCertificationAdapter, ModelCertificationReport


@dataclass(frozen=True)
class CorpusExecution:
    benchmark_id: str
    reference: GreenZCorpusReference


class GreenZCorpusRunner:
    """Keep corpus selection fixed while delegating execution to an injected local runner."""

    def __init__(
        self,
        executor: Callable[[CertificationCase], tuple[bool, tuple[tuple[str, bool], ...], str | None]],
    ) -> None:
        self._adapter = ModelCertificationAdapter(executor)

    def run(self, *, model_id: str, skill_id: str = "GS-PY-001") -> ModelCertificationReport:
        cases = tuple(
            CertificationCase(
                case_id=item.benchmark_id,
                task=f"Run authoritative GreenZ artifact: {item.reference_artifact}",
                capability_tag="CODING",
                repetitions=item.repetitions,
            )
            for item in GREENZ_ENGINEERING_CORPUS
        )
        return self._adapter.certify(model_id=model_id, skill_id=skill_id, corpus=cases)
