# GAIEP Evidence Corpus V1 Runbook

## Purpose

Exercise the already-implemented GAIEP research stack with a controlled 3-task × 4-arm matrix and retain all evaluated trajectories in GreenMemory.

The four arms are:

- `small-python-coder / inspect-plan-implement-test`
- `small-python-coder / inspect-implement-test`
- `qwen3.6-27b / inspect-plan-implement-test`
- `qwen3.6-27b / inspect-implement-test`

This produces 12 trials.

## Important distinction

`self_improvement/controlled_pilot.py` is a deterministic fixture only. It intentionally produces two repeated failures so the research loop can be integration-tested. It must never be confused with real model evidence and must not be inserted into the user's real `.gaiep/greenmemory.sqlite3`.

The real V1 run must use the existing Gateway/model bindings and a separate evidence database or an explicitly approved research database.

## Local validation

From `GAIEP-LAB/greenz-ai-engineering-local`:

```bash
uv run --extra dev pytest self_improvement/test_controlled_pilot.py
uv run --extra dev pytest
uv run --extra dev pyright
uv run --extra dev ruff check self_improvement/controlled_pilot.py self_improvement/test_controlled_pilot.py
uv build
 git diff --check
```

## Real V1 run acceptance

1. Freeze exactly three legitimate task IDs from the existing certification/research corpus.
2. Confirm the selected small Python coder binding. Do not silently substitute a different model.
3. Confirm `qwen3.6:27b` is the intended baseline endpoint.
4. Execute sequentially on the Mac; do not run the two large-model arms concurrently.
5. Persist every completed trajectory into GreenMemory.
6. Verify the matrix contains exactly 12 unique `(task_id, model, scaffold)` cells.
7. Verify provenance is present for governed runtime calls.
8. Verify raw candidate source is not stored in trajectory JSON.
9. Verify GreenMemory integrity after the run.
10. Only after the run, inspect recurring failure clusters.

## Research-loop acceptance

If no failure fingerprint reaches the recurrence threshold, report `INCONCLUSIVE / insufficient evidence` and stop.

If a fingerprint recurs at least twice:

`GreenMemory -> FailureMiner -> ResearchHypothesis -> ResearchProposal -> explicit external approval -> ExperimentRunner -> GreenMemory -> assess_intervention`

The intervention outcome must be one of:

- `IMPROVED`
- `NO_CHANGE`
- `REGRESSED`
- `INCONCLUSIVE`

## Prohibited shortcuts

- Do not manufacture failures in the real GreenMemory corpus.
- Do not treat fixture results as model evidence.
- Do not let FailureResearchLoop execute without explicit approval.
- Do not modify production routing or authorization as part of the experiment.
- Do not train/fine-tune a model from this first corpus automatically.
- Do not introduce embeddings/vector search until deterministic fingerprints prove insufficient.
