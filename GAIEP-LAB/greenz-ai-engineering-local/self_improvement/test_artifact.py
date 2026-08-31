import pytest

from self_improvement.artifact import ArtifactError, normalize_artifact


def test_normalize_explicit_file_map():
    artifact = normalize_artifact({"files": {"src/example.py": "x = 1\n"}})
    assert artifact.files == {"src/example.py": "x = 1\n"}


@pytest.mark.parametrize("path", ["/tmp/x.py", "../x.py", "src/../x.py", "src\\x.py"])
def test_rejects_unsafe_paths(path):
    with pytest.raises(ArtifactError):
        normalize_artifact({"files": {path: "x"}})


def test_rejects_non_explicit_artifact():
    with pytest.raises(ArtifactError):
        normalize_artifact("```python\nx = 1\n```")
