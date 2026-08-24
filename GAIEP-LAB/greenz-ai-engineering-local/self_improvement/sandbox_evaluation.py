"""Sandbox-backed external evaluation for research candidates."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .evaluation import EvaluationResult
from .gate_adapter import ExternalValidationGate
from .sandbox import CandidateSandbox
from .task_factory import EngineeringTask


@dataclass(frozen=True)
class SandboxEvaluation:
    evaluation: EvaluationResult
    files: tuple[str, ...]
    stdout_by_check: Mapping[str, str]
    stderr_by_check: Mapping[str, str]


class SandboxEvaluator:
    """Materialize candidate files, run external gates, then remove the workspace."""

    def __init__(self, sandbox: CandidateSandbox, gate: ExternalValidationGate) -> None:
        self._sandbox = sandbox
        self._gate = gate

    def evaluate(self, task: EngineeringTask, files: Mapping[str, str]) -> SandboxEvaluation:
        workspace = self._sandbox.materialize(files)
        try:
            results = self._gate.run(workspace.path)
            checks = self._gate.checks(results)
            passed = all(checks.values())
            reward = sum(1.0 for value in checks.values() if value) / len(checks)
            failure_class = None
            if not passed:
                if not checks.get("pytest", True):
                    failure_class = "test_failure"
                elif not checks.get("pyright", True):
                    failure_class = "type_failure"
                elif not checks.get("ruff", True):
                    failure_class = "lint_failure"
                else:
                    failure_class = "acceptance_failure"
            evaluation = EvaluationResult(
                task_id=task.task_id,
                passed=passed,
                reward=reward,
                checks=checks,
                failure_class=failure_class,
            )
            return SandboxEvaluation(
                evaluation=evaluation,
                files=workspace.files,
                stdout_by_check={r.name: r.stdout for r in results},
                stderr_by_check={r.name: r.stderr for r in results},
            )
        finally:
            workspace.cleanup()
