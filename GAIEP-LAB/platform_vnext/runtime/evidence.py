from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping


@dataclass(frozen=True)
class EvidenceEvent:
    run_id: str
    sequence: int
    event: str
    status: str
    occurred_at: datetime
    details: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if self.sequence < 0:
            raise ValueError("evidence sequence cannot be negative")
        if self.occurred_at.utcoffset() is None or self.occurred_at.utcoffset().total_seconds() != 0:
            raise ValueError("evidence timestamp must be UTC")


def append_event(
    events: tuple[EvidenceEvent, ...],
    *,
    run_id: str,
    event: str,
    status: str,
    details: Mapping[str, str] | None = None,
) -> tuple[EvidenceEvent, ...]:
    next_sequence = events[-1].sequence + 1 if events else 0
    normalized = tuple(sorted((details or {}).items()))
    item = EvidenceEvent(
        run_id=run_id,
        sequence=next_sequence,
        event=event,
        status=status,
        occurred_at=datetime.now(timezone.utc),
        details=normalized,
    )
    return (*events, item)
