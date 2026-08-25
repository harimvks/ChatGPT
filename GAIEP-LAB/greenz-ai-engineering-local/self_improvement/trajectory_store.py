"""Append-only JSONL store for research trajectory metadata."""

from __future__ import annotations

from pathlib import Path

from .trajectory import TrajectoryRecord


class TrajectoryStore:
    """Persist trajectory metadata locally without storing candidate source."""

    def __init__(self, path: Path) -> None:
        self._path = path

    @property
    def path(self) -> Path:
        return self._path

    def append(self, record: TrajectoryRecord) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(record.to_json() + "\n")

    def read_all(self) -> tuple[TrajectoryRecord, ...]:
        if not self._path.exists():
            return ()
        records: list[TrajectoryRecord] = []
        for line in self._path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                records.append(TrajectoryRecord.from_json(line))
        return tuple(records)

    def completed_keys(self) -> set[tuple[str, str, str]]:
        return {record.key() for record in self.read_all()}
