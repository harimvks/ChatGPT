# `run_task.py` Call-Site Patch Plan

## Target

Current GreenZ AI Engineering `runner/run_task.py` revision:

`093cf730fb343c1f66e1cc281cc6e864425b2440`

The file already defines the intended dependency seam:

```python
ModelCall = Callable[[str, str], ChatResult]
```

and `_default_model_call()` returns a Gateway-backed `ModelCall`. The runner itself consumes the injected callable, so provenance can be added without changing Gateway/provider behavior.

## Exact intended change

At the point where the CLI constructs the default model callable:

```text
_default_model_call(...)
        |
        v
     ModelCall
        |
        v
maybe_wrap_provenance(...)
        |
        v
    run_task(...)
```

The wrapper is enabled only when the provenance feature flag is explicitly enabled.

## Pseudocode

```python
model_call = _default_model_call(
    config,
    repo_root=repo_root,
    capability_tag=capability_tag,
    registry_path=registry_path,
    certifications_dir=certifications_dir,
    timeout_seconds=timeout_seconds,
    prompt_id=prompt_id,
    prompt_version=prompt_version,
)

if provenance_enabled:
    model_call = with_provenance(
        model_call,
        repo_root=repo_root,
        run_id=run_id,
    )
```

The exact argument names must be taken from the complete current CLI implementation before applying the patch; do not infer them from this pseudocode.

## Invariants

- `_default_model_call()` remains unchanged.
- `Gateway`, `ChatResult`, failover, routing, parser, repair, gates, and corrections capture remain unchanged.
- The wrapper returns the same `ChatResult` object it receives.
- Provider failures propagate unchanged.
- Artifact persistence failures propagate when `fail_closed=true`.
- Provenance disabled means byte-for-byte equivalent runner behavior apart from wrapper construction being skipped.
- No VPS/production change is authorized by this staging artifact.

## Validation

After applying the surgical change in a real checkout:

1. Run provenance adapter tests.
2. Run runner tests.
3. Run Gateway/certification tests.
4. Run `ruff`.
5. Run `pyright`.
6. Review `git diff -- runner/run_task.py`.
7. Confirm only the intended call-site and required imports/configuration changed.
8. Execute one provenance-disabled smoke test.
9. Execute one provenance-enabled smoke test.
10. Inspect artifact and reference-index records.

## Why a patch plan rather than a reconstructed file

`runner/run_task.py` contains accumulated production corrections and must not be replaced from a partial API response. The safe operation is a minimal textual edit against the exact blob/checkout, followed by a diff review.
