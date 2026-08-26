"""Durable, append-only evidence storage for GAIEP research runs."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .trajectory import TrajectoryRecord


@dataclass(frozen=True)
class EvidenceRecord:
    """Reference-only durable representation of a trajectory."""

    record_id: str
    created_at: str
    run_id: str | None
    task_id: str
    model_name: str
    scaffold_name: str
    passed: bool
    reward: float
    failure_class: str | None
    trajectory_json: str
    content_hash: str

    @classmethod
    def from_trajectory(cls, record: TrajectoryRecord) -> "EvidenceRecord":
        payload = record.to_json()
        provenance = record.provenance
        run_id = provenance.run_id if provenance is not None else None
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return cls(
            record_id=digest,
            created_at=_utc_now(),
            run_id=run_id,
            task_id=record.task_id,
            model_name=record.model_name,
            scaffold_name=record.scaffold_name,
            passed=record.passed,
            reward=record.reward,
            failure_class=record.failure_class,
            trajectory_json=payload,
            content_hash=digest,
        )


def _utc_now() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).isoformat()


class GreenMemoryStore:
    """Local SQLite evidence ledger with insert-only semantics."""

    SCHEMA_VERSION = 1

    def __init__(self, path: Path) -> None:
        self._path = path
        self._initialize()

    @property
    def path(self) -> Path:
        return self._path

    def _connect(self) -> sqlite3.Connection:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self._path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS evidence_records (
                    record_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    run_id TEXT,
                    task_id TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    scaffold_name TEXT NOT NULL,
                    passed INTEGER NOT NULL CHECK (passed IN (0, 1)),
                    reward REAL NOT NULL,
                    failure_class TEXT,
                    trajectory_json TEXT NOT NULL,
                    content_hash TEXT NOT NULL UNIQUE
                );
                CREATE INDEX IF NOT EXISTS idx_evidence_run ON evidence_records(run_id);
                CREATE INDEX IF NOT EXISTS idx_evidence_task ON evidence_records(task_id);
                CREATE INDEX IF NOT EXISTS idx_evidence_failure ON evidence_records(failure_class);
                CREATE INDEX IF NOT EXISTS idx_evidence_model ON evidence_records(model_name);
                """
            )
            connection.execute(
                "INSERT OR IGNORE INTO metadata(key, value) VALUES('schema_version', ?)",
                (str(self.SCHEMA_VERSION),),
            )

    def append(self, record: TrajectoryRecord) -> str:
        """Persist one trajectory and return its content-addressed record ID."""
        evidence = EvidenceRecord.from_trajectory(record)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO evidence_records(
                    record_id, created_at, run_id, task_id, model_name, scaffold_name,
                    passed, reward, failure_class, trajectory_json, content_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    evidence.record_id,
                    evidence.created_at,
                    evidence.run_id,
                    evidence.task_id,
                    evidence.model_name,
                    evidence.scaffold_name,
                    int(evidence.passed),
                    evidence.reward,
                    evidence.failure_class,
                    evidence.trajectory_json,
                    evidence.content_hash,
                ),
            )
        return evidence.record_id

    def get(self, record_id: str) -> TrajectoryRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT trajectory_json FROM evidence_records WHERE record_id = ?",
                (record_id,),
            ).fetchone()
        return TrajectoryRecord.from_json(row["trajectory_json"]) if row else None

    def find_by_run(self, run_id: str) -> tuple[TrajectoryRecord, ...]:
        return self._query("SELECT trajectory_json FROM evidence_records WHERE run_id = ? ORDER BY created_at, record_id", (run_id,))

    def find_by_task(self, task_id: str) -> tuple[TrajectoryRecord, ...]:
        return self._query("SELECT trajectory_json FROM evidence_records WHERE task_id = ? ORDER BY created_at, record_id", (task_id,))

    def find_failures(self, failure_class: str | None = None) -> tuple[TrajectoryRecord, ...]:
        if failure_class is None:
            return self._query("SELECT trajectory_json FROM evidence_records WHERE passed = 0 ORDER BY created_at, record_id", ())
        return self._query(
            "SELECT trajectory_json FROM evidence_records WHERE passed = 0 AND failure_class = ? ORDER BY created_at, record_id",
            (failure_class,),
        )

    def count(self) -> int:
        with self._connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM evidence_records").fetchone()
        return int(row["count"])

    def _query(self, sql: str, parameters: tuple[Any, ...]) -> tuple[TrajectoryRecord, ...]:
        with self._connect() as connection:
            rows = connection.execute(sql, parameters).fetchall()
        return tuple(TrajectoryRecord.from_json(row["trajectory_json"]) for row in rows)
