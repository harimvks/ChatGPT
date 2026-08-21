"""Canonical references for the existing GreenZ engineering certification corpus.

The corpus is referenced, not copied: source prompts/artifacts remain owned by greenz-ai-engineering.
"""
from __future__ import annotations

from dataclasses import dataclass

from .model_certification import CertificationCase


@dataclass(frozen=True)
class GreenZCorpusReference:
    benchmark_id: str
    source_repo: str
    corpus_version: int
    reference_artifact: str
    repetitions: int


# Baseline references selected from the existing certification evidence. These are not new
# benchmarks. The existing repository remains authoritative for exact prompt/artifact content.
GREENZ_ENGINEERING_CORPUS = (
    GreenZCorpusReference(
        benchmark_id="ENG-CM-112",
        source_repo="harimvks/greenz-ai-engineering",
        corpus_version=3,
        reference_artifact="benchmarks/artifacts/CERT-SWEEP-ENG-CM-112-QWEN3627B-20260816T101111-R3.txt",
        repetitions=3,
    ),
    GreenZCorpusReference(
        benchmark_id="ENG-CM-113",
        source_repo="harimvks/greenz-ai-engineering",
        corpus_version=2,
        reference_artifact="benchmarks/artifacts/CERT-SWEEP-ENG-CM-113-QWEN3627B-20260820T184754-R2.txt",
        repetitions=9,
    ),
    GreenZCorpusReference(
        benchmark_id="ENG-CM-114",
        source_repo="harimvks/greenz-ai-engineering",
        corpus_version=2,
        reference_artifact="benchmarks/artifacts/CERT-SWEEP-ENG-CM-114-QWEN3627B-20260820T185642-R2.txt",
        repetitions=3,
    ),
)


def certification_cases() -> tuple[CertificationCase, ...]:
    return tuple(
        CertificationCase(
            case_id=item.benchmark_id,
            task=f"Execute existing GreenZ engineering benchmark {item.benchmark_id} from the authoritative repository artifact.",
            capability_tag="CODING",
            repetitions=item.repetitions,
        )
        for item in GREENZ_ENGINEERING_CORPUS
    )
