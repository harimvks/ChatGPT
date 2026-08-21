from __future__ import annotations

import pytest

from platform_vnext.compat.platform_adapter import (
    AdapterRequest,
    NotWiredPlatformAdapter,
)


def test_adapter_request_is_normalized() -> None:
    request = AdapterRequest(
        capability_tag="coding",
        prompt="implement X",
        context_id="ctx-1",
        context_hash="abc123",
        classification="INTERNAL",
    )

    assert request.capability_tag == "coding"
    assert request.context_id == "ctx-1"
    assert request.context_hash == "abc123"
    assert request.classification == "INTERNAL"


def test_unwired_adapter_fails_closed() -> None:
    adapter = NotWiredPlatformAdapter()
    request = AdapterRequest("coding", "x", "ctx", "hash", "INTERNAL")

    with pytest.raises(RuntimeError, match="not wired"):
        adapter.generate(request)
