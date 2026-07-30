#!/usr/bin/env python3
"""gh91 — the validation gate (change task group 3). Exit code, not a checkbox.

Runs against `SA_RERUN_gh91/` **before** anything is copied into the corpus. Every assertion
below is mechanised because the failure modes it guards are all silent: a truncated JSON
parses, a JSON analysed under the wrong key is indistinguishable from a correct one by
inspection, and a narrowed scope that lost the monitored surface still reports success.

    3.1 cardinality   — exactly 30 JSONs, one per row of 30_apks.csv
    3.2 completeness  — every JSON carries the `"complete": true` sentinel
    3.3 key applied   — (a) 0 classes outside Mneut and >0 inside, with the parser's real
                        semantics; (b) the run's log carries the Filter package: line
    3.4 right APK     — the JSON's top-level `package` matches manifest_package
    3.5 MOP surface   — sa_reaches_mop stays True with a non-empty denominator (HARD STOP)
    3.6 delta         — recorded, NOT gated: the denominator change per app

WHY 3.3 NEEDS BOTH HALVES
    GATOR filters by `startsWith` (`RvsecAnalysisClient.isAppClass`), so a run filtered by a
    *narrower* key than intended — `app.pachli.core` where `app.pachli` was meant — still
    yields 0 classes outside `app.pachli` and sails through (a). That is the exact failure
    mode the current corpus exhibits in the five widening apps. The JSON does not record its
    filtering key anywhere; its top-level `package` field is the *manifest* package
    regardless of what was filtered on. The log line is the only record, which is why the
    driver captures GATOR's stdout.

WHY 3.5 IS A HARD STOP
    A narrower scope can push the JCA surface out of the key entirely. That is not fixable
    here and must be reported rather than worked around: it would shrink the paper's 164/163.

Usage:
    uv run python scripts/gh91_gate.py            # all assertions; exit 0 iff all pass
    uv run python scripts/gh91_gate.py --json     # machine-readable per-APK detail

Needs the workspace venv: it imports the real `SignatureNormalizer` rather than
approximating class-name normalisation.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import gh91_sa_rerun as drv  # noqa: E402  (path must be set first)
from gh91_campaign import has_sentinel  # noqa: E402

try:
    from rv_android_core.util.android.signature_normalizer import SignatureNormalizer
except ImportError as exc:  # pragma: no cover - environment problem, not a code path
    raise SystemExit(
        f"cannot import SignatureNormalizer ({exc}). Run this under the workspace venv: "
        f"`uv run python scripts/gh91_gate.py`."
    )

# The predecessor JSONs, for the 3.6 delta only. Read-only: this change never writes here.
STATIC_DIR = drv.DATASET_ROOT / "APKS_INSTRUMENTED_jca_dexlib2_experimento-20260706"

FILTER_LINE_RE = re.compile(r"\[RvsecAnalysisClient\]\s*Filter package:\s*(\S+)")

_NORMALIZER = SignatureNormalizer()


def _classes(raw: dict, key: str) -> tuple[int, int]:
    """(inside, outside) class counts for `key`, with the parser's real semantics.

    Substring match after `normalize_class_name`, not `startswith`:
    `static_analysis_parser.py:_parse_classes` filters with `if package not in normalized`,
    because `code_package` may differ from the manifest package in apps built on a library
    namespace. The gate must assert on what the consumer will actually see.
    """
    inside = outside = 0
    for cls in raw.get("reachability") or []:
        if not isinstance(cls, dict):
            continue
        normalized = _NORMALIZER.normalize_class_name(cls.get("className", ""))
        if key and key in normalized:
            inside += 1
        else:
            outside += 1
    return inside, outside


def _mop_surface(raw: dict, key: str) -> tuple[int, int]:
    """(methods in key, methods with reachesTarget) — 3.5's numerator and denominator."""
    total = reaches = 0
    for cls in raw.get("reachability") or []:
        if not isinstance(cls, dict):
            continue
        normalized = _NORMALIZER.normalize_class_name(cls.get("className", ""))
        if key and key not in normalized:
            continue
        for method in cls.get("methods") or []:
            if not isinstance(method, dict):
                continue
            total += 1
            if method.get("reachesTarget"):
                reaches += 1
    return total, reaches


def _filter_key_from_log(path: Path) -> str | None:
    """The key GATOR actually filtered on, read from its own stdout."""
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    match = FILTER_LINE_RE.search(content)
    return match.group(1) if match else None


def _predecessor(apk: str, mneut: str, detected: str) -> dict:
    """The 3.6 delta baseline. Recorded, never gated.

    Three numbers are reported rather than one, because the predecessor's *applied* key is
    not reliably known: `30_apks.csv` records `org.wikipedia.diff` as that app's
    `detected_package`, but its JSON on disk contains zero classes under `.diff` and was in
    fact filtered by `org.wikipedia.feed` (design R3). Comparing against a key that was never
    applied would manufacture a delta.
    """
    path = STATIC_DIR / f"{apk}.json"
    if not path.is_file():
        return {"predecessor_present": False}
    raw = drv.sa_runner._load_json(path)
    if raw is None:
        return {"predecessor_present": False}
    total = len(raw.get("reachability") or [])
    under_mneut, _ = _classes(raw, mneut)
    under_detected, _ = _classes(raw, detected) if detected else (0, 0)
    return {
        "predecessor_present": True,
        "prev_classes_total": total,
        "prev_classes_under_mneut": under_mneut,
        "prev_classes_under_detected": under_detected,
    }


def check(rows: list[dict]) -> tuple[list[dict], dict[str, list[str]]]:
    failures: dict[str, list[str]] = {k: [] for k in ("3.2", "3.3a", "3.3b", "3.4", "3.5")}
    results = []

    for row in rows:
        apk = row["apk"].strip()
        mneut = row["Mneut"].strip()
        manifest_package = row["manifest_package"].strip()
        detected = row.get("detected_package", "").strip()

        json_path = drv.OUT_DIR / f"{apk}.json"
        log_path = drv.OUT_DIR / "logs" / f"{apk}.log"
        entry: dict = {"apk": apk, "Mneut": mneut, "json": str(json_path)}

        if not json_path.is_file():
            entry["error"] = "JSON absent"
            for key in failures:
                failures[key].append(apk)
            results.append(entry)
            continue

        # 3.2 — the sentinel, not "it parses". Bracket recovery repairs a truncated file, so
        # a partial JSON would otherwise pass every downstream check unnoticed.
        entry["complete"] = has_sentinel(json_path)
        if not entry["complete"]:
            failures["3.2"].append(apk)

        raw = drv.sa_runner._load_json(json_path)
        if raw is None:
            entry["error"] = "unparseable"
            for key in ("3.3a", "3.4", "3.5"):
                failures[key].append(apk)
            results.append(entry)
            continue

        # 3.3(a)
        inside, outside = _classes(raw, mneut)
        entry["classes_in_key"] = inside
        entry["classes_outside_key"] = outside
        if outside != 0 or inside == 0:
            failures["3.3a"].append(apk)

        # 3.3(b) — the only record of the key that was actually applied.
        applied = _filter_key_from_log(log_path)
        entry["filter_key_logged"] = applied
        if applied != mneut:
            failures["3.3b"].append(apk)

        # 3.4 — guards against having analysed the wrong APK. `package` is the MANIFEST
        # package regardless of what was filtered on, which is exactly why it cannot serve
        # as evidence for 3.3.
        entry["json_package"] = raw.get("package")
        if entry["json_package"] != manifest_package:
            failures["3.4"].append(apk)

        # 3.5 — HARD STOP.
        methods, reaches = _mop_surface(raw, mneut)
        entry["methods_in_key"] = methods
        entry["methods_reaches_mop"] = reaches
        entry["sa_reaches_mop"] = reaches > 0
        if reaches == 0:
            failures["3.5"].append(apk)

        # 3.6 — recorded, not gated.
        entry.update(_predecessor(apk, mneut, detected))
        results.append(entry)

    return results, failures


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", action="store_true", help="emit per-APK detail as JSON")
    args = ap.parse_args()

    with drv.APKS_CSV.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    # 3.1 — cardinality. Globbed at the top level only: the smoke writes to a sibling
    # directory precisely so this count stays exactly 30 however it is taken.
    produced = sorted(p.name for p in drv.OUT_DIR.glob("*.json"))
    expected = sorted(f"{r['apk'].strip()}.json" for r in rows)
    cardinality_ok = produced == expected

    results, failures = check(rows)

    if args.json:
        print(json.dumps({
            "cardinality_ok": cardinality_ok,
            "expected": len(expected),
            "produced": len(produced),
            "failures": failures,
            "apks": results,
        }, indent=2, sort_keys=True))
    else:
        print(f"gh91 validation gate — {drv.OUT_DIR}\n")
        status = "PASS" if cardinality_ok else "FAIL"
        print(f"  3.1 cardinality        {status}  "
              f"({len(produced)} JSONs produced, {len(expected)} expected)")
        if not cardinality_ok:
            for name in sorted(set(expected) - set(produced)):
                print(f"        missing: {name}")
            for name in sorted(set(produced) - set(expected)):
                print(f"        unexpected: {name}")
        labels = {
            "3.2": 'completeness ("complete": true)',
            "3.3a": "key applied (classes)",
            "3.3b": "key applied (Filter package: line)",
            "3.4": "right APK (manifest package)",
            "3.5": "MOP surface preserved (HARD STOP)",
        }
        for key in ("3.2", "3.3a", "3.3b", "3.4", "3.5"):
            bad = failures[key]
            mark = "PASS" if not bad else "FAIL"
            print(f"  {key:<4} {labels[key]:<35} {mark}"
                  + (f"  ({len(bad)}): {', '.join(sorted(bad))}" if bad else ""))

        print("\n  3.6 denominator delta (recorded, not gated)")
        print(f"      {'apk':45} {'prev(Mneut)':>12} {'prev(det)':>10} {'new':>8}")
        for entry in results:
            if not entry.get("predecessor_present"):
                continue
            print(f"      {entry['apk']:45} {entry['prev_classes_under_mneut']:>12} "
                  f"{entry['prev_classes_under_detected']:>10} "
                  f"{entry.get('classes_in_key', 0):>8}")

    ok = cardinality_ok and not any(failures.values())
    if not args.json:
        print(f"\n{'GATE PASSED' if ok else 'GATE FAILED'} — "
              f"{'group 4 may start' if ok else 'nothing may be copied into the corpus'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
