"""Adapt GAIEP certification YAML artifacts into research tasks.

The adapter is intentionally read-only and dependency-free. It extracts the
stable certification metadata needed by the self-improvement loop without
coupling the research package to the production certification implementation.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from .task_factory import EngineeringTask, TaskFactory


@dataclass(frozen=True)
class CertificationRecord:
    certification_id: str
    capability: str
    model_name: str
    benchmark_id: str
    corpus_version: int | None
    result: str
    functional: bool | None
    ruff: int | None
    pyright: int | None
    latency_s: float | None
    backstop: int | None
    detail: str = ""


_FIELD = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$")


def _scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        return value[1:-1]
    return value


def parse_certification(text: str) -> CertificationRecord:
    """Parse the flat metadata used by GAIEP certification artifacts."""
    values: dict[str, str] = {}
    section = ""
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        is_nested = raw[:1].isspace()
        if line.endswith(":") and not is_nested:
            section = line[:-1]
            continue
        match = _FIELD.match(line)
        if not match:
            continue
        key, value = match.groups()
        if section == "configuration" and is_nested:
            continue
        values[key] = _scalar(value)

    def integer(name: str) -> int | None:
        value = values.get(name)
        return int(value) if value not in (None, "", "null") else None

    def number(name: str) -> float | None:
        value = values.get(name)
        return float(value) if value not in (None, "", "null") else None

    def boolean(name: str) -> bool | None:
        value = values.get(name)
        if value is None:
            return None
        if value.lower() == "true":
            return True
        if value.lower() == "false":
            return False
        return None

    required = ("certification_id", "capability", "model_name", "benchmark_id", "result")
    missing = [name for name in required if name not in values]
    if missing:
        raise ValueError(f"missing certification fields: {', '.join(missing)}")

    return CertificationRecord(
        certification_id=values["certification_id"],
        capability=values["capability"],
        model_name=values["model_name"],
        benchmark_id=values["benchmark_id"],
        corpus_version=integer("corpus_version"),
        result=values["result"],
        functional=boolean("functional"),
        ruff=integer("ruff"),
        pyright=integer("pyright"),
        latency_s=number("latency_s"),
        backstop=integer("backstop"),
        detail=values.get("detail", ""),
    )


def load_certifications(paths: Iterable[Path]) -> list[CertificationRecord]:
    """Load certification artifacts in deterministic path order."""
    records: list[CertificationRecord] = []
    for path in sorted(paths, key=lambda item: str(item)):
        records.append(parse_certification(path.read_text(encoding="utf-8")))
    return records


def certification_to_task(record: CertificationRecord) -> EngineeringTask:
    """Represent an observed certification case as a research task."""
    factory = TaskFactory()
    failure = record.detail or record.result
    return factory.from_seed(
        task_type="debug" if record.result.upper() != "PASS" else "review",
        title=f"Certification follow-up: {record.benchmark_id}",
        objective=(
            f"Investigate the observed {record.result} certification outcome for "
            f"{record.model_name} on {record.benchmark_id}; reproduce and address "
            f"the recorded evidence: {failure}."
        ),
        source="certification_corpus",
        difficulty=3 if record.result.upper() != "PASS" else 2,
        acceptance=("pytest", "ruff", "pyright"),
        constraints=(
            f"certification_id={record.certification_id}",
            f"corpus_version={record.corpus_version}",
            "research_only=true",
        ),
    )
