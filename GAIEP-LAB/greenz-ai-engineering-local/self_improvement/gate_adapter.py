"""Read-only adapter for the existing ruff/pyright/pytest validation boundary."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GateCommand:
    name: str
    command: tuple[str, ...]


@dataclass(frozen=True)
class GateResult:
    name: str
    passed: bool
    return_code: int
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False


class ExternalValidationGate:
    """Execute externally supplied validation commands; never modify source."""

    def __init__(self, commands: Sequence[GateCommand], *, timeout_s: float = 120.0) -> None:
        if not commands:
            raise ValueError("at least one validation command is required")
        if timeout_s <= 0:
            raise ValueError("timeout_s must be positive")
        self._commands = tuple(commands)
        self._timeout_s = timeout_s

    def run(self, workspace: Path) -> tuple[GateResult, ...]:
        """Run every validation command in the supplied workspace."""
        results: list[GateResult] = []
        for spec in self._commands:
            try:
                command = tuple(
                    sys.executable if part == "python" else part
                    for part in spec.command
                )
                completed = subprocess.run(
                    command,
                    cwd=workspace,
                    capture_output=True,
                    text=True,
                    timeout=self._timeout_s,
                    check=False,
                )
            except subprocess.TimeoutExpired as exc:
                results.append(
                    GateResult(
                        name=spec.name,
                        passed=False,
                        return_code=-1,
                        stdout=exc.stdout or "",
                        stderr=exc.stderr or "",
                        timed_out=True,
                    )
                )
                continue
            results.append(
                GateResult(
                    name=spec.name,
                    passed=completed.returncode == 0,
                    return_code=completed.returncode,
                    stdout=completed.stdout,
                    stderr=completed.stderr,
                )
            )
        return tuple(results)

    @staticmethod
    def checks(results: Sequence[GateResult]) -> dict[str, bool]:
        """Convert gate evidence into the check mapping consumed by EvaluationRunner."""
        return {result.name: result.passed for result in results}
