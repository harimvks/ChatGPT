# Phase 5 — GS-PY-001 Python Validation Profile

The Python implementation skill now has a declarative validation profile. The model cannot add arbitrary shell commands to the validation phase.

## Required validation gates

```text
ruff check .
    ↓
pyright
    ↓
pytest -q
```

All three are required for `accepted=True` in the current skill design.

## Why this matters for model certification

Candidate coding models are evaluated on their ability to produce a useful change proposal. The runtime then measures whether the proposal survives the same deterministic engineering gates.

Therefore the model benchmark should record at least:

- proposal validity;
- authorized mutation count;
- mutation diff size;
- ruff result;
- pyright result;
- pytest result;
- repair attempts, if later enabled;
- final acceptance;
- model/provider/latency;
- evidence completeness.

## Model-neutral boundary

The profile does not name a model. A candidate can be local, remote, large, small, or a specialist. Model selection remains a Gateway/certification concern.

## Next step

Add a certification adapter that maps a candidate deployment to `GS-PY-001`, runs the fixed corpus, and records results in the existing certification/evidence structures rather than inventing a second ledger.
