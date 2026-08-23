# GAIEP Self-Improvement Engine — V0

This is the first implementation slice inspired by the Ornith-1.5 self-improvement methodology.

## Scope

V0 implements only the **research/evidence loop**:

```text
seed / observed signal
        ↓
TaskFactory
        ↓
controlled engineering task
        ↓
external evaluator
        ↓
EvaluationResult
        ↓
FailureMiner
        ↓
targeted follow-up task
```

It deliberately does **not** implement autonomous model training, RL, production routing changes, or automatic promotion.

## Design principles

1. **External evidence defines success.** The model cannot self-report a pass.
2. **Tasks are reproducible.** Task IDs are content-derived.
3. **Failures become research signals.** Repeated failure classes can generate targeted follow-ups.
4. **Research stays isolated.** Nothing here modifies production repositories, model weights, routing policy, or certification state.
5. **Promotion remains human-gated.** Any future trained candidate must enter the existing certification/promotion path.

## Ornith-inspired future layers

```text
Task Factory
    ↓
Harness / Scaffold Generator
    ↓
Agent Rollout
    ↓
Sandbox + Validation
    ↓
Reward Engine
    ↓
Trajectory / Evidence Store
    ↓
Curriculum + Task Generation
    ↓
Fine-tuning / RL
    ↓
Certification
```

The V0 boundary intentionally stops before training. This lets us collect real GreenZ engineering evidence before choosing an RL/fine-tuning implementation.

## Next implementation steps

- connect the factory to existing GAIEP certification corpus;
- add a sandbox adapter around the existing ruff/pyright/pytest gate;
- persist task/rollout/evaluation records using existing provenance/storage contracts;
- add scaffold variants and measure task completion by scaffold;
- add trajectory/failure clustering;
- build a dataset export for MLX/PyTorch fine-tuning;
- only then evaluate LoRA/RL training on Mac or NVIDIA infrastructure.
