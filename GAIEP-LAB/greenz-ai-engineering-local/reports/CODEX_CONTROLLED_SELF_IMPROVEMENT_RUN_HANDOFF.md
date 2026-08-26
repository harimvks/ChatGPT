# Codex Handoff — Controlled Self-Improvement V0

## Goal

Run the first controlled recurring-failure experiment using the existing GreenMemory → FailureMiner → FailureResearchLoop → approval → ExperimentRunner path.

Do not create or induce a failure in the real governed runtime. Use a clearly isolated research fixture or existing historical evidence.

## New repository support

`self_improvement/research_outcome.py` now provides:

- `ResearchOutcome`: IMPROVED / NO_CHANGE / REGRESSED / INCONCLUSIVE
- `ResearchOutcomeAssessment`
- `assess_intervention(source, follow_up)`

The assessment is evidence-only. It never trusts model self-reported success.

## P0 — validate

From `GAIEP-LAB/greenz-ai-engineering-local`:

```bash
uv run --extra dev pytest self_improvement/test_research_loop.py self_improvement/test_research_outcome.py
uv run --extra dev pytest
uv run --extra dev pyright
uv run --extra dev ruff check self_improvement/research_loop.py self_improvement/research_outcome.py self_improvement/test_research_loop.py self_improvement/test_research_outcome.py
uv build
git diff --check
```

Do not treat unrelated pre-existing full-Ruff debt as part of this slice.

## P0 — controlled experiment

Use a fixture with exactly two independent source trajectories that share one deterministic failure fingerprint, or use two real historical GreenMemory records if they exist.

Required sequence:

1. Confirm source records are in GreenMemory.
2. Confirm `FailureResearchLoop.discover(minimum_count=2)` returns the expected cluster.
3. Generate one `ResearchProposal`.
4. Verify proposal lineage is `PROPOSED`.
5. Explicitly approve it outside the loop.
6. Submit through `ResearchSubmissionAdapter` to the existing controlled `ExperimentRunner`.
7. Persist the resulting trajectory into GreenMemory.
8. Retrieve source and follow-up evidence.
9. Run `assess_intervention()`.
10. Persist/report the outcome without changing production routing or authorization.

## Expected outcomes

- If the targeted failure disappears and all follow-up checks pass: `IMPROVED`.
- If the targeted failure persists: `NO_CHANGE`.
- If the targeted failure disappears but another failure appears: `REGRESSED`.
- If there is no follow-up evidence or insufficient evidence: `INCONCLUSIVE`.

Never label an intervention improved solely because a model claims success.

## P1 — real evidence corpus

After the fixture passes, inspect the actual local `.gaiep/greenmemory.sqlite3` corpus. Do not manufacture recurrence. If fewer than two matching real failures exist, report `INCONCLUSIVE / insufficient evidence` and stop.

The known real governed seed `real-governed-seed-001` is a successful `market.get_quote` execution and must not be altered.

## Governance invariants

- FailureResearchLoop proposes only.
- External approval is mandatory.
- ExperimentRunner remains the only controlled experiment executor.
- Capability Gateway/Authorization remain the execution authority.
- No automatic routing changes.
- No model promotion.
- No production mutation.
- No training or weight updates.
- No vector DB/RAG in this phase.

## Completion evidence

Report:

- source record IDs
- failure fingerprint
- proposal/hypothesis ID
- approval identity
- experiment run ID
- follow-up record IDs
- outcome classification
- remaining targeted failures
- any new failure fingerprints
- integrity check result
- test/build validation

If the experiment is fixture-only, label it explicitly as fixture evidence; do not present it as real model improvement.
