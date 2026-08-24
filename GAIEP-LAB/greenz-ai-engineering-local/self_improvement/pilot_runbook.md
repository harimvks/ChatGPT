# GAIEP Self-Improvement Pilot — Local Execution Runbook

## Purpose

Execute the frozen model × scaffold × task pilot against the real local GAIEP runtime. This document is an execution contract, not a claim that the pilot has already run.

## Preconditions

- checkout `gaiep/self-improvement-pilot-execution`;
- install the GAIEP-LAB research package and its test dependencies;
- make the existing certification corpus available to the runner;
- start the existing GAIEP Gateway/local model runtime;
- bind `small-python-coder` and `qwen3.6-27b` through environment configuration;
- verify that both logical model bindings resolve to the intended installed model identifiers;
- verify the validation tools (`pytest`, `ruff`, `pyright`) are available.

## Safety

Run only against a disposable research workspace. Do not point candidate materialization at a production GreenZAlgo checkout. Do not grant the model credentials, network access, or write access that are not required by the task. Do not merge or promote results automatically.

## Execution

1. Freeze the manifest and record its hash.
2. Select exactly three existing certification cases according to `pilot_tasks.md`.
3. Run the 12-cell matrix.
4. Persist one trajectory record after every cell.
5. If a cell fails, classify and persist the failure; continue with remaining cells.
6. Generate the comparison report only after all cells are terminal.
7. Re-run failed cells independently before using them as training examples.

## Required evidence

- experiment ID and manifest hash;
- source corpus version and task IDs;
- logical model and resolved endpoint model;
- scaffold identifier;
- latency and termination status;
- artifact validity result;
- pytest/ruff/pyright results;
- reward and failure class;
- trajectory record path;
- report hash.

## Decision rule

The pilot does not promote or route a model. A small model is only eligible for a larger sweep if the end-to-end execution is reproducible and its objective results justify further investigation. Production certification remains a separate governance step.
