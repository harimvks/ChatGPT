# GAIEP Final Corpus → Governed Runtime Integration Handoff

## Purpose

Complete the remaining local-only integration needed to execute the real 3×4 evidence corpus. Do not add a second execution authority, provider-specific research logic, or a second sandbox implementation.

## Current architecture

```text
CorpusMatrix
    ↓
CorpusRunner
    ↓
ModelRunner
    ↓
GovernedModelRunner
    ↓
existing GAIEP governed rollout/runtime
    ↓
existing CandidateSandbox / SandboxEvaluator
    ↓
EvaluationResult
    ↓
RunProvenance
    ↓
GreenMemoryStore
```

The self-improvement layer must remain policy/orchestration only. It must not directly invoke MCP, choose authorization, bypass Context/Skills, or write production state.

## Current contracts already present

- `self_improvement/model_runner.py`: provider-neutral `ModelRequest`, `ModelResult`, `ModelRunner`, and callable test adapter.
- `self_improvement/runner_adapter.py`: governed adapter around an externally supplied rollout boundary.
- `self_improvement/corpus_matrix.py`: deterministic `(task_id, model_name, scaffold_name)` cell identity and matrix validation.
- `self_improvement/corpus_runner.py`: deterministic execution of prevalidated cells through injected `ModelRunner`; it does not persist directly to GreenMemory.
- `self_improvement/controlled_pilot.py`: deterministic 3-task × 4-arm fixture; fixture failures must never be copied into the real `.gaiep` ledger.
- `self_improvement/research_outcome.py`: evidence-based `IMPROVED`, `NO_CHANGE`, `REGRESSED`, `INCONCLUSIVE` classification.
- GreenMemory / FailureResearchLoop / durable lineage / explicit proposal approval are already implemented and validated.

## Step 1 — inspect local implementation before editing

Run from `/Users/hariprasad/Trading/ChatGPT`:

```bash
rg -n "class SandboxEvaluator|SandboxEvaluator|class CandidateSandbox|CandidateSandbox" \
  GAIEP-LAB/greenz-ai-engineering-local

rg -n "GovernedModelRunner|CorpusRunner|ModelRunner|GreenMemoryStore|RunProvenance" \
  GAIEP-LAB/greenz-ai-engineering-local/self_improvement
```

Locate the existing evaluator and governed runtime entrypoint. Do NOT create a replacement if one already exists.

## Step 2 — implement the narrow integration

Wire the existing components so one corpus cell follows this path:

```text
CorpusCell
  ↓
EngineeringTask
  ↓
ModelRequest
  ↓
GovernedModelRunner
  ↓
existing governed execution
  ↓
CandidateSandbox
  ↓
SandboxEvaluator
  ↓
structured result
```

The integration must preserve:

- task ID;
- model name;
- endpoint model, if available;
- scaffold name;
- run ID;
- context manifest/hash;
- skill fingerprint(s);
- authorization decision;
- capability ID/version where applicable;
- observation reference;
- artifact reference;
- evidence reference;
- latency;
- usage metadata;
- evaluation status and failure fingerprint.

If the existing governed runtime already supplies these, propagate them; do not recompute them in the research layer.

## Step 3 — enforce cell/result identity

For every result, assert:

```text
result.task_id == cell.task_id
result.model_name == cell.model_name
result.scaffold_name == cell.scaffold_name
```

If the current `ModelResult` does not contain task/scaffold identity, extend the contract minimally or carry it through immutable metadata. Do not infer identity from free-form model output.

Duplicate cells must fail before execution.
Unknown task IDs must fail before execution.
Unexpected cells must fail corpus validation.

## Step 4 — GreenMemory persistence boundary

Keep persistence outside `CorpusRunner` unless the existing runtime already owns persistence.

Preferred flow:

```text
CorpusRunner → governed result
                    ↓
             evaluation/provenance
                    ↓
              GreenMemoryStore
```

Use the existing GreenMemory APIs. Do not introduce another SQLite schema.

Every real cell should produce one durable lineage record. Re-running the same immutable evidence must be idempotent according to the existing record-ID rules.

## Step 5 — sandbox invariants

Candidate code must execute only inside the existing isolated workspace.

The candidate must not have write access to:

- GAIEP source tree;
- `.gaiep/greenmemory.sqlite3`;
- authorization state;
- MCP credentials/secrets;
- research lineage state.

Evaluation may read the candidate workspace and produce structured evaluation evidence, but must not mutate research policy or approve proposals.

## Step 6 — tests before real execution

Add/extend tests for:

1. one corpus cell reaches the governed runner;
2. evaluator output is retained;
3. provenance survives the complete path;
4. failed evaluation becomes evidence;
5. candidate cannot write outside sandbox;
6. GreenMemory is not mutated by unit tests unless an isolated temporary DB is explicitly supplied;
7. duplicate cell is rejected;
8. unknown task is rejected;
9. model/scaffold/task identity cannot silently change;
10. authorization denial produces no execution observation;
11. 12-cell matrix validation reports exactly 12 unique cells for the real plan.

## Step 7 — validation commands

```bash
cd /Users/hariprasad/Trading/ChatGPT/GAIEP-LAB/greenz-ai-engineering-local

uv run --extra dev pytest
uv run --extra dev pyright
uv run --extra dev ruff check self_improvement
uv build
git diff --check
```

Do not report success unless these actually pass. Existing unrelated Ruff debt may be reported separately only if it is demonstrably outside the changed integration files.

## Step 8 — real corpus execution

Only after Step 7 passes, execute the real 3×4 corpus.

The exact matrix is:

```text
3 legitimate engineering tasks
×
4 predefined experimental arms
=
12 unique trials
```

Use the repository's existing `CorpusMatrix` specification rather than inventing a second matrix.

The real run must use the actual local model/provider binding through the existing governed runtime. No fixture runner is acceptable for this milestone.

Recommended execution properties:

- deterministic task ordering;
- explicit run ID per cell;
- fresh sandbox per trial;
- no reuse of candidate workspaces;
- durable GreenMemory persistence after evaluation;
- failure evidence retained even when a candidate fails;
- no raw candidate/source material copied into trajectory records unless the existing evidence policy explicitly permits it.

## Step 9 — validate the real corpus

Run the matrix validator and verify:

```text
expected cells = 12
observed cells = 12
duplicates = 0
missing = 0
unexpected = 0
```

Then inspect GreenMemory:

```text
records >= 12
integrity = PASS
```

Do not assume every trial passes.

## Step 10 — research-loop trigger

After the real corpus is persisted:

```text
GreenMemory
   ↓
FailureMiner
```

If fewer than two matching failures exist:

```text
no recurring failure
→ INCONCLUSIVE
→ no hypothesis
→ no proposal
```

Do not manufacture failures.

If a legitimate recurring failure exists:

```text
recurring failure
→ hypothesis
→ proposal
→ explicit external approval
→ controlled experiment
→ follow-up evidence
→ research_outcome.assess_intervention()
```

Self-improvement must never self-approve.

## Step 11 — evidence report

Produce a report containing:

- exact Git commit;
- matrix definition;
- 12 trial IDs;
- model/scaffold/task for every trial;
- evaluation result for every trial;
- latency/usage where available;
- provenance completeness;
- failure fingerprints;
- recurring clusters;
- research proposals, if any;
- approval decisions, if any;
- intervention outcomes, if any;
- GreenMemory integrity result;
- any inconclusive/insufficient-evidence decisions.

Clearly label fixture evidence versus real evidence. Never mix them in the production `.gaiep` ledger.

## Hard prohibitions

Do not:

- create another model runner;
- create another sandbox;
- call Ollama/MLX directly from FailureResearchLoop;
- bypass Capability Gateway or Authorization;
- let a candidate modify GreenMemory;
- let research code approve its own proposal;
- fabricate recurring failures;
- call a fixture result a real model result;
- commit `.gaiep/greenmemory.sqlite3`;
- weaken existing provenance or authorization invariants.

## Definition of done

The milestone is complete only when:

```text
12 real governed trials
       ↓
12 durable GreenMemory observations
       ↓
validated corpus
       ↓
FailureMiner analysis
       ↓
INCONCLUSIVE if insufficient recurrence
OR
real approved research cycle if recurrence exists
```

and all tests/type/build/integrity checks pass.

## Final reporting format

Return:

1. commit SHA;
2. changed files;
3. tests and exact counts;
4. real corpus count;
5. GreenMemory count/integrity;
6. recurring failure count;
7. research outcome;
8. any remaining blockers.

Do not claim the real corpus ran unless it actually ran against the local governed runtime.
