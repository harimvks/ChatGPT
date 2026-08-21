"""Gate C smoke runner for a real GreenZ Gateway execution.

This is intentionally read-only: it invokes the existing Gateway and prints normalized evidence;
it never writes to a GreenZ repository and never calls a provider directly.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from uuid import uuid4

from platform_vnext.compat.platform_adapter import AdapterRequest
from platform_vnext.context.manifest import AIRequestContext, ContextManifest
from platform_vnext.runtime.contracts import AgentRun, ModelPolicy, RunStatus, TaskPolicy, WorkspaceScope
from platform_vnext.skills.contracts import GreenSkill, SkillStatus, SkillStep
from platform_vnext.runtime.engine import ContextFactory, RuntimeVNext
from platform_vnext.integration import missing  # type: ignore[import-not-found]
