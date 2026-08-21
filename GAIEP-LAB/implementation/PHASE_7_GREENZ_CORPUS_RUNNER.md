# Phase 7 — GreenZ Engineering Corpus Runner

The certification adapter now has a fixed corpus reference layer for the existing GreenZ engineering cases.

## Authoritative cases

The current baseline references are:

- `ENG-CM-112`, corpus v3, 3 repetitions;
- `ENG-CM-113`, corpus v2, 9 repetitions;
- `ENG-CM-114`, corpus v2, 3 repetitions.

These references correspond to existing GreenZ certification evidence and are **not copied into ChatGPT**. Exact prompts/artifacts remain authoritative in `harimvks/greenz-ai-engineering`.

The repository contains recorded PASS evidence for the Qwen3.6:27B baseline for all three selected references. CM-112 reports 3 ruff blocks and 0 pyright blocks with 115.9s latency; CM-113 reports 3 ruff blocks and 0 pyright blocks with 179.9s latency; CM-114 reports 2 ruff blocks and 0 pyright blocks with 84.7s latency.

## Repetition policy

The runner preserves the existing case repetition counts. This is important for distinguishing a one-off success from stable behavior.

## Candidate sweep rule

Every candidate must use:

```text
same corpus reference
same skill
same context construction
same mutation policy
same validation profile
same repetition count
```

Only the model/deployment is changed.

## What the runner does not do

It does not declare certification. It produces normalized evidence for the existing GreenZ certification machinery.

## Next step

Build the local deployment adapter that maps one certified model deployment to the injected case executor. That adapter should use the real Gateway/provider path and write normalized results without modifying the upstream repositories.
