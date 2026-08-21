"""Transactional filesystem primitive for governed coding skills.

The transaction snapshots original file bytes and restores them if validation fails. Authorization
is delegated to WorkspaceMutationGuard before each mutation.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import tempfile

from .mutation_guard import MutationRequest, WorkspaceMutationGuard
from .write_executor import Mutation


@dataclass(frozen=True)
class TransactionResult:
    committed: bool
    changed_paths: tuple[str, ...]


class MutationTransaction:
    def __init__(self, guard: WorkspaceMutationGuard) -> None:
        self._guard = guard
        self._snapshots: dict[Path, bytes | None] = {}
        self._changed: list[Path] = []
        self._active = False

    def apply(self, mutations: tuple[Mutation, ...]) -> None:
        if self._active:
            raise RuntimeError("transaction already active")
        self._active = True
        try:
            for mutation in mutations:
                target = self._guard.authorize(
                    MutationRequest(mutation.path, mutation.operation, mutation.approved)
                )
                if target not in self._snapshots:
                    self._snapshots[target] = target.read_bytes() if target.exists() else None
                self._apply_one(target, mutation)
                self._changed.append(target)
        except Exception:
            self.rollback()
            raise

    def commit(self) -> TransactionResult:
        if not self._active:
            raise RuntimeError("no active transaction")
        changed = tuple(str(path) for path in self._changed)
        self._snapshots.clear()
        self._changed.clear()
        self._active = False
        return TransactionResult(True, changed)

    def rollback(self) -> TransactionResult:
        changed = tuple(str(path) for path in self._changed)
        for path, original in reversed(tuple(self._snapshots.items())):
            if original is None:
                if path.exists():
                    path.unlink()
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            fd, temp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
            try:
                with os.fdopen(fd, "wb") as handle:
                    handle.write(original)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temp_name, path)
            finally:
                if os.path.exists(temp_name):
                    os.unlink(temp_name)
        self._snapshots.clear()
        self._changed.clear()
        self._active = False
        return TransactionResult(False, changed)

    @staticmethod
    def _apply_one(target: Path, mutation: Mutation) -> None:
        if mutation.operation in {"create", "modify"}:
            if mutation.content is None:
                raise ValueError("create/modify mutation requires content")
            target.parent.mkdir(parents=True, exist_ok=True)
            fd, temp_name = tempfile.mkstemp(dir=target.parent, prefix=f".{target.name}.")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    handle.write(mutation.content)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temp_name, target)
            finally:
                if os.path.exists(temp_name):
                    os.unlink(temp_name)
        elif mutation.operation == "delete":
            if target.exists():
                target.unlink()
        else:
            raise ValueError(f"unsupported operation: {mutation.operation}")
