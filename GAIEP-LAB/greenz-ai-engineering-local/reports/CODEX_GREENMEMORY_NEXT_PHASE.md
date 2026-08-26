# Codex Handoff — GreenMemory Next Phase

## Objective

Complete the GreenMemory durable-evidence work and integrate it into the real GAIEP governed execution/self-improvement path without creating a second execution or authorization authority.

## Current branch

`codex/gaiep-greenmemory-evidence-store`

Base integration point:

`38645e7e41b32c12f4d1441d40806e752d64f9e4`

The branch currently contains the V0 GreenMemory ledger, structured retrieval, deterministic fingerprints, ExperimentRunner persistence, and evidence-backed FailureMiner clustering.

## Already implemented

### Durable storage

- `self_improvement/evidence_store.py`
- local SQLite storage using stdlib `sqlite3`
- append-only public API
- SHA-256 content-addressed record IDs
- idempotent ingestion
- WAL/NORMAL SQLite operational settings
- schema version metadata
- V1 -> V2 column migration/backfill
- normalized skill and capability lineage tables
- context/failure/provenance indexes

### Structured retrieval

`GreenMemoryStore` now supports:

- `get(record_id)`
- `find_by_run(run_id)`
- `find_by_task(task_id)`
- `find_by_context_hash(context_hash)`
- `find_by_skill(fingerprint)`
- `find_by_capability(capability_id, authorized_only=False)`
- `find_failures(failure_class=None)`
- `find_by_failure_fingerprint(fingerprint)`
- `find_similar_failures(record, limit=20)`
- `summary()`
- `verify_integrity()`
- `export_jsonl(path)`

### Deterministic fingerprints

`self_improvement/fingerprint.py` provides:

- `failure_fingerprint(record)`
- `provenance_fingerprint(record)`

Failure fingerprints deliberately exclude task/model identity so recurring failure modes can be clustered across tasks and models.

### Failure Miner

`FailureMiner.cluster_trajectories()` now consumes `TrajectoryRecord` evidence and returns deterministic `EvidenceFailureCluster` objects containing:

- failure class
- fingerprint
- count
- task IDs
- model names

### Experiment integration

`ExperimentRunner` accepts an optional `GreenMemoryStore` and persists each validated trajectory after evaluation.

### Tests/docs

GreenMemory, fingerprint, ExperimentRunner persistence, and FailureMiner evidence-clustering tests are registered in `pyproject.toml`.

## Required next work

### P0 — Validate everything locally

Run from:

`GAIEP-LAB/greenz-ai-engineering-local`

```bash
uv run pytest
uv run ruff check .
uv run pyright
uv build
python -m compileall runtime self_improvement tests
```

If any failures are found, fix them before proceeding. Do not weaken tests or lint configuration.

Also run:

```bash
git diff --check
git status --short
```

The final working tree must be clean.

### P0 — Add migration regression tests

Create a test that constructs a V1 SQLite database using the old schema, inserts a valid V1 trajectory payload, opens it with the V2 `GreenMemoryStore`, and proves:

- the record remains readable;
- the content hash is unchanged;
- derived failure/provenance/context indexes are backfilled;
- skill/capability lineage rows are recreated;
- `verify_integrity()` passes.

Do not require an external migration framework.

### P0 — Add tamper-detection test

Create a test that directly modifies a stored `trajectory_json` value in a test-only SQLite database and proves:

```text
verify_integrity().passed == False
```

and identifies the affected record ID.

Do not expose a mutation API in `GreenMemoryStore`; direct SQL is only for the test fixture.

### P0 — Add denial/evidence invariant tests

Prove that a denied authorization trajectory can be stored and queried, but:

- it has no runtime observation refs;
- it is never treated as an executed capability;
- `find_by_capability(..., authorized_only=True)` excludes the denied capability;
- `find_failures()` and provenance retrieval preserve the denial record.

### P0 — Real runtime ingestion

Find the real GAIEP governed execution finalization point. Do NOT create a parallel execution path.

At the point where a validated `TrajectoryRecord` is finalized:

```text
Context
 → Skills
 → Capability Request
 → Authorization
 → MCP Gateway
 → Runtime
 → Observation
 → Evaluation
 → TrajectoryRecord
 → GreenMemoryStore.append()
```

Use dependency injection so production/runtime code can supply the store. Do not hard-code a filesystem path inside Runtime or Gateway.

### P1 — Repository abstraction

Introduce a small protocol/interface only if necessary, e.g.:

```python
class EvidenceRepository(Protocol):
    def append(self, record: TrajectoryRecord) -> str: ...
```

`GreenMemoryStore` should implement it. Keep SQLite-specific operations out of agent/runtime code.

Do not replace `TrajectoryStore` yet. Keep JSONL as the replay/stream representation.

### P1 — Evidence-backed FailureMiner API

Add a method such as:

```python
mine_store(store: GreenMemoryStore, *, limit: int = 20)
```

or an equivalent dependency-injected design.

It should:

1. retrieve failed trajectories from GreenMemory;
2. cluster by deterministic failure fingerprint;
3. rank clusters by recurrence;
4. expose representative trajectories;
5. produce controlled follow-up research-task candidates only through `TaskFactory`.

FailureMiner must remain research-only. It must not execute, authorize, route, certify, or promote.

### P1 — Evidence lineage API

Add read-only lineage helpers that make it easy to answer:

- Which runs used this context hash?
- Which skills were involved in failures of this class?
- Which capabilities were requested vs authorized?
- Which models/scaffolds exhibit this failure fingerprint?
- Which observations/artifacts/evidence refs belong to this run?

Prefer deterministic SQL queries over semantic search.

### P1 — Atomicity/idempotency hardening

Ensure that one `append()` operation cannot leave an orphaned `evidence_records` row without its normalized skill/capability lineage rows.

The operation must remain transactional.

Add a test that retries the same append and proves:

- exactly one evidence record exists;
- no duplicate normalized lineage rows exist;
- the returned content ID is stable.

### P1 — Concurrency test

Use two SQLite connections/threads in a test fixture to append the same record concurrently. Prove that the final ledger contains one content-addressed record and no corrupted lineage.

Keep the implementation local-first and stdlib-only.

### P1 — Real execution pilot

Create one end-to-end pilot that uses the real GAIEP governed path and produces a durable GreenMemory record containing:

- run ID;
- context manifest/hash;
- GreenSkill fingerprints;
- requested capability;
- authorization decision;
- capability version;
- runtime observation ref when execution occurs;
- artifact/evidence refs;
- model/endpoint identity;
- evaluation result;
- failure fingerprint when failed.

The pilot must also demonstrate the denial path.

### P2 — Research retrieval API

Add a small, stable read-only query facade if repeated callers otherwise depend on SQL details. It should support:

```text
by_run
by_task
by_context
by_skill
by_capability
failures
failure_fingerprint
similar_failures
summary
integrity
```

Do not add vector DB/RAG yet.

### P2 — Optional FTS

Only if actual research queries require text search, evaluate SQLite FTS5 for bounded metadata/notes. Do not index candidate source or hidden model reasoning. Do not add a new dependency solely for search.

## Architectural invariants

These are non-negotiable:

1. GreenMemory is **not** an execution authority.
2. GreenMemory is **not** an authorization authority.
3. GreenMemory cannot bypass Capability Registry/Gateway policy.
4. A denied authorization cannot become a runtime observation.
5. Candidate source must not be persisted by the evidence ledger unless a future explicit artifact policy permits it.
6. Provenance must survive rollout → evaluation → trajectory → durable storage unchanged.
7. Evidence IDs must be deterministic/content-addressed where appropriate.
8. No cloud database requirement.
9. No vector/RAG dependency at this stage.
10. No autonomous model-weight mutation.
11. No automatic certification or promotion.
12. Self-improvement remains downstream/observational; it cannot execute arbitrary capabilities through memory.

## Final validation and reporting

After implementation:

```bash
uv run pytest
uv run ruff check .
uv run pyright
uv build
git diff --check
git status --short
```

Then create:

`reports/GAIEP_GREENMEMORY_IMPLEMENTATION_REPORT.md`

The report must include:

- implementation summary;
- schema version and migration behavior;
- query/index design;
- fingerprint design;
- runtime integration point;
- failure-mining integration;
- security/invariant tests;
- exact validation results;
- remaining limitations;
- recommended next milestone.

Commit the completed work in focused commits and push the branch.

## Next milestone after this handoff

Once the GreenMemory work passes all validation, stop expanding storage features and move to:

**GAIEP V0.1 real end-to-end governed execution + durable evidence pilot.**

The objective is to produce real evidence, not another layer of abstractions.
