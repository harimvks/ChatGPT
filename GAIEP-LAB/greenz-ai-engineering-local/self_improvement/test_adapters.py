from pathlib import Path
import sys

from self_improvement.corpus_adapter import certification_to_task, parse_certification
from self_improvement.gate_adapter import ExternalValidationGate, GateCommand


CERTIFICATION = """certification_id: CERT-ENG-CM112-Q25C14B-CORPUSV3-R1
capability: engineering
model_name: qwen2.5-coder:14b
configuration:
  thinking: false
  num_ctx: 32768
  temperature: 0.1
benchmark_id: ENG-CM-112
corpus_version: 3
result: FAIL
metrics:
  blocks: '2'
  functional: 'false'
  ruff: '4'
  pyright: '0'
  latency_s: '46.7'
  backstop: '9'
  detail: generated pytest did not pass; ruff 4 > 2
issued_at: '2026-08-06T10:44:29.979785+00:00'
runner_version: 2
"""


def test_parse_certification_extracts_stable_evidence():
    record = parse_certification(CERTIFICATION)
    assert record.certification_id.endswith("CORPUSV3-R1")
    assert record.model_name == "qwen2.5-coder:14b"
    assert record.result == "FAIL"
    assert record.functional is False
    assert record.ruff == 4
    assert record.pyright == 0
    assert record.latency_s == 46.7
    assert record.detail.startswith("generated pytest")


def test_certification_becomes_research_task():
    task = certification_to_task(parse_certification(CERTIFICATION))
    assert task.source == "certification_corpus"
    assert task.task_type == "debug"
    assert "ENG-CM-112" in task.title
    assert "CERT-ENG-CM112-Q25C14B-CORPUSV3-R1" in task.constraints
    assert task.acceptance == ("pytest", "ruff", "pyright")


def test_external_gate_executes_commands_without_changing_workspace(tmp_path: Path):
    marker = tmp_path / "marker.txt"
    marker.write_text("source", encoding="utf-8")
    gate = ExternalValidationGate(
        [GateCommand("pytest", (sys.executable, "-c", "print('ok')"))],
        timeout_s=5,
    )
    results = gate.run(tmp_path)
    assert results[0].passed
    assert results[0].return_code == 0
    assert "ok" in results[0].stdout
    assert marker.read_text(encoding="utf-8") == "source"
    assert ExternalValidationGate.checks(results) == {"pytest": True}
