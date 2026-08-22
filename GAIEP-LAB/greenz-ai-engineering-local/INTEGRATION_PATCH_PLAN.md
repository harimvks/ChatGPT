# Production Integration Patch Plan

## Target

Production file:
`runner/run_task.py`

Do **not** replace the file wholesale.

## Surgical change

At the existing `_default_model_call()` seam:

```text
_default_model_call(...)
        |
        v
Gateway -> ChatResult
        |
        +--> existing corrections.capture.log_response()
        |
        v
GAIEP provenance wrapper
```

The safest production wiring is to wrap the returned `ModelCall` at the caller that constructs the default model call. The wrapper must return the original `ChatResult` unchanged.

## Required behavior

### Success

```text
Gateway success
   -> ChatResult
   -> persist_model_completion()
   -> artifact store
   -> reference index
   -> model.completed provenance
   -> return original ChatResult
```

### Provider failure

```text
Gateway exception
   -> existing exception/failover behavior
   -> no false successful completion artifact
```

### Artifact failure

For the initial governed implementation, provenance persistence failure should fail closed rather than silently claim a fully auditable run. If this is too disruptive for a particular lane, expose an explicit policy flag; do not silently swallow it.

## Integration checklist

- [ ] Preserve existing Gateway/failover behavior.
- [ ] Preserve `corrections.capture.log_response()`.
- [ ] Record actual provider/model from `ChatResult`.
- [ ] Link artifact to execution/request identity.
- [ ] Preserve context ID/hash.
- [ ] Keep existing parser and repair loop unchanged.
- [ ] Add feature flag for staged rollout.
- [ ] Add integration tests.
- [ ] Run pytest.
- [ ] Run ruff.
- [ ] Run pyright.
- [ ] Run existing GEOS/certification tests.
- [ ] Review complete git diff.
- [ ] Only then apply to VPS.
