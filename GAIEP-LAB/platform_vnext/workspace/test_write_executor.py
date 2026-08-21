from pathlib import Path

from platform_vnext.workspace.mutation_guard import MutationPolicy, WorkspaceMutationGuard
from platform_vnext.workspace.write_executor import Mutation, WriteSkillExecutor


def test_write_executor_records_hashes_and_diff(tmp_path: Path):
    src = tmp_path / "src"
    src.mkdir()
    target = src / "example.py"
    target.write_text("x = 1\n", encoding="utf-8")

    guard = WorkspaceMutationGuard(
        MutationPolicy(
            workspace_root=tmp_path,
            allowed_roots=(src,),
            allowed_operations=frozenset({"modify"}),
            require_approval=True,
        )
    )
    evidence = WriteSkillExecutor(guard).execute(
        [Mutation(target, "modify", "x = 2\n", approved=True)]
    )

    assert target.read_text(encoding="utf-8") == "x = 2\n"
    assert evidence[0].before_sha256
    assert evidence[0].after_sha256
    assert evidence[0].before_sha256 != evidence[0].after_sha256
    assert "-x = 1" in evidence[0].diff
    assert "+x = 2" in evidence[0].diff
