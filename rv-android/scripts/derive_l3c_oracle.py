#!/usr/bin/env python3
"""Derive the L3-c control-group oracles from the JVM `-javaagent` runs.

The JCA specifications compiled into `JavaMOPAgent.jar` and attached as a plain
JVM `-javaagent` while each app's own unit-test suite runs: AspectJ weaving, no
emulator, no dexlib2. Same 23 `.mop` specs, same monitor generator, same apps as
the campaign — a different weaver and a different execution regime.

Why this profile exists
-----------------------
It is the only recorded regime in which `ErrorType.UnsatisfiedConstraint` is
observable at all, and therefore the only oracle with any power over the
category the inline-truncation defect erases. In the GUI campaign that category
is absent from both variants, because the erased events live in application code
GUI exploration does not reach.

Which records enter (D-O2)
--------------------------
Only `app_producao` tuples, per `categoria_unit_tests.csv`. The excluded `lib`
tuples are `*Test` classes that no Android build contains; admitting them would
let the oracle demand events from sites the APK does not have, which is a false
negative manufactured by the oracle rather than observed in the pipeline. The
filter keeps 138 of 298 control rows, over 12 apps.

The frame-form repair is a guard here, not a transformation
-----------------------------------------------------------
Unlike `events_fair.csv`, these sources arrive with zero frame-form rows — the
upstream summarizer's fallback never fired on them. The same repair is still
applied, but as an assertion: a non-zero count means the upstream defect
reappeared between derivations, and the run aborts rather than quietly repairing
data whose provenance has changed underneath it.

Output shape
------------
One oracle per APK, `<apkBaseName>-oracle.yaml`, with its trace pair under
`validator/traces/<apkBaseName>/` (D-O5).

Usage
-----
    python3 scripts/derive_l3c_oracle.py [--results-dir DIR] [--out-dir DIR]
                                         [--traces-dir DIR]
"""

from __future__ import annotations

import argparse
import collections
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from rv_oracle_common import (  # noqa: E402
    apk_base_name, error_type, oracle_events_block, repair_frame_form, sha256,
    write_trace,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
DEXLIB2 = REPO_ROOT.parent / "rvsec/rvsec-android/rvsec-instrumentation-dexlib2"

DEFAULT_RESULTS = Path(
    "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv"
    "/ase-journal/dataset/results"
)
DEFAULT_ORACLE_DIR = DEXLIB2 / "validator/oracles"
DEFAULT_TRACES_DIR = DEXLIB2 / "validator/traces"

PROFILE = "control_group"
ADMITTED_CATEGORY = "app_producao"

# Apps whose silence under dexlib2 was proved by joining the campaign's
# coverage against the erased sites: the method ran and emitted nothing.
GATED_APPS = ("photok", "aegis", "org.cry.otp")


def is_gated(apk: str) -> bool:
    return any(app in apk for app in GATED_APPS)


def read_repaired(path: Path) -> tuple[list[dict], int]:
    """Read a CSV, applying the frame-form repair and counting what it touched."""
    rows = list(csv.DictReader(path.open()))
    repaired = 0
    for r in rows:
        r.setdefault("location", "")
        if repair_frame_form(r):
            repaired += 1
    return rows, repaired


def load(control_csv: Path, categories_csv: Path, campaign_csv: Path):
    """Control-group misuses after the provenance filter, plus the dexlib2 side."""
    admitted = {
        (r["apk"], r["spec"], r["class"], r["method"])
        for r in csv.DictReader(categories_csv.open())
        if r["categoria"] == ADMITTED_CATEGORY
    }

    control_rows, control_repairs = read_repaired(control_csv)
    campaign_rows, campaign_repairs = read_repaired(campaign_csv)
    # The guard (see the module docstring): these sources are expected to be
    # clean, so any repair at all means the upstream defect came back and the
    # derivation is reading data it was not written against.
    if control_repairs or campaign_repairs:
        raise SystemExit(
            f"frame-form rows found where none were expected: {control_repairs} in "
            f"{control_csv.name}, {campaign_repairs} in {campaign_csv.name}. These "
            f"sources arrive already repaired; a non-zero count means the upstream "
            f"defect reappeared. Fix it upstream rather than repairing here.")

    dropped = collections.Counter()
    control: dict = collections.defaultdict(dict)
    for r in control_rows:
        if (r["apk"], r["spec"], r["class"], r["method"]) not in admitted:
            dropped[r["spec"]] += 1
            continue
        etype = error_type(r["unique_msg"])
        control[r["apk"]].setdefault((r["spec"], r["class"], r["method"], etype), {
            "spec": r["spec"], "class": r["class"], "method": r["method"],
            "error_type": etype, "message": r.get("message", ""),
            "location": r.get("location") or "",
        })

    campaign: dict = collections.defaultdict(dict)
    for r in campaign_rows:
        etype = error_type(r["unique_msg"])
        campaign[r["apk"]].setdefault((r["spec"], r["class"], r["method"], etype), {
            "spec": r["spec"], "class": r["class"], "method": r["method"],
            "error_type": etype, "message": r.get("message", ""),
            "location": r.get("location") or "",
        })

    return control, campaign, dropped


def write_oracle(path: Path, apk: str, events, sources, misuse_count: int,
                 gated: bool) -> None:
    lines = [
        f"name: {apk_base_name(apk)}",
        f"profile: {PROFILE}",
        f"apk: {apk}",
        f"gated: {'true' if gated else 'false'}",
        "provenance:",
        "  class: derived_from_independent_weaver",
        "  source_weaver: aspectj_javaagent",
        f"  source_data: {sources['control'][0]}",
        f"  source_sha256: {sources['control'][1]}",
        "  derivation_script: derive_l3c_oracle.py",
        "  source: |",
        "    The JCA specifications compiled into JavaMOPAgent.jar and attached as a",
        "    plain JVM -javaagent while this app's own unit-test suite runs. AspectJ",
        "    weaving, no emulator, no dexlib2. Same 23 .mop specs, same monitor",
        "    generator, same app as the campaign.",
        "",
        "    Filtered to app_producao tuples per",
        f"    {sources['categories'][0]}",
        f"    (sha256 {sources['categories'][1]}): only application code can be",
        "    expected to exist in the shipped APK. The excluded lib tuples are test",
        "    classes that will never be in one.",
        "",
        "    Presence, never counts: the execution regime differs from the campaign's",
        "    (a project's own unit tests against GUI exploration), so absolute",
        "    occurrence counts are not comparable between the two sides.",
        "  repair: |",
        "    None applied. Unlike events_fair.csv, this source carries zero",
        "    frame-form rows; the derivation asserts that rather than assuming it, and",
        "    aborts if the upstream defect reappears.",
        "description: |",
        "  Control-group profile for a single APK. The only recorded regime in which",
        "  ErrorType.UnsatisfiedConstraint is observable at all, and therefore the",
        "  only oracle with power over the category the inline-truncation defect",
        "  erases.",
        "",
        f"  {misuse_count} unique misuse(s) at the article's key (apk, class, method,",
        f"  spec), listed below as {len(events)} expected event(s): a site that produced",
        "  two error types is one misuse and two events, because the comparator scores",
        "  per event and drops an event that declares no error_type.",
    ]
    if gated:
        lines += [
            "",
            "  GATED. This app's silence under dexlib2 was proved by joining the",
            "  campaign's coverage against the erased sites: the method ran and emitted",
            "  nothing. Absence is evidence here.",
        ]
    else:
        lines += [
            "",
            "  REPORT MODE. This app has no coverage-proved silence, so an event absent",
            "  from the dexlib2 side may mean the site was never reached rather than",
            "  that the weaver dropped it. Its verdict is carried, not gating.",
        ]
    lines += oracle_events_block(events)
    lines += [
        "acceptance:",
        f"  unique_misuse_count: {misuse_count}",
        f"  required_event_count: {len(events)}",
        f"  full_coverage_required: {'true' if gated else 'false'}",
        "notes: |",
        "  Both sides available to this oracle are frozen pre-repair recordings, and",
        "  the dexlib2 side comes from a different execution regime than the control.",
        "  Executing it characterises the erased category; it cannot certify the",
        "  repair. A verdict that flips would need a fresh dexlib2 run over these",
        "  apps, which means an emulator session (L3-a) and is out of scope of the",
        "  change that derived this oracle. Any report citing it must say so.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


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

    all_misuses: set = set()
    unsatisfied: dict = collections.defaultdict(set)
    gated_apks = 0

    print(f"control-group apps (app_producao)   {len(control)}")
    print(f"dropped by the app_producao filter  {sum(dropped.values())} rows")
    print()

    for apk in sorted(control):
        base = apk_base_name(apk)
        events = list(control[apk].values())
        misuses = {(apk, e["spec"], e["class"], e["method"]) for e in events}
        all_misuses |= misuses
        gated = is_gated(apk)
        gated_apks += 1 if gated else 0
        for e in events:
            if e["error_type"] == "UnsatisfiedConstraint":
                unsatisfied[e["spec"]].add((apk, e["class"], e["method"]))

        write_oracle(args.out_dir / f"{base}-oracle.yaml", apk, events, sources,
                     len(misuses), gated)
        trace_dir = args.traces_dir / base
        write_trace(trace_dir / "ajc.logcat", events)
        write_trace(trace_dir / "dexlib2.logcat", campaign.get(apk, {}).values())
        flag = "GATED " if gated else "report"
        print(f"  [{flag}] {base:40} {len(misuses):3} misuses / "
              f"{len(events):3} events   dexlib2={len(campaign.get(apk, {})):3}")

    print()
    print(f"unique misuses (control, app_producao)  {len(all_misuses)}")
    print(f"  over apps                            {len(control)} "
          f"({gated_apks} gated)")
    print("UnsatisfiedConstraint — the category the truncation erases, "
          "observable only here:")
    for spec, sites in sorted(unsatisfied.items()):
        print(f"    {spec:24} {len(sites)} unique misuse(s)")
    print(f"\noracles  {args.out_dir}")
    print(f"traces   {args.traces_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
