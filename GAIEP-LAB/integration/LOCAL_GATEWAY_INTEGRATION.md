# Local Gateway Integration Runbook

This runbook is the bridge from the isolated GAIEP-LAB codebase to the real GreenZ runtime. It does not modify the production repositories.

## Gate A — local static/test gate

Run from the GAIEP-LAB package root:

```bash
ruff check .
pyright
pytest -q
```

Do not proceed to model certification if any gate fails.

## Gate B — real Gateway read-only run

Use a local Python environment containing the existing `greenz-ai-engineering` and `greenz-ai-platform` checkouts at their pinned compatible revisions.

The integration callback must call the existing `CertifiedProviderRegistry` / `Gateway` composition path. Do not instantiate a parallel provider registry and do not call Ollama directly from the certification adapter.

Required captured fields:

- platform commit SHA;
- engineering commit SHA;
- GAIEP-LAB commit SHA;
- context ID/hash;
- skill ID/version;
- capability tag;
- model/provider;
- execution ID;
- latency;
- output hash;
- validation result;
- failover metadata;
- final AgentRun status.

## Gate C — Qwen control

Run the fixed GreenZ engineering certification corpus with the already-established Qwen3.6:27B control deployment. Keep corpus, context policy, skill, mutation policy, and validation profile unchanged.

Record hardware and model metadata including quantization and runtime version.

## Gate D — write test

Use a disposable workspace only. The write test must demonstrate:

1. explicit mutation approval;
2. allowed-root enforcement;
3. before/after SHA-256;
4. unified diff;
5. ruff;
6. pyright;
7. pytest;
8. rollback on validation failure;
9. evidence record.

Never use the production GreenZ repositories for the first write test.

## Gate E — candidate sweep

Only after the Qwen control is reproducible should candidate models be evaluated. Change only the deployment/model. Keep the corpus and validation profile fixed.
