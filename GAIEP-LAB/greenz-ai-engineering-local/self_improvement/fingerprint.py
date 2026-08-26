"""Deterministic fingerprints for durable GAIEP research evidence."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .trajectory import TrajectoryRecord


def _digest(payload: Any) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def failure_fingerprint(record: TrajectoryRecord) -> str | None:
    """Return a generalized fingerprint for an observed failure.

    Task identity and model identity are intentionally excluded so repeated
    failure modes can be clustered across tasks and models.
    """
    if record.passed or not record.failure_class:
        return None
    failed_checks = tuple(name for name, passed in record.checks if not passed)
    return _digest(
        {
            "failure_class": record.failure_class,
            "failed_checks": failed_checks,
            "artifact_file_extensions": tuple(
                sorted({name.rsplit(".", 1)[-1] for name in record.artifact_files if "." in name})
            ),
        }
    )


def provenance_fingerprint(record: TrajectoryRecord) -> str:
    """Fingerprint the governed execution context, excluding mutable outcomes."""
    provenance = record.provenance
    if provenance is None:
        return _digest({"provenance": None})
    context = provenance.context
    return _digest(
        {
            "context_hash": context.context_hash if context else None,
            "skill_fingerprints": provenance.skill_fingerprints,
            "capability_ids_requested": provenance.capability_ids_requested,
            "capability_ids_authorized": provenance.capability_ids_authorized,
            "gateway_model": provenance.gateway_model,
            "gateway_endpoint_model": provenance.gateway_endpoint_model,
        }
    )
