"""Normalize model rollout responses into safe candidate file maps."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Mapping


class ArtifactError(ValueError):
    """Raised when a model response cannot safely become a candidate patch."""


@dataclass(frozen=True)
class CandidateArtifact:
    files: dict[str, str]


def _safe_path(path: str) -> str:
    if not path or path.startswith("/") or "\\" in path:
        raise ArtifactError(f"unsafe candidate path: {path!r}")
    normalized = PurePosixPath(path)
    if normalized.is_absolute() or ".." in normalized.parts or "." in normalized.parts:
        raise ArtifactError(f"unsafe candidate path: {path!r}")
    return str(normalized)


def normalize_artifact(value: Any) -> CandidateArtifact:
    """Accept only explicit file-map shapes; never infer executable content."""
    if isinstance(value, CandidateArtifact):
        return value
    if not isinstance(value, Mapping):
        raise ArtifactError("rollout artifact must be a mapping of paths to text")

    raw_files = value.get("files", value)
    if not isinstance(raw_files, Mapping) or not raw_files:
        raise ArtifactError("rollout artifact must contain a non-empty file map")

    files: dict[str, str] = {}
    for raw_path, content in raw_files.items():
        if not isinstance(raw_path, str) or not isinstance(content, str):
            raise ArtifactError("candidate paths and contents must be strings")
        path = _safe_path(raw_path)
        if path in files:
            raise ArtifactError(f"duplicate candidate path: {path}")
        files[path] = content
    return CandidateArtifact(files=files)
