# GreenMemory Durable Evidence Store

## Purpose

Provide a local-first, durable research evidence ledger for GAIEP trajectories. The store is deliberately separate from Runtime authorization and does not execute capabilities, change routing, or mutate model/certification state.

## Current design

SQLite is the persistence substrate because it is local, transactional, zero-dependency beyond Python's standard library, and suitable for the early GAIEP research workload.

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
      +-- structured lineage indexes
      +-- deterministic failure/provenance fingerprints
      +-- research queries
      +-- integrity verification
      +-- JSONL export
```

## Stored data boundary

The store persists trajectory metadata and provenance references. Candidate source is not stored by `GreenMemoryStore`; the trajectory contract records artifact file names rather than file contents.

A record contains:

- run/task/model/scaffold identity;
- pass/failure/reward/check results;
- failure classification;
- endpoint/latency/usage metadata;
- `RunProvenance` including context, skills, authorization, observations, artifacts, and evidence references;
- deterministic failure fingerprint for clustering repeated failure modes;
- deterministic provenance fingerprint for grouping equivalent governed execution contexts;
- context hash index;
- normalized skill fingerprint index;
- normalized requested/authorized capability index.

## Invariants

1. **Append-only API:** the store exposes insertion and read/query operations only; there are no update/delete operations.
2. **Content identity:** canonical trajectory JSON is SHA-256 hashed and used as the record ID.
3. **Idempotent ingestion:** replaying the same trajectory does not create a duplicate record.
4. **Authorization separation:** GreenMemory is observational storage and cannot authorize or execute capabilities.
5. **No candidate source:** raw candidate source is not persisted through this store.
6. **Durable restart:** reopening the same SQLite file restores records and provenance.
7. **Deterministic fingerprints:** failure clustering excludes task/model identity; provenance fingerprints represent governed context rather than mutable outcomes.
8. **Integrity verification:** `verify_integrity()` recomputes content hashes without mutating the ledger.
9. **Reference-preserving export:** `export_jsonl()` exports canonical trajectory records without adding source material.
10. **Migration safety:** schema initialization upgrades the V1 evidence table in place and backfills derived indexes from the canonical trajectory payload.

## Query surface

Current retrieval supports:

- record ID;
- run ID;
- task ID;
- context hash;
- GreenSkill fingerprint;
- capability ID, optionally authorized-only;
- all failures;
- failure class;
- exact failure fingerprint;
- similar failures for a supplied failed trajectory;
- aggregate memory summary by pass/fail, failure class and model.

These queries are deterministic and local. They intentionally do not introduce a vector database or semantic retrieval dependency.

## Experiment integration

`ExperimentRunner` accepts an optional `GreenMemoryStore`. When supplied, each validated `TrajectoryRecord` is appended after evaluation. This makes the evidence ledger available to controlled model/scaffold experiments without giving GreenMemory ownership of routing, authorization or promotion.

The existing JSONL `TrajectoryStore` remains an experiment-stream/replay artifact. GreenMemory is the durable research ledger; the two are not required to be collapsed yet.

## Failure-mining integration target

The current store provides the data boundary required for the next self-improvement layer:

```text
GreenMemory
   |
   +-- failure fingerprint
   +-- task history
   +-- model history
   +-- skill/context lineage
   +-- capability lineage
   |
   v
FailureMiner
   |
   +-- repeated failure clusters
   +-- targeted follow-up tasks
   +-- evidence-backed curriculum candidates
```

The next implementation should consume these deterministic queries from `FailureMiner` rather than querying SQLite directly from model/scaffold code.

## Explicit non-goals

- no vector/RAG dependency yet;
- no autonomous model training;
- no promotion/certification decisions;
- no runtime authorization through memory;
- no source-code corpus ingestion into this ledger;
- no cloud database requirement.
