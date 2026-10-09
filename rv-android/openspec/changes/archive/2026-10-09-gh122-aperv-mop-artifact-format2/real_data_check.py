"""Task 5.1 of gh122: derive a sample of gh120 `.apk.json` documents in memory.

Read-only. Takes a directory of `.apk.json` files and writes nothing next to them:
every artifact is derived in memory and only the report goes to stdout.

For each document it reports what task 5.1 asks:
- `targets`, which must be above 0 for a gh120 document;
- the INV-DRV-10 violations over every pair list: widget and handler `dist` lists
  hold only pairs at `d <= DIST_WEIGHED_MAX`, `activityDist` lists at most `DIST_K`
  pairs, and every list is non-empty, sorted by `(d, i)`, with distinct in-range
  indices;
- the size of `mopActivitiesAugmented` with and without the source-3 constructor
  exclusion. "Without" re-derives with `CONSTRUCTOR_METHOD_NAMES` emptied, which is
  the only thing the exclusion reads;
- the number of `handlers` records and how many carry `dist`;
- the share of flagged emitted widgets that carry a `click` pair, and the share
  that carry a pair on at least one of their flagged events. The second is the
  fairer reading: a widget flagged only on `entertext` or `select` has its pairs
  under that event and none under `click`;
- the reaching methods the producer left without `targetDistances`, which no
  derivation can give a distance.

Usage:
    uv run python real_data_check.py <dir-with-apk.json-copies>
"""

import json
import os
import sys

from aperv_tool.tools.aperv import derive_mop_artifact as dm


def _pair_lists(artifact):
    """Every pair list of the artifact: a label, the list, and whether it is weighed.

    Widget and handler lists are the ones the jar weighs, cut at `d <= 3`;
    `activityDist` lists are cut to the three nearest.
    """
    for activity, widgets in artifact["widgets"].items():
        for short_id, widget in widgets.items():
            for event, pairs in widget.get("dist", {}).items():
                yield f"widgets.{activity}.{short_id}.{event}", pairs, True
    for activity, pairs in artifact["activityDist"].items():
        yield f"activityDist.{activity}", pairs, False
    for class_name, record in artifact["handlers"].items():
        for event, pairs in record.get("dist", {}).items():
            yield f"handlers.{class_name}.{event}", pairs, True


def _drv10_violations(artifact):
    """Labels of the pair lists that break INV-DRV-10."""
    targets = artifact["targets"]
    bad = []
    for label, pairs, weighed in _pair_lists(artifact):
        indices = [i for i, _ in pairs]
        keys = [(d, i) for i, d in pairs]
        cut_holds = (
            all(d <= dm.DIST_WEIGHED_MAX for _, d in pairs)
            if weighed
            else len(pairs) <= dm.DIST_K
        )
        if (
            not pairs
            or not cut_holds
            or len(set(indices)) != len(indices)
            or keys != sorted(keys)
            or not all(0 <= i < targets and d >= 0 for i, d in pairs)
        ):
            bad.append(label)
    return bad


def _augmented_without_exclusion(document):
    saved = dm.CONSTRUCTOR_METHOD_NAMES
    dm.CONSTRUCTOR_METHOD_NAMES = frozenset()
    try:
        return len(dm.derive(document)["mopActivitiesAugmented"])
    finally:
        dm.CONSTRUCTOR_METHOD_NAMES = saved


def main(directory):
    names = sorted(n for n in os.listdir(directory) if n.endswith(".apk.json"))
    header = (
        "apk | targets | DRV-10 bad | aug (excl) | aug (no excl) | mopActivities | "
        "handlers | handlers w/ dist | flagged widgets | w/ click pair | "
        "w/ pair on a flagged event | reaching methods | reaching w/o pairs"
    )
    print(header)
    print("|".join(["---"] * 13))
    totals = {
        "flagged": 0,
        "click": 0,
        "any": 0,
        "handlers": 0,
        "handlers_dist": 0,
        "reaching": 0,
        "reaching_no_pairs": 0,
    }
    all_bad = 0
    zero_targets = []
    for name in names:
        path = os.path.join(directory, name)
        with open(path, encoding="utf-8") as source:
            document = json.load(source)
        artifact = dm.derive(
            document, source_file=name, source_digest=dm.digest_of_file(path)
        )

        bad = _drv10_violations(artifact)
        all_bad += len(bad)
        if artifact["targets"] == 0:
            zero_targets.append(name)

        flagged = [
            widget
            for widgets in artifact["widgets"].values()
            for widget in widgets.values()
            if any(value != dm.MOP_NONE for value in widget["mop"].values())
        ]
        with_click = sum(1 for w in flagged if dm.CLICK_EVENT_TYPE in w.get("dist", {}))
        with_any = sum(
            1
            for w in flagged
            if any(
                value != dm.MOP_NONE and event in w.get("dist", {})
                for event, value in w["mop"].items()
            )
        )
        reaching = [
            method
            for entry in document.get("reachability") or []
            for method in entry.get("methods") or []
            if method.get("reachesTarget") is True
            or method.get("directlyReachesTarget") is True
        ]
        reaching_no_pairs = sum(1 for m in reaching if not m.get("targetDistances"))
        handlers = artifact["handlers"]
        handlers_dist = sum(1 for r in handlers.values() if "dist" in r)

        totals["flagged"] += len(flagged)
        totals["click"] += with_click
        totals["any"] += with_any
        totals["reaching"] += len(reaching)
        totals["reaching_no_pairs"] += reaching_no_pairs
        totals["handlers"] += len(handlers)
        totals["handlers_dist"] += handlers_dist

        print(
            f"{name} | {artifact['targets']} | {len(bad)} | "
            f"{len(artifact['mopActivitiesAugmented'])} | "
            f"{_augmented_without_exclusion(document)} | "
            f"{len(artifact['mopActivities'])} | {len(handlers)} | {handlers_dist} | "
            f"{len(flagged)} | {with_click} | {with_any} | {len(reaching)} | "
            f"{reaching_no_pairs}"
        )

    print()
    print(f"documents: {len(names)}")
    print(f"documents with targets == 0: {len(zero_targets)} {zero_targets}")
    print(f"INV-DRV-10 violations: {all_bad}")
    print(f"handlers: {totals['handlers']}, with dist: {totals['handlers_dist']}")
    flagged = totals["flagged"] or 1
    print(
        f"flagged emitted widgets: {totals['flagged']}, with a click pair: "
        f"{totals['click']} ({totals['click'] / flagged:.1%}), with a pair on a "
        f"flagged event: {totals['any']} ({totals['any'] / flagged:.1%})"
    )
    print(
        f"reaching methods: {totals['reaching']}, without targetDistances: "
        f"{totals['reaching_no_pairs']}"
    )


if __name__ == "__main__":
    main(sys.argv[1])
