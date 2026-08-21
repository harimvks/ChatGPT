import re
from collections.abc import Iterable

GENERIC_FORBIDDEN_SUBSTRINGS: frozenset[str] = frozenset(
    {"access_token", "api_key", "apikey", "password", "secret", "private_key"}
)
_VALUE_TEMPLATE = r"{term}\s*['\"]?\s*[:=]\s*['\"]?[^\s'\"]{{8,}}"


def scan_for_forbidden_content(payload: str, *, extra_forbidden: Iterable[str] = ()) -> None:
    for forbidden in (*GENERIC_FORBIDDEN_SUBSTRINGS, *extra_forbidden):
        if re.search(_VALUE_TEMPLATE.format(term=re.escape(forbidden)), payload, re.IGNORECASE):
            raise ValueError(f"forbidden credential-like value detected for {forbidden!r}")
