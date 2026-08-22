# GreenZ AI Engineering — Local Integration Workspace

This directory is a **ChatGPT-side staging copy** for GAIEP Runtime VNext work. It is intentionally separate from the production GreenZ AI Engineering repository and VPS checkout.

## Source

Production source repository:
`harimvks/greenz-ai-engineering`

Working source branch:
`feat/gaiep-runtime-vnext-phase0`

## Purpose

Use this workspace to prepare and review the GAIEP provenance integration before it is applied to the VPS checkout.

### Current target integration

```text
runner/run_task.py
        |
        v
_default_model_call()
        |
        v
Gateway -> ChatResult
        |
        +--> existing corrections capture
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

## Safety rule

Do not replace the production `runner/run_task.py` wholesale from an incomplete API response. The production file contains accumulated corrections and governance behavior. The eventual VPS change must be a surgical edit with a reviewed diff and full validation.

## Integration contract

1. Preserve Gateway routing and failover.
2. Preserve `ChatResult` semantics.
3. Preserve `corrections.capture.log_response()`.
4. Persist successful model output as a content-addressed artifact.
5. Register the artifact against the model request.
6. Emit durable model provenance.
7. Do not create a false successful provenance record for failed model calls.
8. Add a feature flag before enabling this in production.
9. Run pytest, ruff, pyright and the existing GEOS runner/certification tests before VPS integration.
