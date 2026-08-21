# Phase 6 — Model Certification Adapter

## Purpose

Normalize candidate-model results for `GS-PY-001` without creating a competing certification ledger.

```text
Candidate Deployment
       |
       v
Fixed GS-PY-001 Corpus
       |
       v
Same Context / Skill / Mutation Policy
       |
       v
Same Validation Profile
       |
       v
CaseResult
       |
       v
ModelCertificationReport
       |
       v
Existing GreenZ certification structures
```

## Result classes

- `PASS` — accepted and validation gates pass.
- `FAIL` — rejected and validation gates do not provide a conditional result.
- `CONDITIONAL` — not accepted, but at least one validation gate passes; this is a diagnostic class, not automatic certification.
- `ERROR` — execution/provider/test harness error.

## Repetition

Each corpus case declares its repetition count. The adapter preserves one result per execution so latency and failure behavior remain observable.

## Important constraint

The adapter does **not** decide that a model is certified. It only normalizes evidence. The existing GreenZ certification gate/ledger remains authoritative.

## Candidate evaluation

The first candidate sweep should use the existing GreenZ certification corpus where possible. Do not silently substitute generic coding benchmarks.

For the Mac deployment, record:

```text
model identifier
artifact/quantization
hardware
resident/peak memory
latency
case status
validation results
failure reason
OOM/crash/error
```

This preserves comparability with the existing Qwen3.6:27B certification evidence.
