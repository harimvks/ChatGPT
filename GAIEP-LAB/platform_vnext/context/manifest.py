from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class AIRequestContext:
    context_id: str
    schema_version: str
    builder_name: str
    builder_version: str
    capability_name: str
    capability_version: str
    target_type: str
    target_ref: str
    created_at: datetime
    content_hash: str
    payload: str

    def __post_init__(self) -> None:
        for field_name in (
            "context_id", "schema_version", "builder_name", "builder_version",
            "capability_name", "capability_version", "target_type", "target_ref",
            "content_hash", "payload",
        ):
            if not getattr(self, field_name).strip():
                raise ValueError(f"AIRequestContext.{field_name} cannot be empty")
        if self.created_at.utcoffset() != timedelta(0):
            raise ValueError("AIRequestContext.created_at must be timezone-aware UTC")


@dataclass(frozen=True)
class ContextManifest:
    context: AIRequestContext
    classification: str
    redaction_checked: bool

    def __post_init__(self) -> None:
        if not self.classification.strip():
            raise ValueError("ContextManifest.classification cannot be empty")


@runtime_checkable
class PromptBuilder(Protocol):
    def render(self, manifest: ContextManifest, template: str) -> str:
        ...
