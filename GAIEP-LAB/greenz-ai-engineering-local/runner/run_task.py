"""
greenz-ai-engineering

Module:        Runner / RunTask
Purpose:       CLI orchestrator: load work package -> build bounded context -> call the model
               through the Gateway -> parse file blocks -> allowlist-filter -> write -> gate ->
               bounded repair loop -> write run manifest. Exit 0 iff green.

               CORRECTED during the port from GreenZAlgoV3's scripts/geos/run_task.py: the model
               call was hardcoded to raw Ollama via config.model. Fixed at the ONE seam this was
               already designed around — ``ModelCall`` was already an injected callable
               (``Callable[[str, str], ChatResult]``), so nothing in run_task() itself changed at
               all; only ``_default_model_call`` (the one place that built the default
               implementation) now builds a Gateway-routed call instead of a raw one. See
               runner/gateway_client.py for the actual fix.

               Also corrected: the manifest used to record ``config.model``/
               ``config.fallback_model`` — static config values. Since the Gateway resolves the
               model dynamically per call, the manifest now records what was ACTUALLY used
               (``model``/``provider_name`` from the first successful call), which is the more
               honest thing to log anyway — it can never silently disagree with what really ran.
Owner:         Runner
Public:        No  (invoke via `uv run python -m runner.run_task <wp.yaml>`)
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from runner import context as ctx
from runner.allowlist import build_allowed_globs, check_path
from runner.autofix import apply_autofixes
from runner.config import GeosConfig, load_config
from runner.gate import GateResult, run_gate
from runner.gateway_client import ChatResult, build_gateway, build_models, build_registry, chat
from runner.model_provenance import with_provenance
from runner.overwrite_guard import check_overwrite
from runner.parse import ParseError, parse_file_map
from runner.qwen_lane import truthy, validate_qwen_task

logger = logging.getLogger("geos.run_task")

# The model-call function is injected so tests can run without a live Ollama.
ModelCall = Callable[[str, str], ChatResult]

_DEFAULT_REGISTRY = Path("ai/policies/provider_registry.yaml")
_DEFAULT_CERTIFICATIONS_DIR = Path("benchmarks/certifications")

#: This repo's own root. The prompt's declared version is read from HERE regardless of which repo
#: the generated files land in -- the same rule, and the same reason, that already anchors registry
#: resolution on this repo: prompts/ exists in greenz-ai-engineering and nowhere else, so resolving
#: it against a cross-repo write target would look for a file that cannot be there.
_ENGINEERING_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class IterationRecord:
    """Per-iteration bookkeeping for the run manifest."""

    iteration: int
    elapsed_seconds: float
    approx_tokens: int
    parsed_files: list[str]
    written_files: list[str]
    refused_paths: list[dict[str, str]]
    gate_passed: bool
    gate_failed_step: str | None
    gate_output_tail: str


@dataclass
class RunResult:
    """Overall run outcome and the manifest payload."""

    task_id: str
    passed: bool
    iterations_used: int
    manifest_path: Path | None
    manifest: dict[str, object]
    iteration_records: list[IterationRecord] = field(default_factory=list["IterationRecord"])


def _default_model_call(
    config: GeosConfig,
    *,
    repo_root: Path,
    capability_tag: str = "CODING",
    registry_path: Path = _DEFAULT_REGISTRY,
    certifications_dir: Path = _DEFAULT_CERTIFICATIONS_DIR,
    timeout_seconds: int | None = None,
    prompt_id: str = "implementation",
    prompt_version: str | None = None,
) -> ModelCall:
    """A ModelCall bound to the Gateway, resolved for ``capability_tag``.

    Batch code generation needs a longer ceiling than the interactive default;
    ``timeout_seconds`` overrides it for the harness only.

    [corrected 2026-08-12] ``prompt_id``/``prompt_version`` are parameters now. They used to be
    hardcoded to ``"implementation"`` plus a config value, which was wrong for every caller that
    is not run_task: qwen_review.py routes through here with its OWN audit prompt, so 14 REVIEW
    response logs on disk attest the implementation prompt for calls that never used it. A
    provenance field that cannot vary by caller records the caller's identity, not the call's.

    ``prompt_version=None`` means "read what the implementation prompt declares", which keeps the
    default caller correct without making every caller restate it.
    """
    effective_timeout = timeout_seconds or config.request_timeout_seconds
    resolved_registry_path = repo_root / registry_path
    registry = build_registry(
        registry_path=resolved_registry_path, certifications_dir=repo_root / certifications_dir
    )
    models = build_models(registry_path=resolved_registry_path)
    gateway = build_gateway(
        registry=registry,
        models=models,
        base_url=config.base_url,
        timeout_seconds=effective_timeout,
        observability_dir=repo_root / "observability" / "routing_events",
    )

    def call(system: str, user: str) -> ChatResult:
        result = chat(
            gateway=gateway,
            capability_tag=capability_tag,
            system=system,
            user=user,
        )
        # LOUD ON SUBSTITUTION. [owner-directed 2026-08-14] Failover stays -- an answer from the
        # second candidate beats no answer -- but it must not be SILENT. The Gateway swaps one
        # model for another on a timeout, and this repo directs CODING to a specific model for
        # measured reliability reasons: [measured 2026-08-14] four calls that day fell back to a
        # model this corpus scores 0/3 functional on ENG-CM-113, and the only trace was in the
        # routing-event ledger. A reviewer reading the diff had no way to know which model wrote
        # it. WARNING rather than a refusal, because whether the substitution matters depends on
        # the task -- the same MoE scored 3/3 and 10-20x faster on ENG-CM-117 -- and that
        # judgement belongs to the person reading, not to this line.
        if result.failed_over_from:
            logger.warning(
                "MODEL SUBSTITUTED: %s answered after %s failed. Review this output knowing it "
                "was NOT written by the first-choice model for %s.",
                result.provider_name,
                ", ".join(result.failed_over_from),
                capability_tag,
            )

        return result

    if not config.gaiep_provenance_enabled:
        return call
    return with_provenance(
        call,
        capability_name=capability_tag.lower(),
        prompt_id=prompt_id,
        # Resolved ONCE here, not per call: reading it inside the closure would re-read the file
        # on every model call, and would let a mid-run edit to the prompt split one run's
        # provenance across two versions.
        prompt_version=prompt_version or ctx.load_system_prompt_version(_ENGINEERING_ROOT),
        fail_closed=config.gaiep_provenance_fail_closed,
    )


def _write_files(
    files: dict[str, str],
    allowed_globs: list[str],
    repo_root: Path,
    dry_run: bool,
    allow_overwrite: frozenset[str],
) -> tuple[list[str], list[dict[str, str]]]:
    """Allowlist- and overwrite-guard files, then write. Returns (written, refused).

    ``allow_overwrite`` bypasses the destructive-overwrite guard for those exact normalized
    paths — the work package's escape hatch for intentional removals."""
    written: list[str] = []
    refused: list[dict[str, str]] = []
    for raw_path, content in files.items():
        decision = check_path(raw_path, allowed_globs, repo_root)
        if not decision.allowed:
            logger.warning("REFUSED %s — %s", raw_path, decision.reason)
            refused.append({"path": raw_path, "reason": decision.reason})
            continue
        target = repo_root / decision.path
        fix_result = apply_autofixes(decision.path, content)
        if fix_result.applied:
            logger.info("AUTOFIX %s — applied: %s", decision.path, ", ".join(fix_result.applied))
            content = fix_result.content
        if decision.path not in allow_overwrite:
            old_text = target.read_text(encoding="utf-8") if target.is_file() else None
            guard = check_overwrite(decision.path, old_text, content)
            if not guard.allowed:
                logger.warning("REFUSED %s — %s", decision.path, guard.reason)
                refused.append({"path": decision.path, "reason": guard.reason})
                continue
        if dry_run:
            logger.info("DRY-RUN would write %s (%d bytes)", decision.path, len(content))
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            logger.info("WROTE %s (%d bytes)", decision.path, len(content))
        written.append(decision.path)
    return written, refused


def _call_and_parse(
    model_call: ModelCall, system: str, user: str
) -> tuple[dict[str, str], ChatResult]:
    """Call the model and parse the file map, with one reformat retry."""
    result = model_call(system, user)
    try:
        return parse_file_map(result.text), result
    except ParseError as exc:
        logger.warning("Model output unparseable (%s); requesting one reformat.", exc)
        retry_user = (
            user
            + "\n\n=== REFORMAT REQUIRED ===\n"
            + "Your previous reply could not be parsed. Reply with ONLY the file blocks: "
            + "<<<FILE: path>>> then the exact file contents then <<<END_FILE>>> (one per "
            + "file), and no other text."
        )
        retry = model_call(system, retry_user)
        return parse_file_map(retry.text), retry


def _test_targets(work_package: ctx.WorkPackage) -> list[str]:
    """Test paths for the gate: explicit `tests` plus any test globs in `files`."""
    targets = list(work_package.tests)
    for entry in work_package.files:
        cleaned = entry.strip().rstrip("/")
        if cleaned.startswith("tests/") and cleaned not in targets:
            targets.append(cleaned)
    return targets


class LaneValidationError(RuntimeError):
    """A package declaring `qwen_lane: true` was run without satisfying the lane policy."""


def _refuse_unvalidated_lane_package(work_package: ctx.WorkPackage) -> None:
    """Apply the Qwen-lane policy to a package that opted into the lane, whichever door it enters.

    THE GATE EXISTED AND ONE OF THE TWO ENTRY POINTS WALKED PAST IT. [measured 2026-08-18]
    `runner/qwen_task.py` describes itself as "the safe front door... run a work package through
    the EXISTING runner AFTER the lane validator approves it", and it does call
    `validate_qwen_task`. This module -- the runner that front door delegates to -- never did, and
    it is directly invocable (`uv run python -m runner.run_task <wp.yaml>`). So a package could
    declare `qwen_lane: true`, fail the policy, and run anyway by being handed to the back door.

    That is not hypothetical: three of the sixty-six packages in `runs/tasks/` fail
    `validate_qwen_task` today and all three RAN. Two of them (P-D30-02, P-D30-03) carry
    `allowed_task_type: new_function`, a type name that is not in APPROVED_TASK_TYPES and never
    was; the third (M2-D05-01) carries `platform_contract_plus_writer`. Nothing rejected them
    because nothing on this path was looking.

    THE SAME SHAPE THIS REPOSITORY KEEPS FINDING, in a new variant. `_SCAN_DIRS` covering 5 of 11
    packages, `SENSITIVE_PREFIXES` maintained by memory, a lookahead test scoped to one file --
    each was a correct rule with an incomplete reach. This one is a correct rule with a complete
    reach and an unguarded second route to the same work. The fix is the same in spirit: make the
    check unavoidable rather than conventional.

    NOT A BAN ON run_task. A package that does not opt into the lane is untouched -- this module
    remains the general runner, and Claude-authored work that was never lane-bounded still runs
    here exactly as before. What it refuses is the specific contradiction of claiming lane
    membership while failing lane policy, which is the only case where bypassing meant anything.
    """
    if not truthy(work_package.raw.get("qwen_lane")):
        return
    decision = validate_qwen_task(work_package.raw)
    if decision.ok:
        return
    complaints = "\n".join(f"  - {error}" for error in decision.errors)
    raise LaneValidationError(
        f"{work_package.task_id} declares qwen_lane: true but fails the Qwen-lane policy:\n"
        f"{complaints}\n"
        "Fix the package, or drop `qwen_lane: true` if it was never meant to be lane work. "
        "Running it through runner.run_task instead of runner.qwen_task does not make it "
        "compliant -- that route used to skip this check, which is the bug this refusal closes."
    )


def run_task(
    *,
    work_package_path: Path,
    repo_root: Path,
    config: GeosConfig,
    model_call: ModelCall,
    max_iters: int,
    dry_run: bool,
    module_hint: str | None,
    prompt_root: Path | None = None,
) -> RunResult:
    """Execute one work package end-to-end with a bounded repair loop.

    ``prompt_root`` defaults to ``repo_root`` (unchanged single-repo behavior). It exists
    separately because the system prompt (``prompts/implementation.md``) is generic
    "how to write Python code" guidance that lives in THIS repo only -- a work package
    targeting a sibling repo (``repo_root`` pointed elsewhere, e.g. greenz-ai-platform) still
    needs it sourced from here, not from a copy that doesn't exist in the target repo.
    """
    work_package = ctx.load_work_package(work_package_path)
    _refuse_unvalidated_lane_package(work_package)
    system_prompt = ctx.load_system_prompt(prompt_root if prompt_root is not None else repo_root)
    allowed_globs = build_allowed_globs(work_package.files)
    allow_overwrite_raw: object = work_package.raw.get("allow_overwrite") or []
    allow_overwrite = frozenset(
        str(entry).strip().replace("\\", "/")
        for entry in cast(list[object], allow_overwrite_raw)
        if str(entry).strip()
    )
    test_targets = _test_targets(work_package)

    records: list[IterationRecord] = []
    repair_note: str | None = None
    last_written: list[str] = []
    passed = False
    used_model: str | None = None
    used_provider: str | None = None

    for iteration in range(1, max_iters + 1):
        logger.info(
            "=== iteration %d/%d (task %s) ===", iteration, max_iters, work_package.task_id
        )
        package = ctx.build_context(
            work_package=work_package,
            repo_root=repo_root,
            system_prompt=system_prompt,
            budget_tokens=config.max_context_tokens,
            module_hint=module_hint,
            repair=repair_note,
        )
        logger.info(
            "context ~%d tokens (budget %d)%s",
            package.approx_tokens,
            package.budget_tokens,
            " — OVER BUDGET" if package.over_budget else "",
        )
        if package.over_budget:
            # "MAY BE TRUNCATED BY THE MODEL" WAS FALSE, and saying it taught readers to ignore
            # this line. [measured 2026-08-18] max_context_tokens is 12000 while every registered
            # deployment declares context_window 32768 with max_output_tokens 16384 -- so the
            # model's real input headroom is 16384, and this fired at 15012 tokens on a prompt the
            # model was never close to truncating. It cried wolf at 12k and would have stayed
            # silent at the cliff it named.
            #
            # WHAT IT IS: an ASSEMBLY budget, chosen by this harness, not a limit the model
            # imposes. Exceeding it means the assembled context is larger than intended -- worth
            # knowing, and worth keeping loud enough to notice a package that has ballooned -- but
            # it is not a truncation warning and no longer claims to be. The narrowing that DOES
            # drop content is select_api_blocks against KERNEL_CHAR_CAP, which reports what it
            # dropped separately; a tier-0 file that will not fit raises rather than vanishing.
            # TWO DIFFERENT CLAIMS, and collapsing them is how this line got miscalibrated
            # twice in one day. Over the ASSEMBLY budget means "bigger than intended" and is
            # informational. Over the model's INPUT HEADROOM means the model itself is out of
            # room, which is a different and much worse thing -- P-D30-06 assembled 23481 tokens,
            # the incumbent failed all three iterations, and the Gateway failed over to the MoE.
            if package.approx_tokens > config.input_headroom_tokens:
                logger.error(
                    "Context (~%d tokens) exceeds the MODEL'S input headroom (~%d). This is not "
                    "a soft budget: deployments declare a 32768 window with 16384 reserved for "
                    "output, so the prompt is competing with the reply for space. Expect "
                    "truncation, degraded output, or an outright provider failure. Narrow the "
                    "work package's `specification:` list -- that is what drives assembled size.",
                    package.approx_tokens,
                    config.input_headroom_tokens,
                )
            else:
                logger.warning(
                    "Context (~%d tokens) exceeds this harness's assembly budget (%d). That is a "
                    "budget chosen here, NOT the model's limit -- real input headroom is ~%d "
                    "tokens and this prompt is under it. Nothing has been truncated or dropped.",
                    package.approx_tokens,
                    package.budget_tokens,
                    config.input_headroom_tokens,
                )

        started = time.monotonic()
        try:
            files, chat_result = _call_and_parse(
                model_call, package.system_prompt, package.user_prompt
            )
        except ParseError as exc:
            elapsed = time.monotonic() - started
            logger.error("Iteration %d: unparseable after retry: %s", iteration, exc)
            records.append(
                IterationRecord(
                    iteration=iteration,
                    elapsed_seconds=round(elapsed, 2),
                    approx_tokens=package.approx_tokens,
                    parsed_files=[],
                    written_files=[],
                    refused_paths=[],
                    gate_passed=False,
                    gate_failed_step="parse",
                    # The raw reply, not just the complaint about it. [measured 2026-08-10] A
                    # forty-minute lane run failed three times on "unbalanced markers" and left
                    # no record of what the model emitted, so the failure erased its own
                    # evidence -- the exact unobservable-failure shape this project keeps
                    # finding elsewhere, here in the harness meant to catch it.
                    gate_output_tail=f"{exc}\n\n--- raw model output ---\n{exc.raw}",
                )
            )
            # [correction 2026-08-10] SAID "could not be parsed as JSON", AND THE LANE DOES NOT
            # USE JSON. The required format is <<<FILE: path>>> / <<<END_FILE>>> delimiter
            # blocks, which _call_and_parse's own retry states correctly one layer down. So from
            # iteration 2 onward the model was being told the wrong thing about its own failure,
            # and being pushed toward emitting JSON instead of the format actually wanted.
            #
            # The concrete guidance is deliberate rather than a restatement: the observed
            # failure signature (N FILE, N END_FILE, 0 well-formed) is what you get when content
            # follows `>>>` on the SAME line, and naming that beats repeating the rule.
            repair_note = (
                f"Your last output could not be parsed: {exc}\n"
                "Use <<<FILE: path>>> on its own line, then the file contents starting on the "
                "NEXT line, then <<<END_FILE>>> on its own line. Do not put content on the same "
                "line as a marker, and emit no text outside the blocks."
            )
            continue

        used_model = used_model or chat_result.model
        used_provider = used_provider or chat_result.provider_name
        elapsed = time.monotonic() - started
        written, refused = _write_files(files, allowed_globs, repo_root, dry_run, allow_overwrite)
        last_written = written

        if dry_run:
            provenance_state = (
                "GAIEP provenance: ENABLED; AI response provenance will be persisted."
                if config.gaiep_provenance_enabled
                else "GAIEP provenance: DISABLED; no durable AI response provenance will be captured."
            )
            records.append(
                IterationRecord(
                    iteration=iteration,
                    elapsed_seconds=round(elapsed, 2),
                    approx_tokens=package.approx_tokens,
                    parsed_files=sorted(files),
                    written_files=written,
                    refused_paths=refused,
                    gate_passed=False,
                    gate_failed_step="skipped (dry-run)",
                    gate_output_tail=(
                        "dry-run: no target files or run manifest written; "
                        f"{provenance_state} gate skipped"
                    ),
                )
            )
            logger.info(
                "dry-run: stopping after one iteration (no gate; no target writes). %s",
                provenance_state,
            )
            break

        gate = run_gate(repo_root=repo_root, written_paths=written, test_targets=test_targets)
        records.append(
            _record_from_gate(
                iteration, elapsed, package.approx_tokens, files, written, refused, gate
            )
        )

        if gate.passed:
            logger.info("iteration %d: GATE GREEN", iteration)
            passed = True
            break

        repair_note = _build_repair_note(gate, files)
        logger.info("iteration %d: gate failed at '%s'; repairing.", iteration, _failed_name(gate))

    manifest = _build_manifest(
        work_package, config, records, passed, dry_run, last_written, used_model, used_provider
    )
    manifest_path = None if dry_run else _write_manifest(repo_root, work_package.task_id, manifest)
    return RunResult(
        task_id=work_package.task_id,
        passed=passed,
        iterations_used=len(records),
        manifest_path=manifest_path,
        manifest=manifest,
        iteration_records=records,
    )


def _record_from_gate(
    iteration: int,
    elapsed: float,
    approx_tokens: int,
    files: dict[str, str],
    written: list[str],
    refused: list[dict[str, str]],
    gate: GateResult,
) -> IterationRecord:
    failed = gate.failed_step
    return IterationRecord(
        iteration=iteration,
        elapsed_seconds=round(elapsed, 2),
        approx_tokens=approx_tokens,
        parsed_files=sorted(files),
        written_files=written,
        refused_paths=refused,
        gate_passed=gate.passed,
        gate_failed_step=None if gate.passed else (failed.name if failed else "unknown"),
        gate_output_tail=("" if gate.passed else _tail(gate.failure_digest())),
    )


def _failed_name(gate: GateResult) -> str:
    step = gate.failed_step
    return step.name if step else "unknown"


# Bounds for the repair note. [measured 2026-08-08] The uncapped version was the real reason
# work-package prompts blew past runner.yaml's max_context_tokens: a first iteration rendered at
# ~6.8k tokens, but each retry re-sent the FULL contents of every generated file, pushing the
# same task to ~15.7k and then ~21.6k. Only a warning was emitted, so the model was silently
# handed a prompt the harness itself considered over budget -- and on this hardware a larger
# prompt means a larger KV cache and more memory pressure, which is not a free cost.
_REPAIR_OUTPUT_LIMIT = 4000  # chars of failing-tool output
_REPAIR_FILES_LIMIT = 20000  # chars of file contents (~5k tokens)


def _files_named_in(digest: str, files: dict[str, str]) -> list[str]:
    """The generated files the failing tool actually named in its output.

    ruff/pyright/pytest all report the offending path, so a gate failure usually implicates one
    file out of several. Resending only those is both smaller and more focused than dumping the
    whole set back every iteration.
    """
    return sorted(path for path in files if path in digest)


def _build_repair_note(gate: GateResult, files: dict[str, str]) -> str:
    """Feed the failing tool output plus the implicated file contents back to the model.

    Deliberately does NOT resend every generated file. It sends the full text of the files the
    failure names, plus the bare path list of the rest so the model still knows what exists and
    can return another file if the real fix lives there. Both sections are bounded -- an
    unbounded repair note is what silently doubled and tripled the prompt across retries.
    """
    digest = gate.failure_digest()
    if len(digest) > _REPAIR_OUTPUT_LIMIT:
        digest = "...[earlier tool output trimmed]...\n" + digest[-_REPAIR_OUTPUT_LIMIT:]

    implicated = _files_named_in(digest, files)
    # If the tool named nothing recognisable, fall back to the old behaviour (all files) rather
    # than guessing -- an empty repair note would be worse than a large one.
    chosen = implicated or sorted(files)

    blocks: list[str] = []
    used = 0
    omitted: list[str] = []
    for path in chosen:
        block = f"--- CURRENT {path} ---\n{files[path]}"
        if used + len(block) > _REPAIR_FILES_LIMIT and blocks:
            omitted.append(path)
            continue
        blocks.append(block)
        used += len(block)

    not_shown = sorted(set(files) - {p for p in chosen if p not in omitted})
    footer = ""
    if not_shown:
        footer = (
            "\n\nOther files in this task (contents not shown; return one only if the fix "
            "genuinely belongs there):\n" + "\n".join(f"  {p}" for p in not_shown)
        )

    return (
        "The quality gate FAILED. Fix ONLY these failures and return the corrected file(s) as "
        "<<<FILE: path>>> ... <<<END_FILE>>> blocks. Return every file you change, and no "
        "others.\n\n"
        f"{digest}\n\n"
        f"Current file contents:\n" + "\n\n".join(blocks) + footer
    )


def _tail(text: str, limit: int = 4000) -> str:
    return text if len(text) <= limit else text[-limit:]


def _build_manifest(
    work_package: ctx.WorkPackage,
    config: GeosConfig,
    records: list[IterationRecord],
    passed: bool,
    dry_run: bool,
    written: list[str],
    used_model: str | None,
    used_provider: str | None,
) -> dict[str, object]:
    return {
        "task_id": work_package.task_id,
        "work_package": str(work_package.source_path),
        "model": used_model,  # what actually ran, resolved by the Gateway -- never a static config value
        "provider_name": used_provider,
        "base_url": config.base_url,
        "dry_run": dry_run,
        "iterations": [record.__dict__ for record in records],
        "iterations_used": len(records),
        "total_elapsed_seconds": round(sum(r.elapsed_seconds for r in records), 2),
        "files_written": written,
        "final_status": "PASS" if passed else "FAIL",
    }


def _write_manifest(repo_root: Path, task_id: str, manifest: dict[str, object]) -> Path:
    """[external implementation review] The path used to be {task_id}-{iterations}.json with a
    plain write_text -- re-running the same task with the same iteration count silently
    overwrote the previous run's manifest, on a lane whose records are supposed to be immutable
    historical evidence. A UTC timestamp makes each run's manifest its own file, and open("x")
    makes even a same-second collision a loud FileExistsError rather than a silent replace."""
    runs_dir = repo_root / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    n = manifest.get("iterations_used", 0)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = runs_dir / f"{task_id}-{n}-{stamp}.json"
    with path.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    logger.info("manifest written: %s", path.relative_to(repo_root))
    return path


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="runner.run_task",
        description="Task runner: work package -> context -> Gateway -> gate -> repair.",
    )
    parser.add_argument("work_package", type=Path, help="Path to the work package YAML file.")
    parser.add_argument(
        "--max-iters", type=int, default=4, help="Max generate+repair iterations (default 4)."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Build context and call the model; write no target files and no run manifest. "
            "GAIEP provenance is state-aware: when enabled, AI response provenance is "
            "persisted; when disabled, no durable AI response provenance is captured."
        ),
    )
    parser.add_argument(
        "--module-hint", type=str, default=None, help="Extra hint appended to the context."
    )
    parser.add_argument(
        "--config", type=Path, default=None, help="Override path to runner/config/runner.yaml."
    )
    parser.add_argument(
        "--capability-tag",
        type=str,
        default="CODING",
        help="Gateway capability tag to route this task through (default CODING).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=600,
        help="Per-model-call timeout in seconds for batch code-gen (default 600).",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help=(
            "Where the generated files LAND. Defaults to this repo. Point it at a sibling "
            "(e.g. ../GreenZAlgo_V4) to run a work package that targets that codebase -- "
            "run_task() has supported two roots since it was written, and the system prompt is "
            "still read from THIS repo either way, because prompts/ exists only here."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns 0 iff the final gate is green (or a dry-run ran)."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    args = _build_arg_parser().parse_args(argv)
    # THIS repo, always -- it is where prompts/, the provider registry and the certification
    # ledger live, and none of those move when the TARGET moves.
    prompt_root = Path(__file__).resolve().parents[1]
    # Where generated files land. `run_task` has always taken these as two arguments and its
    # docstring spells out why; only the CLI was missing the flag, which quietly made the lane
    # single-repo in practice while reading as though it were not.
    repo_root = (args.repo_root or prompt_root).resolve()

    config = load_config(args.config)
    try:
        result = run_task(
            work_package_path=args.work_package,
            repo_root=repo_root,
            prompt_root=prompt_root,
            config=config,
            model_call=_default_model_call(
                config,
                # The Gateway's registry and ledger are read from THIS repo, never the target: a
                # work package aimed at V4 must still route through the certification evidence
                # gathered here, or routing would depend on which codebase is being written to.
                repo_root=prompt_root,
                capability_tag=args.capability_tag,
                timeout_seconds=args.timeout,
            ),
            max_iters=args.max_iters,
            dry_run=args.dry_run,
            module_hint=args.module_hint,
        )
    except LaneValidationError as exc:
        # A POLICY REFUSAL IS NOT A CRASH, and printing it as one teaches operators to read past
        # tracebacks. The message already names the package and every failing rule; that is the
        # whole output, and exit 2 distinguishes "this was refused before it ran" from exit 1,
        # which means the model ran and the gate stayed red.
        logger.error("REFUSED: %s", exc)
        return 2

    if args.dry_run:
        logger.info("DRY-RUN complete for %s (no gate, no writes).", result.task_id)
        return 0
    if result.passed:
        logger.info("PASS: %s green in %d iteration(s).", result.task_id, result.iterations_used)
        return 0
    logger.error(
        "FAIL: %s did not reach a green gate in %d iteration(s). See %s.",
        result.task_id,
        result.iterations_used,
        result.manifest_path,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
