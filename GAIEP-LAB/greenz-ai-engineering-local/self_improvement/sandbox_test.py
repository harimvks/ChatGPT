from pathlib import Path

import pytest

from self_improvement.sandbox import CandidateSandbox


def test_materialize_creates_only_candidate_files():
    workspace = CandidateSandbox().materialize({"src/example.py": "print('ok')\n"})
    try:
        assert (workspace.path / "src/example.py").read_text() == "print('ok')\n"
        assert workspace.files == ("src/example.py",)
    finally:
        workspace.cleanup()


def test_materialize_rejects_path_traversal():
    with pytest.raises(ValueError, match="unsafe candidate path"):
        CandidateSandbox().materialize({"../outside.py": "bad"})


def test_materialize_rejects_absolute_paths():
    with pytest.raises(ValueError, match="unsafe candidate path"):
        CandidateSandbox().materialize({str(Path('/tmp/outside.py')): "bad"})
