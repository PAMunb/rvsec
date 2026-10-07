#!/usr/bin/env python3
"""Check that a UiAutomation client reads the handler stamp the app logged.

usage: check_delivery.py <probe results dir>

For every `*.probe.txt` under the directory (written by `run_probe.py` beside a
task's `.logcat`), each dump of the probe is compared with the app's `RVSEC-BIND`
lines in that `.logcat` written up to the dump's time (logcat `threadtime`,
`MM-DD HH:MM:SS.mmm`, compared as text: one run never crosses a year).

State as of a dump:
  * View lines (`view kind=... id=... handler=... obj=...`) set one key (`click`
    or `longClick`) of one view object; `handler=-` clears it, a key never logged
    for that object is absent. Lines with `id=-` cannot be paired and are ignored.
  * Compose lines (`compose kind=... node=... bounds=... handler=...
    [longClickHandler=...]`) carry both keys of one node: `kind=click` gives
    `click=handler` and `longClick=longClickHandler` (absent if not written);
    `kind=longClick` gives `click` absent and `longClick=handler`. The last line
    for a node replaces the earlier ones.

Pairing a dump node, View first:
  * View: the node's view-id resource name equals the `id` of View lines. When
    several view objects logged that id and their states differ, the id is
    ambiguous: the node is counted as `ambiguous`, neither matched nor
    mismatched. When their states agree, that state is the expected one.
  * Compose: the node's screen bounds and class equal a Compose line's `bounds`
    and `node`. The class is part of the key because a Compose node often shares
    its bounds with its host view or with a merged child.
  * A paired node matches when both of its extras equal the expected keys, an
    absent extra being equal to an absent key; otherwise it is a mismatch.
  * A node that pairs with no line but carries an extra is counted as
    `stamped_unlogged`; it is reported, not failed.
  * Lines whose node never pairs in any dump of the app are counted per APK as
    `unpaired_lines` (View ids and Compose nodes logged up to the last dump);
    reported, not failed.

Steps whose foreground package is not the app's are skipped.

Exit 0 when no paired node mismatches and at least one View node and one Compose
node were paired across the run; exit 1 otherwise.
"""
import re
import sys
from pathlib import Path

PROBE_SUFFIX = ".probe.txt"
BIND_LINE = re.compile(
    r"^(\d\d-\d\d \d\d:\d\d:\d\d\.\d{3})\s+\d+\s+\d+\s+[VDIWEF] RVSEC-BIND\s*:\s*(.*)$"
)


def absent(value):
    """`-` (and a missing value) mean the key is absent."""
    return None if value in (None, "-") else value


def read_bind_lines(logcat: Path):
    """Return `[(time, fields)]` of the `RVSEC-BIND` lines, in file order.

    `fields` maps each `key=value` token of the payload, plus `type` (`view` or
    `compose`, the payload's first token).
    """
    lines = []
    with open(logcat, encoding="utf-8", errors="replace") as f:
        for raw in f:
            match = BIND_LINE.match(raw.rstrip("\n"))
            if not match:
                continue
            first, *tokens = match.group(2).split()
            fields = dict(tok.split("=", 1) for tok in tokens if "=" in tok)
            fields["type"] = first
            lines.append((match.group(1), fields))
    return lines


def read_dumps(path: Path):
    """Return `(package, steps)` of a probe output file.

    Each step is a dict with `index`, `time`, `package`, `action`, `target`
    (class, view-id, bounds) and `nodes`, a list of
    `(class, view_id, bounds, click, longClick)` with absent values as None.
    """
    package = None
    steps = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for raw in f:
            cols = raw.rstrip("\n").split("\t")
            if cols[0] == "APP" and len(cols) >= 2:
                package = cols[1]
            elif cols[0] == "STEP" and len(cols) >= 8:
                steps.append({
                    "index": int(cols[1]),
                    "time": cols[2],
                    "package": cols[3],
                    "action": cols[4],
                    "target": tuple(cols[5:8]),
                    "nodes": [],
                })
            elif cols[0] == "NODE" and len(cols) >= 6 and steps:
                cls, view_id, bounds, click, long_click = cols[1:6]
                steps[-1]["nodes"].append(
                    (cls, view_id, bounds, absent(click), absent(long_click))
                )
    return package, steps


def state_at(lines, time):
    """View and Compose stamp state from the lines written up to `time`.

    Returns `(view, compose)`: `view[id][obj] = {"click": h, "longClick": h}` and
    `compose[(bounds, class)] = (click, longClick)`.
    """
    view, compose = {}, {}
    for stamp, fields in lines:
        if stamp > time:
            continue
        if fields["type"] == "view" and absent(fields.get("id")):
            keys = view.setdefault(fields["id"], {}).setdefault(
                fields.get("obj"), {"click": None, "longClick": None}
            )
            keys[fields.get("kind")] = absent(fields.get("handler"))
        elif fields["type"] == "compose":
            handler = absent(fields.get("handler"))
            if fields.get("kind") == "click":
                pair = (handler, absent(fields.get("longClickHandler")))
            else:
                pair = (None, handler)
            compose[(fields.get("bounds"), fields.get("node"))] = pair
    return view, compose


def check_step(step, lines):
    """Pair the nodes of one dump with the stamp state as of its time."""
    view, compose = state_at(lines, step["time"])
    result = {"view": 0, "compose": 0, "match": 0, "mismatch": [], "ambiguous": 0,
              "stamped_unlogged": 0, "paired_keys": set()}
    for cls, view_id, bounds, click, long_click in step["nodes"]:
        seen = (click, long_click)
        if view_id != "-" and view_id in view:
            states = {(k["click"], k["longClick"]) for k in view[view_id].values()}
            result["paired_keys"].add(("view", view_id))
            if len(states) > 1:
                result["ambiguous"] += 1
                continue
            kind, key, expected = "view", view_id, states.pop()
        elif (bounds, cls) in compose:
            kind, key, expected = "compose", f"{cls} {bounds}", compose[(bounds, cls)]
            result["paired_keys"].add(("compose", (bounds, cls)))
        else:
            if seen != (None, None):
                result["stamped_unlogged"] += 1
            continue
        result[kind] += 1
        if seen == expected:
            result["match"] += 1
        else:
            result["mismatch"].append((kind, key, seen, expected))
    return result


def line_keys(lines, time):
    """The pairing keys of the lines written up to `time`."""
    view, compose = state_at(lines, time)
    return {("view", k) for k in view} | {("compose", k) for k in compose}


def fmt(pair):
    return f"click={pair[0] or '-'} longClick={pair[1] or '-'}"


def check_apk(dump_path: Path, out):
    """Check one task; write its report to `out`; return its totals."""
    logcat = dump_path.with_name(dump_path.name[: -len(PROBE_SUFFIX)] + ".logcat")
    package, steps = read_dumps(dump_path)
    lines = read_bind_lines(logcat) if logcat.is_file() else []
    totals = {"steps": len(steps), "in_app": 0, "view": 0, "compose": 0, "match": 0,
              "mismatch": 0, "ambiguous": 0, "stamped_unlogged": 0, "unpaired_lines": 0,
              "bind_lines": len(lines)}
    out.write(f"{dump_path.parent.name} ({package})\n")
    if not logcat.is_file():
        out.write(f"  no logcat at {logcat}\n")
    paired_keys, last_time = set(), None
    for step in steps:
        head = f"  step {step['index']} {step['action']} {' '.join(step['target'])}"
        if step["package"] != package:
            out.write(f"{head}: skipped, foreground {step['package']}\n")
            continue
        totals["in_app"] += 1
        last_time = step["time"]
        r = check_step(step, lines)
        paired_keys |= r["paired_keys"]
        for name in ("view", "compose", "match", "ambiguous", "stamped_unlogged"):
            totals[name] += r[name]
        totals["mismatch"] += len(r["mismatch"])
        out.write(
            f"{head}: paired={r['view'] + r['compose']} (view={r['view']} "
            f"compose={r['compose']}) match={r['match']} mismatch={len(r['mismatch'])} "
            f"ambiguous={r['ambiguous']} stamped_unlogged={r['stamped_unlogged']}\n"
        )
        for kind, key, seen, expected in r["mismatch"]:
            out.write(f"    MISMATCH {kind} {key}: node {fmt(seen)} / line {fmt(expected)}\n")
    if last_time is not None:
        totals["unpaired_lines"] = len(line_keys(lines, last_time) - paired_keys)
    out.write("  total: " + " ".join(f"{k}={v}" for k, v in totals.items()) + "\n")
    return totals


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        sys.stderr.write(__doc__.split("\n\n")[1] + "\n")
        return 2
    dumps = sorted(Path(argv[0]).rglob("*" + PROBE_SUFFIX))
    view = compose = mismatch = 0
    for dump_path in dumps:
        totals = check_apk(dump_path, sys.stdout)
        view += totals["view"]
        compose += totals["compose"]
        mismatch += totals["mismatch"]
    ok = mismatch == 0 and view > 0 and compose > 0
    print(f"run: tasks={len(dumps)} paired_view={view} paired_compose={compose} "
          f"mismatch={mismatch} -> {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
