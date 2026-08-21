# Real Platform Integration Harness

This directory contains the operator-side harness for proving the GAIEP VNext vertical slice against the real `greenz-ai-platform` checkout.

## Safety rules

- The upstream GreenZ repositories are not modified by this harness.
- The harness does not install, start, or configure a provider.
- The harness does not bypass certification.
- The harness does not create a second provider/model registry.
- The platform checkout should match the recorded baseline before the first compatibility run.

Recorded baseline:

```text
harimvks/greenz-ai-platform
3776af2704b5b2cc9f6629239c43d8fe3d48d241
```

## Local preflight

From the GAIEP-LAB checkout:

```bash
python GAIEP-LAB/integration/run_real_platform.py \
  --platform-root /path/to/greenz-ai-platform \
  --capability-name "<existing certified capability>" \
  --capability-version "<version>" \
  --capability-tag CODING \
  --template '<existing safe template>'
```

The first run only verifies that the pinned platform modules can be imported. This is deliberate.

## Live execution gate

A live run is allowed only after the deployment-specific composition root is identified. That root must provide the existing `CertifiedProviderRegistry` and `Gateway` construction path.

Do **not** create an ad-hoc registry in this harness. The objective is to prove that VNext can sit above the existing certified runtime, not to create a test-only routing universe.

## Required evidence from the first live run

Capture:

- upstream platform commit SHA;
- VNext commit SHA;
- context ID and context hash;
- capability name/version/tag;
- classification;
- certified provider/model selected;
- execution ID;
- failover chain, if any;
- latency;
- output validation result;
- final AgentRun status;
- evidence record.

A successful live run should demonstrate:

```text
real ContextBuilder
      ↓
real ContextManifest
      ↓
real certification
      ↓
real Gateway
      ↓
real certified provider/model
      ↓
real execution metadata
      ↓
VNext evidence
```
