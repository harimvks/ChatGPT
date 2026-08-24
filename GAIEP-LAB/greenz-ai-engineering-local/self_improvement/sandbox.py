"""Research-only workspace materialization for candidate artifacts.

The sandbox accepts an explicit file mapping and creates a temporary workspace.
It rejects absolute paths and traversal outside the workspace. It never writes
back to the source repository.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tempfile
from typing import Mapping


@dataclass(frozen=True)
class SandboxWorkspace:
    path: Path
    files: tuple[str, ...]

    def cleanup(self) -> None:
        import shutil
        shutil.rmtree(self.path, ignore_errors=True)


class CandidateSandbox:
    """Materialize candidate files into an isolated temporary directory."""

    def __init__(self, *, prefix: str = "gaiep-candidate-") -> None:
        self._prefix = prefix

    def materialize(self, files: Mapping[str, str]) -> SandboxWorkspace:
        if not files:
            raise ValueError("candidate artifact must contain at least one file")

        root = Path(tempfile.mkdtemp(prefix=self._prefix))
        written: list[str] = []
        try:
            for relative_name, content in files.items():
                relative = Path(relative_name)
                if relative.is_absolute() or ".." in relative.parts:
                    raise ValueError(f"unsafe candidate path: {relative_name}")
                target = (root / relative).resolve()
                if root.resolve() not in target.parents and target != root.resolve():
                    raise ValueError(f"candidate path escapes workspace: {relative_name}")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
                written.append(relative.as_posix())
        except Exception:
            import shutil
            shutil.rmtree(root, ignore_errors=True)
            raise
        return SandboxWorkspace(path=root, files=tuple(written))
