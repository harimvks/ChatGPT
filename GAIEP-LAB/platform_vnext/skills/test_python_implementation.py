from pathlib import Path

from platform_vnext.skills.python_implementation import (
    ProposalGenerator,
    PythonChangeProposal,
    PythonImplementationSkillExecutor,
    ValidationResult,
)
from platform_vnext.workspace.mutation_guard import MutationPolicy, WorkspaceMutationGuard
from platform_vnext.workspace.write_executor import Mutation


class Generator:
    def propose(self, task: str) -> PythonChangeProposal:
        assert task == "fix example"
        return PythonChangeProposal(
            mutations=(Mutation(Path("src/example.py"), "modify", "x = 2\n", approved=True),),
            rationale="fix example",
        )


class Validator:
    def run(self, workspace: Path):
        assert workspace.exists()
        return (
            ValidationResult(True, "ruff check src"),
            ValidationResult(True, "pyright src"),
            ValidationResult(True, "pytest -q"),
        )


def test_python_skill_requires_all_validation_gates(tmp_path: Path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "example.py").write_text("x = 1\n", encoding="utf-8")
    guard = WorkspaceMutationGuard(
        MutationPolicy(
            workspace_root=tmp_path,
            allowed_roots=(src,),
            allowed_operations=frozenset({"modify"}),
            require_approval=True,
        )
    )

    result = PythonImplementationSkillExecutor(guard, Generator(), Validator()).execute("fix example")

    assert result.accepted is True
    assert len(result.mutation_evidence) == 1
    assert len(result.validations) == 3
    assert (src / "example.py").read_text(encoding="utf-8") == "x = 2\n"
