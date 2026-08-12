"""Verify the corrected parser against the 162 artefacts of the Estudo 03 corpus.

This is the evidence the change rests on, re-derived from the artefacts rather
than quoted. It answers three questions, offline, without an emulator or a run:

1. Does the parsed universe equal the artefact's own ``reachability`` member?
   (INV-ANA-59 — the denominator is the producer's, whole.)
2. Do the applications built with ``applicationIdSuffix`` — the ones the old
   filter emptied — now report a non-zero denominator? (The reason for gh102.)
3. Does the new ACTIVITY rule keep deciding what the producer key decided?
   (INV-ANA-60 / design D2 — the regression guard, since this is the one filter
   that carries real weight.)

The "before" column is computed here by replaying the deleted filter
(``key not in class_name``) against the same artefacts, so the comparison is
against what the old code did, not against a remembered number.

Run:
    uv run python openspec/changes/gh102-artifact-scoped-parse/verify_corpus.py
"""

import json
import os
import sys
from collections import namedtuple

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "..",
        "modules",
        "rv-static-analysis",
        "src",
    ),
)

from rv_static_analysis.parser.static.static_analysis_parser import (  # noqa: E402
    StaticAnalysisParser,
)

CORPUS = (
    "/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/"
    "APKS_INSTRUMENTED_jca_dexlib2_experimento-FINAL_selected162"
)

Row = namedtuple(
    "Row",
    "apk declared classes_before classes_after methods_before methods_after "
    "act_before act_after reach_len suffix",
)


def normalize(name):
    """Mirror SignatureNormalizer for the replayed old filter (inner classes)."""
    return name


def producer_key(declared, reach_names):
    """The largest dotted prefix of the applicationId that matches a class.

    Reproduces the ``codePackage`` GATOR was invoked with in 162/162 of the
    corpus (§7.5 of the handoff). Used here only to reconstruct the *old*
    behaviour and the key-based ACTIVITY decision it implied — it is an audit
    device, deliberately not part of the shipped code.
    """
    parts = declared.split(".")
    for n in range(len(parts), 0, -1):
        cand = ".".join(parts[:n])
        if any(cand in c for c in reach_names):
            return cand
    return declared


def main():
    parser = StaticAnalysisParser()
    files = sorted(f for f in os.listdir(CORPUS) if f.endswith(".apk.json"))
    if not files:
        sys.exit(f"no artefacts under {CORPUS}")

    rows = []
    for fname in files:
        path = os.path.join(CORPUS, fname)
        raw = json.load(open(path))
        reach = raw.get("reachability") or []
        reach_names = [c.get("className", "") for c in reach]
        declared = raw.get("package", "")

        # After: the shipped parser.
        data = parser.parse_file(path)
        classes_after = len(data.classes.classes)
        methods_after = len(data.classes.methods)
        act_after = sum(1 for w in data.windows.windows if w.type.name == "ACTIVITY")

        # Before: replay the deleted filter with the declared applicationId,
        # which is what App.code_package returns since gh98.
        kept = [c for c in reach if declared and declared in c.get("className", "")]
        classes_before = len(kept)
        methods_before = sum(len(c.get("methods") or []) for c in kept)
        # The old ACTIVITY filter tested the key only, not class membership.
        act_before = sum(
            1
            for w in (raw.get("windows") or [])
            if w.get("type", "ACTIVITY") == "ACTIVITY"
            and declared
            and declared in w.get("name", "")
        )

        # The key-based ACTIVITY decision under the *producer's* key — the
        # decision the new membership rule must reproduce (design D2).
        key = producer_key(declared, reach_names)
        act_by_key = sum(
            1
            for w in (raw.get("windows") or [])
            if w.get("type", "ACTIVITY") == "ACTIVITY" and key in w.get("name", "")
        )

        rows.append(
            (
                Row(
                    apk=fname[: -len(".apk.json")],
                    declared=declared,
                    classes_before=classes_before,
                    classes_after=classes_after,
                    methods_before=methods_before,
                    methods_after=methods_after,
                    act_before=act_before,
                    act_after=act_after,
                    reach_len=len(reach),
                    suffix=(declared not in " ".join(reach_names[:1]) and classes_before == 0),
                ),
                act_by_key,
            )
        )

    # --- 4.2: parsed classes == reachability length, for all 162 ---
    mismatched = [r.apk for r, _ in rows if r.classes_after != r.reach_len]
    # --- 4.2: the previously-empty applications recover a denominator ---
    was_zero = [r for r, _ in rows if r.classes_before == 0]
    still_zero = [r.apk for r in was_zero if r.classes_after == 0]
    # --- 4.3: ACTIVITY decision agrees with the producer key, for all 162 ---
    diverged = [(r.apk, r.act_after, k) for r, k in rows if r.act_after != k]
    total_act = sum(r.act_after for r, _ in rows)
    truncated = [
        (r.apk, r.classes_before, r.classes_after)
        for r, _ in rows
        if 0 < r.classes_before < r.classes_after
    ]

    print(f"artefacts parsed: {len(rows)}")
    print()
    print("INV-ANA-59  parsed classes == len(reachability)")
    print(f"  mismatches: {len(mismatched)} {mismatched[:5]}")
    print()
    print("gh102       applications the old filter emptied")
    print(f"  zero-denominator before: {len(was_zero)}")
    print(f"  still zero after:        {len(still_zero)} {still_zero[:5]}")
    print()
    print("gh102       applications the old filter truncated (non-zero but short)")
    print(f"  truncated: {len(truncated)}")
    for apk, b, a in sorted(truncated, key=lambda t: t[1] - t[2])[:8]:
        print(f"    {apk:44s} {b:6d} -> {a:6d}")
    print()
    print("INV-ANA-60  ACTIVITY decision vs the producer key (design D2)")
    print(f"  activities admitted: {total_act}")
    print(f"  divergences:         {len(diverged)} {diverged[:5]}")
    print()

    ok = not mismatched and not still_zero and not diverged
    print("RESULT:", "PASS" if ok else "FAIL")

    out = os.path.join(os.path.dirname(__file__), "corpus_verification.csv")
    with open(out, "w") as fh:
        fh.write(
            "apk,declared_package,classes_before,classes_after,"
            "methods_before,methods_after,activities_before,activities_after\n"
        )
        for r, _ in rows:
            fh.write(
                f"{r.apk},{r.declared},{r.classes_before},{r.classes_after},"
                f"{r.methods_before},{r.methods_after},{r.act_before},{r.act_after}\n"
            )
    print("per-APK table:", out)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
