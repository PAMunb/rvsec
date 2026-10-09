"""Reaching methods with no `targetDistances`, split by Compose and View-only apps.

Read-only follow-up to task 5.1, raised by the gh121 session: on parceltracker,
19.6 % of the reaching methods carry no `targetDistances`, so its stamped Compose
handlers reach the device flagged and with no distance. This script measures the
same thing over a directory of `.apk.json` copies and writes nothing next to them.

An app counts as Compose when any `reachability[]` signature takes an
`androidx.compose.runtime.Composer` parameter, which every compiled `@Composable`
function does.

For each document it reports:
- the reaching methods and those without `targetDistances`;
- the reaching handler methods (the `handlers` table's methods, D4) and those
  without `targetDistances`;
- the `handlers` records with a flagged event and no pair for it;
- the flagged emitted widgets and those with no pair on any flagged event.

Usage:
    uv run python reach_without_distance.py <dir-with-apk.json-copies>
"""

import json
import os
import sys

from aperv_tool.tools.aperv import derive_mop_artifact as dm

COMPOSER_TYPE = "androidx.compose.runtime.Composer"


def _reaching(method):
    return (
        method.get("reachesTarget") is True
        or method.get("directlyReachesTarget") is True
    )


def _flagged_without_pair(records):
    """Records (widgets or handlers) with a flagged event that carries no pair."""
    return sum(
        1
        for record in records
        if any(
            value != dm.MOP_NONE and event not in record.get("dist", {})
            for event, value in record["mop"].items()
        )
    )


def _measure(document):
    methods = [
        method
        for entry in document.get("reachability") or []
        for method in entry.get("methods") or []
        if isinstance(method, dict)
    ]
    signatures = [m.get("signature") or "" for m in methods]
    reaching = [m for m in methods if _reaching(m)]
    handler_methods = [
        m for m in reaching if dm._handler_events(m.get("signature") or "")
    ]
    artifact = dm.derive(document)
    flagged_widgets = [
        widget
        for widgets in artifact["widgets"].values()
        for widget in widgets.values()
        if any(value != dm.MOP_NONE for value in widget["mop"].values())
    ]
    flagged_handlers = [
        record
        for record in artifact["handlers"].values()
        if any(value != dm.MOP_NONE for value in record["mop"].values())
    ]
    return {
        "compose": any(COMPOSER_TYPE in s for s in signatures),
        "reaching": len(reaching),
        "reaching_np": sum(1 for m in reaching if not m.get("targetDistances")),
        "handler_m": len(handler_methods),
        "handler_m_np": sum(1 for m in handler_methods if not m.get("targetDistances")),
        "handlers_flagged": len(flagged_handlers),
        "handlers_flagged_np": _flagged_without_pair(flagged_handlers),
        "widgets_flagged": len(flagged_widgets),
        "widgets_flagged_np": _flagged_without_pair(flagged_widgets),
    }


def _share(part, whole):
    return f"{part}/{whole} ({part / whole:.1%})" if whole else f"{part}/0"


def main(directory):
    names = sorted(n for n in os.listdir(directory) if n.endswith(".apk.json"))
    columns = (
        "reaching",
        "reaching_np",
        "handler_m",
        "handler_m_np",
        "handlers_flagged",
        "handlers_flagged_np",
        "widgets_flagged",
        "widgets_flagged_np",
    )
    print("apk | compose | " + " | ".join(columns))
    print("|".join(["---"] * (len(columns) + 2)))
    totals = {True: dict.fromkeys(columns, 0), False: dict.fromkeys(columns, 0)}
    apps = {True: 0, False: 0}
    affected = {True: 0, False: 0}
    for name in names:
        with open(os.path.join(directory, name), "rb") as source:
            document = json.loads(source.read())
        row = _measure(document)
        del document
        group = row["compose"]
        apps[group] += 1
        affected[group] += row["reaching_np"] > 0
        for column in columns:
            totals[group][column] += row[column]
        print(
            f"{name} | {'yes' if group else 'no'} | "
            + " | ".join(str(row[c]) for c in columns)
        )

    print()
    for group, label in ((True, "Compose"), (False, "View-only")):
        t = totals[group]
        lines = (
            f"{label}: {apps[group]} apps, "
            f"{affected[group]} with any reaching method lacking pairs",
            "  reaching methods without targetDistances: "
            + _share(t["reaching_np"], t["reaching"]),
            "  reaching handler methods without targetDistances: "
            + _share(t["handler_m_np"], t["handler_m"]),
            "  flagged handler records with a flagged event lacking a pair: "
            + _share(t["handlers_flagged_np"], t["handlers_flagged"]),
            "  flagged emitted widgets with a flagged event lacking a pair: "
            + _share(t["widgets_flagged_np"], t["widgets_flagged"]),
        )
        print("\n".join(lines))


if __name__ == "__main__":
    main(sys.argv[1])
