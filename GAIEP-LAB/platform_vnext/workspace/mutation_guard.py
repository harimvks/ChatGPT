"""Filesystem mutation authorization for GAIEP Runtime VNext.

This layer authorizes *paths and operations* before any write-capable skill gets a filesystem
handle. It intentionally performs no mutation itself.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import FrozenSet, Literal

Operation = Literal["create", "modify", "delete", "rename"]


@dataclass(frozen=True)
class MutationPolicy:
    workspace_root: Path
    allowed_roots: tuple[Path, ...] = ()
    forbidden_roots: tuple[Path, ...] = ()
    allowed_operations: FrozenSet[Operation] = frozenset()
    require_approval: bool = True


@dataclass(frozen=True)
class MutationRequest:
    path: Path
    operation: Operation
    approved: bool = False


class MutationDenied(PermissionError):
    pass


class WorkspaceMutationGuard:
    """Fail-closed path and operation authorization."""

    def __init__(self, policy: MutationPolicy) -> None:
        self._policy = policy
        self._root = policy.workspace_root.resolve()
        self._allowed = tuple(p.resolve() for p in policy.allowed_roots)
        self._forbidden = tuple(p.resolve() for p in policy.forbidden_roots)

    @property
    def workspace_root(self) -> Path:
        """Return the canonical workspace root used by authorized operations."""
        return self._root

    def authorize(self, request: MutationRequest) -> Path:
        if request.operation not in self._policy.allowed_operations:
            raise MutationDenied(f"operation {request.operation!r} is not allowed")
        if self._policy.require_approval and not request.approved:
            raise MutationDenied("explicit mutation approval is required")

        target = request.path if request.path.is_absolute() else self._root / request.path
        resolved = target.resolve(strict=False)

        if not self._inside(resolved, self._root):
            raise MutationDenied("path escapes workspace root")
        if self._forbidden and any(self._inside(resolved, root) for root in self._forbidden):
            raise MutationDenied("path is inside a forbidden root")
        if self._allowed and not any(self._inside(resolved, root) for root in self._allowed):
            raise MutationDenied("path is outside allowed mutation roots")

        # Existing symlinks are rejected rather than followed. A later hardened implementation
        # can permit explicitly audited symlink targets, but the default is fail-closed.
        cursor = resolved
        while cursor != self._root and cursor != cursor.parent:
            if cursor.is_symlink():
                raise MutationDenied("symlink path components are not permitted")
            cursor = cursor.parent
        return resolved

    @staticmethod
    def _inside(path: Path, root: Path) -> bool:
        try:
            path.relative_to(root)
            return True
        except ValueError:
            return False
