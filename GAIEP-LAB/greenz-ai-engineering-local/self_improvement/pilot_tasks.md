# Pilot Task Selection

The first end-to-end pilot must use existing certification cases, not newly invented benchmark tasks.

## Selection policy

Select three implementation-oriented cases from the current certification corpus with:

1. deterministic task IDs;
2. reproducible acceptance criteria;
3. available validation commands or equivalent external checks;
4. distinct engineering behavior;
5. no production repository mutation.

Prefer one case each representing:

- isolated implementation;
- test-oriented implementation;
- integration/refactor behavior.

## Execution rule

The task selector must record the exact source case IDs and corpus version in the experiment manifest. If fewer than three suitable cases are available, stop and report the shortage rather than inventing replacements.

## Candidate models

Use logical names only:

- `small-python-coder`
- `qwen3.6-27b`

Resolve them through the existing environment-driven model binding and then through the GAIEP Gateway.

## Reproducibility

The same task set, scaffold definitions, validation commands, and scoring rules must be used for every model/scaffold arm.
