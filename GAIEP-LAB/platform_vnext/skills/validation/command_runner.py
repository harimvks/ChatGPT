"""Allowlisted validation command execution for coding skills.

Commands are declared by the skill, not invented by the model. The runner executes only the
configured argv and records stdout/stderr/return code for evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
from typing import Sequence


@dataclass(frozen=True)
class ValidationCommand:
    name: str
    argv: tuple[str, ...]
    timeout_seconds: int = 120


@dataclass(frozen=True)
class CommandResult:
    name: str
    argv: tuple[str, ...]
    return_code: int
    stdout: str
    stderr: str
    timed_out: bool = False

    @property
    def passed(self) -> bool:
        return self.return_code == 0 and not self.timed_out


class ValidationCommandRunner:
    def __init__(self, *, workspace: Path, allowed_commands: Sequence[str]) -> None:
        self._workspace = workspace.resolve()
        self._allowed = frozenset(allowed_commands)

    def run(self, command: ValidationCommand) -> CommandResult:
        if not command.argv or command.argv[0] not in self._allowed:
            raise PermissionError(f"validation command is not allowlisted: {command.argv!r}")
        if command.timeout_seconds <= 0:
            raise ValueError("validation timeout must be positive")

        try:
            completed = subprocess.run(
                command.argv,
                cwd=self._workspace,
                text=True,
                capture_output=True,
                timeout=command.timeout_seconds,
                check=False,
            )
            return CommandResult(
                name=command.name,
                argv=command.argv,
                return_code=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
            )
        except subprocess.TimeoutExpired as exc:
            return CommandResult(
                name=command.name,
                argv=command.argv,
                return_code=-1,
                stdout=exc.stdout or "",
                stderr=exc.stderr or "",
                timed_out=True,
            )
