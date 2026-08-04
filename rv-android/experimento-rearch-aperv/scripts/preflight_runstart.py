#!/usr/bin/env python3
"""PRE-FLIGHT — the smoke's acceptance criterion, and the campaign's starting gate.

Four checks over the first line of one trace per arm. The campaign does not start until
every arm passes every one of them. This is an operator script over a recorded trace: it
runs on no execution path, and no runtime component, Java or Python, reads `RUN_START` —
the record is write-only on both sides (`run-spec` INV-RUN-03, INV-APV-57), and verifying
an echo is post-hoc analysis by construction. The one reader in `modules/aperv-tool` is the
offline `analysis.trace_ndjson`, which is not on an execution path either.

The four checks, and what each one is worth:

  1. props_digest  equals the digest of the `ape.properties` the harness pushed. Proves
                   transport with no mapping ambiguity: the jar read exactly the bytes
                   sent. Skipped, and reported as SKIP, when no pushed file is supplied.

  2. preset+params equal the arm's declared plan. This is the one execution gh95 deferred
                   here: without it, a jar built before stage 2 would treat `ape.preset`
                   as an unknown key and silently collapse every arm to jar defaults while
                   the results directory still carried the arm's name.

  3. build.sha     equals the `rearch` commit that was built. The load-bearing one. The
                   image's Dockerfile clones `phtcosta/ape` with no branch and no SHA pin
                   and the jar under test arrives by bind-mount, so TWO jars exist in the
                   container and `RUN_START.build.sha` is the only thing that says which
                   one ran. This check is gh71's scar tissue: an image whose own
                   default-branch jar wins the mount produces a campaign that looks
                   healthy and measures the wrong binary.

  4. corpus_basis  equals the SHA-256 recomputed from the corpus list file — recomputed
                   here, never transcribed. This check does double duty, which is why it
                   gates rather than merely reports, and its two failure modes are named
                   separately because they mean different things:

                     ABSENT      the DSL parameter path dropped the value before it
                                 reached `ape.properties`. The value's only route to the
                                 device is `RV_TOOLS`' `@corpus_basis=` segment, through
                                 `_parse_single_tool_spec` and `configure()`'s fold, so an
                                 absent key means a seam in that chain is broken.
                     MISMATCHED  the value arrived carrying the wrong list.

Usage:
    uv run python scripts/preflight_runstart.py --results results --manifest manifest.json
    uv run python scripts/preflight_runstart.py ... --pushed-properties <dir>

Exits 1 on any FAIL, 0 when every arm passes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PASS = "PASS"
FAIL = "FAIL"
SKIP = "SKIP"


def read_run_start(trace: Path) -> Optional[Dict[str, Any]]:
    """The trace's first line as a dict, or None if it is not a `RUN_START`.

    Parsed with `json.loads` rather than through `aperv_tool.analysis.trace_ndjson`: that
    reader keeps `run_id`, `t0` and `params` and drops `preset`, `build` and
    `corpus_basis`, which are three of the four things checked here. From stage 2 onward
    `RUN_START` is a single JSON object on the first line, so this check does not depend on
    the NDJSON reader at all.
    """
    try:
        with open(trace, encoding="utf-8", errors="replace") as handle:
            first = handle.readline()
    except OSError:
        return None
    if not first.startswith("{"):
        return None
    try:
        record = json.loads(first)
    except json.JSONDecodeError:
        return None
    return record if record.get("type") == "RUN_START" else None


def find_traces(results_dir: Path, arms: List[Dict[str, Any]]) -> Dict[str, Path]:
    """One trace per arm: the first, by sorted path, whose filename carries the arm token.

    One is enough because these four facts are properties of the deployment, not of the
    application: a second trace of the same arm cannot have run a different jar.
    """
    found: Dict[str, Path] = {}
    traces = sorted(results_dir.rglob("*.trace"))
    for arm in arms:
        token = arm["rv_tools_token"]
        for trace in traces:
            if trace.name.endswith(f"__{token}.trace"):
                found[token] = trace
                break
    return found


def check_props_digest(
    record: Dict[str, Any], pushed: Optional[Path]
) -> Tuple[str, str]:
    """`props_digest` against the SHA-256 of the `ape.properties` the harness pushed."""
    observed = record.get("props_digest")
    if pushed is None:
        return SKIP, f"no pushed ape.properties supplied (echoed {observed!r})"
    if not pushed.is_file():
        return FAIL, f"pushed properties not found at {pushed}"
    expected = hashlib.sha256(pushed.read_bytes()).hexdigest()
    if observed == expected:
        return PASS, f"props_digest {observed}"
    return FAIL, f"props_digest {observed!r} != sha256({pushed.name}) {expected}"


def check_plan(record: Dict[str, Any], arm: Dict[str, Any]) -> Tuple[str, str]:
    """`preset` and every declared override, against what the run echoed.

    A declared key ABSENT from `params` is not a mismatch, and the reason is structural:
    the jar omits a key that sits at its own default, so absence means "running the
    default". Two of this campaign's declared values — `frontierBoostWeight=200` and
    `activityTriggerEnabled=true` — are exactly the jar's defaults, so they are expected to
    be absent, and treating that as a failure would fail every healthy run. What licenses
    reading absence this way is check 1: `props_digest` already proves the jar received the
    bytes the harness pushed.

    The gate would then be vacuous for an arm whose declared keys are all at default, so
    the count of keys actually compared is asserted, not assumed: an arm that compared
    nothing FAILs.
    """
    problems: List[str] = []
    observed_preset = record.get("preset")
    if observed_preset != arm["preset"]:
        problems.append(f"preset {observed_preset!r} != declared {arm['preset']!r}")

    params = record.get("params") or {}
    compared = 0
    at_default: List[str] = []
    for key, expected in (arm.get("expected_params") or {}).items():
        if key not in params:
            at_default.append(key)
            continue
        compared += 1
        if not values_equal(params[key], expected):
            problems.append(f"{key} {params[key]!r} != declared {expected!r}")
    if compared == 0 and arm.get("expected_params"):
        problems.append(
            "no declared key was present in params, so this check compared nothing"
        )

    detail = f"preset={observed_preset}, {compared} key(s) compared"
    if at_default:
        detail += (
            f", {len(at_default)} at jar default ({', '.join(sorted(at_default))})"
        )
    if problems:
        return FAIL, "; ".join(problems)
    return PASS, detail


def check_build_sha(
    record: Dict[str, Any], expected_sha: Optional[str]
) -> Tuple[str, str]:
    """`build.sha` against the `rearch` commit that was built."""
    observed = (record.get("build") or {}).get("sha")
    if not expected_sha:
        return FAIL, (
            f"manifest declares no build.expected_sha to check against "
            f"(the run reports {observed!r}); fill it after task 6.2"
        )
    if observed == expected_sha:
        return PASS, f"build.sha {observed}"
    return FAIL, (
        f"build.sha {observed!r} != built {expected_sha!r} — the image's own "
        "default-branch jar won the bind mount (the gh71 failure mode)"
    )


def check_corpus_basis(
    record: Dict[str, Any], subset_file: Optional[Path], declared: Optional[str]
) -> Tuple[str, str]:
    """`corpus_basis` against the digest recomputed from the list file."""
    observed = record.get("corpus_basis")
    expected = declared
    if subset_file is not None and subset_file.is_file():
        corpus_id = (declared or "corpus:").split(":", 1)[0]
        expected = f"{corpus_id}:{hashlib.sha256(subset_file.read_bytes()).hexdigest()}"
    if expected is None:
        return FAIL, "no corpus basis declared and no list file to recompute one from"
    if observed is None:
        return FAIL, (
            "ABSENT — the DSL parameter path dropped the value before it reached "
            "ape.properties; fall back to a per-arm overrides entry (design D8)"
        )
    if observed != expected:
        return FAIL, f"MISMATCHED — echoed {observed!r}, list hashes to {expected!r}"
    return PASS, f"corpus_basis {observed}"


def values_equal(observed: Any, expected: Any) -> bool:
    """Compare a typed echo against a declared value, numerics by value.

    `RUN_START.params` carries declared types — a weight is a number, a gate a boolean —
    but 0.7 and "0.7", or 0 and False, must not be conflated: booleans are compared as
    booleans, everything numeric by numeric value, everything else by string form.
    """
    if isinstance(observed, bool) or isinstance(expected, bool):
        return bool(observed) == bool(expected) and (
            isinstance(observed, bool) == isinstance(expected, bool)
        )
    try:
        return float(observed) == float(expected)
    except (TypeError, ValueError):
        return str(observed) == str(expected)


def run(
    results_dir: Path,
    manifest: Dict[str, Any],
    repo_root: Path,
    pushed_dir: Optional[Path],
) -> Tuple[List[Dict[str, Any]], bool]:
    """Run the four checks over every declared arm, one trace each.

    Args:
        results_dir: Smoke results tree, searched recursively for `.trace` files.
        manifest: The campaign manifest as `make_manifest.py` writes it.
        repo_root: rv-android root. The corpus list is resolved against it and re-hashed
            here, so the check is against the list file rather than against the digest the
            manifest transcribed from it.
        pushed_dir: Directory holding `<arm-token>.properties` as pushed, or None, which
            makes check 1 abstain rather than invent a verdict.

    Returns:
        `(report, ok)`. Each report row carries "arm", "check", "status" (PASS/FAIL/SKIP),
        "detail", and "trace" once a trace was found. `ok` is False if any row FAILed:
        a missing trace, an unreadable `RUN_START` and a wrong jar are one verdict, because
        each one leaves an arm unverified and the gate is all-or-nothing.
    """
    arms = manifest.get("arms") or []
    if not arms:
        return [
            {
                "arm": "-",
                "check": "manifest",
                "status": FAIL,
                "detail": "manifest declares no arms",
            }
        ], False

    traces = find_traces(results_dir, arms)
    subset_file = repo_root / manifest["corpus"]["subset_file"]
    declared_basis = manifest["corpus"].get("corpus_basis")
    expected_sha = (manifest.get("build") or {}).get("expected_sha")

    report: List[Dict[str, Any]] = []
    for arm in arms:
        token = arm["rv_tools_token"]
        trace = traces.get(token)
        if trace is None:
            report.append(
                {
                    "arm": token,
                    "check": "trace",
                    "status": FAIL,
                    "detail": f"no .trace found under {results_dir}",
                }
            )
            continue
        record = read_run_start(trace)
        if record is None:
            report.append(
                {
                    "arm": token,
                    "check": "RUN_START",
                    "status": FAIL,
                    "detail": f"{trace} has no RUN_START on its first line",
                }
            )
            continue
        pushed = pushed_dir / f"{token}.properties" if pushed_dir else None
        for name, (status, detail) in [
            ("props_digest", check_props_digest(record, pushed)),
            ("preset+params", check_plan(record, arm)),
            ("build.sha", check_build_sha(record, expected_sha)),
            ("corpus_basis", check_corpus_basis(record, subset_file, declared_basis)),
        ]:
            report.append(
                {
                    "arm": token,
                    "check": name,
                    "status": status,
                    "detail": detail,
                    "trace": str(trace),
                }
            )

    failed = any(row["status"] == FAIL for row in report)
    return report, not failed


def render(report: List[Dict[str, Any]]) -> str:
    """The report as text, grouped by arm in the order the manifest declared them."""
    lines = ["# Pre-flight — RUN_START against the declared campaign\n"]
    for arm in dict.fromkeys(row["arm"] for row in report):
        lines.append(f"## {arm}")
        for row in [r for r in report if r["arm"] == arm]:
            lines.append(f"  {row['status']:<4} {row['check']:<14} {row['detail']}")
        lines.append("")
    n_fail = sum(1 for row in report if row["status"] == FAIL)
    n_pass = sum(1 for row in report if row["status"] == PASS)
    n_skip = sum(1 for row in report if row["status"] == SKIP)
    lines.append(f"{n_pass} PASS · {n_fail} FAIL · {n_skip} SKIP")
    lines.append(
        "GATE: the campaign starts."
        if n_fail == 0
        else "GATE: the campaign does NOT start."
    )
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", default="results", help="smoke results tree")
    parser.add_argument("--manifest", default="manifest.json")
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[2]),
        help="rv-android root; the corpus list is recomputed from it",
    )
    parser.add_argument(
        "--pushed-properties",
        default=None,
        help="directory holding <arm-token>.properties as pushed, for check 1",
    )
    parser.add_argument("--json", action="store_true", help="emit the report as JSON")
    args = parser.parse_args(argv)

    manifest = json.loads(Path(args.manifest).read_text())
    pushed = Path(args.pushed_properties) if args.pushed_properties else None
    report, ok = run(Path(args.results), manifest, Path(args.repo_root), pushed)
    print(json.dumps(report, indent=2) if args.json else render(report), end="")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
