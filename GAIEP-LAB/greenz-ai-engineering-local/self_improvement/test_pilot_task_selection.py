from self_improvement.corpus_adapter import CertificationRecord
from self_improvement.pilot_task_selection import select_pilot_tasks


def _record(cert_id: str, benchmark: str, detail: str) -> CertificationRecord:
    return CertificationRecord(
        certification_id=cert_id,
        capability="CODING_IMPLEMENTATION",
        model_name="qwen3.6-27b",
        benchmark_id=benchmark,
        corpus_version=3,
        result="PASS",
        functional=True,
        ruff=0,
        pyright=0,
        latency_s=1.0,
        backstop=0,
        detail=detail,
    )


def test_select_pilot_tasks_requires_three_distinct_implementation_behaviors():
    selected = select_pilot_tasks(
        [
            _record("CERT-003", "integration-refactor-case", "adapter boundary refactor"),
            _record("CERT-001", "isolated-implementation-case", "single-file feature"),
            _record("CERT-002", "test-oriented-implementation-case", "pytest regression"),
        ]
    )

    assert [item.source_case_id for item in selected] == ["CERT-001", "CERT-002", "CERT-003"]
    assert [item.behavior for item in selected] == [
        "isolated_implementation",
        "test_oriented_implementation",
        "integration_refactor_behavior",
    ]
    assert all("research_only=true" in item.task.constraints for item in selected)


def test_select_pilot_tasks_fails_closed_when_cases_are_missing():
    try:
        select_pilot_tasks([_record("CERT-001", "isolated-implementation-case", "feature")])
    except RuntimeError as exc:
        assert "fewer than three" in str(exc)
    else:
        raise AssertionError("expected shortage failure")
