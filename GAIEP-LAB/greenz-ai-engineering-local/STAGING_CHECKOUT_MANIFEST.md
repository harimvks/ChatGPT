# GAIEP Staging Checkout Manifest

## Purpose

This is the reproducible staging manifest for the GAIEP model-provenance integration. It is not a production/VPS checkout and must not be treated as one.

## Source of truth

Production runner revision pinned for integration work:

`greenz-ai-engineering` / `runner/run_task.py`

Revision:

`093cf730fb343c1f66e1cc281cc6e864425b2440`

The staging integration must be applied against that exact revision, or a later revision whose runner changes have been explicitly reviewed.

## Staged components

```text
runner/
  provenance_model_call.py
  model_provenance_integration.py

runtime/
  artifact_store.py
  artifact_refs.py
  artifact_hooks.py
  artifact_lifecycle.py
  model_provenance.py
  model_artifact_adapter.py

tests/
  runner/test_provenance_model_call.py
  runtime/test_artifact_refs.py
  runtime/test_artifact_hooks.py
  runtime/test_model_artifact_adapter.py
```

## Integration sequence

```text
Exact production runner revision
              |
              v
        _default_model_call
              |
              v
            Gateway
              |
              v
          ChatResult
              |
              v
     optional provenance wrapper
              |
              v
     ModelCompletionProvenance
              |
              v
       ArtifactRegistrar
          /          \
         v            v
   Artifact Store   Reference Index
         \            /
          \          /
           v        v
          durable provenance
```

## Required local setup

Clone the actual `greenz-ai-engineering` repository at the pinned revision into a local staging checkout. Copy/apply only the reviewed GAIEP runtime files and the surgical runner patch. Do not copy the entire production runner from this ChatGPT repository.

The ChatGPT repository is a **review/staging ledger**, not the production source tree.

## Validation commands

```bash
pytest -q
ruff check .
pyright
```

Then run the project's existing GEOS/Gateway/certification test suites.

## Acceptance criteria

- Existing runner behavior is unchanged when provenance is disabled.
- Successful model calls create content-addressed artifacts.
- Artifact references identify the model request/run.
- Provider failures do not create false successful completion artifacts.
- Artifact persistence failures fail closed when configured.
- Actual provider/model/failover metadata comes from `ChatResult`.
- Existing parser, repair, correction capture, gates, and certification behavior remain intact.
- No production/VPS files are changed until the local staging validation is complete.

## Promotion rule

Only after the local checkout passes the complete validation matrix should the patch be manually applied to the VPS repository and reviewed again there.
