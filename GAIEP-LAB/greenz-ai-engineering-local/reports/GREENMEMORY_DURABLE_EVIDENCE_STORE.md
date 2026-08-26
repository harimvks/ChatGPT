# GreenMemory Durable Evidence Store

## Purpose

Provide a local-first, durable research evidence ledger for GAIEP trajectories. The store is deliberately separate from Runtime authorization and does not execute capabilities, change routing, or mutate model/certification state.

## V0 design

SQLite is the persistence substrate because it is local, transactional, zero-dependency beyond Python's standard library, and suitable for the expected early GAIEP research workload.

```text
Governed Runtime
      |
      v
RunProvenance + Evaluation + TrajectoryRecord
      |
      v
GreenMemoryStore
      |
      +-- durable SQLite ledger
      +-- content-addressed record ID
      +-- provenance-preserving JSON payload
      +-- indexed run/task/model/failure metadata
      +-- research queries
```

## Stored data boundary

The store persists trajectory metadata and provenance references. Candidate source is not stored by `GreenMemoryStore`; the trajectory contract already records artifact file names rather than file contents.

A record contains:

- run/task/model/scaffold identity;
- pass/failure/reward/check results;
- failure classification;
- endpoint/latency/usage metadata;
- `RunProvenance` including context, skills, authorization, observations, artifacts, and evidence references.

## Invariants

1. **Append-only API:** the store exposes insertion and read/query operations only; there are no update/delete operations.
2. **Content identity:** the canonical trajectory JSON is SHA-256 hashed and used as the record ID.
3. **Idempotent ingestion:** replaying the same trajectory does not create a duplicate record.
4. **Authorization separation:** GreenMemory is observational storage and cannot authorize or execute capabilities.
5. **No candidate source:** raw candidate source is not persisted through this store.
6. **Durable restart:** reopening the same SQLite file restores records and provenance.

## Query surface

V0 supports retrieval by:

- run ID;
- task ID;
- all failures;
- failure class;
- record ID.

Future research layers can add indexed retrieval by context hash, GreenSkill fingerprint, capability, model certification fingerprint, and evidence lineage without changing the Runtime contract.

## Next integration

The next implementation should call `GreenMemoryStore.append()` at the point where a validated `TrajectoryRecord` is finalized. The existing JSONL `TrajectoryStore` can remain as an experiment-stream/replay artifact; GreenMemory becomes the durable research ledger rather than replacing the execution trace format immediately.
