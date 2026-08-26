# Codex Handoff — Real Evidence → Research Cycle

## Current implementation

The branch now contains:

- durable GreenMemory evidence store;
- runtime provenance derived from MCP/runtime events;
- FailureMiner recurring-failure clustering;
- `FailureResearchLoop` for deterministic hypotheses/proposals;
- durable research lineage;
- explicit proposal lifecycle: `PROPOSED`, `APPROVED`, `SUBMITTED`, `COMPLETED`, `REJECTED`, `FAILED`;
- `ResearchSubmissionAdapter` requiring explicit external approval;
- controlled `ExperimentRunner` submission;
- read-only hypothesis lineage reporting.

## Remaining objective

Prove one real governed GAIEP execution can feed the complete research cycle. Do not invent evidence and do not bypass the existing Capability/MCP authorization boundary.

## Required real-runtime flow

```text
real GAIEP request
  -> ContextEngine
  -> Skill disclosure
  -> capability request
  -> authorization
  -> MCP Gateway
  -> runtime
  -> observation/artifact/evidence
  -> RunProvenance
  -> TrajectoryRecord
  -> GreenMemory
  -> FailureMiner
  -> ResearchProposal
  -> explicit external approval
  -> ResearchSubmissionAdapter
  -> controlled ExperimentRunner
  -> evaluation
  -> new TrajectoryRecord
  -> GreenMemory
  -> research lineage report
```

## P0 — runtime evidence ingestion

Use the existing real Context/Skills -> MCP Gateway -> Runtime vertical path. Execute exactly one safe, non-production research task through the governed boundary.

Verify the persisted GreenMemory record contains:

- run ID;
- context manifest ID/hash;
- skill fingerprint(s);
- requested capability ID/version;
- authorization decision;
- endpoint/model identity;
- latency/usage when available;
- observation reference;
- artifact reference(s);
- evidence reference(s).

Verify retrieval by run, context hash, skill fingerprint and authorized capability.

Do not write candidate source into GreenMemory.

## P0 — real failure-cycle fixture

If the real run does not produce a recurring failure, do not manufacture one. Use two already-existing real evidence records with the same deterministic failure fingerprint, or stop and report that the recurrence threshold is not met.

For a valid recurring failure:

1. run `FailureResearchLoop.discover()`;
2. generate a proposal using the corresponding engineering task;
3. verify the hypothesis references exact evidence IDs;
4. verify a `PROPOSED` lineage event exists;
5. explicitly approve outside the loop;
6. submit through `ResearchSubmissionAdapter`;
7. run the controlled experiment;
8. verify resulting evidence is persisted;
9. verify lineage connects source evidence -> hypothesis -> task -> experiment -> result evidence.

## P0 — denial safety

Execute a denied capability request in a controlled test/runtime fixture and verify:

- authorization decision is retained;
- no runtime execution occurs;
- no execution observation is fabricated;
- GreenMemory stores the denial evidence;
- authorized-capability queries exclude the denied capability.

## P0 — validation

```bash
uv run --extra dev pytest
uv run --extra dev pyright
uv run --extra dev ruff check self_improvement/research_loop.py self_improvement/research_report.py self_improvement/test_research_loop.py self_improvement/test_research_report.py
uv build
git diff --check
```

Full Ruff failures outside this slice may remain known technical debt; do not silently reclassify them as this feature's failures.

## P1 — improve lineage reporting

Add a report that can show the complete lifecycle for each hypothesis, including status transitions and result evidence. Keep it read-only.

## Hard invariants

- Research code never authorizes capabilities.
- Research code never directly invokes MCP/runtime capabilities.
- Proposal generation never executes.
- Approval is external to `FailureResearchLoop`.
- GreenMemory is append-only/idempotent.
- Denied authorization cannot produce an execution observation.
- Every hypothesis retains exact source evidence IDs.
- Every result evidence record retains normal RunProvenance.
- No raw candidate source is stored in GreenMemory.
- No model promotion/routing/training changes occur in this phase.

## Explicitly out of scope

Do not add vector search, embeddings, RAG, LoRA/SFT, RL, autonomous production changes, model promotion, or automatic routing changes until the real evidence research cycle is demonstrated and reviewed.
