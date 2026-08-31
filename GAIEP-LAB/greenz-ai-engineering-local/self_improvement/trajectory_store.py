"""Append-only JSONL store for research trajectory metadata."""

from __future__ import annotations

from pathlib import Path

from .trajectory import TrajectoryRecord


class TrajectoryStore:
    """Persist trajectory metadata locally without storing candidate source."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def append(self, record: TrajectoryRecord) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(record.to_json() + "\n")
