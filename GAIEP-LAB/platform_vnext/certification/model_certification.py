"""Model certification adapter for governed GreenSkill evaluation.

This module is deliberately ledger-neutral: it produces normalized case results that can be
translated into the existing GreenZ certification structures. It does not create a competing
certification database.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from time import monotonic
from typing import Callable, Iterable


class CaseStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    CONDITIONAL = "CONDITIONAL"
    ERROR = "ERROR"


@dataclass(frozen=True)
class CertificationCase:
    case_id: str
    task: str
    capability_tag: str = "CODING"
    repetitions: int = 1


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    status: CaseStatus
    elapsed_seconds: float
    accepted: bool
    validation_summary: tuple[tuple[str, bool], ...] = ()
    failure_reason: str | None = None


@dataclass(frozen=True)
class ModelCertificationReport:
    model_id: str
    skill_id: str
    cases: tuple[CaseResult, ...]

    @property
    def passed(self) -> int:
        return sum(item.status is CaseStatus.PASS for item in self.cases)

    @property
    def failed(self) -> int:
        return sum(item.status is CaseStatus.FAIL for item in self.cases)

    @property
    def conditional(self) -> int:
        return sum(item.status is CaseStatus.CONDITIONAL for item in self.cases)


class CertificationExecutor:
    """Injected execution boundary for one fixed certification case."""

    def __call__(self, case: CertificationCase) -> tuple[bool, tuple[tuple[str, bool], ...], str | None]:
        raise NotImplementedError


class ModelCertificationAdapter:
    """Run a fixed corpus through a skill and normalize results for the existing ledger."""

    def __init__(self, executor: Callable[[CertificationCase], tuple[bool, tuple[tuple[str, bool], ...], str | None]]) -> None:
        self._executor = executor

    def certify(self, *, model_id: str, skill_id: str, corpus: Iterable[CertificationCase]) -> ModelCertificationReport:
        results: list[CaseResult] = []
        for case in corpus:
            if case.repetitions <= 0:
                raise ValueError(f"case {case.case_id} must request at least one repetition")
            for repetition in range(case.repetitions):
                started = monotonic()
                try:
                    accepted, validations, failure_reason = self._executor(case)
                    elapsed = monotonic() - started
                except Exception as exc:  # certification must record execution errors, not hide them
                    elapsed = monotonic() - started
                    results.append(CaseResult(case.case_id, CaseStatus.ERROR, elapsed, False, failure_reason=str(exc)))
                    continue

                status = CaseStatus.PASS if accepted else CaseStatus.FAIL
                if not accepted and any(valid for _, valid in validations):
                    status = CaseStatus.CONDITIONAL
                results.append(CaseResult(case.case_id, status, elapsed, accepted, validations, failure_reason))
        return ModelCertificationReport(model_id=model_id, skill_id=skill_id, cases=tuple(results))
