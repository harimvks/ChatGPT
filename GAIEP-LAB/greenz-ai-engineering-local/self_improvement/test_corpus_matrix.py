from self_improvement.controlled_pilot import build_controlled_pilot
from self_improvement.corpus_matrix import CorpusCell, validate_cells


def test_controlled_plan_has_twelve_expected_cells() -> None:
    spec = build_controlled_pilot()
    result = validate_cells(spec.plan, ())
    assert result.expected_cells == 12
    assert result.observed_cells == 0
    assert len(result.missing_cells) == 12
    assert not result.passed


def test_matrix_validator_accepts_exact_complete_matrix() -> None:
    spec = build_controlled_pilot()
    cells = [
        CorpusCell(task_id, arm.model_name, arm.scaffold_name)
        for task_id in spec.plan.task_ids
        for arm in spec.plan.arms
    ]
    result = validate_cells(spec.plan, cells)
    assert result.passed
    assert result.duplicate_cells == ()
    assert result.missing_cells == ()


def test_matrix_validator_rejects_duplicates_and_missing_cells() -> None:
    spec = build_controlled_pilot()
    cells = [
        CorpusCell(spec.plan.task_ids[0], spec.plan.arms[0].model_name, spec.plan.arms[0].scaffold_name),
        CorpusCell(spec.plan.task_ids[0], spec.plan.arms[0].model_name, spec.plan.arms[0].scaffold_name),
    ]
    result = validate_cells(spec.plan, cells)
    assert not result.passed
    assert len(result.duplicate_cells) == 1
    assert len(result.missing_cells) == 11
