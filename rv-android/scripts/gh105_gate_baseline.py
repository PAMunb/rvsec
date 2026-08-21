#!/usr/bin/env python3
"""The expected baseline the gh105 gates are registered against, and its report.

**This file has a demolition date.** Task 7.6 deletes it, the JSON it writes and
the pytest wrappers that read it, once every gate is green on its own. It exists
because of an ordering problem that has no other honest answer: the gates of this
change are written *before* the edits that make them pass -- G-ACC cannot pass
until the 17 orphans are absorbed, the placement gates not until the 27 reads move
out of `condition(...)`, G-ORDER not until the automata are repaired. Wiring them
into CI as *assert zero findings* would leave `tests/parity` red across most of the
change, and a suite that is expected to be red stops being read: every checkpoint
in between would be noise, and a real regression would arrive inside it unnoticed.

So each gate is registered against what it reported on the unmodified tree. The
pytest wrapper asserts *no regression against the recorded baseline*, not *zero
findings*, and a group lands by removing its rows from this file. The number only
goes down, and the day it goes up the suite says so.

It is not `gate_allowlist.csv`. That file records findings that are deliberately
permanent, each with the measurement and the reason behind it. This one records
findings that are merely *not repaired yet*, and its whole purpose is to disappear.

Usage:
    uv run python scripts/gh105_gate_baseline.py --write   # emit both artifacts
    uv run python scripts/gh105_gate_baseline.py           # compare, exit 1 on drift
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import gh105_order_gate  # noqa: E402
import gh105_predicate_graph as graph  # noqa: E402

DEFAULT_BASELINE = Path("data/jca_android/gate_baseline.json")
DEFAULT_REPORT = Path("data/jca_android/evidence/gate_baseline_report.md")
DEFAULT_SPECS = Path("../rvsec/rvsec-mop/src/main/resources")

# The task that deletes the mechanism. Recorded in the artifact itself so the
# scaffolding carries its own removal order rather than relying on someone
# remembering it two groups later.
DEMOLITION_TASK = "7.6"


def collect(
    specs_root: Path,
    graph_path: Path = graph.DEFAULT_GRAPH,
    allowlist: Path = Path("data/jca_android/gate_allowlist.csv"),
    rules_root: Path = gh105_order_gate.DEFAULT_RULES,
    map_path: Path = gh105_order_gate.DEFAULT_MAP,
) -> tuple[dict, graph.GateRun, gh105_order_gate.OrderRun]:
    """Both gate suites over the enumerated universe, reduced to keys and counts.

    A baseline row is `[set, file, subject]` and never a line number or a message:
    a finding that stopped matching because a file was reformatted would reappear
    as a regression, and a mechanism that cries wolf on formatting is a mechanism
    that gets deleted early and for the wrong reason.
    """
    run = graph.run_gates(specs_root, "all", graph_path, allowlist)
    order = gh105_order_gate.run(specs_root, "all", rules_root, map_path)

    gates: dict[str, list[list[str]]] = {}
    for finding in run.findings:
        gates.setdefault(finding.gate, []).append(
            [finding.spec_set, finding.file, finding.subject]
        )
    for finding in order.findings:
        gates.setdefault("G-ORDER", []).append(
            [finding.spec_set, f"{finding.spec}.mop", "order"]
        )
    for rows in gates.values():
        rows.sort()

    return {
        "demolition_task": DEMOLITION_TASK,
        "what_this_is": (
            "findings measured on the tree before this change edits it; each pytest "
            "wrapper asserts no finding outside this set. Not an allow-list: these "
            "are unrepaired, not permitted."
        ),
        "counts": {
            "universe": run.universe,
            "read": run.read,
            "skipped": run.skipped,
            "structural_findings": len(run.findings),
            "informative": len(run.informative),
            "allow_listed": len(run.allowed),
            "order_passed": len(order.passed),
            "order_failed": len(order.findings),
            "order_skipped": len(order.skipped),
        },
        "gates": gates,
    }, run, order


def render_report(payload: dict, run, order) -> str:
    """The human half of the same measurement.

    `passed`/`failed`/`skipped` over the whole universe is the evidence for
    INV-INS-140: a gate that enumerates its universe and says what it could not
    decide is a gate whose green means something.
    """
    counts = payload["counts"]
    lines = [
        "# gh105 — the gate baseline, measured before the first edit",
        "",
        "What every gh105 gate reports on the unmodified specification universe. It is the",
        "reference each pytest wrapper is registered against (design D-13): the wrappers assert",
        "*no finding outside this set*, so a group lands as a drop in these numbers and a",
        "regression lands as a finding nobody recorded. Task "
        f"{payload['demolition_task']} deletes the mechanism once the gates stand on their own.",
        "",
        "## The universe, enumerated",
        "",
        "| set | files | read | skipped | predicate sites |",
        "|---|---|---|---|---|",
    ]
    for report in run.reports:
        lines.append(
            f"| `{report.name}` | {report.total} | {report.read} | "
            f"{len(report.skipped)} | {len(report.rows)} |"
        )
    lines += [
        f"| **total** | **{counts['universe']}** | **{counts['read']}** | "
        f"**{counts['skipped']}** | | ",
        "",
        "Every skipped file carries its reason:",
        "",
    ]
    for report in run.reports:
        for name, reason in report.skipped:
            lines.append(f"- `{report.name}/{name}` — {reason}")
    lines += [
        "",
        "## The structural suite",
        "",
        "| gate | findings |",
        "|---|---|",
    ]
    for gate, rows in sorted(payload["gates"].items()):
        lines.append(f"| {gate} | {len(rows)} |")
    lines += [
        f"| **failing total** | **{counts['structural_findings'] + counts['order_failed']}** |",
        "",
        f"Informative (reported in sets these gates do not govern): {counts['informative']}. "
        f"Allow-listed (permanent, with reasons): {counts['allow_listed']}.",
        "",
        "Gates scoped away from a set say so, with the reason:",
        "",
    ]
    seen: set[tuple[str, str]] = set()
    for gate, spec_set, reason in run.gate_skips:
        if (gate, spec_set) in seen:
            continue
        seen.add((gate, spec_set))
        lines.append(f"- {gate} over `{spec_set}` — {reason}")
    lines += [
        "",
        "## G-ORDER",
        "",
        f"{counts['order_passed']} specifications equivalent to their api30 rule, "
        f"{counts['order_failed']} divergent, {counts['order_skipped']} skipped of "
        f"{counts['universe']} enumerated. Each divergence carries the shortest word the two "
        "languages disagree on:",
        "",
    ]
    for finding in order.findings:
        lines.append(f"- `{finding.spec_set}/{finding.spec}` — {finding.message}")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--specs-root", type=Path, default=DEFAULT_SPECS)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--write", action="store_true", help="emit both artifacts")
    arguments = parser.parse_args(argv)

    payload, run, order = collect(arguments.specs_root)

    if arguments.write:
        arguments.baseline.parent.mkdir(parents=True, exist_ok=True)
        arguments.baseline.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        arguments.report.parent.mkdir(parents=True, exist_ok=True)
        arguments.report.write_text(render_report(payload, run, order), encoding="utf-8")
        print(f"wrote {arguments.baseline} and {arguments.report}")
        return 0

    if not arguments.baseline.is_file():
        print(f"no baseline at {arguments.baseline}; run with --write", file=sys.stderr)
        return 2

    recorded = json.loads(arguments.baseline.read_text(encoding="utf-8"))["gates"]
    drifted = False
    for gate in sorted(set(recorded) | set(payload["gates"])):
        was = {tuple(row) for row in recorded.get(gate, [])}
        now = {tuple(row) for row in payload["gates"].get(gate, [])}
        for row in sorted(now - was):
            drifted = True
            print(f"  [{gate}] NEW {row[0]}/{row[1]} {row[2]}")
        for row in sorted(was - now):
            print(f"  [{gate}] repaired {row[0]}/{row[1]} {row[2]}")
    print("regression" if drifted else "no finding outside the recorded baseline")
    return 1 if drifted else 0


if __name__ == "__main__":
    raise SystemExit(main())
