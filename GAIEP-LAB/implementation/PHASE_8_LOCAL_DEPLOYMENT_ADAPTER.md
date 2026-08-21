# Phase 8 — Local Deployment Adapter

The fixed GreenZ corpus is now wrapped in a local deployment identity and operator entrypoint.

## Deployment identity

The run records:

- model identifier;
- provider;
- runtime version;
- artifact digest when available;
- quantization when available;
- hardware when available;
- UTC start time;
- normalized corpus report.

## Deliberate safety boundary

The operator entrypoint does **not** directly call Ollama or another provider. The local callback must connect to the existing GreenZ `CertifiedProviderRegistry` / `Gateway` composition path.

This prevents the certification harness from accidentally becoming a parallel routing/certification system.

## Required local execution path

```text
Mac
 |
 +-- existing greenz-ai-engineering checkout
 |
 +-- existing certified provider registry
 |
 +-- existing Gateway
 |
 +-- candidate deployment
 |
 v
GAIEP-LAB local adapter
 |
 v
GreenZ corpus
 |
 +-- CM-112 x3
 +-- CM-113 x9
 +-- CM-114 x3
 |
 v
Validation / evidence
 |
 v
normalized report
```

## Current state

The adapter and operator entrypoint are implemented, but the actual provider callback is intentionally left unwired in GitHub. The final connection requires the real local Python environment and its existing Gateway composition.

Once wired, run the control model first, then candidates, without changing the corpus or validation profile between runs.
