from pathlib import Path

from self_improvement.pilot_execution import (
    build_execution_plan,
    make_gateway_rollout_factory,
)


def _cert(cert_id: str, benchmark: str, detail: str) -> str:
    return f"""certification_id: {cert_id}
capability: CODING_IMPLEMENTATION
model_name: qwen3.6-27b
benchmark_id: {benchmark}
corpus_version: 7
result: PASS
functional: true
ruff: 0
pyright: 0
latency_s: 1.0
backstop: 0
detail: {detail}
"""


def test_build_execution_plan_records_source_cases_and_env_bindings(tmp_path: Path, monkeypatch):
    paths = []
    for name, benchmark, detail in [
        ("CERT-001", "isolated-implementation-case", "single-file feature"),
        ("CERT-002", "test-oriented-implementation-case", "pytest regression"),
        ("CERT-003", "integration-refactor-case", "adapter boundary refactor"),
    ]:
        path = tmp_path / f"{name}.yaml"
        path.write_text(_cert(name, benchmark, detail))
        paths.append(path)

    monkeypatch.setenv("GAIEP_MODEL_SMALL_PYTHON_CODER", "local-small")
    monkeypatch.setenv("GAIEP_MODEL_QWEN3_6_27B", "local-qwen")

    plan = build_execution_plan(paths)

    assert plan.manifest.trial_count() == 12
    assert plan.source_case_ids == ("CERT-001", "CERT-002", "CERT-003")
    assert plan.manifest.source_case_ids == plan.source_case_ids
    assert {binding.endpoint_model for binding in plan.model_bindings} == {
        "local-small",
        "local-qwen",
    }


def test_gateway_rollout_factory_binds_endpoint_model():
    class Arm:
        model_name = "small-python-coder"
        scaffold_name = "inspect-implement-test"

    calls = []

    def model_call_factory(binding):
        def call(system, user):
            calls.append((binding.logical_name, binding.endpoint_model, system, user))
            return {"files": {"x.py": "x = 1\n"}, "model": binding.endpoint_model}

        return call

    from self_improvement.experiment_config import ModelBinding
    from self_improvement.task_factory import TaskFactory

    factory = make_gateway_rollout_factory(
        model_call_factory=model_call_factory,
        bindings=(ModelBinding("small-python-coder", "local-small"),),
    )
    task = TaskFactory().from_seed(
        task_type="implementation", title="T", objective="Implement X"
    )
    result = factory(Arm()).run(task)

    assert result.model_name == "small-python-coder"
    assert result.endpoint_model == "local-small"
    assert result.artifact == {"files": {"x.py": "x = 1\n"}, "model": "local-small"}
    assert calls[0][0:2] == ("small-python-coder", "local-small")
