import pytest

from self_improvement.experiment_config import load_model_binding


def test_load_model_binding(monkeypatch):
    monkeypatch.setenv("GAIEP_MODEL_SMALL_PYTHON_CODER", "qwen3.5-4b-python-coder")
    binding = load_model_binding("small-python-coder")
    assert binding.logical_name == "small-python-coder"
    assert binding.endpoint_model == "qwen3.5-4b-python-coder"


def test_missing_binding_is_explicit(monkeypatch):
    monkeypatch.delenv("GAIEP_MODEL_SMALL_PYTHON_CODER", raising=False)
    with pytest.raises(RuntimeError, match="missing experiment model binding"):
        load_model_binding("small-python-coder")
