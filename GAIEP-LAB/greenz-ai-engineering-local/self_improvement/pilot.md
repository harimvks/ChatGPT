# GAIEP Small Python Model Pilot

## Purpose

Measure whether a cheaper Python-specialist model can safely take a subset of engineering work away from the current Qwen3.6-27B baseline when both are evaluated with identical tasks and external validation.

## Arms

| Logical model | Scaffold A | Scaffold B |
|---|---|---|
| small-python-coder | inspect-plan-implement-test | inspect-implement-test |
| qwen3.6-27b | inspect-plan-implement-test | inspect-implement-test |

The logical model names are resolved by environment configuration. The experiment must not hard-code a provider or bypass the GAIEP Gateway.

## Initial sample

Start with 3 existing certification tasks that represent different engineering behavior. Expand to 10–20 only after the end-to-end path is verified.

## Primary metrics

- pytest / functional pass
- pyright pass
- ruff pass
- composite reward
- latency
- failure class
- artifact validity
- scaffold effect

## Safety gates

- research branch only
- isolated candidate workspace
- no production repository writes
- no automatic merge
- no routing changes
- no certification bypass
- no model-weight updates

## Success criterion

Do not declare the smaller model useful from one successful task. A candidate becomes eligible for a larger sweep only after reproducible end-to-end execution and evidence collection. Any production routing decision remains a separate certification/governance decision.
