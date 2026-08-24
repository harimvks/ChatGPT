from self_improvement.experiment import ExperimentArm
from self_improvement.pilot_report import summarize, to_markdown
from self_improvement.pilot_runner import PilotTrialResult
from self_improvement.trajectory import TrajectoryRecord


def test_report_groups_by_model_and_scaffold():
    trials = [
        PilotTrialResult("t1", ExperimentArm("m", "s"), "a", "b", TrajectoryRecord("t1", "m", "s", (), True, 1.0, (("pytest", True),))),
        PilotTrialResult("t2", ExperimentArm("m", "s"), "a", "b", TrajectoryRecord("t2", "m", "s", (), False, 0.0, (("pytest", False),))),
    ]
    rows = summarize(trials)
    assert len(rows) == 1
    assert rows[0].trials == 2
    assert rows[0].pass_rate == 0.5
    assert "50.0%" in to_markdown(trials)
