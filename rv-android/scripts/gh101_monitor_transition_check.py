#!/usr/bin/env python3
"""INV-INS-110: no event of a specification transitions to `fail` from every state.

The monitor generator does not reject an event that appears in a specification's
event list and in no row of its `fsm`. It gives that event a transition row
sending every state to `fail`. The specification does not merely leave the event
unmodelled -- it becomes an unconditional accuser, emitting
`InvalidSequenceOfMethodCalls` on the first occurrence of a call that may be
perfectly ordered.

Two events were in that state: `g3` in `TrustManagerFactorySpec` and
`unsafe_protocol` in `SSLContextSpec`. Both were inert, because a second defect
kept them out of the monitored object's parameter slice, so repairing the
binding without the automaton would have converted a dead event into an
unconditional accuser. That is why this check exists rather than a review.

It reads the generated monitor rather than the `.mop`, because the `.mop` is not
where the consequence is visible: the row is something the generator writes.

Usage:
    gh101_monitor_transition_check.py <MultiSpec_1RuntimeMonitor.java>
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# The generator emits two monitor kinds and the check must read both. A
# specification whose events all bind its parameter gets an AbstractAtomicMonitor;
# one whose events land in the empty parameter slice gets an
# AbstractSynchronizedMonitor -- which is exactly the shape the two defective
# events produced, so matching only the first kind would have skipped them.
MONITOR_CLASS = re.compile(
    r"^(?:final )?class (\w+)Monitor extends .*Abstract(?:Atomic|Synchronized)Monitor"
)
# `static final int Prop_1_transition_g3[] = {0, 3, 3, 3};;`
TRANSITION = re.compile(
    r"static final int (\w+)_transition_(\w+)\[\]\s*=\s*\{([^}]*)\}"
)
# `...Category_fail = nextstate == 4;` in the atomic form,
# `...Category_fail = Prop_1_state == 3;` in the synchronized one.
FAIL_STATE = re.compile(
    r"(\w+)Monitor_(\w+)_Category_fail\s*=\s*(?:nextstate|\w*_?state) == (\d+)"
)


def check(monitor: Path) -> list[str]:
    """Every (specification, event) whose transition row is fail from every state."""
    text = monitor.read_text(encoding="utf-8")

    # The fail index is per specification and per property, and the generator
    # writes it into every event method, so the first occurrence is enough.
    fail_state: dict[tuple[str, str], int] = {}
    for spec, prop, state in FAIL_STATE.findall(text):
        fail_state.setdefault((spec, prop), int(state))

    offenders: list[str] = []
    current = None
    for line in text.splitlines():
        if match := MONITOR_CLASS.match(line):
            current = match.group(1)
            continue
        if current is None:
            continue
        if match := TRANSITION.search(line):
            prop, event, body = match.groups()
            fail = fail_state.get((current, prop))
            if fail is None:
                continue
            row = [int(value) for value in body.split(",") if value.strip()]
            if row and all(value == fail for value in row):
                offenders.append(f"{current}.{event}: {row} -- fail is {fail}")

    return offenders


def main() -> int:
    """
    Parse the monitor path and report any event with an all-fail transition row.

    Both outcomes print to stderr rather than stdout: this is a gate, and its
    output is a verdict rather than data for a pipe.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("monitor", type=Path)
    args = parser.parse_args()

    if not args.monitor.is_file():
        print(f"generated monitor not found: {args.monitor}", file=sys.stderr)
        return 1

    offenders = check(args.monitor)
    if offenders:
        print(
            "INV-INS-110 violated -- bound events with an all-fail row:",
            file=sys.stderr,
        )
        print("\n".join(f"  {line}" for line in offenders), file=sys.stderr)
        return 1

    print("no bound event has an all-fail transition row", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
