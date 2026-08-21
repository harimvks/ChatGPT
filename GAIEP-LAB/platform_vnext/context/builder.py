import hashlib
import json
from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping
from datetime import datetime

from .manifest import AIRequestContext, ContextManifest
from .redaction import scan_for_forbidden_content


class ContextBuilderBase(ABC):
    SCHEMA_VERSION: str
    BUILDER_NAME: str
    BUILDER_VERSION: str
    CAPABILITY_NAME: str
    CAPABILITY_VERSION: str
    CLASSIFICATION: str
    MAX_PAYLOAD_BYTES: int

    @abstractmethod
    def payload_fields(self) -> Mapping[str, object]:
        ...

    def extra_forbidden(self) -> Iterable[str]:
        return ()

    def build(self, *, context_id: str, target_type: str, target_ref: str, created_at: datetime) -> ContextManifest:
        payload = json.dumps(dict(self.payload_fields()), sort_keys=True)
        payload_bytes = payload.encode("utf-8")
        if len(payload_bytes) > self.MAX_PAYLOAD_BYTES:
            raise ValueError(
                f"{self.BUILDER_NAME}:{self.BUILDER_VERSION} context payload exceeds budget "
                f"({len(payload_bytes)} > {self.MAX_PAYLOAD_BYTES} bytes)"
            )
        scan_for_forbidden_content(payload, extra_forbidden=self.extra_forbidden())
        context = AIRequestContext(
            context_id=context_id,
            schema_version=self.SCHEMA_VERSION,
            builder_name=self.BUILDER_NAME,
            builder_version=self.BUILDER_VERSION,
            capability_name=self.CAPABILITY_NAME,
            capability_version=self.CAPABILITY_VERSION,
            target_type=target_type,
            target_ref=target_ref,
            created_at=created_at,
            content_hash=hashlib.sha256(payload_bytes).hexdigest(),
            payload=payload,
        )
        return ContextManifest(context=context, classification=self.CLASSIFICATION, redaction_checked=True)
