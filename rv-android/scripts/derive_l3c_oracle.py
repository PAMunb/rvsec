#!/usr/bin/env python3
"""Derive the L3-c control-group oracle from the JVM `-javaagent` baseline.

The dataset ships two AspectJ regimes, not one. The paired regime (L3-b) runs
`ajc`-instrumented APKs in an emulator alongside dexlib2. The other, used here,
compiles the same 23 JCA `.mop` specifications into `JavaMOPAgent.jar` and
attaches it as a plain JVM `-javaagent` while each app's own unit-test suite
runs — no emulator, no dexlib2, same specs, same monitor generator, same apps.

That makes it a control group, and it is the only recorded regime in which
`ErrorType.UnsatisfiedConstraint` exists at all: 43 occurrences here against
zero across the whole dexlib2 campaign. It is the only instrument with power
over the category the inline-truncation defect erases.

Nobody built it to prove this. It is a methodological baseline of the dataset,
which is exactly why it is worth something: it was not designed to confirm the
hypothesis it confirms.

The provenance filter (D-O2)
----------------------------
Two filters are applied, and both narrow rather than widen what the oracle
claims:

1. **`app_producao` only.** `categoria_unit_tests.csv` classifies every
   `(apk, spec, class, method)` tuple as application code, library code,
   Robolectric noise or test code. Only application code can be expected to
   exist in the shipped APK — the `lib` tuples here are photok `*Test` classes
   that will never be in one. Including them would let the oracle demand events
   from sites the Android build does not contain, which is the open question
   design.md left for this script, answered conservatively.

2. **Gate on proved silence.** Absence in the control is evidence only where
   the site was reached under GUI exploration and still emitted nothing. Three
   apps have that: photok, aegis and org.cry.otp. Only their events are gated;
   every other app's are carried in report mode, so the verdict cannot rest on
   an app whose silence might just be an unreached screen.

Presence, never counts
----------------------
The execution regime differs from the campaign's — a project's own unit tests
against GUI exploration — so absolute counts are not comparable. Only the
presence or absence of a `(spec, errorType)` category is.

Sources are read-only and content-addressed. Nothing under the dataset tree is
written by this script.

Usage
-----
    python3 scripts/derive_l3c_oracle.py [--results-dir DIR] [--out-dir DIR]
                                         [--traces-dir DIR]
"""

from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEXLIB2 = REPO_ROOT.parent / "rvsec/rvsec-android/rvsec-instrumentation-dexlib2"

DEFAULT_RESULTS = Path(
    "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv"
    "/ase-journal/dataset/results"
)
DEFAULT_ORACLE_DIR = DEXLIB2 / "validator/oracles"
DEFAULT_TRACES_DIR = DEXLIB2 / "validator/traces"

ORACLE_NAME = "l3c-control"
ADMITTED_CATEGORY = "app_producao"

# Apps whose silence under dexlib2 was proved by joining the campaign's
# coverage against the erased sites: the method ran and emitted nothing.
GATED_APPS = ("photok", "aegis", "org.cry.otp")


def error_type(unique_msg: str) -> str:
    """`class:::method:::spec:::ErrorType:::message` — field 4."""
    parts = unique_msg.split(":::")
    return parts[3] if len(parts) >= 4 else "Unknown"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def is_gated(apk: str) -> bool:
    return any(app in apk for app in GATED_APPS)


def load(control_csv: Path, categories_csv: Path, campaign_csv: Path):
    """Control-group categories after the provenance filter, plus the dexlib2 side."""
    admitted = {
        (r["apk"], r["spec"], r["class"], r["method"])
        for r in csv.DictReader(categories_csv.open())
        if r["categoria"] == ADMITTED_CATEGORY
    }

    control = collections.defaultdict(
        lambda: {"message": "", "apks": set(), "sites": set(), "count": 0, "gated": False})
    dropped = collections.Counter()
    for r in csv.DictReader(control_csv.open()):
        tuple_key = (r["apk"], r["spec"], r["class"], r["method"])
        if tuple_key not in admitted:
            dropped[r["spec"]] += 1
            continue
        key = (r["spec"], error_type(r["unique_msg"]))
        entry = control[key]
        entry["message"] = entry["message"] or r.get("message", "")
        entry["apks"].add(r["apk"])
        entry["sites"].add(f"{r['class']}.{r['method']}")
        entry["count"] += 1
        if is_gated(r["apk"]):
            entry["gated"] = True

    campaign = collections.defaultdict(
        lambda: {"message": "", "sites": set(), "count": 0})
    for r in csv.DictReader(campaign_csv.open()):
        key = (r["spec"], error_type(r["unique_msg"]))
        entry = campaign[key]
        entry["message"] = entry["message"] or r.get("message", "")
        entry["sites"].add(f"{r['class']}.{r['method']}")
        entry["count"] += 1

    return control, campaign, dropped


def write_oracle(path: Path, control, sources) -> None:
    gated = {k: v for k, v in control.items() if v["gated"]}
    lines = [
        f"name: {ORACLE_NAME}",
        "profile: control_group",
        "provenance:",
        "  class: derived_from_independent_weaver",
        "  source_weaver: aspectj_javaagent",
        f"  source_data: {sources['control'][0]}",
        f"  source_sha256: {sources['control'][1]}",
        "  derivation_script: derive_l3c_oracle.py",
        "  source: |",
        "    The JCA specifications compiled into JavaMOPAgent.jar and attached as a",
        "    plain JVM -javaagent while each app's own unit-test suite runs. AspectJ",
        "    weaving, no emulator, no dexlib2. Same 23 .mop specs, same monitor",
        "    generator, same apps as the campaign.",
        "",
        "    Filtered to app_producao tuples per",
        f"    {sources['categories'][0]}",
        f"    (sha256 {sources['categories'][1]}): only application code can be",
        "    expected to exist in the shipped APK. The excluded lib tuples are test",
        "    classes that will never be in one.",
        "",
        f"    Gated on the apps whose dexlib2 silence was proved by coverage join:",
        f"    {', '.join(GATED_APPS)}. Every other app's events are carried in report",
        "    mode, because absence is evidence only where the site was reached.",
        "",
        "    Presence, never counts: the execution regime differs from the campaign's",
        "    (a project's own unit tests against GUI exploration), so absolute",
        "    occurrence counts are not comparable between the two sides.",
        "description: |",
        "  Control-group profile. The only recorded regime in which",
        "  ErrorType.UnsatisfiedConstraint is observable at all, and therefore the",
        "  only oracle with power over the category the inline-truncation defect",
        "  erases.",
        "",
        "  One entry per (spec, errorType) — the granularity TraceComparator matches",
        "  on. Entries below are the gated set; report-mode categories are listed",
        "  under notes.",
        "expected_events:",
    ]
    for i, ((spec, etype), info) in enumerate(sorted(gated.items()), start=1):
        sites = sorted(info["sites"])
        rep = sites[0].rsplit(".", 1)
        lines += [
            f"  - id: {i}",
            f"    spec: {spec}",
            f"    error_type: {etype}",
            f"    location: {{ class: {rep[0]}, method: {rep[1] if len(rep) > 1 else '?'} }}",
            "    expected_message_substring: null",
            f"    observed_sites: {len(sites)}   # documentary; not matched",
            f"    observed_apks: {len(info['apks'])}",
        ]

    report_only = sorted(k for k, v in control.items() if not v["gated"])
    lines += [
        "acceptance:",
        f"  required_event_count: {len(gated)}",
        "  full_coverage_required: true",
        "notes: |",
        "  Report-mode categories (present in the control group, not gated because",
        "  their apps have no coverage-proved silence):",
    ]
    lines += [f"    - {spec}/{etype}" for spec, etype in report_only] or ["    (none)"]
    lines += [
        "",
        "  Both sides available to this oracle are frozen pre-repair recordings, and",
        "  the dexlib2 side comes from a different execution regime than the control.",
        "  Executing it characterises the erased category; it cannot certify the",
        "  repair. A verdict that flips would need a fresh dexlib2 run over these",
        "  apps, which means an emulator session (L3-a) and is out of scope of the",
        "  change that derived this oracle. Any report citing it must say so.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def write_trace(path: Path, events) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    out = []
    for (spec, etype), info in sorted(events.items()):
        detail = (info["message"] or "").replace("\n", " ") or f"{len(info['sites'])} site(s)"
        out.append(f"RVSEC: [{spec}] {etype}: {detail}")
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_ORACLE_DIR)
    ap.add_argument("--traces-dir", type=Path, default=DEFAULT_TRACES_DIR)
    args = ap.parse_args()

    control_csv = args.results_dir / "errors_unit_tests.csv"
    categories_csv = args.results_dir / "categoria_unit_tests.csv"
    campaign_csv = args.results_dir / "errors.csv"
    for label, p in (("control group", control_csv), ("categories", categories_csv),
                     ("campaign", campaign_csv)):
        if not p.is_file():
            raise SystemExit(f"{label} CSV not found at {p}")

    control, campaign, dropped = load(control_csv, categories_csv, campaign_csv)
    sources = {
        "control": (control_csv, sha256(control_csv)),
        "categories": (categories_csv, sha256(categories_csv)),
        "campaign": (campaign_csv, sha256(campaign_csv)),
    }

    args.out_dir.mkdir(parents=True, exist_ok=True)
    oracle_path = args.out_dir / f"{ORACLE_NAME}-oracle.yaml"
    write_oracle(oracle_path, control, sources)

    trace_dir = args.traces_dir / ORACLE_NAME
    write_trace(trace_dir / "ajc.logcat", control)
    write_trace(trace_dir / "dexlib2.logcat", campaign)

    gated = {k: v for k, v in control.items() if v["gated"]}
    missing = set(control) - set(campaign)

    print(f"control-group categories (app_producao)  {len(control)}")
    print(f"  gated ({', '.join(GATED_APPS)})        {len(gated)}")
    print(f"  report mode                            {len(control) - len(gated)}")
    print(f"dropped by the app_producao filter       {sum(dropped.values())} events")
    print(f"campaign (dexlib2) categories            {len(campaign)}")
    print(f"\npresent in the control, absent from the dexlib2 campaign: {len(missing)}")
    for spec, etype in sorted(missing):
        info = control[(spec, etype)]
        flag = "GATED " if info["gated"] else "report"
        print(f"  [{flag}] {spec}/{etype}  "
              f"{info['count']} events, {len(info['apks'])} apk(s), "
              f"{len(info['sites'])} site(s)")
    print(f"\noracle  {oracle_path}")
    print(f"traces  {trace_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
