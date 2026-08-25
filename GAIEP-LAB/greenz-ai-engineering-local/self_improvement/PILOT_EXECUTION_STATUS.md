# GAIEP Self-Improvement Pilot Execution Status

Status: blocked by missing local pilot inputs
Date: 2026-08-25
Branch: `gaiep/self-improvement-pilot-execution`

## Completed in this branch

- Pilot execution code is bound to injected Gateway `ModelCall` rather than a second router.
- Exactly-three evidence-backed task selection is implemented.
- `PilotManifest` records source certification case IDs and corpus version.
- Model binding preflight checks `GAIEP_MODEL_SMALL_PYTHON_CODER` and `GAIEP_MODEL_QWEN3_6_27B`.
- Trajectory JSONL can resume completed task/model/scaffold cells.
- Trial records preserve logical model, endpoint model, scaffold, latency, usage, checks, reward, and failure class.
- Candidate artifacts still require explicit `{"files": {"relative/path.py": "contents"}}` shape.

## Verification

```text
self_improvement tests: 33 passed
ruff touched self_improvement files: passed
pyright touched self_improvement implementation files: 0 errors
```

## Local runtime discovery

Local Ollama responded on `127.0.0.1:11434` and reported these completion-capable models:

```text
qwen2.5-coder:7b-instruct-q5_K_M
hf.co/unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:IQ4_XS
qwen3.6:27b
```

`qwen3.6:27b` is present locally. The small Python coder binding is not inferred because the handoff explicitly requires the actually selected local Python-specialist model.

## Blocking dependencies

1. No certification corpus files are present under `GAIEP-LAB/greenz-ai-engineering-local/`; only `self_improvement/corpus_adapter.py` exists.
2. `GAIEP_MODEL_SMALL_PYTHON_CODER` is not set.
3. `GAIEP_MODEL_QWEN3_6_27B` is not set.
4. No concrete local Gateway `ModelCall` factory is present in this branch to execute real model trials.

## Fail-closed preflight result

Running `build_execution_plan([])` produced:

```text
RuntimeError: fewer than three suitable implementation pilot cases; missing: isolated_implementation, test_oriented_implementation, integration_refactor_behavior
```

## Required before 12-trial execution

Provide or make available inside this authorized ChatGPT branch:

1. The current certification corpus files containing at least one suitable case each for:
   - isolated implementation;
   - test-oriented implementation;
   - integration/refactor behavior.
2. Environment bindings:
   - `GAIEP_MODEL_SMALL_PYTHON_CODER=<actual selected local Python-specialist model>`
   - `GAIEP_MODEL_QWEN3_6_27B=qwen3.6:27b` or the certified runtime name if different.
3. A real injected Gateway `ModelCall` factory, or the local GAIEP Gateway package/module in this branch.

The pilot should not be declared empirically complete until all 12 trial records are generated from those real inputs.
