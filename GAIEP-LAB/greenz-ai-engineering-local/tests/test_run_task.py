"""
greenz-ai-engineering

Module:        Tests / RunTask
Purpose:       Integration-level regression tests for runner/run_task.py -- the orchestrator that
               wires context.py + allowlist.py + overwrite_guard.py + parse.py + gate.py together
               and is where allowlist/overwrite-guard decisions become real filesystem writes
               (_write_files). Before this file, run_task.py had zero test coverage despite
               ModelCall being deliberately designed as an injected callable ("so tests can run
               without a live Ollama") -- this is that seam finally being used.

               run_gate() itself shells out to real `uv run ruff/pyright/pytest` subprocesses,
               which is gate.py's own concern (and expensive/environment-dependent) -- not
               something this file re-tests. These tests monkeypatch `runner.run_task.run_gate`
               with a controllable fake that still returns the REAL GateResult/StepResult
               dataclasses (never a Mock/stub object), so run_task's own branching on
               `gate.passed` / `gate.failed_step` / `gate.failure_digest()` is exercised for real.
               What's under test here is run_task's wiring -- allowlist filtering, overwrite-guard
               refusal, actual disk writes, the bounded repair loop, and manifest content -- not
               gate.py's internals (covered separately) or the Gateway call itself (covered by
               test_gateway_routing.py).
Owner:         Tests
Public:        No
"""

from __future__ import annotations

import json
from datetime import UTC
from decimal import Decimal
from pathlib import Path

import pytest
from providers.provider import AIModelOptions

from runner.config import GeosConfig
from runner.gate import GateResult, StepResult
from runner.gateway_client import ChatResult
from runner.run_task import LaneValidationError, _build_repair_note, run_task

_OPTS = AIModelOptions(
    provider="ollama",
    model="qwen3.6:27b",
    model_version="27b",
    quantization="Q4_K_M",
    temperature=Decimal("0.1"),
    seed=None,
    context_window=32768,
    runtime_version="ollama-0.31.1",
)


def _chat_result(text: str, *, model: str = "qwen3.6:27b") -> ChatResult:
    return ChatResult(
        text=text,
        model=model,
        elapsed_seconds=0.01,
        provider_name="fake_provider",
        options=_OPTS,
        context_id="ctx-fake",
        context_hash="deadbeef",
    )


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _config() -> GeosConfig:
    return GeosConfig(
        base_url="http://127.0.0.1:11434",
        request_timeout_seconds=30,
        max_context_tokens=100_000,
    )


def _file_block(path: str, content: str) -> str:
    return f"<<<FILE: {path}>>>\n{content}<<<END_FILE>>>\n"


def _make_repo(
    tmp_path: Path, *, files: list[str], allow_overwrite: list[str] | None = None
) -> Path:
    """Build a minimal fake repo_root: implementation prompt + a work package YAML."""
    _write(tmp_path / "prompts" / "implementation.md", "You are an implementation engineer.\n")
    lines = ["task_id: CM-TEST", "files:"]
    lines += [f"  - {f}" for f in files]
    if allow_overwrite:
        lines.append("allow_overwrite:")
        lines += [f"  - {p}" for p in allow_overwrite]
    _write(tmp_path / "work_packages" / "CM-TEST.yaml", "\n".join(lines) + "\n")
    return tmp_path / "work_packages" / "CM-TEST.yaml"


def _passing_gate(**_kwargs: object) -> GateResult:
    return GateResult(
        passed=True,
        steps=[
            StepResult(name="ruff format", command=["true"], passed=True, returncode=0, output="")
        ],
    )


def _failing_gate(**_kwargs: object) -> GateResult:
    return GateResult(
        passed=False,
        steps=[
            StepResult(
                name="pytest",
                command=["uv", "run", "pytest"],
                passed=False,
                returncode=1,
                output="FAILED tests/unit/foo/test_bar.py::test_bar - AssertionError",
            )
        ],
    )


# ---------------------------------------------------------------------------
# Happy path: real disk writes + allowlist refusal + manifest content
# ---------------------------------------------------------------------------


def test_run_task_writes_allowed_files_refuses_disallowed_and_writes_real_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("runner.run_task.run_gate", _passing_gate)

    allowed_path = "src/greenzalgo/modules/foo/bar.py"
    disallowed_path = "src/greenzalgo/kernel/evil.py"  # not in files[], not under tests/
    wp_path = _make_repo(tmp_path, files=[allowed_path])

    model_text = _file_block(allowed_path, "def bar() -> int:\n    return 1\n") + _file_block(
        disallowed_path, "EVIL = True\n"
    )

    def model_call(system: str, user: str) -> ChatResult:
        return _chat_result(model_text)

    result = run_task(
        work_package_path=wp_path,
        repo_root=tmp_path,
        config=_config(),
        model_call=model_call,
        max_iters=4,
        dry_run=False,
        module_hint=None,
    )

    # (a) the allowed file is actually written to disk at the right path.
    written_file = tmp_path / allowed_path
    assert written_file.is_file()
    assert written_file.read_text(encoding="utf-8") == "def bar() -> int:\n    return 1\n"

    # (b) the disallowed path is refused, not written -- verified against the real temp dir.
    assert not (tmp_path / disallowed_path).exists()

    assert result.passed is True
    assert result.iterations_used == 1
    assert len(result.iteration_records[0].refused_paths) == 1
    assert result.iteration_records[0].refused_paths[0]["path"] == disallowed_path
    assert "not in allowlist" in result.iteration_records[0].refused_paths[0]["reason"]

    # (c) the manifest is written and contains real, non-fabricated data about what happened.
    assert result.manifest_path is not None
    assert result.manifest_path.is_file()
    on_disk = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert on_disk["task_id"] == "CM-TEST"
    assert on_disk["final_status"] == "PASS"
    assert on_disk["files_written"] == [allowed_path]
    assert on_disk["model"] == "qwen3.6:27b"
    assert on_disk["provider_name"] == "fake_provider"
    assert on_disk["iterations_used"] == 1
    refused = on_disk["iterations"][0]["refused_paths"]
    assert len(refused) == 1
    assert refused[0]["path"] == disallowed_path


# ---------------------------------------------------------------------------
# Overwrite guard wired through _write_files
# ---------------------------------------------------------------------------


def test_run_task_overwrite_guard_blocks_destructive_rewrite_and_original_survives(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("runner.run_task.run_gate", _passing_gate)

    target_path = "src/greenzalgo/modules/foo/bar.py"
    original = '"""bar module."""\n\nimport os\n\n__all__ = ["a", "b"]\n\na = 1\nb = 2\n'
    _write(tmp_path / target_path, original)
    wp_path = _make_repo(tmp_path, files=[target_path])

    # Destructive: drops "b" from __all__ -- exactly the shrinking-surface case overwrite_guard
    # exists to catch.
    destructive = '"""bar module."""\n\nimport os\n\n__all__ = ["a"]\n\na = 1\n'

    def model_call(system: str, user: str) -> ChatResult:
        return _chat_result(_file_block(target_path, destructive))

    result = run_task(
        work_package_path=wp_path,
        repo_root=tmp_path,
        config=_config(),
        model_call=model_call,
        max_iters=1,
        dry_run=False,
        module_hint=None,
    )

    # The refusal must actually propagate through _write_files: nothing written for this path.
    assert result.iteration_records[0].written_files == []
    refused = result.iteration_records[0].refused_paths
    assert len(refused) == 1
    assert refused[0]["path"] == target_path
    assert "__all__" in refused[0]["reason"]

    # The original file on disk must be completely unchanged.
    assert (tmp_path / target_path).read_text(encoding="utf-8") == original


def test_run_task_allow_overwrite_bypasses_the_guard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("runner.run_task.run_gate", _passing_gate)

    target_path = "src/greenzalgo/modules/foo/bar.py"
    original = '"""bar module."""\n\n__all__ = ["a", "b"]\n\na = 1\nb = 2\n'
    _write(tmp_path / target_path, original)
    wp_path = _make_repo(tmp_path, files=[target_path], allow_overwrite=[target_path])

    destructive = '"""bar module."""\n\n__all__ = ["a"]\n\na = 1\n'

    def model_call(system: str, user: str) -> ChatResult:
        return _chat_result(_file_block(target_path, destructive))

    result = run_task(
        work_package_path=wp_path,
        repo_root=tmp_path,
        config=_config(),
        model_call=model_call,
        max_iters=1,
        dry_run=False,
        module_hint=None,
    )

    assert result.iteration_records[0].refused_paths == []
    assert (tmp_path / target_path).read_text(encoding="utf-8") == destructive


# ---------------------------------------------------------------------------
# Bounded repair loop
# ---------------------------------------------------------------------------


def test_run_task_retries_on_gate_failure_and_succeeds_on_second_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target_path = "src/greenzalgo/modules/foo/bar.py"
    wp_path = _make_repo(tmp_path, files=[target_path])

    gate_calls: list[dict[str, object]] = []

    def fake_gate(**kwargs: object) -> GateResult:
        gate_calls.append(kwargs)
        return _failing_gate() if len(gate_calls) == 1 else _passing_gate()

    monkeypatch.setattr("runner.run_task.run_gate", fake_gate)

    prompts_seen: list[str] = []

    def model_call(system: str, user: str) -> ChatResult:
        prompts_seen.append(user)
        content = "def bar() -> int:\n    return 1\n"
        return _chat_result(_file_block(target_path, content))

    result = run_task(
        work_package_path=wp_path,
        repo_root=tmp_path,
        config=_config(),
        model_call=model_call,
        max_iters=4,
        dry_run=False,
        module_hint=None,
    )

    assert result.passed is True
    assert result.iterations_used == 2
    assert len(gate_calls) == 2
    # Bounded retry: it stopped at 2 iterations, not run out to max_iters=4.
    assert len(prompts_seen) == 2
    # The repair loop actually fed the gate's failure back into the next prompt.
    assert "REPAIR REQUEST" in prompts_seen[1]
    assert "AssertionError" in prompts_seen[1]
    assert result.iteration_records[0].gate_passed is False
    assert result.iteration_records[0].gate_failed_step == "pytest"
    assert result.iteration_records[1].gate_passed is True


def test_run_task_stops_at_max_iters_when_gate_never_passes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("runner.run_task.run_gate", _failing_gate)

    target_path = "src/greenzalgo/modules/foo/bar.py"
    wp_path = _make_repo(tmp_path, files=[target_path])

    call_count = {"n": 0}

    def model_call(system: str, user: str) -> ChatResult:
        call_count["n"] += 1
        return _chat_result(_file_block(target_path, "def bar() -> int:\n    return 1\n"))

    result = run_task(
        work_package_path=wp_path,
        repo_root=tmp_path,
        config=_config(),
        model_call=model_call,
        max_iters=3,
        dry_run=False,
        module_hint=None,
    )

    assert result.passed is False
    assert result.iterations_used == 3
    assert call_count["n"] == 3
    assert result.manifest["final_status"] == "FAIL"


# ---------------------------------------------------------------------------
# dry-run: no writes, no gate, single iteration
# ---------------------------------------------------------------------------


def test_run_task_unparseable_output_triggers_one_reformat_retry_per_iteration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """_call_and_parse() retries once inline on ParseError before giving up for that iteration
    (see run_task.py's own docstring: 'with one reformat retry'). If both calls in an iteration
    are unparseable, that whole iteration is recorded as a parse failure and the outer repair
    loop moves on -- run_gate must never be reached for that iteration."""

    def _gate_must_not_run(**_k: object) -> GateResult:
        raise AssertionError("gate must not run when nothing parsed")

    monkeypatch.setattr("runner.run_task.run_gate", _gate_must_not_run)

    target_path = "src/greenzalgo/modules/foo/bar.py"
    wp_path = _make_repo(tmp_path, files=[target_path])

    call_count = {"n": 0}

    def model_call(system: str, user: str) -> ChatResult:
        call_count["n"] += 1
        return _chat_result("this is not a valid file block or JSON at all")

    result = run_task(
        work_package_path=wp_path,
        repo_root=tmp_path,
        config=_config(),
        model_call=model_call,
        max_iters=2,
        dry_run=False,
        module_hint=None,
    )

    assert result.passed is False
    assert result.iterations_used == 2
    # one initial + one reformat retry per iteration
    assert call_count["n"] == 4
    assert result.iteration_records[0].gate_failed_step == "parse"
    assert result.iteration_records[0].written_files == []


def test_run_task_dry_run_reports_provenance_disabled_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_gate(**_kwargs: object) -> GateResult:
        return _passing_gate()

    monkeypatch.setattr("runner.run_task.run_gate", fake_gate)

    target_path = "src/greenzalgo/modules/foo/bar.py"
    wp_path = _make_repo(tmp_path, files=[target_path])

    result = run_task(
        work_package_path=wp_path,
        repo_root=tmp_path,
        config=_config(),
        model_call=lambda _s, _u: _chat_result(
            _file_block(target_path, "def bar() -> int:\n    return 1\n")
        ),
        max_iters=4,
        dry_run=True,
        module_hint=None,
    )

    tail = result.iteration_records[0].gate_output_tail
    assert "GAIEP provenance: DISABLED" in tail
    assert "no durable AI response provenance will be captured" in tail


def test_run_task_dry_run_reports_provenance_enabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_gate(**_kwargs: object) -> GateResult:
        return _passing_gate()

    monkeypatch.setattr("runner.run_task.run_gate", fake_gate)

    target_path = "src/greenzalgo/modules/foo/bar.py"
    wp_path = _make_repo(tmp_path, files=[target_path])
    config = GeosConfig(
        base_url="http://127.0.0.1:11434",
        request_timeout_seconds=30,
        max_context_tokens=100_000,
        gaiep_provenance_enabled=True,
    )

    result = run_task(
        work_package_path=wp_path,
        repo_root=tmp_path,
        config=config,
        model_call=lambda _s, _u: _chat_result(
            _file_block(target_path, "def bar() -> int:\n    return 1\n")
        ),
        max_iters=4,
        dry_run=True,
        module_hint=None,
    )

    tail = result.iteration_records[0].gate_output_tail
    assert "GAIEP provenance: ENABLED" in tail
    assert "AI response provenance will be persisted" in tail


def test_run_task_dry_run_writes_nothing_and_skips_the_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_if_called(**_kwargs: object) -> GateResult:
        raise AssertionError("gate must not run in dry-run mode")

    monkeypatch.setattr("runner.run_task.run_gate", fail_if_called)

    target_path = "src/greenzalgo/modules/foo/bar.py"
    wp_path = _make_repo(tmp_path, files=[target_path])

    def model_call(system: str, user: str) -> ChatResult:
        return _chat_result(_file_block(target_path, "def bar() -> int:\n    return 1\n"))

    result = run_task(
        work_package_path=wp_path,
        repo_root=tmp_path,
        config=_config(),
        model_call=model_call,
        max_iters=4,
        dry_run=True,
        module_hint=None,
    )

    assert not (tmp_path / target_path).exists()
    assert result.iterations_used == 1
    assert result.manifest_path is None
    assert result.passed is False


# ---------------------------------------------------------------------------
# Repair-note bounds
#
# [measured 2026-08-08] The repair note used to resend the FULL contents of every generated
# file on every retry. A work package that rendered at ~6.8k tokens on iteration 1 reached
# ~15.7k and then ~21.6k on retries -- past runner.yaml's own max_context_tokens, which only
# warned. These tests keep the note bounded and focused, because the previous behaviour was a
# bound that existed in config and was enforced nowhere.
# ---------------------------------------------------------------------------


def _gate_failing_on(output: str) -> GateResult:
    return GateResult(
        steps=[
            StepResult(
                name="ruff check",
                command=["ruff", "check", "."],
                returncode=1,
                passed=False,
                output=output,
            ),
        ],
        passed=False,
    )


def test_repair_note_sends_only_the_file_the_failure_names() -> None:
    files = {"src/a.py": "A" * 500, "src/b.py": "B" * 500, "tests/test_a.py": "T" * 500}
    note = _build_repair_note(_gate_failing_on("E501 --> src/b.py:1:1"), files)

    assert "--- CURRENT src/b.py ---" in note
    assert "BBBB" in note
    assert "--- CURRENT src/a.py ---" not in note
    assert "AAAA" not in note


def test_repair_note_still_names_the_files_it_did_not_send() -> None:
    """The model must know the other files exist, so it can return one if the real fix is there."""
    files = {"src/a.py": "A" * 500, "src/b.py": "B" * 500}
    note = _build_repair_note(_gate_failing_on("E501 --> src/b.py:1:1"), files)

    assert "Other files in this task" in note
    assert "src/a.py" in note


def test_repair_note_falls_back_to_all_files_when_the_tool_names_none() -> None:
    """An unrecognisable failure must not produce an empty note -- that would be worse."""
    files = {"src/a.py": "A" * 500, "src/b.py": "B" * 500}
    note = _build_repair_note(_gate_failing_on("segmentation fault"), files)

    assert "--- CURRENT src/a.py ---" in note
    assert "--- CURRENT src/b.py ---" in note


def test_repair_note_caps_tool_output() -> None:
    note = _build_repair_note(_gate_failing_on("E" * 50_000), {"src/a.py": "A" * 10})

    assert len(note) < 20_000
    assert "earlier tool output trimmed" in note


def test_repair_note_caps_total_file_content() -> None:
    """Many implicated files must not reproduce the unbounded-growth bug."""
    files = {f"src/f{i}.py": "X" * 9000 for i in range(8)}
    digest = " ".join(f"--> {p}:1:1" for p in files)
    note = _build_repair_note(_gate_failing_on(digest), files)

    assert len(note) < 30_000, "repair note must stay bounded even when every file is implicated"


def test_repair_note_is_far_smaller_than_resending_everything() -> None:
    """The regression this whole section exists for, stated as a ratio."""
    files = {f"src/f{i}.py": "X" * 4000 for i in range(6)}
    note = _build_repair_note(_gate_failing_on("--> src/f3.py:1:1"), files)

    assert len(note) < sum(len(c) for c in files.values()) // 2


def test_a_manifest_is_never_silently_replaced_even_on_a_same_second_collision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """[external implementation review] {task_id}-{n}.json with plain write_text meant a re-run
    silently replaced the previous run's manifest. The fix is two layers: a UTC timestamp in the
    filename (distinct runs -> distinct files), and open("x") so the residual same-second
    collision raises instead of replacing. The clock is frozen to force that collision
    deterministically -- and the first manifest's bytes must survive the refused second write.

    Found by a tamper check: reverting open("x") to write_text failed NO test, which meant the
    guard was unpinned. This is the pin."""
    from datetime import datetime as real_datetime

    from runner import run_task as rt

    class _FrozenDatetime:
        @staticmethod
        def now(tz: object = None) -> object:
            return real_datetime(2026, 8, 11, 12, 0, 0, tzinfo=UTC)

    monkeypatch.setattr(rt, "datetime", _FrozenDatetime)

    first = rt._write_manifest(tmp_path, "TASK-1", {"iterations_used": 1, "run": "first"})
    assert "20260811T120000Z" in first.name

    with pytest.raises(FileExistsError):
        rt._write_manifest(tmp_path, "TASK-1", {"iterations_used": 1, "run": "second"})

    assert json.loads(first.read_text(encoding="utf-8"))["run"] == "first"


# ---------------------------------------------------------------------------------------------
# The lane refusal. [added 2026-08-18]
#
# run_task is directly invocable (`uv run python -m runner.run_task <wp.yaml>`), and until this
# guard landed it never applied validate_qwen_task -- while runner/qwen_task.py, which describes
# itself as "the safe front door", did. So the policy was enforced on one of two routes to the
# same work. Three of sixty-six packages in runs/tasks/ fail the policy and all three ran.
#
# These tests pin BOTH directions, because a refusal that also blocks legitimate non-lane work
# would be traded one bug for another: run_task is still the general runner.
# ---------------------------------------------------------------------------------------------


def _lane_package(tmp_path: Path, *, extra: str) -> Path:
    _write(tmp_path / "prompts" / "implementation.md", "You are an implementation engineer.\n")
    return _write(
        tmp_path / "work_packages" / "CM-LANE.yaml",
        "task_id: CM-LANE\nfiles:\n  - src/greenzalgo/modules/acquisition/ledger/x.py\n" + extra,
    )


def test_a_lane_package_that_fails_lane_policy_is_refused(tmp_path: Path) -> None:
    """The bypass itself: qwen_lane: true with a task type the policy does not approve."""
    wp = _lane_package(
        tmp_path,
        extra=(
            "qwen_lane: true\n"
            "requires_claude_review: true\n"
            "risk_level: low\n"
            "allowed_task_type: new_function\n"  # exactly what P-D30-02/03 carried
            "allowed_paths:\n  - src/greenzalgo/modules/acquisition/ledger/**\n"
        ),
    )

    with pytest.raises(LaneValidationError) as excinfo:
        run_task(
            work_package_path=wp,
            repo_root=tmp_path,
            config=_config(),
            model_call=lambda _s, _u: _chat_result(""),
            max_iters=1,
            dry_run=True,
            module_hint=None,
        )

    message = str(excinfo.value)
    assert "CM-LANE" in message
    assert "new_function" in message, "the refusal must name the offending value, not just refuse"


def test_a_package_that_does_not_claim_the_lane_is_untouched(tmp_path: Path) -> None:
    """The direction that matters just as much: run_task is still the GENERAL runner.

    This package would fail validate_qwen_task on several counts -- no risk_level, no
    allowed_task_type, no allowed_paths. It never claimed the lane, so none of that applies, and a
    guard that refused it would have broken every Claude-authored package in the repository.
    """
    wp = _lane_package(tmp_path, extra="")

    result = run_task(
        work_package_path=wp,
        repo_root=tmp_path,
        config=_config(),
        model_call=lambda _s, _u: _chat_result(""),
        max_iters=1,
        dry_run=True,
        module_hint=None,
    )

    assert result.task_id == "CM-LANE"


def test_a_lane_package_that_satisfies_the_policy_still_runs(tmp_path: Path) -> None:
    """A refusal that fired on compliant lane work would push authors back to the bypass."""
    wp = _lane_package(
        tmp_path,
        extra=(
            "qwen_lane: true\n"
            "requires_claude_review: true\n"
            "risk_level: low\n"
            "allowed_task_type: pure_service\n"
            "allowed_paths:\n  - src/greenzalgo/modules/acquisition/ledger/**\n"
        ),
    )

    result = run_task(
        work_package_path=wp,
        repo_root=tmp_path,
        config=_config(),
        model_call=lambda _s, _u: _chat_result(""),
        max_iters=1,
        dry_run=True,
        module_hint=None,
    )

    assert result.task_id == "CM-LANE"
