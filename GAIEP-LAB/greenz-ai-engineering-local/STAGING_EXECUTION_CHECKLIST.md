# GAIEP Staging Execution Checklist

This is the final pre-VPS validation checklist for the staged ModelCall provenance integration.

## 1. Checkout

```bash
git clone https://github.com/harimvks/ChatGPT.git
git checkout gaiep-local-runtime-integration
```

The staging manifest pins the GreenZ runner source revision that the patch targets. Do not apply the patch to a different production revision without re-reviewing the diff.

## 2. Environment

Create an isolated Python environment and install the exact dependencies from the GreenZ runner checkout being tested.

Do not use the Mac's global Python environment.

## 3. Static validation

```bash
ruff check .
pyright
```

Both must pass before runtime tests are considered meaningful.

## 4. Unit tests

```bash
pytest -q GAIEP-LAB/greenz-ai-engineering-local/tests
```

Expected coverage includes:

- artifact store integrity;
- artifact reference accounting;
- lifecycle/GC policy;
- model artifact adapter;
- provenance ModelCall wrapper;
- provider failure propagation;
- artifact persistence failure propagation.

## 5. Integration smoke tests

Run two modes:

### Provenance disabled

Expected:

```text
ModelCall behavior = legacy behavior
Artifact writes     = none
Reference writes    = none
```

### Provenance enabled

Expected:

```text
ModelCall behavior     = unchanged
Model output            = content-addressed artifact
Model request           = reference owner
Provider/model metadata = preserved
Context identity        = preserved
```

## 6. Existing GreenZ validation

In the actual GreenZ checkout against which the patch will be applied:

```bash
pytest -q
ruff check .
pyright
```

Then run the existing GEOS/certification/sweep tests required by that repository.

## 7. Manual artifact inspection

After one successful provenance-enabled call:

```text
artifacts/
├── sha256/
│   └── <prefix>/<sha256>
└── index.db
```

Verify:

- stored bytes equal the model output;
- SHA-256 matches the path;
- SQLite contains the artifact;
- SQLite contains the `model_request` owner;
- reference count is correct;
- no duplicate artifact is created for identical content.

## 8. Failure tests

Verify:

```text
provider failure
    -> exception
    -> no successful completion artifact
```

and:

```text
artifact-store failure
    -> provenance failure when fail_closed=true
```

## 9. Diff gate

Before VPS integration:

```bash
git diff -- runner/run_task.py
```

The expected production change should be small and limited to:

- provenance import;
- feature-flag/config resolution;
- wrapping the existing `ModelCall` at its construction seam.

No Gateway/provider/parser/repair/gate logic should be changed.

## 10. VPS promotion

Only after all gates above pass:

1. Apply the reviewed patch to the VPS checkout.
2. Run the same static and test suite on VPS.
3. Start with provenance disabled.
4. Run a controlled smoke test.
5. Enable provenance explicitly.
6. Inspect artifacts and reference index.
7. Keep rollback to the previous commit immediately available.

## Status semantics

Never mark a stage `PASS` merely because source files were created. `PASS` requires an executable validation result from the relevant checkout/environment.
