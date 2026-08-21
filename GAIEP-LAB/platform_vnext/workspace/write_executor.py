"""Write-capable Skill executor built on WorkspaceMutationGuard.

The executor performs only explicitly authorized operations and records before/after SHA-256
hashes plus a unified diff for auditability. It is intentionally small; higher-level skill logic
must produce the mutation plan and validation remains a separate gate.
"""
from __future__ import annotations

from dataclasses import dataclass
import difflib
import hashlib
from pathlib import Path
from typing import Iterable

from .mutation_guard import MutationRequest, WorkspaceMutationGuard


@dataclass(frozen=True)
class Mutation:
    path: Path
    operation: str
    content: str | None = None
    approved: bool = False


@dataclass(frozen=True)
class MutationEvidence:
    path: str
    operation: str
    before_sha256: str | None
    after_sha256: str | None
    diff: str


class WriteSkillExecutor:
    def __init__(self, guard: WorkspaceMutationGuard) -> None:
        self._guard = guard

    def execute(self, mutations: Iterable[Mutation]) -> tuple[MutationEvidence, ...]:
        evidence: list[MutationEvidence] = []
        for mutation in mutations:
            target = self._guard.authorize(
                MutationRequest(
                    path=mutation.path,
                    operation=mutation.operation,  # type: ignore[arg-type]
                    approved=mutation.approved,
                )
            )
            before = target.read_text(encoding="utf-8") if target.exists() else ""
            before_hash = _sha256(before) if target.exists() else None

            if mutation.operation in {"create", "modify"}:
                if mutation.content is None:
                    raise ValueError("create/modify mutation requires content")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(mutation.content, encoding="utf-8")
            elif mutation.operation == "delete":
                if target.exists():
                    target.unlink()
            else:
                raise ValueError(f"unsupported operation: {mutation.operation}")

            after = target.read_text(encoding="utf-8") if target.exists() else ""
            after_hash = _sha256(after) if target.exists() else None
            diff = "".join(
                difflib.unified_diff(
                    before.splitlines(keepends=True),
                    after.splitlines(keepends=True),
                    fromfile=f"a/{target}",
                    tofile=f"b/{target}",
                )
            )
            evidence.append(
                MutationEvidence(
                    path=str(target),
                    operation=mutation.operation,
                    before_sha256=before_hash,
                    after_sha256=after_hash,
                    diff=diff,
                )
            )
        return tuple(evidence)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
