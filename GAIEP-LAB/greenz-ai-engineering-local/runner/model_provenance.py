"""
greenz-ai-engineering

Module:        Runner / ModelProvenance
Purpose:       Optional GAIEP provenance wrapper for the runner's ModelCall seam. The Gateway
               remains the source of ChatResult truth; this module only persists successful
               completions through the existing corrections/provenance artifact path.
Owner:         Runner
Public:        No
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime

from corrections.capture import log_response
from runner.gateway_client import ChatResult

ModelCall = Callable[[str, str], ChatResult]

logger = logging.getLogger("geos.model_provenance")


def with_provenance(
    model_call: ModelCall,
    *,
    capability_name: str,
    prompt_id: str,
    prompt_version: str,
    fail_closed: bool = True,
) -> ModelCall:
    """Wrap a ModelCall with successful-completion provenance.

    The wrapper deliberately returns the original ChatResult object. Provider/model/context/
    failover metadata stay owned by ChatResult and no Gateway/provider behavior is rewritten.
    """

    def call(system: str, user: str) -> ChatResult:
        started = datetime.now(UTC)
        result = model_call(system, user)
        try:
            log_response(
                output_text=result.text,
                options=result.options,
                provider_name=result.provider_name,
                capability_name=capability_name,
                context_id=result.context_id,
                context_hash=result.context_hash,
                prompt_id=prompt_id,
                prompt_version=prompt_version,
                started_at=started,
                completed_at=datetime.now(UTC),
                input_token_estimate=len(system.split()) + len(user.split()),
                output_token_estimate=len(result.text.split()),
                execution_id=result.execution_id,
            )
        except Exception:
            if fail_closed:
                raise
            logger.exception("GAIEP model provenance persistence failed; continuing fail-open")
        return result

    return call
