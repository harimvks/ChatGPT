# Phase 1 — Platform Compatibility Adapter

## Objective

Connect GAIEP Runtime VNext to the existing `greenz-ai-platform` runtime without duplicating its Gateway, provider registry, certification gate, context primitives, or provider implementations.

## Current state

The lab contains a deliberately fail-closed adapter boundary. It accepts a normalized VNext request and returns a normalized response shape, but it raises until the real composition root is wired.

## Required upstream mapping

```text
VNext AdapterRequest
    |
    +--> capability_tag --------> Gateway capability tag
    +--> prompt ----------------> provider generate prompt
    +--> context_id ------------> request/evidence correlation
    +--> context_hash ----------> context provenance
    +--> classification --------> cloud-eligibility policy
                                      |
                                      v
                              certification gate
                                      |
                                      v
                                  Gateway
                                      |
                                      v
                                AIProvider
                                      |
                                      v
                              AdapterResponse
```

## Non-goals

- Do not create a second provider registry.
- Do not create a second certification ledger.
- Do not create a VNext-specific model-selection algorithm before compatibility is proven.
- Do not bypass classification or certification.
- Do not silently fall back to a local mock provider.

## Acceptance gates

1. One real capability tag can traverse the adapter into the existing Gateway.
2. The resolved provider/model in `AdapterResponse` is the provider/model actually used.
3. Classification restrictions remain enforced by the upstream policy path.
4. Certification remains enforced by the upstream certification composition root.
5. A missing eligible provider fails closed.
6. Context ID/hash survive the request-to-evidence boundary.
7. Existing upstream tests remain green.
8. VNext contract tests remain green.

## Next implementation step

Build an integration adapter against the real platform composition root. The adapter should depend on interfaces, not on GreenZAlgo V4 modules, so VNext remains independently testable.
