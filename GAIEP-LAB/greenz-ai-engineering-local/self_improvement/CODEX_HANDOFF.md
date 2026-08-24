# GAIEP Self-Improvement Pilot — Codex Handoff

## Objective

Complete and execute the first real GAIEP self-improvement pilot on the user's Mac. The repository-side research framework is implemented. Codex is responsible for binding it to the actual local GAIEP runtime, selecting real certification cases, executing the controlled experiment, and fixing any integration/test issues found during execution.

## Repository / branch

- Repository: `harimvks/ChatGPT`
- Branch: `gaiep/self-improvement-pilot-execution`
- Scope: `GAIEP-LAB/greenz-ai-engineering-local/self_improvement/`

Do not merge into production or alter production routing as part of this pilot.

## What is already implemented

- `corpus_adapter.py` — read-only conversion of flat certification artifacts into `EngineeringTask` objects.
- `task_factory.py` — research task construction.
- `rollout.py` — injected `ResearchRolloutRunner` boundary.
- `gateway_rollout.py` — Gateway-compatible rollout adapter using an injected `ModelCall`-compatible callable.
- `artifact.py` — strict candidate file-map normalization and path safety.
- `sandbox.py` — isolated temporary candidate workspace.
- `gate_adapter.py` — external validation command boundary.
- `sandbox_evaluation.py` — normalize → sandbox → validate → objective result.
- `evaluation.py` — external objective scoring.
- `trajectory.py` — immutable research trajectory metadata.
- `trajectory_store.py` — append-only JSONL trajectory metadata store.
- `failure_miner.py` — follow-up task generation from failures.
- `experiment.py` — controlled model × scaffold experiment matrix.
- `experiment_config.py` — environment-driven logical model binding.
- `experiment_runner.py` — executes every task/arm pair.
- `pilot_manifest.py` — frozen pilot manifest and exact-3-task guard.
- `pilot_preflight.py` — fail-closed model-binding preflight.
- `pilot_tasks.md` — deterministic task selection policy.
- `pilot.md` / `PILOT_READY.md` / `pilot_runbook.md` — pilot documentation.

## Architecture to preserve

```text
Existing certification corpus
          ↓
     Pilot Manifest
          ↓
       Preflight
          ↓
 Experiment Runner
          ↓
      GAIEP Gateway
          ↓
    Research Rollout
          ↓
 Candidate Artifact
          ↓
 Artifact Normalizer
          ↓
    Isolated Sandbox
          ↓
 pytest / ruff / pyright
          ↓
 EvaluationResult
          ↓
 TrajectoryRecord / JSONL
          ↓
 FailureMiner
```

The research package must not own model routing. The Gateway remains the routing boundary. Do not create a second provider/router implementation.

## Immediate work for Codex

### 1. Inspect the actual runtime

Find the real GAIEP Gateway implementation, its `ModelCall` request/response contract, and the existing local model execution path. Search the repository rather than guessing names.

Useful search terms:

- `ModelCall`
- `capability_tag`
- `Gateway`
- `CODING`
- `REVIEW`
- `qwen3.6`
- `ollama`
- `omlx`
- `runner`
- existing certification runner / ledger

The repository contains architecture/runtime documents under `GAIEP/` and the LAB boundary under `GAIEP-LAB/`. Respect those existing contracts.

### 2. Bind the logical models

The pilot uses logical names:

- `small-python-coder`
- `qwen3.6-27b`

Resolve them through the existing Gateway/model registry if available. If an environment binding is needed, use:

```text
GAIEP_MODEL_SMALL_PYTHON_CODER=<actual locally served model name>
GAIEP_MODEL_QWEN3_6_27B=<actual locally served model name>
```

Do not assume the small model is Qwen3.5-4B. Use the model that is actually installed/served and has been selected for the current Python-specialist experiment.

### 3. Select the real three tasks

Do NOT invent task IDs.

Find the current certification corpus and select exactly three suitable implementation-oriented cases according to `pilot_tasks.md`:

1. isolated implementation;
2. test-oriented implementation;
3. integration/refactor behavior.

Record exact source IDs and corpus version in the pilot manifest.

Important: `corpus_adapter.py` currently maps a certification PASS to a `review` task and a non-PASS to a `debug` task. That is useful for failure research but does not by itself satisfy the implementation-oriented pilot policy. Do not silently treat three arbitrary certification records as implementation tasks. Either use existing implementation-capable cases or make the smallest evidence-backed adapter extension needed.

### 4. Complete the real Gateway adapter

Connect `GatewayResearchRollout` to the actual Gateway using dependency injection or the existing runtime contract. Do not duplicate routing logic.

The adapter must preserve:

- task ID;
- logical model identity;
- actual endpoint model identity where available;
- scaffold identity;
- prompt/context;
- returned candidate artifact;
- latency / usage metadata if already available.

### 5. Candidate artifact contract

The model/agent output must be normalized into an explicit file map:

```python
{"files": {"relative/path.py": "file contents"}}
```

Reject prose-only or ambiguous outputs. Preserve existing traversal/absolute-path protections.

### 6. Run the pilot

First run only 3 tasks × 2 models × 2 scaffolds = 12 trials.

Scaffolds:

- `inspect-plan-implement-test`
- `inspect-implement-test`

Use the same tasks, validation commands, scoring, and runtime constraints for every arm.

Persist a trajectory after each trial so an interrupted run can resume without losing evidence.

### 7. Re-run failures

Every failed trial should be independently replayable. Do not modify the task/scaffold/model configuration when replaying unless the replay is explicitly recorded as a new experiment.

### 8. Produce the report

Report at minimum:

- trials completed;
- pass rate;
- reward;
- pytest / ruff / pyright outcomes;
- latency;
- failure classes;
- model effect;
- scaffold effect;
- task-level results.

Do not declare a model "better" from one successful case. The pilot is evidence collection, not certification.

## Mac constraints

The user's Mac has 24 GB unified memory and previous local-model testing has shown memory fragility around the 17–18 GB model-residency region. Do not run both large models concurrently. Sequential execution is preferred. Keep concurrency at 1 unless the existing runtime has a measured safe configuration.

Do not change quantization or serving parameters between comparison arms unless they are explicitly recorded in the experiment manifest. The baseline Qwen3.6-27B configuration should remain the previously certified configuration.

## Safety / governance

Absolutely no:

- production repository writes;
- automatic merge;
- automatic model promotion;
- certification bypass;
- production routing changes;
- model-weight updates;
- autonomous RL training;
- deletion or mutation of existing certification evidence.

The pilot is research-only.

## Required completion evidence

Before declaring the pilot complete, provide:

1. exact branch/commit;
2. exact three source task IDs + corpus version;
3. actual model bindings;
4. 12 trial records;
5. trajectory JSONL path/artifact;
6. pilot report;
7. test results;
8. failed-trial replay results, if any;
9. concise conclusion with confidence limitations.

If the local runtime or corpus is unavailable, stop at the missing dependency and report it. Never fabricate model results.

## Suggested Codex sequence

```text
inspect repository/runtime contracts
        ↓
run existing tests
        ↓
find actual Gateway + certification corpus
        ↓
fix integration issues
        ↓
select/freeze 3 real tasks
        ↓
configure real model bindings
        ↓
run preflight
        ↓
run 12 trials sequentially
        ↓
replay failures
        ↓
produce report
        ↓
review diff / tests / evidence
```

## Desired end state

The pilot should answer one empirical question:

> Can the selected cheap Python-specialist model, with a suitable scaffold and the same external validation gates, safely complete a useful subset of GAIEP engineering work compared with the Qwen3.6-27B baseline?

Do not answer that question from model benchmarks. Answer it from the GreenZ/GAIEP corpus evidence generated by this pilot.
