"""
Offline parser for the APE-RV UI-coverage dump.

At teardown the agent dumps what it actually exercised, one line per UI state
(`UICOV`) and one per Activity (`UICOV-ACT`), into its stdout — which the tool
captures as the run's `.trace` file. The lines say how many actions the agent
*discovered* on a screen against how many it *interacted* with, which is the
middle link of the chain from a decision to a violation: decision -> action ->
MOP screen -> violation. The ends of that chain are already measured (`[APE-STEP]`
for the decision, `RVSEC` logcat lines for the violation); this is the part that
says whether a screen the agent reached was actually exercised.

The dump had **no automated consumer** before this module: a search for `UICOV`
across the whole rv-android tree returned zero hits in Python, and the only
historical consumption was manual. The sister `ape` change hoists the emission
to the front of the teardown chain so that 333 of the 338 runs that lose it today
keep it; without a parser that recovery produces data nothing reads.

Two constraints below are not preferences:

**Activity grain is mandatory for anything crossing runs (INV-APV-36).** The
per-state `UICOV` key embeds `StateKey.toString()`, whose hash includes the JVM
identity hash of a `Naming` object that overrides neither `equals` nor
`hashCode`. State keys therefore do not survive a process boundary: the measured
Jaccard between replicas of the same (APK, arm) is 0.000 at mean, median *and*
maximum — not one state line in the corpus pairs with its counterpart. `UICOV`
rows are parsed for intra-run use; `aggregate_activities()` is the only cross-run
entry point this module offers, and it reads `UICOV-ACT` alone.

**Every run is reported with an explicit status (INV-APV-37).** The quantity
being studied *is* the loss rate — 462 of 880 recorded runs carry a dump — so a
parser that silently dropped the runs without one would compute coverage over the
survivors and present it as coverage over all runs. That is exactly the error
that produced the retracted 165/880 figure. Hence `DumpStatus.ABSENT` is a
result, not an omission, and `DumpPresence` carries its own denominator.

Read-only and offline: it opens recorded files and writes none.
"""

from __future__ import annotations

import csv
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from aperv_tool.analysis.run_identity import try_parse_run_filename

# The dump line shape this parser was written against. The jar stamps no version
# into the dump itself, so the constant records which shape was verified: both
# line kinds carry `discovered`, `interacted`, `gap` and `byType`, `UICOV` ends
# with `mopReach` and `UICOV-ACT` with `liveStates`. A jar-side field change
# should bump this rather than silently misparse into plausible numbers.
DUMP_SCHEMA_VERSION = 1

# Matched as SUBSTRINGS, never anchored at the start of the line. Every line the
# agent prints is prefixed `[APE] `, and the dump lines come from Logger.format,
# which — unlike most other output — does NOT carry the `*** INFO *** ` infix. An
# anchored pattern silently matches nothing. The ACT tag is tested first because
# `UICOV` is a prefix of `UICOV-ACT`.
_ACTIVITY_TAG = "[APE-RV] UICOV-ACT "
_STATE_TAG = "[APE-RV] UICOV "

# byType is `TYPE:interacted/discovered` — in that order. Verified against the
# corpus: the per-type first components sum to `interacted` and the second to
# `discovered` on every complete line.
_BY_TYPE_ENTRY = re.compile(
    r"^(?P<type>[A-Z_]+):(?P<interacted>\d+)/(?P<discovered>\d+)$"
)


class DumpStatus(str, Enum):
    """Per-run dump status. Never omitted, never inferred (INV-APV-37).

    Attributes:
        COMPLETE: Every dump line found in the trace parsed.
        PARTIAL: At least one dump line failed to parse, the expected cause
            being a tail cut by the process being killed mid-write. The lines
            that did parse are kept.
        ABSENT: The trace carries no dump line at all. A result in its own
            right, not a gap: the loss rate is the quantity under study, so
            these runs stay in every denominator.
    """

    COMPLETE = "complete"
    PARTIAL = "partial"
    ABSENT = "absent"


@dataclass(frozen=True)
class ActivityCoverage:
    """One `UICOV-ACT` line: coverage of one Activity within one run.

    Activity names are plain class names and survive a process boundary, which
    is what makes this the one grain a cross-run join may use (INV-APV-36).

    Attributes:
        activity: Activity class name exactly as the agent reported it.
        discovered: Actions the agent found on this Activity.
        interacted: Actions it actually exercised — a subset of discovered.
        live_states: UI states still held for this Activity at teardown.
        by_type: Per-widget-type breakdown as {type: (interacted, discovered)},
            interacted first, mirroring the jar's `TYPE:interacted/discovered`.
        mop_reach: Always None — the jar emits `mopReach` on `UICOV` only.
    """

    activity: str
    discovered: int
    interacted: int
    live_states: int
    by_type: dict[str, tuple[int, int]] = field(default_factory=dict)
    # `mopReach` is emitted on `UICOV` and NOT on `UICOV-ACT`, so MOP reach is
    # not reconstructible at Activity grain from the current jar. The field is
    # kept and left None so a consumer reads "not available" instead of quietly
    # finding no attribute and inferring zero. Propagating it into the ACT line
    # is item O2 on the jar side, deliberately in neither change.
    mop_reach: None = None


@dataclass(frozen=True)
class StateCoverage:
    """
    One `UICOV` line: coverage of one UI state within one run.

    Intra-run only. `state_key` embeds a JVM identity hash and is meaningless
    outside the process that produced it (INV-APV-36).

    Attributes:
        state_key: `StateKey.toString()` as printed. Opaque, and a valid
            identifier only within the run that emitted it.
        discovered: Actions the agent found on this state.
        interacted: Actions it actually exercised — a subset of discovered.
        mop_reach: Actions on this state that reach a monitored operation,
            per the agent's own MOP data.
        by_type: Per-widget-type breakdown as {type: (interacted, discovered)},
            interacted first, mirroring the jar's `TYPE:interacted/discovered`.
    """

    state_key: str
    discovered: int
    interacted: int
    mop_reach: int
    by_type: dict[str, tuple[int, int]] = field(default_factory=dict)


@dataclass(frozen=True)
class RunCoverage:
    """Everything one recorded run says about its own UI coverage.

    Attributes:
        trace_path: The `.trace` file this was read from.
        apk: APK file name from the trace filename, or None when the filename
            does not follow rv-platform's run-identity shape.
        repetition: Repetition index, None under the same condition as apk.
        timeout_seconds: Run budget in seconds, part of the run identity —
            it is what keeps two campaigns at different budgets disjoint.
            None under the same condition as apk.
        arm: Tool and variant (e.g. `aperv:sata_mop`), None under the same
            condition as apk.
        status: Whether this run dumped, partially dumped, or did not dump.
        activities: `UICOV-ACT` rows, empty when status is ABSENT.
        states: `UICOV` rows, empty when status is ABSENT. Intra-run use only.
        unparsed_lines: Dump lines that did not parse; nonzero iff status is
            PARTIAL.
        schema_version: Dump line shape this row was parsed under.
    """

    trace_path: Path
    apk: str | None
    repetition: int | None
    timeout_seconds: int | None
    arm: str | None
    status: DumpStatus
    activities: tuple[ActivityCoverage, ...] = ()
    states: tuple[StateCoverage, ...] = ()
    # Dump lines that did not parse — a truncated tail being the expected cause.
    # Counted rather than raised: the run stays in the report either way.
    unparsed_lines: int = 0
    schema_version: int = DUMP_SCHEMA_VERSION

    @property
    def has_dump(self) -> bool:
        return self.status is not DumpStatus.ABSENT


@dataclass(frozen=True)
class DumpPresence:
    """
    A dump-presence rate that cannot be quoted without its denominator.

    INV-APV-37: a figure computed over the runs that dumped must never be
    mistaken for a figure over all runs, so the rate is not exposed as a bare
    float anywhere in this module.

    Attributes:
        runs_with_dump: Runs whose trace carried at least one dump line.
        runs_total: Runs considered, including those that dumped nothing.
    """

    runs_with_dump: int
    runs_total: int

    @property
    def rate(self) -> float:
        """Fraction of runs carrying a dump; 0.0 when no run was considered."""
        return self.runs_with_dump / self.runs_total if self.runs_total else 0.0

    def __str__(self) -> str:
        return f"{self.runs_with_dump}/{self.runs_total} ({100 * self.rate:.1f}%)"


def _parse_fields(payload: str) -> dict[str, str]:
    """
    Split a dump payload into its `key=value` tokens.

    Whitespace-delimited because no value contains a space: state keys, activity
    names and the byType list are all single tokens. `partition` rather than
    `split` because state keys legally contain `=` inside `@[W=3]`.

    Args:
        payload: The dump line text after its tag, never the whole line.

    Returns:
        {key: value} for every token that carried a `=`. Tokens without one are
        dropped rather than raising, so a truncated tail degrades to missing
        keys, which the callers turn into a PARTIAL status.
    """
    fields: dict[str, str] = {}
    for token in payload.split():
        key, separator, value = token.partition("=")
        if separator:
            fields[key] = value
    return fields


def _parse_by_type(raw: str) -> dict[str, tuple[int, int]]:
    """Parse `TYPE:interacted/discovered,...` into {type: (interacted, discovered)}.

    Entries that do not match are skipped, not reported: byType is a breakdown
    of totals that are read from their own fields, so a truncated tail here
    costs detail without invalidating the line.
    """
    by_type: dict[str, tuple[int, int]] = {}
    for entry in raw.split(","):
        match = _BY_TYPE_ENTRY.match(entry)
        if match:
            by_type[match.group("type")] = (
                int(match.group("interacted")),
                int(match.group("discovered")),
            )
    return by_type


def _parse_activity_line(payload: str) -> ActivityCoverage | None:
    """Parse one `UICOV-ACT` payload, or None when it is incomplete.

    Args:
        payload: Line text after the `UICOV-ACT ` tag, not the whole line.

    Returns:
        The Activity row, or None when a required field is missing or
        unparseable — which the caller counts toward a PARTIAL status.
    """
    fields = _parse_fields(payload)
    try:
        # `gap` is deliberately not read: it carries one decimal under
        # Locale.ROOT, while discovered and interacted are integers and are the
        # authoritative fields. Deriving anything from gap would import a
        # rounding the jar applied for display.
        return ActivityCoverage(
            activity=fields["activity"],
            discovered=int(fields["discovered"]),
            interacted=int(fields["interacted"]),
            live_states=int(fields["liveStates"]),
            by_type=_parse_by_type(fields.get("byType", "")),
        )
    except (KeyError, ValueError):
        return None


def _parse_state_line(payload: str) -> StateCoverage | None:
    """Parse one `UICOV` payload, or None when it is incomplete.

    Args:
        payload: Line text after the `UICOV ` tag, not the whole line.

    Returns:
        The state row, or None when a required field is missing or
        unparseable — which the caller counts toward a PARTIAL status.
    """
    fields = _parse_fields(payload)
    try:
        return StateCoverage(
            state_key=fields["state"],
            discovered=int(fields["discovered"]),
            interacted=int(fields["interacted"]),
            mop_reach=int(fields["mopReach"]),
            by_type=_parse_by_type(fields.get("byType", "")),
        )
    except (KeyError, ValueError):
        return None


def _split_run_identity(
    trace_path: Path,
) -> tuple[str | None, int | None, int | None, str | None]:
    """Recover (apk, repetition, timeout, arm) from the trace filename.

    Args:
        trace_path: Path whose name carries the run identity.

    Returns:
        (apk, repetition, timeout, arm), or all four as None when the name does
        not follow the expected shape. A file that cannot be attributed to a run
        is still parsed and still reported — dropping it would remove a run from
        the denominator (INV-APV-37).
    """
    key = try_parse_run_filename(trace_path)
    if key is None:
        return None, None, None, None
    return key.apk, key.repetition, key.timeout_s, key.arm


def parse_run(trace_path: Path | str) -> RunCoverage:
    """
    Parse one run's trace file into its coverage rows and dump status.

    A run with no dump line at all is ABSENT — reported, never dropped. A run
    whose dump lines do not all parse is PARTIAL, and every line that did parse
    is retained: the expected cause is a tail truncated by the process being
    killed mid-write, and discarding the run would throw away the complete lines
    that precede the cut.

    Args:
        trace_path: Path to a recorded `.trace` file. Never written to.

    Returns:
        The run's coverage rows and status, with the run identity recovered from
        the filename where the filename allows it.

    Raises:
        OSError: When the file cannot be opened. A caller pointing at a
            nonexistent path is a usage error, and is kept distinct from a run
            that legitimately has no dump — the latter returns ABSENT.
    """
    trace_path = Path(trace_path)
    apk, repetition, timeout_seconds, arm = _split_run_identity(trace_path)

    activities: list[ActivityCoverage] = []
    states: list[StateCoverage] = []
    unparsed = 0

    # Read as bytes and decode per line: a trace killed mid-write can end on a
    # partial multi-byte sequence, which would abort a text-mode read of the
    # whole file and lose the complete lines before it.
    with open(trace_path, "rb") as trace_file:
        for raw_line in trace_file:
            if b"UICOV" not in raw_line:
                continue
            line = raw_line.decode("utf-8", errors="replace")
            activity_at = line.find(_ACTIVITY_TAG)
            if activity_at >= 0:
                parsed = _parse_activity_line(line[activity_at + len(_ACTIVITY_TAG) :])
                if parsed is None:
                    unparsed += 1
                else:
                    activities.append(parsed)
                continue
            state_at = line.find(_STATE_TAG)
            if state_at >= 0:
                state = _parse_state_line(line[state_at + len(_STATE_TAG) :])
                if state is None:
                    unparsed += 1
                else:
                    states.append(state)

    if not activities and not states and not unparsed:
        status = DumpStatus.ABSENT
    elif unparsed:
        status = DumpStatus.PARTIAL
    else:
        status = DumpStatus.COMPLETE

    return RunCoverage(
        trace_path=trace_path,
        apk=apk,
        repetition=repetition,
        timeout_seconds=timeout_seconds,
        arm=arm,
        status=status,
        activities=tuple(activities),
        states=tuple(states),
        unparsed_lines=unparsed,
    )


def parse_tree(root: Path | str) -> list[RunCoverage]:
    """
    Parse every recorded run under a results tree, in stable filename order.

    Args:
        root: Directory holding recorded runs at any depth.

    Returns:
        One RunCoverage per `.trace` file found — including the runs with no
        dump, which is the whole point of the denominator (INV-APV-37).
    """
    root = Path(root)
    return [parse_run(trace) for trace in sorted(root.rglob("*.trace"))]


def dump_presence(runs: list[RunCoverage]) -> DumpPresence:
    """Count how many of these runs carry a dump, keeping the denominator."""
    return DumpPresence(
        runs_with_dump=sum(1 for run in runs if run.has_dump),
        runs_total=len(runs),
    )


def presence_by_arm(runs: list[RunCoverage]) -> dict[str | None, DumpPresence]:
    """Group runs by arm and report dump presence per arm.

    Args:
        runs: Runs to group. Arms are compared as recorded, so `aperv:sata_mop`
            and `aperv:sata_mop_llm` are separate keys.

    Returns:
        {arm: presence}, each carrying its own denominator (INV-APV-37), sorted
        by arm name. Runs whose filename yielded no arm group under the None
        key rather than being discarded.
    """
    grouped: dict[str | None, list[RunCoverage]] = defaultdict(list)
    for run in runs:
        grouped[run.arm].append(run)
    return {
        arm: dump_presence(arm_runs)
        for arm, arm_runs in sorted(grouped.items(), key=lambda item: str(item[0]))
    }


def aggregate_activities(
    runs: list[RunCoverage],
) -> dict[str, tuple[int, int, int]]:
    """
    Aggregate coverage across runs at Activity grain — the only cross-run join.

    INV-APV-36: this reads `UICOV-ACT` rows exclusively. State keys are never a
    join key here or anywhere else, because they embed a JVM identity hash and
    pair across runs at a measured rate of zero. There is deliberately no
    state-level counterpart to this function.

    Args:
        runs: Runs to aggregate. Runs without a dump contribute nothing and are
            not an error — the caller keeps their count via dump_presence().

    Returns:
        {activity: (discovered, interacted, contributing_runs)}, where discovered
        and interacted are summed over the runs that reported that Activity.
    """
    totals: dict[str, tuple[int, int, int]] = {}
    for run in runs:
        for activity in run.activities:
            discovered, interacted, contributing = totals.get(
                activity.activity, (0, 0, 0)
            )
            totals[activity.activity] = (
                discovered + activity.discovered,
                interacted + activity.interacted,
                contributing + 1,
            )
    return dict(sorted(totals.items()))


def main(argv: list[str] | None = None) -> int:
    """
    Print per-run coverage rows as CSV for a results tree.

    Usage: python -m aperv_tool.analysis.coverage_dump <results_dir>

    The CSV goes to stdout and the presence summary to stderr, so redirecting
    stdout yields a clean data file while the denominators still reach the
    operator (INV-APV-37). Rows are emitted for every run, including the ones
    whose status is ABSENT and whose counts are therefore zero — reading the
    counts without reading the status column is the error this layout guards
    against.

    Args:
        argv: Argument list without the program name. Defaults to sys.argv[1:].

    Returns:
        0. Failures leave through SystemExit rather than a status code.

    Raises:
        SystemExit: With code 2 when the argument count is wrong or the path is
            not a directory.
    """
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print(
            "usage: python -m aperv_tool.analysis.coverage_dump <results_dir>",
            file=sys.stderr,
        )
        raise SystemExit(2)

    root = Path(args[0])
    if not root.is_dir():
        print(f"not a readable run directory: {root}", file=sys.stderr)
        raise SystemExit(2)

    runs = parse_tree(root)
    writer = csv.writer(sys.stdout)
    writer.writerow(
        [
            "apk",
            "repetition",
            "timeout",
            "arm",
            "status",
            "activities",
            "states",
            "discovered",
            "interacted",
        ]
    )
    for run in runs:
        writer.writerow(
            [
                run.apk,
                run.repetition,
                run.timeout_seconds,
                run.arm,
                run.status.value,
                len(run.activities),
                len(run.states),
                sum(activity.discovered for activity in run.activities),
                sum(activity.interacted for activity in run.activities),
            ]
        )

    # The denominator travels with the rate, always (INV-APV-37).
    print(f"# dump presence: {dump_presence(runs)}", file=sys.stderr)
    for arm, presence in presence_by_arm(runs).items():
        print(f"#   {arm}: {presence}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
