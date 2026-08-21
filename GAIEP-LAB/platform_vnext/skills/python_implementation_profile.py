"""Deterministic validation profile for GS-PY-001.

The profile is intentionally declarative. It is the skill/governance layer that decides which
validators may run; the model cannot add arbitrary shell commands.
"""
from __future__ import annotations

from platform_vnext.skills.validation.command_runner import ValidationCommand


GS_PY_001_VALIDATION = (
    ValidationCommand("ruff-check", ("ruff", "check", "."), 120),
    ValidationCommand("pyright", ("pyright",), 180),
    ValidationCommand("pytest", ("pytest", "-q"), 300),
)

GS_PY_001_ALLOWED_COMMANDS = ("ruff", "pyright", "pytest")
