import re
from collections.abc import Iterable

GENERIC_FORBIDDEN_SUBSTRINGS: frozenset[str] = frozenset(
    {"access_token", "api_key", "apikey", "password", "secret", "private_key"}
)

_VALUE_TEMPLATE = r"{term}\s*['\"]?\s*[:=]\s*['\"]?[^\s'\"]{{8,}}"


def scan_for_forbidden_content(payload: str, *, extra_forbidden: Iterable[str] = ()) -> None:
    """Fail closed when a forbidden term is followed by an assigned-looking value."""
    for forbidden in (*GENERIC_FORBIDDEN_SUBSTRINGS, *extra_forbidden):
        pattern = _VALUE_TEMPLATE.format(term=re.escape(forbidden))
        if re.search(pattern, payload, re.IGNORECASE):
            raise ValueError(
                f"content must not contain {forbidden!r} followed by what looks like a real value"
            )
