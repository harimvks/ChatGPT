"""Deterministic validation helpers for real GAIEP evidence-corpus runs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .experiment import ExperimentArm, ExperimentPlan


@dataclass(frozen=True)
class CorpusCell:
    task_id: str
    model_name: str
    scaffold_name: str


@dataclass(frozen=True)
class CorpusValidation:
    expected_cells: int
    observed_cells: int
    duplicate_cells: tuple[CorpusCell, ...]
    missing_cells: tuple[CorpusCell, ...]

    @property
    def passed(self) -> bool:
        return not self.duplicate_cells and not self.missing_cells and self.observed_cells == self.expected_cells


def expected_cells(plan: ExperimentPlan) -> tuple[CorpusCell, ...]:
    return tuple(
        CorpusCell(task_id, arm.model_name, arm.scaffold_name)
        for task_id in plan.task_ids
        for arm in plan.arms
    )


def validate_cells(plan: ExperimentPlan, observed: Iterable[CorpusCell]) -> CorpusValidation:
    """Validate a completed corpus without executing or mutating anything."""
    expected = set(expected_cells(plan))
    observed_list = list(observed)
    seen: set[CorpusCell] = set()
    duplicates: list[CorpusCell] = []
    for cell in observed_list:
        if cell in seen:
            duplicates.append(cell)
        seen.add(cell)
    return CorpusValidation(
        expected_cells=len(expected),
        observed_cells=len(observed_list),
        duplicate_cells=tuple(sorted(set(duplicates), key=_sort_key)),
        missing_cells=tuple(sorted(expected - seen, key=_sort_key)),
    )


def _sort_key(cell: CorpusCell) -> tuple[str, str, str]:
    return (cell.task_id, cell.model_name, cell.scaffold_name)
