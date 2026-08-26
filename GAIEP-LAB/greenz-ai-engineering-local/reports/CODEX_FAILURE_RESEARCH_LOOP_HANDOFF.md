# Codex Handoff — Failure Research Loop V0

## Objective

Complete the deterministic failure-to-research loop on `codex/gaiep-greenmemory-evidence-store` and connect it to the existing governed experiment path without creating a second execution or authorization authority.

## Implemented in this branch

- `self_improvement/research_loop.py`
- `FailureResearchLoop.discover()` reads durable GreenMemory failures and returns recurring `EvidenceFailureCluster` objects.
- `FailureResearchLoop.propose()` creates deterministic `ResearchHypothesis` + `ResearchProposal` objects linked to source evidence IDs and task IDs.
- proposals use the existing `TaskFactory`; they do not execute anything.
- `test_research_loop.py` covers recurrence threshold, evidence linkage, deterministic task source, and proposal bounds.
- `pyproject.toml` registers the new tests.
- `self_improvement.__init__` exports the new public types.

## Required Codex work

### P0 — Validate and repair

Run from `GAIEP-LAB/greenz-ai-engineering-local`:

```bash
uv run --extra dev pytest self_improvement/test_research_loop.py self_improvement/test_evidence_store.py self_improvement/test_failure_miner.py
uv run --extra dev pytest
uv run --extra dev pyright
uv run --extra dev ruff check self_improvement/research_loop.py self_improvement/test_research_loop.py self_improvement/evidence_store.py self_improvement/failure_miner.py
uv build
 git diff --check
```

Fix only issues introduced by this slice. Do not expand scope to unrelated pre-existing lint debt.

### P0 — Correct evidence linkage

The current `_record_id()` helper derives the same content-addressed ID used by GreenMemory. Prefer a public GreenMemory lookup/helper if one is added; do not duplicate identity rules in multiple modules.

### P0 — Add execution handoff adapter

Add a small adapter that accepts a `ResearchProposal` and submits it to the existing controlled `ExperimentRunner`/research loop only after an explicit caller request. It must never auto-execute merely because a proposal exists.

The adapter should return a structured submission record containing:

- proposal/hypothesis ID
- task ID
- originating evidence IDs
- submission timestamp
- execution status (`PROPOSED`, `SUBMITTED`, `COMPLETED`, `REJECTED`)

Do not add autonomous scheduling.

### P0 — Persist research lineage

Add durable lineage records to GreenMemory for:

`evidence record -> failure fingerprint -> hypothesis -> research task -> experiment run -> resulting evidence`

Prefer normalized SQLite tables with foreign keys. Preserve append-only semantics. Add idempotency and restart tests.

### P0 — Closed-loop integration test

Build one deterministic test fixture that proves:

1. two recurring failed trajectories enter GreenMemory;
2. FailureResearchLoop discovers the recurring fingerprint;
3. a hypothesis is generated with exact evidence IDs;
4. a research task is generated through TaskFactory;
5. the task is submitted to the existing controlled runner;
6. evaluation produces a new trajectory;
7. the new trajectory is persisted to GreenMemory;
8. lineage connects original evidence to follow-up evidence.

Use a fake/in-memory model callable. Do not invoke a real model in unit tests.

### P1 — Research governance

Add explicit proposal-state transitions:

`PROPOSED -> APPROVED -> SUBMITTED -> COMPLETED`

and terminal states `REJECTED` / `FAILED`.

Approval must be external to FailureResearchLoop. The loop can recommend; it cannot approve itself.

### P1 — Failure recurrence policy

Keep the initial recurrence threshold deterministic. Default to 2 independent evidence records. Do not introduce embeddings or semantic similarity yet.

### P1 — Reporting

Add a compact report/API showing:

- recurring failure fingerprint
- count
- models affected
- tasks affected
- originating evidence
- generated hypothesis
- generated follow-up task
- resulting experiment/evidence, when available

## Hard invariants

1. FailureResearchLoop is research-only.
2. It cannot execute capabilities.
3. It cannot grant authorization.
4. It cannot change model routing.
5. It cannot promote a model.
6. It cannot mutate production repositories.
7. Proposal creation alone never starts an experiment.
8. Every generated hypothesis must retain evidence lineage.
9. Every follow-up task must have deterministic identity.
10. New evidence must flow back into GreenMemory.

## Final validation target

The final branch should demonstrate:

`real/fixture trajectory -> GreenMemory -> recurring failure -> hypothesis -> proposal -> explicit approval/submission -> controlled experiment -> evaluation -> GreenMemory`

No vector database, RAG, LoRA/SFT, RL, autonomous agent loop, or production routing changes belong in this phase.
