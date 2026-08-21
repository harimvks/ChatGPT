from pathlib import Path

import pytest

from platform_vnext.workspace.mutation_guard import (
    MutationDenied,
    MutationPolicy,
    MutationRequest,
    WorkspaceMutationGuard,
)


def guard(tmp_path: Path) -> WorkspaceMutationGuard:
    allowed = tmp_path / "src"
    allowed.mkdir()
    return WorkspaceMutationGuard(
        MutationPolicy(
            workspace_root=tmp_path,
            allowed_roots=(allowed,),
            forbidden_roots=(tmp_path / ".git",),
            allowed_operations=frozenset({"create", "modify"}),
            require_approval=True,
        )
    )


def test_allows_approved_change_inside_allowed_root(tmp_path):
    path = guard(tmp_path).authorize(MutationRequest(Path("src/main.py"), "modify", approved=True))
    assert path == (tmp_path / "src/main.py").resolve()


def test_requires_explicit_approval(tmp_path):
    with pytest.raises(MutationDenied, match="approval"):
        guard(tmp_path).authorize(MutationRequest(Path("src/main.py"), "modify"))


def test_rejects_outside_allowed_root(tmp_path):
    with pytest.raises(MutationDenied, match="outside allowed"):
        guard(tmp_path).authorize(MutationRequest(Path("README.md"), "modify", approved=True))


def test_rejects_forbidden_root(tmp_path):
    forbidden = tmp_path / ".git"
    forbidden.mkdir()
    policy = MutationPolicy(
        workspace_root=tmp_path,
        allowed_roots=(tmp_path,),
        forbidden_roots=(forbidden,),
        allowed_operations=frozenset({"modify"}),
        require_approval=True,
    )
    with pytest.raises(MutationDenied, match="forbidden"):
        WorkspaceMutationGuard(policy).authorize(
            MutationRequest(Path(".git/config"), "modify", approved=True)
        )


def test_rejects_workspace_escape(tmp_path):
    with pytest.raises(MutationDenied, match="escapes"):
        guard(tmp_path).authorize(
            MutationRequest(Path("../outside.py"), "modify", approved=True)
        )


def test_rejects_disallowed_operation(tmp_path):
    with pytest.raises(MutationDenied, match="not allowed"):
        guard(tmp_path).authorize(MutationRequest(Path("src/main.py"), "delete", approved=True))
