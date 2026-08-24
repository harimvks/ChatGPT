import pytest

from self_improvement.experiment import ExperimentArm, ExperimentPlan
from self_improvement.pilot_manifest import PilotManifest, freeze_task_ids


def test_manifest_freezes_three_tasks_and_counts_trials():
    plan = ExperimentPlan(
        name="pilot-v0",
        task_ids=("a", "b", "c"),
        arms=(ExperimentArm("m1", "s1"), ExperimentArm("m2", "s2")),
    )
    manifest = PilotManifest.from_plan(plan, corpus_version="cert-v1")
    assert manifest.trial_count() == 6
    assert manifest.corpus_version == "cert-v1"


def test_task_freeze_requires_exactly_three_unique_ids():
    assert freeze_task_ids(["a", "b", "c"]) == ("a", "b", "c")
    with pytest.raises(ValueError):
        freeze_task_ids(["a", "b"])
    with pytest.raises(ValueError):
        freeze_task_ids(["a", "a", "b"])
