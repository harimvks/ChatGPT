from self_improvement.experiment import ExperimentArm
from self_improvement.pilot_report import summarize, to_markdown
from self_improvement.pilot_runner import PilotTrialResult
from self_improvement.trajectory import TrajectoryRecord


def test_report_groups_by_model_and_scaffold():
    trials = [
        PilotTrialResult("t1", ExperimentArm("m", "s"), "a", "b", TrajectoryRecord("t1", "m", "s", (), True, 1.0, (("pytest", True),), latency_s=2.0)),
        PilotTrialResult("t2", ExperimentArm("m", "s"), "a", "b", TrajectoryRecord("t2", "m", "s", (), False, 0.0, (("pytest", False),), failure_class="test_failure", latency_s=4.0)),
    ]
    rows = summarize(trials)
    assert len(rows) == 1
    assert rows[0].trials == 2
    assert rows[0].pass_rate == 0.5
    assert rows[0].mean_latency_s == 3.0
    report = to_markdown(trials)
    assert "50.0%" in report
    assert "test_failure: 1" in report
