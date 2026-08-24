from self_improvement.gate_adapter import ExternalValidationGate, GateCommand
from self_improvement.sandbox import CandidateSandbox
from self_improvement.sandbox_evaluation import SandboxEvaluator
from self_improvement.task_factory import TaskFactory


def test_sandbox_evaluation_runs_gate_in_isolated_workspace():
    task = TaskFactory().from_seed(
        task_type="testing",
        title="Validate candidate",
        objective="Run validation",
    )
    gate = ExternalValidationGate([
        GateCommand("pytest", ("python", "-c", "print('tests ok')")),
        GateCommand("ruff", ("python", "-c", "print('lint ok')")),
    ])
    result = SandboxEvaluator(CandidateSandbox(), gate).evaluate(
        task,
        {"candidate.py": "value = 1\n"},
    )
    assert result.evaluation.passed
    assert result.evaluation.reward == 1.0
    assert result.files == ("candidate.py",)
    assert "tests ok" in result.stdout_by_check["pytest"]
