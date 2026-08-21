"""GreenSkill execution skeleton for bounded Python implementation tasks."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Protocol

from platform_vnext.workspace.mutation_guard import WorkspaceMutationGuard
from platform_vnext.workspace.write_executor import Mutation, MutationEvidence, WriteSkillExecutor


@dataclass(frozen=True)
class PythonChangeProposal:
    mutations: tuple[Mutation, ...]
    rationale: str = ""


@dataclass(frozen=True)
class ValidationResult:
    passed: bool
    command: str
    output: str = ""


@dataclass(frozen=True)
class PythonImplementationResult:
    mutation_evidence: tuple[MutationEvidence, ...]
    validations: tuple[ValidationResult, ...]
    accepted: bool


class ProposalGenerator(Protocol):
    def propose(self, task: str) -> PythonChangeProposal: ...


class ValidationRunner(Protocol):
    def run(self, workspace: Path) -> Iterable[ValidationResult]: ...


class PythonImplementationSkillExecutor:
    """Execute a bounded Python implementation proposal through governed mutation and validation."""

    def __init__(
        self,
        guard: WorkspaceMutationGuard,
        proposal_generator: ProposalGenerator,
        validator: ValidationRunner,
    ) -> None:
        self._writer = WriteSkillExecutor(guard)
        self._proposal_generator = proposal_generator
        self._validator = validator
        self._workspace = guard.workspace_root

    def execute(self, task: str) -> PythonImplementationResult:
        proposal = self._proposal_generator.propose(task)
        evidence = self._writer.execute(proposal.mutations)
        validations = tuple(self._validator.run(self._workspace))
        accepted = bool(validations) and all(item.passed for item in validations)
        return PythonImplementationResult(
            mutation_evidence=evidence,
            validations=validations,
            accepted=accepted,
        )
