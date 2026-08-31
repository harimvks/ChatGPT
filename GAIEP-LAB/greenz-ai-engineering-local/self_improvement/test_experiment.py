from self_improvement.experiment import build_small_model_pilot


def test_small_model_pilot_is_reproducible_and_explicit():
    plan = build_small_model_pilot(["t1", "t2", "t3"])
    assert plan.name == "gaiep-small-python-pilot-v0"
    assert plan.matrix_size() == 12
    assert {arm.scaffold_name for arm in plan.arms} == {
        "inspect-plan-implement-test",
        "inspect-implement-test",
    }
    assert {arm.model_name for arm in plan.arms} == {
        "small-python-coder",
        "qwen3.6-27b",
    }
