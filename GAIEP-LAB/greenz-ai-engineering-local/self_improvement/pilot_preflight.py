"""Preflight checks for the local GAIEP self-improvement pilot."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class PreflightCheck:
    name: str
    passed: bool
    detail: str


def check_model_binding(logical_name: str) -> PreflightCheck:
    key = "GAIEP_MODEL_" + "".join(ch if ch.isalnum() else "_" for ch in logical_name.upper())
    value = os.getenv(key)
    if value:
        return PreflightCheck(key, True, value)
    return PreflightCheck(key, False, "missing")


def check_required_environment(model_names: tuple[str, ...]) -> tuple[PreflightCheck, ...]:
    return tuple(check_model_binding(name) for name in model_names)


def assert_preflight(checks: tuple[PreflightCheck, ...]) -> None:
    failures = [check for check in checks if not check.passed]
    if failures:
        details = "; ".join(f"{item.name}: {item.detail}" for item in failures)
        raise RuntimeError(f"pilot preflight failed: {details}")
