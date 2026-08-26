"""Durable, append-only evidence storage for GAIEP research runs."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .fingerprint import failure_fingerprint, provenance_fingerprint
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
    failure_fingerprint: str | None
    provenance_fingerprint: str
    context_hash: str | None
    trajectory_json: str
    content_hash: str

    @classmethod
    def from_trajectory(cls, record: TrajectoryRecord) -> EvidenceRecord:
        payload = record.to_json()
        provenance = record.provenance
        context_hash = (
            provenance.context.context_hash if provenance and provenance.context else None
        )
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return cls(
            record_id=digest,
            created_at=_utc_now(),
            run_id=provenance.run_id if provenance is not None else None,
            task_id=record.task_id,
            model_name=record.model_name,
            scaffold_name=record.scaffold_name,
            passed=record.passed,
            reward=record.reward,
            failure_class=record.failure_class,
            failure_fingerprint=failure_fingerprint(record),
            provenance_fingerprint=provenance_fingerprint(record),
            context_hash=context_hash,
            trajectory_json=payload,
            content_hash=digest,
        )


@dataclass(frozen=True)
class ResearchLineageEvent:
    """Append-only research lineage event linking failures to follow-up evidence."""

    event_id: str
    hypothesis_id: str
    failure_fingerprint: str
    research_task_id: str
    status: str
    source_evidence_ids: tuple[str, ...]
    experiment_run_id: str | None = None
    result_evidence_id: str | None = None
    created_at: str = ""

    @classmethod
    def create(
        cls,
        *,
        hypothesis_id: str,
        failure_fingerprint: str,
        research_task_id: str,
        status: str,
        source_evidence_ids: tuple[str, ...],
        experiment_run_id: str | None = None,
        result_evidence_id: str | None = None,
        created_at: str | None = None,
    ) -> ResearchLineageEvent:
        identity = {
            "hypothesis_id": hypothesis_id,
            "failure_fingerprint": failure_fingerprint,
            "research_task_id": research_task_id,
            "status": status,
            "source_evidence_ids": tuple(sorted(source_evidence_ids)),
            "experiment_run_id": experiment_run_id,
            "result_evidence_id": result_evidence_id,
        }
        event_id = (
            "research-lineage-"
            + hashlib.sha256(json.dumps(identity, sort_keys=True).encode("utf-8")).hexdigest()[:24]
        )
        return cls(
            event_id=event_id,
            hypothesis_id=hypothesis_id,
            failure_fingerprint=failure_fingerprint,
            research_task_id=research_task_id,
            status=status,
            source_evidence_ids=tuple(sorted(source_evidence_ids)),
            experiment_run_id=experiment_run_id,
            result_evidence_id=result_evidence_id,
            created_at=created_at or _utc_now(),
        )


@dataclass(frozen=True)
class IntegrityReport:
    """Read-only integrity verification result."""

    checked: int
    valid: int
    invalid_record_ids: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.invalid_record_ids


@dataclass(frozen=True)
class MemorySummary:
    """Compact aggregate view for research and diagnostics."""

    total: int
    passed: int
    failed: int
    average_reward: float
    failure_classes: tuple[tuple[str, int], ...]
    models: tuple[tuple[str, int], ...]


def _utc_now() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).isoformat()


class GreenMemoryStore:
    """Local SQLite evidence ledger with insert-only semantics."""

    SCHEMA_VERSION = 3

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
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = NORMAL")
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
                    failure_fingerprint TEXT,
                    provenance_fingerprint TEXT NOT NULL DEFAULT '',
                    context_hash TEXT,
                    trajectory_json TEXT NOT NULL,
                    content_hash TEXT NOT NULL UNIQUE
                );
                CREATE TABLE IF NOT EXISTS evidence_skills (
                    record_id TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    PRIMARY KEY (record_id, fingerprint),
                    FOREIGN KEY (record_id) REFERENCES evidence_records(record_id)
                );
                CREATE TABLE IF NOT EXISTS evidence_capabilities (
                    record_id TEXT NOT NULL,
                    capability_id TEXT NOT NULL,
                    authorized INTEGER NOT NULL CHECK (authorized IN (0, 1)),
                    PRIMARY KEY (record_id, capability_id, authorized),
                    FOREIGN KEY (record_id) REFERENCES evidence_records(record_id)
                );
                CREATE TABLE IF NOT EXISTS research_lineage_events (
                    event_id TEXT PRIMARY KEY,
                    hypothesis_id TEXT NOT NULL,
                    failure_fingerprint TEXT NOT NULL,
                    research_task_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    experiment_run_id TEXT,
                    result_evidence_id TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (result_evidence_id) REFERENCES evidence_records(record_id)
                );
                CREATE TABLE IF NOT EXISTS research_lineage_sources (
                    event_id TEXT NOT NULL,
                    evidence_record_id TEXT NOT NULL,
                    PRIMARY KEY (event_id, evidence_record_id),
                    FOREIGN KEY (event_id) REFERENCES research_lineage_events(event_id),
                    FOREIGN KEY (evidence_record_id) REFERENCES evidence_records(record_id)
                );
                """
            )
            self._ensure_columns(connection)
            connection.execute(
                "INSERT OR REPLACE INTO metadata(key, value) VALUES('schema_version', ?)",
                (str(self.SCHEMA_VERSION),),
            )
            connection.executescript(
                """
                CREATE INDEX IF NOT EXISTS idx_evidence_run ON evidence_records(run_id);
                CREATE INDEX IF NOT EXISTS idx_evidence_task ON evidence_records(task_id);
                CREATE INDEX IF NOT EXISTS idx_evidence_failure ON evidence_records(failure_class);
                CREATE INDEX IF NOT EXISTS idx_evidence_failure_fp
                    ON evidence_records(failure_fingerprint);
                CREATE INDEX IF NOT EXISTS idx_evidence_provenance_fp
                    ON evidence_records(provenance_fingerprint);
                CREATE INDEX IF NOT EXISTS idx_evidence_context ON evidence_records(context_hash);
                CREATE INDEX IF NOT EXISTS idx_evidence_model ON evidence_records(model_name);
                CREATE INDEX IF NOT EXISTS idx_evidence_skills ON evidence_skills(fingerprint);
                CREATE INDEX IF NOT EXISTS idx_evidence_capabilities
                    ON evidence_capabilities(capability_id, authorized);
                CREATE INDEX IF NOT EXISTS idx_research_lineage_hypothesis
                    ON research_lineage_events(hypothesis_id, created_at);
                CREATE INDEX IF NOT EXISTS idx_research_lineage_task
                    ON research_lineage_events(research_task_id, created_at);
                CREATE INDEX IF NOT EXISTS idx_research_lineage_source
                    ON research_lineage_sources(evidence_record_id);
                """
            )
            self._backfill_indexes(connection)

    @staticmethod
    def _ensure_columns(connection: sqlite3.Connection) -> None:
        existing = {
            str(row["name"])
            for row in connection.execute("PRAGMA table_info(evidence_records)").fetchall()
        }
        additions = {
            "failure_fingerprint": "TEXT",
            "provenance_fingerprint": "TEXT NOT NULL DEFAULT ''",
            "context_hash": "TEXT",
        }
        for name, definition in additions.items():
            if name not in existing:
                connection.execute(f"ALTER TABLE evidence_records ADD COLUMN {name} {definition}")

    @staticmethod
    def _backfill_indexes(connection: sqlite3.Connection) -> None:
        rows = connection.execute(
            "SELECT record_id, trajectory_json FROM evidence_records"
        ).fetchall()
        for row in rows:
            record = TrajectoryRecord.from_json(row["trajectory_json"])
            failure_fp = failure_fingerprint(record)
            provenance_fp = provenance_fingerprint(record)
            context_hash = (
                record.provenance.context.context_hash
                if record.provenance and record.provenance.context
                else None
            )
            connection.execute(
                """
                UPDATE evidence_records
                SET failure_fingerprint = ?, provenance_fingerprint = ?, context_hash = ?
                WHERE record_id = ?
                """,
                (failure_fp, provenance_fp, context_hash, row["record_id"]),
            )
            provenance = record.provenance
            if provenance:
                for skill in provenance.skill_fingerprints:
                    connection.execute(
                        (
                            "INSERT OR IGNORE INTO evidence_skills(record_id, fingerprint) "
                            "VALUES (?, ?)"
                        ),
                        (row["record_id"], skill),
                    )
                for capability in provenance.capability_ids_requested:
                    authorized = int(capability in provenance.capability_ids_authorized)
                    connection.execute(
                        """
                        INSERT OR IGNORE INTO evidence_capabilities(
                        record_id, capability_id, authorized
                    )
                        VALUES (?, ?, ?)
                        """,
                        (row["record_id"], capability, authorized),
                    )

    @staticmethod
    def record_id_for(record: TrajectoryRecord) -> str:
        """Return the content-addressed evidence ID used by this store."""
        return EvidenceRecord.from_trajectory(record).record_id

    def append(self, record: TrajectoryRecord) -> str:
        """Persist one trajectory and return its content-addressed record ID."""
        evidence = EvidenceRecord.from_trajectory(record)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO evidence_records(
                    record_id, created_at, run_id, task_id, model_name, scaffold_name,
                    passed, reward, failure_class, failure_fingerprint,
                    provenance_fingerprint, context_hash, trajectory_json, content_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    evidence.failure_fingerprint,
                    evidence.provenance_fingerprint,
                    evidence.context_hash,
                    evidence.trajectory_json,
                    evidence.content_hash,
                ),
            )
            connection.executemany(
                "INSERT OR IGNORE INTO evidence_skills(record_id, fingerprint) VALUES (?, ?)",
                ((evidence.record_id, value) for value in record.provenance.skill_fingerprints)
                if record.provenance
                else (),
            )
            if record.provenance:
                connection.executemany(
                    """
                    INSERT OR IGNORE INTO evidence_capabilities(
                        record_id, capability_id, authorized
                    )
                    VALUES (?, ?, ?)
                    """,
                    (
                        (
                            evidence.record_id,
                            capability,
                            int(capability in record.provenance.capability_ids_authorized),
                        )
                        for capability in record.provenance.capability_ids_requested
                    ),
                )
        return evidence.record_id

    def append_research_lineage_event(self, event: ResearchLineageEvent) -> str:
        """Persist one append-only research lineage event and return its event ID."""
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO research_lineage_events(
                    event_id, hypothesis_id, failure_fingerprint, research_task_id, status,
                    experiment_run_id, result_evidence_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.hypothesis_id,
                    event.failure_fingerprint,
                    event.research_task_id,
                    event.status,
                    event.experiment_run_id,
                    event.result_evidence_id,
                    event.created_at,
                ),
            )
            connection.executemany(
                """
                INSERT OR IGNORE INTO research_lineage_sources(event_id, evidence_record_id)
                VALUES (?, ?)
                """,
                ((event.event_id, evidence_id) for evidence_id in event.source_evidence_ids),
            )
        return event.event_id

    def find_research_lineage_by_hypothesis(
        self, hypothesis_id: str
    ) -> tuple[ResearchLineageEvent, ...]:
        return self._query_lineage(
            """
            SELECT * FROM research_lineage_events
            WHERE hypothesis_id = ? ORDER BY
                CASE status
                    WHEN 'PROPOSED' THEN 1
                    WHEN 'APPROVED' THEN 2
                    WHEN 'SUBMITTED' THEN 3
                    WHEN 'COMPLETED' THEN 4
                    WHEN 'REJECTED' THEN 5
                    WHEN 'FAILED' THEN 6
                    ELSE 99
                END,
                created_at,
                event_id
            """,
            (hypothesis_id,),
        )

    def find_research_lineage_by_task(
        self, research_task_id: str
    ) -> tuple[ResearchLineageEvent, ...]:
        return self._query_lineage(
            """
            SELECT * FROM research_lineage_events
            WHERE research_task_id = ? ORDER BY
                CASE status
                    WHEN 'PROPOSED' THEN 1
                    WHEN 'APPROVED' THEN 2
                    WHEN 'SUBMITTED' THEN 3
                    WHEN 'COMPLETED' THEN 4
                    WHEN 'REJECTED' THEN 5
                    WHEN 'FAILED' THEN 6
                    ELSE 99
                END,
                created_at,
                event_id
            """,
            (research_task_id,),
        )

    def get(self, record_id: str) -> TrajectoryRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT trajectory_json FROM evidence_records WHERE record_id = ?",
                (record_id,),
            ).fetchone()
        return TrajectoryRecord.from_json(row["trajectory_json"]) if row else None

    def find_by_run(self, run_id: str) -> tuple[TrajectoryRecord, ...]:
        return self._query(
            "SELECT trajectory_json FROM evidence_records WHERE run_id = ? "
            "ORDER BY created_at, record_id",
            (run_id,),
        )

    def find_by_task(self, task_id: str) -> tuple[TrajectoryRecord, ...]:
        return self._query(
            "SELECT trajectory_json FROM evidence_records WHERE task_id = ? "
            "ORDER BY created_at, record_id",
            (task_id,),
        )

    def find_by_context_hash(self, context_hash: str) -> tuple[TrajectoryRecord, ...]:
        return self._query(
            "SELECT trajectory_json FROM evidence_records WHERE context_hash = ? "
            "ORDER BY created_at, record_id",
            (context_hash,),
        )

    def find_by_skill(self, fingerprint: str) -> tuple[TrajectoryRecord, ...]:
        return self._query(
            """
            SELECT e.trajectory_json FROM evidence_records e
            JOIN evidence_skills s ON s.record_id = e.record_id
            WHERE s.fingerprint = ? ORDER BY e.created_at, e.record_id
            """,
            (fingerprint,),
        )

    def find_by_capability(
        self, capability_id: str, *, authorized_only: bool = False
    ) -> tuple[TrajectoryRecord, ...]:
        sql = (
            "SELECT e.trajectory_json FROM evidence_records e "
            "JOIN evidence_capabilities c ON c.record_id = e.record_id "
            "WHERE c.capability_id = ?"
        )
        parameters: tuple[Any, ...] = (capability_id,)
        if authorized_only:
            sql += " AND c.authorized = 1"
        sql += " ORDER BY e.created_at, e.record_id"
        return self._query(sql, parameters)

    def find_failures(self, failure_class: str | None = None) -> tuple[TrajectoryRecord, ...]:
        if failure_class is None:
            return self._query(
                "SELECT trajectory_json FROM evidence_records WHERE passed = 0 "
                "ORDER BY created_at, record_id",
                (),
            )
        return self._query(
            "SELECT trajectory_json FROM evidence_records WHERE passed = 0 "
            "AND failure_class = ? ORDER BY created_at, record_id",
            (failure_class,),
        )

    def find_by_failure_fingerprint(self, fingerprint: str) -> tuple[TrajectoryRecord, ...]:
        return self._query(
            "SELECT trajectory_json FROM evidence_records WHERE failure_fingerprint = ? "
            "ORDER BY created_at, record_id",
            (fingerprint,),
        )

    def find_similar_failures(
        self, record: TrajectoryRecord, *, limit: int = 20
    ) -> tuple[TrajectoryRecord, ...]:
        fingerprint = failure_fingerprint(record)
        if fingerprint is None:
            return ()
        return self._query(
            """
            SELECT trajectory_json FROM evidence_records
            WHERE failure_fingerprint = ? AND record_id != ?
            ORDER BY created_at DESC, record_id LIMIT ?
            """,
            (fingerprint, hashlib.sha256(record.to_json().encode("utf-8")).hexdigest(), limit),
        )

    def summary(self) -> MemorySummary:
        with self._connect() as connection:
            totals = connection.execute(
                "SELECT COUNT(*) AS total, SUM(passed) AS passed, "
                "AVG(reward) AS average_reward FROM evidence_records"
            ).fetchone()
            failures = connection.execute(
                """
                SELECT failure_class, COUNT(*) AS count FROM evidence_records
                WHERE passed = 0 AND failure_class IS NOT NULL
                GROUP BY failure_class ORDER BY count DESC, failure_class
                """
            ).fetchall()
            models = connection.execute(
                "SELECT model_name, COUNT(*) AS count FROM evidence_records "
                "GROUP BY model_name ORDER BY count DESC, model_name"
            ).fetchall()
        total = int(totals["total"] or 0)
        passed = int(totals["passed"] or 0)
        return MemorySummary(
            total=total,
            passed=passed,
            failed=total - passed,
            average_reward=float(totals["average_reward"] or 0.0),
            failure_classes=tuple(
                (str(row["failure_class"]), int(row["count"])) for row in failures
            ),
            models=tuple((str(row["model_name"]), int(row["count"])) for row in models),
        )

    def verify_integrity(self) -> IntegrityReport:
        """Recompute every content hash without mutating the store."""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT record_id, trajectory_json, content_hash FROM evidence_records "
                "ORDER BY record_id"
            ).fetchall()
        invalid: list[str] = []
        for row in rows:
            digest = hashlib.sha256(row["trajectory_json"].encode("utf-8")).hexdigest()
            if digest != row["content_hash"] or digest != row["record_id"]:
                invalid.append(str(row["record_id"]))
        return IntegrityReport(len(rows), len(rows) - len(invalid), tuple(invalid))

    def export_jsonl(self, path: Path) -> int:
        """Export the canonical trajectory payloads without altering the ledger."""
        records = self._query(
            "SELECT trajectory_json FROM evidence_records ORDER BY created_at, record_id",
            (),
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            for record in records:
                handle.write(record.to_json() + "\n")
        return len(records)

    def count(self) -> int:
        with self._connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM evidence_records").fetchone()
        return int(row["count"])

    def _query_lineage(
        self, sql: str, parameters: tuple[Any, ...]
    ) -> tuple[ResearchLineageEvent, ...]:
        with self._connect() as connection:
            rows = connection.execute(sql, parameters).fetchall()
            source_rows = connection.execute(
                "SELECT event_id, evidence_record_id FROM research_lineage_sources"
            ).fetchall()
        sources: dict[str, list[str]] = {}
        for row in source_rows:
            sources.setdefault(str(row["event_id"]), []).append(str(row["evidence_record_id"]))
        return tuple(
            ResearchLineageEvent(
                event_id=str(row["event_id"]),
                hypothesis_id=str(row["hypothesis_id"]),
                failure_fingerprint=str(row["failure_fingerprint"]),
                research_task_id=str(row["research_task_id"]),
                status=str(row["status"]),
                source_evidence_ids=tuple(sorted(sources.get(str(row["event_id"]), ()))),
                experiment_run_id=row["experiment_run_id"],
                result_evidence_id=row["result_evidence_id"],
                created_at=str(row["created_at"]),
            )
            for row in rows
        )

    def _query(self, sql: str, parameters: tuple[Any, ...]) -> tuple[TrajectoryRecord, ...]:
        with self._connect() as connection:
            rows = connection.execute(sql, parameters).fetchall()
        return tuple(TrajectoryRecord.from_json(row["trajectory_json"]) for row in rows)
