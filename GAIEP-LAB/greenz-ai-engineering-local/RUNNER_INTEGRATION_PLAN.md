# GAIEP Runner Integration Plan

## Purpose

Prepare a staging-only, feature-flagged integration of GAIEP model provenance into the existing GreenZ AI Engineering runner. This document does not authorize changes to the VPS or production repository.

## Existing boundary

```text
run_task.py
    |
    v
_default_model_call()
    |
    v
Gateway
    |
    v
ChatResult
    |
    +--> existing corrections capture / parsing / gates
    |
    v
with_provenance()
    |
    v
persist_model_completion()
    |
    +--> FileArtifactStore
    +--> SQLite ArtifactReferenceIndex
    |
    v
model.completed / trajectory
```

## Integration rules

1. The Gateway remains the provider/model abstraction.
2. `_default_model_call()` remains the production ModelCall seam.
3. `ChatResult` remains the source of truth for resolved provider/model/execution/context metadata.
4. Provenance must not change the returned `ChatResult`.
5. Failed model calls must not produce successful completion provenance.
6. Artifact persistence failures are fail-closed when provenance is enabled.
7. Existing corrections capture, parser, repair, failover, gates, and certification behavior must remain unchanged.
8. Provenance is disabled by default until the staging test suite and existing GEOS tests pass.
9. No production/VPS integration is implied by this staging branch.

## Feature flag

Target configuration shape:

```yaml
provenance:
  enabled: false
  fail_closed: true
  artifact_root: artifacts
```

When disabled, execution follows the existing path. When enabled, the ModelCall is wrapped with `with_provenance()`.

## Wiring target

```python
model_call = _default_model_call(...)
if provenance_enabled:
    model_call = with_provenance(
        model_call,
        repo_root=repo_root,
        run_id=run_id,
    )
```

The final implementation must be a surgical patch to the exact current `run_task.py`; never reconstruct or replace the file from a truncated API response.

## Validation matrix

| Scenario | Expected result |
|---|---|
| Successful model call | Original `ChatResult` returned; artifact persisted |
| Provider failure | Original exception propagates; no successful artifact |
| Artifact-store failure | Provenance failure propagates when enabled |
| Failover | Actual final provider/model and failover metadata preserved |
| Parser/repair | Existing behavior unchanged |
| Existing corrections capture | Still emitted |
| Provenance disabled | Legacy behavior unchanged |
| Certification sweep | No unintended provenance coupling |
| Shared artifact | No duplicate bytes; additional reference only |

## Promotion gate

Do not apply to VPS until all of the following are true:

- staging integration tests pass;
- existing GEOS runner tests pass;
- certification tests pass;
- ruff passes;
- pyright passes;
- full diff is reviewed;
- feature flag is explicitly enabled only in the intended environment;
- rollback procedure is documented.
