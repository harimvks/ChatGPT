"""Provider-neutral execution boundary for the real evidence corpus.

This module orchestrates an experiment matrix through an injected runner. It
contains no model/provider logic and never writes to GreenMemory directly;
persistence remains an explicit responsibility of the caller/runtime.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

from .corpus_matrix import CorpusCell
from .model_runner import ModelRequest, ModelResult, ModelRunner
from .task_factory import EngineeringTask


@dataclass(frozen=True)
class CorpusTrial:
    """One observed matrix cell and its model result."""

    cell: CorpusCell
    result: ModelResult


class CorpusRunner:
    """Execute a prevalidated corpus matrix using an injected model runner."""

    def __init__(self, runner: ModelRunner) -> None:
        self._runner = runner

    def run(
        self,
        cells: Sequence[CorpusCell],
        tasks: dict[str, EngineeringTask],
        request_factory: Callable[[CorpusCell, EngineeringTask], ModelRequest],
    ) -> tuple[CorpusTrial, ...]:
        """Run cells deterministically in supplied order.

        The caller supplies task resolution and request construction so this
        layer cannot silently invent tasks, models, scaffolds, or routing.
        """
        trials: list[CorpusTrial] = []
        seen: set[tuple[str, str, str]] = set()
        for cell in cells:
            key = (cell.task_id, cell.model_name, cell.scaffold_name)
            if key in seen:
                raise ValueError(f"duplicate corpus cell: {key}")
            seen.add(key)
            task = tasks.get(cell.task_id)
            if task is None:
                raise KeyError(f"unknown task_id: {cell.task_id}")
            request = request_factory(cell, task)
            result = self._runner.run(request)
            trials.append(CorpusTrial(cell=cell, result=result))
        return tuple(trials)
