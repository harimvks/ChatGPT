"""Context Engine Phase-1 contracts for the GAIEP lab snapshot."""

from runtime.context.contracts import (
    CompressionRecord,
    CompressionStrategy,
    ContextBudget,
    ContextItem,
    ContextItemKind,
    ContextManifest,
    ContextProfile,
    ContextValidationError,
    SelectionReason,
)

__all__ = [
    "CompressionRecord",
    "CompressionStrategy",
    "ContextBudget",
    "ContextItem",
    "ContextItemKind",
    "ContextManifest",
    "ContextProfile",
    "ContextValidationError",
    "SelectionReason",
]

from runtime.context.engine import ContextBuildRequest, DeterministicContextEngine

__all__ = [
    "ContextBuildRequest",
    "DeterministicContextEngine",
]
