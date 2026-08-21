from pathlib import Path

import pytest

from platform_vnext.workspace.atomic_write import MutationTransaction
from platform_vnext.workspace.mutation_guard import MutationPolicy, WorkspaceMutationGuard, MutationRequest
from platform_vnext.workspace.write_executor import Mutation


def make_guard(tmp_path: Path) -> WorkspaceMutationGuard:
    src = tmp_path / "src"
    src.mkdir()
    return WorkspaceMutationGuard(
        MutationPolicy(
            workspace_root=tmp_path,
            allowed_roots=(src,),
            allowed_operations=frozenset({"create", "modify", "delete"}),
            require_approval=True,
        )
    )


def test_transaction_rolls_back_existing_and_new_files(tmp_path: Path):
    src = tmp_path / "src"
    src.mkdir()
    existing = src / "a.py"
    existing.write_text("x = 1\n", encoding="utf-8")
    new = src / "b.py"

    tx = MutationTransaction(make_guard(tmp_path))
    tx.apply((
        Mutation(existing, "modify", "x = 2\n", approved=True),
        Mutation(new, "create", "y = 3\n", approved=True),
    ))
    assert existing.read_text(encoding="utf-8") == "x = 2\n"
    assert new.exists()

    result = tx.rollback()
    assert not result.committed
    assert existing.read_text(encoding="utf-8") == "x = 1\n"
    assert not new.exists()


def test_transaction_commits(tmp_path: Path):
    src = tmp_path / "src"
    src.mkdir()
    target = src / "a.py"
    target.write_text("x = 1\n", encoding="utf-8")

    tx = MutationTransaction(make_guard(tmp_path))
    tx.apply((Mutation(target, "modify", "x = 2\n", approved=True),))
    result = tx.commit()
    assert result.committed
    assert target.read_text(encoding="utf-8") == "x = 2\n"


def test_transaction_rolls_back_when_later_mutation_is_denied(tmp_path: Path):
    src = tmp_path / "src"
    src.mkdir()
    target = src / "a.py"
    target.write_text("x = 1\n", encoding="utf-8")

    tx = MutationTransaction(make_guard(tmp_path))
    with pytest.raises(PermissionError):
        tx.apply((
            Mutation(target, "modify", "x = 2\n", approved=True),
            Mutation(Path("../escape.py"), "modify", "bad\n", approved=True),
        ))
    assert target.read_text(encoding="utf-8") == "x = 1\n"
