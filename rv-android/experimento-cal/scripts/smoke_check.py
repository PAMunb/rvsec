#!/usr/bin/env python3
"""SMOKE gate — evaluate a completed smoke run against the iteration manifest.

The smoke run (4 APKs × the extreme arms, 90s, 1 rep) is the last cheap check before the
full RUN+MONITOR state: it proves the deployed configuration actually reaches the emulator
and the LLM server as intended. This script reads the smoke results tree and the manifest
and asserts, per smoke task, that reality matches the contract.

Per smoke task (spec "Smoke Gate", INV-CAL-07):
  * the `[APE-LLM-CONFIG]` trace line equals the arm's manifest `expected_config_ack`
    field-by-field (numeric fields compared tolerantly: 0 == 0.0 == "0"; booleans
    case-insensitive) — this catches silent config drift, the failure class the whole
    scaffold exists to prevent;
  * `[APE-LLM-CONFIG-ACK] server_model=` equals the manifest `expected_server_model` —
    proof of which weights the server actually served;
  * the task identity is COMPLETED with coverage > 0 (from tasks.json) — proof the arm
    explored rather than crashed on startup;
  * the logcat contains 0 `VerifyError` — proof instrumentation did not corrupt the dex.

Any mismatch aborts the iteration (exit 1) with a report naming arm / field / expected /
observed. The scaffold NEVER self-adjusts configuration — a mismatch is a human decision
(re-generate the iteration, fix the variant, or investigate the server), never a silent
retry with different settings.

Exit code: 0 when every smoke task passes, 1 on any mismatch, 2 on usage error.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Trace grammar (d90c1f4). The negative lookahead keeps `[APE-LLM-CONFIG]` from also
# matching `[APE-LLM-CONFIG-ACK]`; the KV regex reads every `field=value` token so lookups
# are by name and order-independent.
CONFIG_LINE_RE = re.compile(r"\[APE-LLM-CONFIG\](?!-ACK)")
CONFIG_ACK_RE = re.compile(r"\[APE-LLM-CONFIG-ACK\]")
KV_RE = re.compile(r"(\w+)=(\S+)")

VERIFY_ERROR = "VerifyError"


# --- trace parsing ---------------------------------------------------------------------
def parse_config_line(trace_text: str) -> Optional[Dict[str, str]]:
    """Parse the requested-config `[APE-LLM-CONFIG]` line into a {field: value} dict.

    Returns None if no such line exists (a task that never emitted its config — itself a
    smoke failure). All values are strings; the caller compares them tolerantly.
    """
    for line in trace_text.splitlines():
        if CONFIG_LINE_RE.search(line):
            return dict(KV_RE.findall(line))
    return None


def parse_server_model(trace_text: str) -> Optional[str]:
    """Parse `server_model` from the `[APE-LLM-CONFIG-ACK]` line, or None if absent."""
    for line in trace_text.splitlines():
        if CONFIG_ACK_RE.search(line):
            kv = dict(KV_RE.findall(line))
            return kv.get("server_model")
    return None


def tolerant_equal(expected: Any, observed: str) -> bool:
    """Compare a manifest expected value against an observed trace string, tolerantly.

    Booleans compare case-insensitively (`True` == "true"); numbers compare by value so
    0 == 0.0 == "0" and 0.7 == "0.7"; everything else compares as an exact string. bool is
    checked before int/float because in Python `bool` is a subclass of `int`.
    """
    if observed is None:
        return False
    if isinstance(expected, bool):
        return observed.strip().lower() == str(expected).lower()
    if isinstance(expected, (int, float)):
        try:
            return float(observed) == float(expected)
        except (TypeError, ValueError):
            return False
    return str(expected) == observed


# --- identity + file layout ------------------------------------------------------------
def toolfrag(name: str, variant: str) -> str:
    """The `<toolfrag>` used in logcat/trace filenames: 'ape', else '<name>:<variant>'."""
    return "ape" if name == "ape" else f"{name}:{variant}"


def identity_base(config: Dict[str, Any]) -> str:
    """The `<apk>__<rep>__<timeout>__<toolfrag>` filename stem for a task's identity."""
    tc = config["tool_config"]
    frag = toolfrag(tc["name"], tc.get("variant", ""))
    return f"{config['apk_name']}__{config['repetition']}__{config['timeout']}__{frag}"


def find_smoke_task_files(iter_dir: Path) -> List[Path]:
    """Locate every smoke `tasks.json` under results/ (dirs whose name contains 'smoke').

    Smoke result directories are named `<phase>_smoke_NN`; the run results share the tree
    but never carry 'smoke', so this glob isolates the smoke pass without needing the phase.
    """
    results = iter_dir / "results"
    if not results.is_dir():
        return []
    return sorted(p for p in results.glob("*smoke*/**/tasks.json") if p.is_file())


# --- per-task evaluation ---------------------------------------------------------------
def _arm_by_token(manifest: Dict[str, Any], token: str) -> Optional[Dict[str, Any]]:
    for arm in manifest["arms"]:
        if arm["rv_tools_token"] == token:
            return arm
    return None


def check_task(
    manifest: Dict[str, Any],
    task_dir: Path,
    task: Dict[str, Any],
    failures: List[str],
) -> None:
    """Evaluate one smoke task; append a human-readable line to `failures` per mismatch."""
    config = task["config"]
    tc = config["tool_config"]
    # Non-LLM arms use the bare 'ape'/'aperv:<v>' token as their rv_tools_token; LLM arms
    # match by token. Resolve the manifest arm for its expected config.
    token_full = (
        "ape" if tc["name"] == "ape" else f"{tc['name']}:{tc.get('variant', '')}"
    )
    arm = _arm_by_token(manifest, token_full)
    ident = identity_base(config)
    where = f"{token_full} / {config['apk_name']} (identity {ident})"

    # --- state + coverage (from tasks.json) --------------------------------------------
    result = task.get("result", {})
    state = str(result.get("state", "")).upper()
    if state != "COMPLETED":
        failures.append(f"{where}: state={state!r} (expected COMPLETED)")
    cov = result.get("coverage_metrics", {}).get("method_coverage", 0)
    try:
        cov_val = float(cov)
    except (TypeError, ValueError):
        cov_val = 0.0
    if cov_val <= 0:
        failures.append(f"{where}: method_coverage={cov} (expected > 0)")

    # --- logcat: zero VerifyError ------------------------------------------------------
    logcat = task_dir / config["apk_name"] / f"{ident}.logcat"
    if logcat.exists():
        n_verify = logcat.read_text(errors="replace").count(VERIFY_ERROR)
        if n_verify:
            failures.append(
                f"{where}: logcat contains {n_verify} VerifyError (expected 0)"
            )
    else:
        failures.append(f"{where}: logcat missing at {logcat}")

    # --- trace: [APE-LLM-CONFIG] + [APE-LLM-CONFIG-ACK] --------------------------------
    expected_cfg = arm.get("expected_config_ack", {}) if arm else {}
    if not expected_cfg:
        # Non-LLM arm (ape builtin / ANC2): no LLM config line to audit.
        return

    trace = task_dir / config["apk_name"] / f"{ident}.trace"
    if not trace.exists():
        failures.append(f"{where}: trace missing at {trace}")
        return
    trace_text = trace.read_text(errors="replace")

    observed_cfg = parse_config_line(trace_text)
    if observed_cfg is None:
        failures.append(f"{where}: no [APE-LLM-CONFIG] line in trace")
    else:
        for field, expected in expected_cfg.items():
            observed = observed_cfg.get(field)
            if not tolerant_equal(expected, observed):
                failures.append(
                    f"{where}: [APE-LLM-CONFIG] field {field!r} "
                    f"expected={expected!r} observed={observed!r}"
                )

    observed_model = parse_server_model(trace_text)
    expected_model = manifest["expected_server_model"]
    if observed_model != expected_model:
        failures.append(
            f"{where}: [APE-LLM-CONFIG-ACK] server_model "
            f"expected={expected_model!r} observed={observed_model!r}"
        )


def run_smoke_check(iter_dir: Path) -> List[str]:
    """Evaluate every smoke task and return the list of mismatch lines (empty == pass)."""
    manifest = json.loads((iter_dir / "manifest.json").read_text())
    failures: List[str] = []
    task_files = find_smoke_task_files(iter_dir)
    if not task_files:
        failures.append(f"no smoke tasks.json found under {iter_dir / 'results'}")
        return failures
    for tasks_json in task_files:
        task_dir = tasks_json.parent
        data = json.loads(tasks_json.read_text())
        for task in data.get("tasks", []):
            check_task(manifest, task_dir, task, failures)
    return failures


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--iter-dir", required=True, help="path to the generated iterN/ directory"
    )
    args = parser.parse_args(argv)

    iter_dir = Path(args.iter_dir)
    if not (iter_dir / "manifest.json").exists():
        sys.stderr.write(f"no manifest.json under iter-dir: {iter_dir}\n")
        return 2

    failures = run_smoke_check(iter_dir)
    if failures:
        print("[FAIL] SMOKE gate — configuration mismatch (NOT auto-corrected):")
        for f in failures:
            print(f"  - {f}")
        print("--- SMOKE FAIL ---")
        return 1
    print("[PASS] SMOKE gate — all smoke tasks match the manifest")
    print("--- SMOKE PASS ---")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
