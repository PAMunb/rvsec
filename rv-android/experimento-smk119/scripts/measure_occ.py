"""
Measure the `RVSEC-OCC` occurrence stream of the gh119 smoke runs.

The collector writes one `RVSEC` line on the first occurrence of an identity and one
`RVSEC-OCC` line on the first occurrence and then at most once per identity per
100 ms (INV-INS-170..172). The smoke asks what that stream costs and whether it
arrives whole under real exploration. Per `.logcat` under the results directory this
script reports the five measures of design D10:

1. `RVSEC-OCC` lines per second: the mean over the span of the run's lines and the
   peak over 1 s bins;
2. the maximum `n` per identity, and the identities with the largest `n`;
3. the pairing: every `RVSEC` line needs an `RVSEC-OCC` line with `n=1` on the same
   key, and every `n=1` line needs its `RVSEC` line. An unpaired line on either side
   is a measured loss;
4. the peak of all captured lines per second, any tag;
5. the placement of the `RVSEC-OCC` lines on the exploration timeline, through the
   `ApeRvHb` heartbeats, with the same reader and rule `clock_logcat_join` and
   `step_bundle` use.

The key of the pairing is eight fields: the first six of the `RVSEC` line
(`ErrorSummary.toString()`) plus the `code` and `event` the collector reads out of
the message envelope. Those two are recomputed here with the collector's own rule
(`ErrorDescription.envelopeValue`): present only when the message contains `v=1 `,
the first `code=`/`ev=` token otherwise, and `UNSPECIFIED` when absent.

A `RVSEC-OCC` payload must split into exactly nine comma fields with an integer
`n >= 1`. A line that does not is counted and reported as malformed; it still counts
toward the volume and the placement, because it is a line the device logged. The report
is written either way, and the exit status is 1 when any `RVSEC-OCC` or `RVSEC` line is
malformed or unreadable, so a format drift fails the run instead of passing as a number.

Offline and read-only on its inputs: no device, no adb. The only file written is
`<results>/measure_occ.json`.

Usage: uv run python experimento-smk119/scripts/measure_occ.py <results_dir>
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

from aperv_tool.analysis.clock_logcat_join import (
    Phase,
    _read_heartbeats,
    place_on_timeline,
    read_tagged_lines,
)
from aperv_tool.analysis.trace_ndjson import TraceReader

OCC_TAG = "RVSEC-OCC"
VIOLATION_TAG = "RVSEC"
OCC_FIELDS = 9
IDENTITY_FIELDS = 8
SUMMARY_FIELDS = 6
UNSPECIFIED = "UNSPECIFIED"
TOP_IDENTITIES = 5
MALFORMED_EXAMPLES = 5
OUTPUT_NAME = "measure_occ.json"

# The collector's envelope rule (ErrorDescription.ENVELOPE_MARKER / ENVELOPE_CODE /
# ENVELOPE_EVENT), so the key computed here is the key the device computed.
ENVELOPE_MARKER = "v=1 "
_ENVELOPE_CODE = re.compile(r"(?:^|\s)code=(\S+)")
_ENVELOPE_EVENT = re.compile(r"(?:^|\s)ev=(\S+)")

# Any captured threadtime line, whatever its tag; the 14-character prefix
# `MM-DD HH:MM:SS` is its 1 s bin. Separator lines (`--------- beginning of ...`)
# do not match and are not captured lines.
_ANY_LINE = re.compile(rb"^\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}\s+\d+\s+\d+\s+[VDIWEF] ")
_SECOND_PREFIX = 14


class MalformedOccLine(ValueError):
    """An `RVSEC-OCC` payload that is not nine fields ending in an integer n >= 1."""


def parse_occ(payload: str) -> tuple[tuple[str, ...], int]:
    """Split one `RVSEC-OCC` payload into its eight-field identity and its count n."""
    fields = payload.split(",")
    if len(fields) != OCC_FIELDS:
        raise MalformedOccLine(f"{len(fields)} fields, expected {OCC_FIELDS}")
    try:
        n = int(fields[IDENTITY_FIELDS])
    except ValueError as error:
        raise MalformedOccLine(f"n is not an integer: {fields[IDENTITY_FIELDS]!r}") from error
    if n < 1:
        raise MalformedOccLine(f"n is below 1: {n}")
    return tuple(fields[:IDENTITY_FIELDS]), n


def violation_key(payload: str) -> tuple[str, ...] | None:
    """The eight-field key of one `RVSEC` payload, or None when it has under seven fields."""
    fields = payload.split(",", SUMMARY_FIELDS)
    if len(fields) <= SUMMARY_FIELDS:
        return None
    message = fields[SUMMARY_FIELDS]
    code = event = UNSPECIFIED
    if ENVELOPE_MARKER in message:
        code_match = _ENVELOPE_CODE.search(message)
        event_match = _ENVELOPE_EVENT.search(message)
        code = code_match.group(1) if code_match else UNSPECIFIED
        event = event_match.group(1) if event_match else UNSPECIFIED
    return tuple(fields[:SUMMARY_FIELDS]) + (code, event)


def _rate(stamps: list) -> dict:
    """Mean and peak lines per second. The span is counted in whole 1 s bins,
    first to last inclusive, so a run whose lines fit in one second has span 1."""
    if not stamps:
        return {"lines": 0, "span_s": 0, "mean_per_s": 0.0, "peak_per_s": 0}
    bins = Counter(stamp.replace(microsecond=0) for stamp in stamps)
    span_s = int((max(bins) - min(bins)).total_seconds()) + 1
    return {
        "lines": len(stamps),
        "span_s": span_s,
        "mean_per_s": round(len(stamps) / span_s, 3),
        "peak_per_s": max(bins.values()),
    }


def _all_lines_peak(logcat_path: Path) -> dict:
    """Total captured lines and their peak per 1 s bin, any tag."""
    bins: Counter[bytes] = Counter()
    with open(logcat_path, "rb") as logcat_file:
        for raw_line in logcat_file:
            if _ANY_LINE.match(raw_line):
                bins[raw_line[:_SECOND_PREFIX]] += 1
    return {"lines": sum(bins.values()), "peak_per_s": max(bins.values(), default=0)}


def _key_text(key: tuple[str, ...]) -> str:
    return ",".join(key)


def _unpaired(left: Counter, right: Counter) -> list[dict]:
    """Keys present more often on the left than on the right, with the excess."""
    return [
        {"key": _key_text(key), "count": count - right[key]}
        for key, count in sorted(left.items())
        if count > right[key]
    ]


def measure_logcat(logcat_path: Path) -> dict:
    """The five D10 measures for one run's logcat."""
    occ_lines = read_tagged_lines(logcat_path, OCC_TAG)
    rvsec_lines = read_tagged_lines(logcat_path, VIOLATION_TAG)

    # Identities and counts from the well-formed occurrence lines.
    max_n: dict[tuple[str, ...], int] = {}
    occ_first: Counter = Counter()
    malformed: list[str] = []
    for _stamp, payload in occ_lines:
        try:
            identity, n = parse_occ(payload)
        except MalformedOccLine:
            malformed.append(payload)
            continue
        max_n[identity] = max(n, max_n.get(identity, 0))
        if n == 1:
            occ_first[identity] += 1

    # Pairing is a multiset match: a restarted process starts every count again, so
    # one key can legitimately carry several RVSEC lines and as many n=1 lines.
    rvsec_keys: Counter = Counter()
    rvsec_malformed = 0
    for _stamp, payload in rvsec_lines:
        key = violation_key(payload)
        if key is None:
            rvsec_malformed += 1
        else:
            rvsec_keys[key] += 1
    unpaired_rvsec = _unpaired(rvsec_keys, occ_first)
    unpaired_occ = _unpaired(occ_first, rvsec_keys)

    # Placement, with the heartbeat reader and rule of clock_logcat_join.
    heartbeats = _read_heartbeats(logcat_path)
    placement = {phase.value: 0 for phase in Phase}
    steps_with_occ: set[int] = set()
    for stamp, _payload in occ_lines:
        if not heartbeats:
            placement[Phase.UNALIGNED.value] += 1
            continue
        phase, step, _anchor = place_on_timeline(stamp, heartbeats)
        placement[phase.value] += 1
        if step is not None:
            steps_with_occ.add(step)

    trace_path = logcat_path.with_suffix(".trace")
    trace_steps = sum(1 for _row in TraceReader(trace_path)) if trace_path.is_file() else None

    top = sorted(max_n.items(), key=lambda item: (-item[1], item[0]))[:TOP_IDENTITIES]
    return {
        "logcat": str(logcat_path),
        "trace": str(trace_path) if trace_path.is_file() else None,
        "trace_steps": trace_steps,
        "occ": {
            **_rate([stamp for stamp, _payload in occ_lines]),
            "unreadable": occ_lines.skipped,
            "malformed": len(malformed),
            "malformed_examples": malformed[:MALFORMED_EXAMPLES],
        },
        "identities": {
            "count": len(max_n),
            "max_n": max(max_n.values(), default=0),
            "top": [{"identity": _key_text(key), "n": n} for key, n in top],
        },
        "pairing": {
            "rvsec_lines": len(rvsec_lines),
            "rvsec_unreadable": rvsec_lines.skipped,
            "rvsec_malformed": rvsec_malformed,
            "occ_n1_lines": sum(occ_first.values()),
            "paired": sum((rvsec_keys & occ_first).values()),
            "unpaired_rvsec": sum(item["count"] for item in unpaired_rvsec),
            "unpaired_occ_n1": sum(item["count"] for item in unpaired_occ),
            "unpaired_rvsec_keys": unpaired_rvsec,
            "unpaired_occ_n1_keys": unpaired_occ,
        },
        "all_lines": _all_lines_peak(logcat_path),
        "placement": {
            **placement,
            "heartbeats": len(heartbeats),
            "steps_with_occ": len(steps_with_occ),
        },
    }


def measure_tree(results_dir: Path) -> dict:
    """Measure every `.logcat` under the results directory, in path order."""
    return {
        "results_dir": str(results_dir),
        "runs": [measure_logcat(path) for path in sorted(results_dir.rglob("*.logcat"))],
    }


def _print_table(report: dict) -> None:
    header = (
        f"{'run':<44} {'occ':>7} {'mean/s':>7} {'peak/s':>6} {'max n':>7} "
        f"{'paired':>6} {'lostR':>5} {'lostO':>5} {'malf':>4} {'all pk/s':>8} "
        f"{'pre':>5} {'step':>6} {'post':>5} {'unal':>5}"
    )
    print(header)
    print("-" * len(header))
    for run in report["runs"]:
        occ, pairing, placement = run["occ"], run["pairing"], run["placement"]
        name = Path(run["logcat"]).name.split("__")[0][:44]
        print(
            f"{name:<44} {occ['lines']:>7} {occ['mean_per_s']:>7.2f} {occ['peak_per_s']:>6} "
            f"{run['identities']['max_n']:>7} {pairing['paired']:>6} "
            f"{pairing['unpaired_rvsec']:>5} {pairing['unpaired_occ_n1']:>5} "
            f"{occ['malformed']:>4} {run['all_lines']['peak_per_s']:>8} "
            f"{placement[Phase.PRE_EXPLORATION.value]:>5} "
            f"{placement[Phase.EXPLORATION.value]:>6} "
            f"{placement[Phase.POST_EXPLORATION.value]:>5} "
            f"{placement[Phase.UNALIGNED.value]:>5}"
        )
    print(
        "lostR = RVSEC without its n=1; lostO = n=1 without its RVSEC; "
        "malf = RVSEC-OCC lines that are not nine fields with integer n"
    )


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1 or not Path(args[0]).is_dir():
        print("usage: measure_occ.py <results_dir>", file=sys.stderr)
        return 2
    results_dir = Path(args[0])
    report = measure_tree(results_dir)
    output = results_dir / OUTPUT_NAME
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    _print_table(report)
    print(f"{len(report['runs'])} logcat files; report written to {output}")
    bad = sum(
        run["occ"]["malformed"]
        + run["occ"]["unreadable"]
        + run["pairing"]["rvsec_malformed"]
        + run["pairing"]["rvsec_unreadable"]
        for run in report["runs"]
    )
    if bad:
        print(f"{bad} malformed or unreadable lines; see {output}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
