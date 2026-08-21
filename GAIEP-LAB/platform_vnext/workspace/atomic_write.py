"""Transactional filesystem primitive for governed coding skills.

The transaction snapshots original file bytes and restores them if the caller marks validation as
failed. Authorization is still delegated to WorkspaceMutationGuard before each mutation.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tempfile

from .mutation_guard import Mutation, MutationDenied, MutationRequest, WorkspaceMutationGuard
