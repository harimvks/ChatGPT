"""Controlled engineering-task generation for GAIEP research.

The first version is intentionally deterministic: it turns observed GreenZ
engineering signals into candidate tasks. A future model-based generator may
propose tasks, but all generated tasks must pass this same schema/filtering
boundary before execution.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class EngineeringTask:
    task_id: str
    task_type: str
    title: str
    objective: str
    repository_path: str | None = None
    source: str = "seed"
    difficulty: int = 1
    acceptance: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class TaskFactory:
    """Create reproducible candidate tasks without executing them."""

    ALLOWED_TYPES = frozenset({"implementation", "refactor", "debug", "testing", "review"})

    def from_seed(self, *, task_type: str, title: str, objective: str,
                  repository_path: str | None = None, acceptance: Iterable[str] = (),
                  constraints: Iterable[str] = (), difficulty: int = 1,
                  source: str = "seed") -> EngineeringTask:
        if task_type not in self.ALLOWED_TYPES:
            raise ValueError(f"unsupported task_type: {task_type}")
        if not title.strip() or not objective.strip():
            raise ValueError("title and objective are required")
        if not 1 <= difficulty <= 5:
            raise ValueError("difficulty must be between 1 and 5")

        identity = {
            "task_type": task_type,
            "title": title.strip(),
            "objective": objective.strip(),
            "repository_path": repository_path,
            "acceptance": list(acceptance),
            "constraints": list(constraints),
            "difficulty": difficulty,
            "source": source,
        }
        task_id = "task-" + sha256(
            json.dumps(identity, sort_keys=True).encode("utf-8")
        ).hexdigest()[:16]
        return EngineeringTask(task_id=task_id, **identity)

    def write_jsonl(self, tasks: Iterable[EngineeringTask], path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            for task in tasks:
                handle.write(json.dumps(task.to_dict(), sort_keys=True) + "\n")
