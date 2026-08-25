"""Reference-only provenance bridge for GAIEP research trajectories."""

from __future__ import annotations

import json
from dataclasses import dataclass


def _require_non_empty(label: str, value: str) -> None:
    if not value.strip():
        raise ValueError(f"{label} cannot be empty")


def _dedupe_sorted(values: tuple[str, ...], *, label: str) -> tuple[str, ...]:
    cleaned = tuple(str(value).strip() for value in values if str(value).strip())
    if len(set(cleaned)) != len(cleaned):
        raise ValueError(f"{label} cannot contain duplicates")
    return tuple(sorted(cleaned))


@dataclass(frozen=True)
class ContextProvenance:
    manifest_id: str
    context_hash: str

    def __post_init__(self) -> None:
        _require_non_empty("ContextProvenance.manifest_id", self.manifest_id)
        _require_non_empty("ContextProvenance.context_hash", self.context_hash)

    def to_dict(self) -> dict[str, str]:
        return {"manifest_id": self.manifest_id, "context_hash": self.context_hash}

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> ContextProvenance:
        return cls(
            manifest_id=str(payload.get("manifest_id", "")),
            context_hash=str(payload.get("context_hash", "")),
        )


@dataclass(frozen=True)
class AuthorizationProvenance:
    decision_ref: str
    decision: str
    reason: str
    capability_id: str
    capability_version: str | None = None
    policy_version: str | None = None

    def __post_init__(self) -> None:
        _require_non_empty("AuthorizationProvenance.decision_ref", self.decision_ref)
        _require_non_empty("AuthorizationProvenance.decision", self.decision)
        _require_non_empty("AuthorizationProvenance.reason", self.reason)
        _require_non_empty("AuthorizationProvenance.capability_id", self.capability_id)
        if self.capability_version is not None:
            _require_non_empty(
                "AuthorizationProvenance.capability_version", self.capability_version
            )
        if self.policy_version is not None:
            _require_non_empty("AuthorizationProvenance.policy_version", self.policy_version)

    def to_dict(self) -> dict[str, str | None]:
        return {
            "capability_id": self.capability_id,
            "capability_version": self.capability_version,
            "decision": self.decision,
            "decision_ref": self.decision_ref,
            "policy_version": self.policy_version,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> AuthorizationProvenance:
        capability_version = payload.get("capability_version")
        policy_version = payload.get("policy_version")
        return cls(
            decision_ref=str(payload.get("decision_ref", "")),
            decision=str(payload.get("decision", "")),
            reason=str(payload.get("reason", "")),
            capability_id=str(payload.get("capability_id", "")),
            capability_version=str(capability_version) if capability_version is not None else None,
            policy_version=str(policy_version) if policy_version is not None else None,
        )


@dataclass(frozen=True)
class RunProvenance:
    run_id: str
    context: ContextProvenance | None = None
    skill_fingerprints: tuple[str, ...] = ()
    authorization: tuple[AuthorizationProvenance, ...] = ()
    observation_refs: tuple[str, ...] = ()
    artifact_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    gateway_model: str | None = None
    gateway_endpoint_model: str | None = None
    capability_ids_requested: tuple[str, ...] = ()
    capability_ids_authorized: tuple[str, ...] = ()
    policy_decision_refs: tuple[str, ...] = ()
    started_at_ref: str | None = None
    finished_at_ref: str | None = None

    def __post_init__(self) -> None:
        _require_non_empty("RunProvenance.run_id", self.run_id)
        for label, value in (
            ("RunProvenance.gateway_model", self.gateway_model),
            ("RunProvenance.gateway_endpoint_model", self.gateway_endpoint_model),
            ("RunProvenance.started_at_ref", self.started_at_ref),
            ("RunProvenance.finished_at_ref", self.finished_at_ref),
        ):
            if value is not None:
                _require_non_empty(label, value)
        object.__setattr__(
            self,
            "skill_fingerprints",
            _dedupe_sorted(self.skill_fingerprints, label="skill_fingerprints"),
        )
        object.__setattr__(
            self,
            "observation_refs",
            _dedupe_sorted(self.observation_refs, label="observation_refs"),
        )
        object.__setattr__(
            self, "artifact_refs", _dedupe_sorted(self.artifact_refs, label="artifact_refs")
        )
        object.__setattr__(
            self, "evidence_refs", _dedupe_sorted(self.evidence_refs, label="evidence_refs")
        )
        object.__setattr__(
            self,
            "capability_ids_requested",
            _dedupe_sorted(self.capability_ids_requested, label="capability_ids_requested"),
        )
        object.__setattr__(
            self,
            "capability_ids_authorized",
            _dedupe_sorted(self.capability_ids_authorized, label="capability_ids_authorized"),
        )
        object.__setattr__(
            self,
            "policy_decision_refs",
            _dedupe_sorted(self.policy_decision_refs, label="policy_decision_refs"),
        )
        authorized = set(self.capability_ids_authorized)
        requested = set(self.capability_ids_requested)
        if not authorized.issubset(requested):
            raise ValueError("authorized capabilities must be requested first")
        denied = tuple(item for item in self.authorization if item.decision.upper() != "ALLOW")
        if denied and self.observation_refs:
            raise ValueError("denied authorization cannot be recorded as executed observation")

    def to_dict(self) -> dict[str, object]:
        return {
            "artifact_refs": self.artifact_refs,
            "authorization": tuple(item.to_dict() for item in self.authorization),
            "capability_ids_authorized": self.capability_ids_authorized,
            "capability_ids_requested": self.capability_ids_requested,
            "context": self.context.to_dict() if self.context else None,
            "evidence_refs": self.evidence_refs,
            "finished_at_ref": self.finished_at_ref,
            "gateway_endpoint_model": self.gateway_endpoint_model,
            "gateway_model": self.gateway_model,
            "observation_refs": self.observation_refs,
            "policy_decision_refs": self.policy_decision_refs,
            "run_id": self.run_id,
            "skill_fingerprints": self.skill_fingerprints,
            "started_at_ref": self.started_at_ref,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> RunProvenance:
        context_payload = payload.get("context")
        authorization_payload = payload.get("authorization", ())
        return cls(
            run_id=str(payload.get("run_id", "")),
            context=(
                ContextProvenance.from_dict(context_payload)
                if isinstance(context_payload, dict)
                else None
            ),
            skill_fingerprints=tuple(str(item) for item in payload.get("skill_fingerprints", ())),
            authorization=tuple(
                AuthorizationProvenance.from_dict(item)
                for item in authorization_payload
                if isinstance(item, dict)
            ),
            observation_refs=tuple(str(item) for item in payload.get("observation_refs", ())),
            artifact_refs=tuple(str(item) for item in payload.get("artifact_refs", ())),
            evidence_refs=tuple(str(item) for item in payload.get("evidence_refs", ())),
            gateway_model=(
                str(payload["gateway_model"]) if payload.get("gateway_model") is not None else None
            ),
            gateway_endpoint_model=(
                str(payload["gateway_endpoint_model"])
                if payload.get("gateway_endpoint_model") is not None
                else None
            ),
            capability_ids_requested=tuple(
                str(item) for item in payload.get("capability_ids_requested", ())
            ),
            capability_ids_authorized=tuple(
                str(item) for item in payload.get("capability_ids_authorized", ())
            ),
            policy_decision_refs=tuple(
                str(item) for item in payload.get("policy_decision_refs", ())
            ),
            started_at_ref=(
                str(payload["started_at_ref"])
                if payload.get("started_at_ref") is not None
                else None
            ),
            finished_at_ref=(
                str(payload["finished_at_ref"])
                if payload.get("finished_at_ref") is not None
                else None
            ),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True)
