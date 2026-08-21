from platform_vnext.certification.model_certification import (
    CaseStatus,
    CertificationCase,
    ModelCertificationAdapter,
)


def test_certification_normalizes_pass_fail_and_conditional():
    def execute(case):
        if case.case_id == "pass":
            return True, (("ruff", True), ("pytest", True)), None
        if case.case_id == "conditional":
            return False, (("ruff", True), ("pytest", False)), "test failure"
        return False, (("ruff", False), ("pytest", False)), "validation failure"

    report = ModelCertificationAdapter(execute).certify(
        model_id="candidate-model",
        skill_id="GS-PY-001",
        corpus=(
            CertificationCase("pass", "implement function"),
            CertificationCase("conditional", "fix test"),
            CertificationCase("fail", "refactor module"),
        ),
    )

    assert [case.status for case in report.cases] == [
        CaseStatus.PASS,
        CaseStatus.CONDITIONAL,
        CaseStatus.FAIL,
    ]
    assert report.passed == 1
    assert report.conditional == 1
    assert report.failed == 1


def test_certification_records_executor_errors():
    def execute(_):
        raise RuntimeError("provider unavailable")

    report = ModelCertificationAdapter(execute).certify(
        model_id="candidate-model",
        skill_id="GS-PY-001",
        corpus=(CertificationCase("error", "implement"),),
    )
    assert report.cases[0].status is CaseStatus.ERROR
    assert report.cases[0].failure_reason == "provider unavailable"
