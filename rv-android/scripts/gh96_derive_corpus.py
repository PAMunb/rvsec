#!/usr/bin/env python3
"""
One-shot batch derivation over the pinned corpus (gh96, tasks 7.1/7.2).

Runs `derive_mop_artifact.derive()` over every `.apk.json` of
`<workspace>/rvsec-dataset/static_analysis/` and reports, per relocated rule, how
many apps actually exercise it. A rule no app exercises is not covered by the
corpus, so its coverage has to move to a synthetic fixture — the driver fails in
that case rather than letting the gate report a green it did not earn.

This does not replace the JVM equivalence gate (tasks 7.3-7.6), which compares the
old parser on the raw full JSON against the new parser on the derived artifact and
needs the `ape` side's stage-7 reader. What it does establish is that the generator
survives 345 real producer documents with no crash and no refusal, and that the
per-rule exercise counts match what the change measured during exploration.

Delete once the equivalence gate is green (P3); the recorded results survive in the
change's artifacts.

    uv run python scripts/gh96_derive_corpus.py [--corpus DIR] [--out DIR]
"""

import argparse
import json
import os
import sys
import time

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        os.pardir,
        "modules",
        "aperv-tool",
        "src",
    ),
)

from aperv_tool.tools.aperv.derive_mop_artifact import (  # noqa: E402
    DerivationError,
    derive,
    digest_of,
    serialize_canonical,
)

DEFAULT_CORPUS = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    os.pardir,
    os.pardir,
    os.pardir,
    "rvsec-dataset",
    "static_analysis",
)

# The four rules whose coverage the corpus is supposed to establish. Each maps to a
# predicate over one derived artifact.
EXERCISE_RULES = {
    "flagged_widget_dropped_for_empty_id": lambda a: a["stats"]["droppedFlaggedNoId"]
    > 0,
    "d8_synthetic_lambda_recovered": lambda a: a["stats"]["recovered"] > 0,
    "dialog_rekeyed_or_orphaned": lambda a: a["stats"]["orphanDialogs"] > 0
    or a["_hasDialog"],
    "augmented_set_differs": lambda a: len(a["mopActivitiesAugmented"])
    > len(a["mopActivities"]),
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", default=DEFAULT_CORPUS)
    parser.add_argument("--out", default=None, help="write one .mop.json per app here")
    args = parser.parse_args()

    corpus = os.path.abspath(args.corpus)
    files = sorted(f for f in os.listdir(corpus) if f.endswith(".apk.json"))
    if not files:
        print(f"FAIL: no .apk.json under {corpus}", file=sys.stderr)
        return 2
    if args.out:
        os.makedirs(args.out, exist_ok=True)

    exercised = {rule: [] for rule in EXERCISE_RULES}
    failures = []
    source_bytes = artifact_bytes = 0
    totals = {}
    started = time.time()

    for index, name in enumerate(files, start=1):
        path = os.path.join(corpus, name)
        try:
            with open(path, "rb") as handle:
                raw = handle.read()
            document = json.loads(raw)
            artifact = derive(document, source_file=name, source_digest=digest_of(raw))
            payload = serialize_canonical(artifact)
        except (DerivationError, json.JSONDecodeError, OSError) as error:
            failures.append((name, f"{type(error).__name__}: {error}"))
            continue

        source_bytes += len(raw)
        artifact_bytes += len(payload)
        for key, value in artifact["stats"].items():
            totals[key] = totals.get(key, 0) + value

        # A DIALOG window that merged cleanly leaves no counter behind, so the rule's
        # exercise has to be read from the source document rather than from stats.
        # The probe travels beside the artifact rather than inside it, so nothing
        # non-wire is ever written out.
        windows = document.get("windows")
        probe = dict(artifact)
        probe["_hasDialog"] = any(
            isinstance(w, dict) and w.get("type") == "DIALOG"
            for w in (windows if isinstance(windows, list) else [])
        )
        for rule, predicate in EXERCISE_RULES.items():
            if predicate(probe):
                exercised[rule].append(name)

        if args.out:
            with open(
                os.path.join(args.out, name.replace(".json", ".mop.json")), "wb"
            ) as out:
                out.write(payload)
        if index % 50 == 0:
            print(f"  … {index}/{len(files)}", file=sys.stderr)

    elapsed = time.time() - started
    print(f"\nderived {len(files) - len(failures)}/{len(files)} apps in {elapsed:.1f}s")
    if failures:
        # Report before the size arithmetic: with every app failing, both totals are
        # zero and a ZeroDivisionError would hide the reason the run failed.
        print(f"\nFAIL: {len(failures)} apps did not derive:")
        for name, reason in failures[:20]:
            print(f"  {name}: {reason}")
        return 1
    print(
        f"bytes: {source_bytes / 1e6:.1f} MB source -> "
        f"{artifact_bytes / 1e6:.2f} MB artifact "
        f"({100 * artifact_bytes / source_bytes:.2f}% of source, "
        f"{source_bytes / artifact_bytes:.0f}x reduction)"
    )
    print("\naggregate stats over the corpus:")
    for key in sorted(totals):
        print(f"  {key:22s} {totals[key]:>12,}")

    print("\nper-rule exercise counts (apps):")
    for rule in EXERCISE_RULES:
        count = len(exercised[rule])
        print(f"  {rule:38s} {count:>4d}" + ("" if count else "   <-- NOT EXERCISED"))

    dry = [rule for rule, apps in exercised.items() if not apps]
    if dry:
        print(
            "\nFAIL: no corpus app exercises "
            + ", ".join(dry)
            + " — record the substitution and move that rule's coverage to a "
            "synthetic fixture in the permanent suite."
        )
        return 1

    print("\nOK: every app derived and every rule is exercised.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
