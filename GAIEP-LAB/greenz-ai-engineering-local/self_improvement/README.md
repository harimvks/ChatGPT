# GAIEP Self-Improvement Engine — V0

This is the first implementation slice inspired by the Ornith-1.5 self-improvement methodology.

## Scope

V0 implements the **research/evidence loop** while remaining isolated from production repositories and certification state:

```text
seed / observed signal
        ↓
TaskFactory
        ↓
controlled engineering task
        ↓
external validation gate
        ↓
EvaluationResult
        ↓
FailureMiner
        ↓
targeted follow-up task
```

The integration layer now includes:

- `corpus_adapter.py` — read-only adapter for GAIEP certification artifacts;
- `gate_adapter.py` — subprocess boundary for externally supplied `ruff` / `pyright` / `pytest` commands;
- deterministic conversion of certification evidence into `EngineeringTask` records;
- tests covering corpus parsing and external validation execution.

## Design principles

1. **External evidence defines success.** The model cannot self-report a pass.
2. **Tasks are reproducible.** Task IDs are content-derived.
3. **Certification evidence is preserved.** Model, benchmark, corpus version, result, functional status, lint/type/test evidence, latency, backstop, and failure detail are retained.
4. **Validation remains external.** The gate executes supplied commands and returns immutable evidence; it does not alter source code.
5. **Failures become research signals.** Repeated failure classes can generate targeted follow-ups.
6. **Research stays isolated.** Nothing here modifies production repositories, model weights, routing policy, or certification state.
7. **Promotion remains human-gated.** Any future trained candidate must enter the existing certification/promotion path.

## Next layers

```text
Certification Corpus
        ↓
Task / Case Adapter
        ↓
Harness / Scaffold Generator
        ↓
Agent Rollout
        ↓
Sandbox + Validation Gate
        ↓
Reward / Evidence Engine
        ↓
Trajectory / Failure Store
        ↓
Curriculum + Task Generation
        ↓
Fine-tuning / RL
        ↓
Certification
```

Training remains intentionally out of scope until real rollout/evaluation evidence is accumulated.
