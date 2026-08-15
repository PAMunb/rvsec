"""Does this run count? The admissibility rule, in one place.

A task record saying ``COMPLETED`` records that the tool returned without raising
an exception. It does **not** record that the run did what it was supposed to do:
the platform observes the tool's process terminate, not whether it explored. One
run of the decisive campaign was written ``COMPLETED`` after 65 s of an 1800 s
budget, with an 864-byte trace, zero step lines and every coverage counter at
zero — the explorer had died in ``setActivityController`` with a
``DeadObjectException``, the binder gone before coupling. Read as an outcome, that
run is a legitimate zero. It is not one.

This module is the **sole owner** of the per-run verdict (INV-CAN-05). ``gates``
calls it and reimplements none of its predicates, so a run that is excluded is
excluded once, for one reason, printed once. The criteria themselves are the
promotion of ``experimento-comp162/scripts/admissibility.py``, unchanged: the
campaign wrote them for two consumers that had to judge two campaigns by the same
rule, which is precisely the property that would have been lost had the rule been
written a third time here.

``arm_label`` came across in the promotion and is **not** a criterion; it is
identity vocabulary, and it now has its seat beside its inverse in
``run_identity``. It is imported here, so ``liveness.arm_label`` still resolves for
the consumers that reach for it there.

## The criteria, applied per identity ``(apk, arm, replica)``

Blind to the arm and to the direction of the effect:

- **C1** — ``COMPLETED`` with an empty ``error_message``.
- **C2** — ``execution_time_s >= timeout - TEARDOWN_GRACE_S``. Exploration is
  budget-limited **by construction**, so elapsed time is the discriminator; the
  exit code is not, because a dead emulator and an application crash are
  indistinguishable through it.
- **C5** — ``method_coverage > 0`` **and** ``activities_coverage > 0``.

## The exclusion rule

**An inadmissible replica does not drop the application.** It is discarded and the
``(application, arm)`` cell keeps the replicas that remain. That is what replicated
runs are for: a transient failure — an ``adb install`` that caught the device
offline, an emulator that died — says nothing about the application, and letting it
exclude the whole application would throw away good data in three times as many
opportunities as a single-replica campaign has.

**The application leaves when some arm has no admissible replica at all.** There is
then no value for that arm and the pair breaks. The exclusion is therefore **per
application, never per arm**: the test is paired, and removing one arm while keeping
the others unbalances the pair exactly where the data is worst — the bias enters in
the direction of whichever arms survived. cmp163 showed why: on
``org.wikipedia_50595`` the surviving arm would have been the reference one.

What remains to record, and what ``select`` hands back so it can be recorded:
**how many cells were left with fewer replicas than the maximum observed**. A cell's
mean over two replicas is noisier than over three, and that is asymmetry between
cells which the reading must see rather than absorb in silence.

## What this module adds to the promoted rule

The campaign rule answers "is this run admissible". Two further questions are asked
of the same facts, and answering them anywhere else would mean reading the same run
twice under two definitions:

- **The full-budget predicate** (``full_budget``) is C2 named as what it is, so a
  gate can ask it directly instead of matching on a reason string.
- **The corpse signals and the corpse class.** Three independent signals — a trace
  below a size floor, coverage all zero, a named fatal exception — and, beside the
  boolean, a classification of the run by its **last non-empty trace line**. On the
  decisive run that classification refuted the design's own causal story: the runs
  had not died mid-exploration, their teardown had not fit the capture window.

**Admissibility is decided by C1/C2/C5 alone.** The corpse signals are reported
beside it, never folded into it: the rule is the campaign's and stays the campaign's,
and the decisive corpse fails C2 and C5 on its own facts anyway. A run may therefore
be admissible and still carry a signal — that combination is exactly what a reader
needs to see rather than have decided for them.

**Absence is never a signal.** A fact the caller did not supply leaves its signal
unset; it never counts as evidence of a corpse, for the same reason ``not-run`` is
never a pass.
"""

from __future__ import annotations

import glob
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Mapping, Optional, Sequence

from aperv_tool.analysis.run_identity import RunKey, arm_label

# The teardown slack the tool itself uses on both sides: the command's timeout is
# the budget plus this grace, and the completeness floor is the budget minus it.
TEARDOWN_GRACE_S = 45

# The size below which a trace is a corpse signal. Measured on cmp162's 1458
# traces: the smallest is 251,204 bytes and the fifth percentile is 1.06 MB, while
# the decisive run's corpse was 864 bytes against a second-smallest of 2.4 MB in
# its own campaign. 64 KiB sits roughly four times below the smallest healthy trace
# ever observed and seventy-five times above the corpse, so the floor separates the
# two populations without a grey zone in either campaign.
TRACE_FLOOR_BYTES = 64 * 1024

#: The three criteria of the promoted rule, in the order a reason tuple lists them.
CRITERIA = ("C1", "C2", "C5")

# The three corpse signals, named so a report can print which ones fired rather
# than asserting "corpse". They are independent by construction: a trace can be
# truncated with coverage intact, and an exception can be named with a full trace.
SIGNAL_TRACE_BELOW_FLOOR = "trace_below_floor"
SIGNAL_COVERAGE_ALL_ZERO = "coverage_all_zero"
SIGNAL_FATAL_EXCEPTION = "fatal_exception"
SIGNALS = (SIGNAL_TRACE_BELOW_FLOOR, SIGNAL_COVERAGE_ALL_ZERO, SIGNAL_FATAL_EXCEPTION)

#: How a run's writing stopped, read from its last non-empty trace line.
CorpseClass = Literal[
    "normal_end", "crash", "cut_during_teardown", "cut_elsewhere", "n/a"
]

# The markers, each observed in cmp162's own traces. `crash` is checked first
# because a crash notice is printed wherever the crash happened, including after
# the closing report, and the last line is by definition the last thing that
# happened.
#
# `crash` means the last thing written was a fatal-termination notice. It does not
# distinguish the explorer dying from the application under test dying: the Monkey
# prints its crash notice for the latter, and separating the two needs the logcat,
# not this line.
_CRASH_MARKERS = (
    "** System appears to have crashed",
    "FATAL EXCEPTION",
    "// CRASH",
    "// NOT RESPONDING",
)

# The process's closing report. `## Network stats:` is the Monkey's last word and
# is the last line of the large majority of cmp162's healthy traces.
_NORMAL_END_MARKERS = (
    "## Network stats:",
    "// Monkey finished",
)

# The shutdown sequence that follows the declared end of exploration: the NDJSON
# `RUN_END` record, the package being stopped, and the statistics dump the jar
# prints on its way out (`[APE]      0  BAD_STATE` and its siblings).
_TEARDOWN_MARKERS = (
    '"type":"RUN_END"',
    "Try to stop package",
)


def _looks_like_statistics_dump(line: str) -> bool:
    """A line of the jar's closing counter table, e.g. ``[APE]     10  FILL_BUFFER``."""
    parts = line.split()
    return (
        len(parts) == 3
        and parts[0] == "[APE]"
        and parts[1].isdigit()
        and parts[2].isupper()
    )


def _names_a_throwable(line: str) -> bool:
    """A Java throwable named on the line, e.g. ``android.os.DeadObjectException``."""
    for token in line.replace("(", " ").replace(")", " ").replace(":", " ").split():
        bare = token.strip(",;")
        if bare.endswith("Exception") or bare.endswith("Error"):
            return True
    return False


def classify_last_line(line: Optional[str]) -> CorpseClass:
    """What was happening when the trace stopped being written.

    Args:
        line: The run's last non-empty trace line, as the caller read it, or None
            when the trace is absent or empty.

    Returns:
        ``normal_end`` when the line is the process's closing report;
        ``crash`` when it names a fatal termination; ``cut_during_teardown`` when
        it belongs to the shutdown sequence that follows the declared end of
        exploration; ``cut_elsewhere`` for any other line, which means the process
        stopped mid-exploration with nothing announcing it; ``n/a`` when there is
        no line to read.
    """
    if line is None:
        return "n/a"
    stripped = line.strip()
    if not stripped:
        return "n/a"
    if any(marker in stripped for marker in _CRASH_MARKERS):
        return "crash"
    if _names_a_throwable(stripped):
        return "crash"
    if any(marker in stripped for marker in _NORMAL_END_MARKERS):
        return "normal_end"
    if any(marker in stripped for marker in _TEARDOWN_MARKERS):
        return "cut_during_teardown"
    if _looks_like_statistics_dump(stripped):
        return "cut_during_teardown"
    return "cut_elsewhere"


def floor_for(timeout_s: int) -> int:
    """C2's floor for a budget."""
    return timeout_s - TEARDOWN_GRACE_S


def _absent(value: Any) -> bool:
    """True for a value the caller did not supply, ``NaN`` included.

    Frames carry missing numbers as ``NaN``, and ``NaN`` compares false against
    every threshold, which would silently turn "not measured" into "did not pass".
    It is recognised here without importing the frame library: this module judges
    records, not frames.
    """
    if value is None:
        return True
    return isinstance(value, float) and math.isnan(value)


@dataclass(frozen=True, slots=True)
class RunFacts:
    """Everything the verdict is allowed to depend on, for one run.

    Only facts, never files: the module opens nothing except through
    ``judge_identities``, so a caller with a frame, a caller with a task record and
    a test with three literals all reach the same verdict by the same path.

    Attributes:
        identity: The run's key. Carried so a reason can name the run it belongs to.
        task_state: The task record's state, ``COMPLETED`` or otherwise.
        error_message: The task record's error message. A record can be
            ``COMPLETED`` and still carry one, which C1 treats as a failure.
        execution_time_s: Observed wall-clock duration of the run, from
            ``tasks.json`` / ``performance.csv`` and **never from a trace**
            (INV-CAN-08) — no trace carries an end-of-run summary.
        declared_timeout_s: The budget the run was given, from its identity.
        method_coverage: Fraction or count of methods covered, as recorded.
        activities_coverage: Fraction or count of activities covered, as recorded.
        trace_bytes: Size of the run's trace on disk, or None when not measured.
        fatal_exception: The name of a fatal exception attributed to the run, or
            None. A caller that did not look supplies None, which is not a signal.
        last_trace_line: The run's last non-empty trace line, or None.
    """

    identity: RunKey
    task_state: Optional[str]
    error_message: Optional[str] = None
    execution_time_s: Optional[float] = None
    declared_timeout_s: Optional[int] = None
    method_coverage: Optional[float] = None
    activities_coverage: Optional[float] = None
    trace_bytes: Optional[int] = None
    fatal_exception: Optional[str] = None
    last_trace_line: Optional[str] = None

    @property
    def budget_s(self) -> int:
        """The declared budget, defaulting to the identity's timeout.

        The two are the same number in every campaign written so far; the field
        exists so a caller judging a run against a budget the filename does not
        carry can say so instead of renaming the run.
        """
        if _absent(self.declared_timeout_s):
            return self.identity.timeout_s
        return int(self.declared_timeout_s)

    @classmethod
    def from_mapping(cls, row: Mapping[str, Any]) -> "RunFacts":
        """Build the facts from one row of a Layer-0 frame.

        The column contract is the attribute names above, plus the four of
        ``run_identity.IDENTITY_COLUMNS`` for the identity. Every column except
        those four is optional and missing means unmeasured, not zero.

        **Two column names here are the loader's, not this class's attributes**,
        and both were wrong until the end-to-end smoke ran. The replica column is
        ``rep`` — ``repetition`` is the ``RunKey`` attribute and the key inside a
        raw ``tasks.json`` config, neither of which is a frame column — and the
        task state is ``state``, not ``task_state``. The first made
        ``gates.run_all`` unable to accept a loaded frame at all; the second was
        worse, because it did not raise: every run read as a null state, failed
        C1, and the whole campaign came back inadmissible with a plausible
        reason. A frame column and an attribute that share a meaning are not
        thereby the same string.

        Args:
            row: One record of the frame, as a mapping.

        Returns:
            The ``RunFacts``.

        Raises:
            KeyError: One of the four identity columns is absent. The identity is
                the one thing that cannot be defaulted — a verdict about a run
                nobody can name is not a verdict.
        """
        identity = RunKey(
            apk=row["apk"],
            repetition=int(row["rep"]),
            timeout_s=int(row["timeout_s"]),
            arm=row["arm"],
        )

        def get(name: str) -> Any:
            value = row.get(name)
            return None if _absent(value) else value

        return cls(
            identity=identity,
            task_state=get("state"),
            error_message=get("error_message"),
            execution_time_s=get("execution_time_s"),
            declared_timeout_s=get("declared_timeout_s"),
            method_coverage=get("method_coverage"),
            activities_coverage=get("activities_coverage"),
            trace_bytes=get("trace_bytes"),
            fatal_exception=get("fatal_exception"),
            last_trace_line=get("last_trace_line"),
        )


@dataclass(frozen=True, slots=True)
class Admissibility:
    """The verdict on one run.

    Attributes:
        admissible: C1 and C2 and C5. Nothing else moves it.
        reasons: Every criterion the run failed, then every corpse signal it fired,
            in a fixed order. An admissible run with a signal is possible and is
            reported that way on purpose.
        corpse_class: The run's last non-empty trace line, classified.
    """

    admissible: bool
    reasons: tuple[str, ...]
    corpse_class: CorpseClass

    @property
    def failed_criteria(self) -> tuple[str, ...]:
        """The C-criteria among the reasons — the campaign rule's own answer."""
        return tuple(reason for reason in self.reasons if reason in CRITERIA)

    @property
    def corpse_signals(self) -> tuple[str, ...]:
        """The corpse signals among the reasons."""
        return tuple(reason for reason in self.reasons if reason in SIGNALS)

    @property
    def is_corpse(self) -> bool:
        """All three signals fired.

        All three, not any: the detector's value on the decisive run was that it
        returned exactly one run out of 360 with no grey zone, and each signal alone
        has a benign reading — a short trace on an application with three screens, a
        zero-coverage run of an application that never started, an exception the run
        survived.
        """
        return len(self.corpse_signals) == len(SIGNALS)


def full_budget(run: RunFacts) -> bool:
    """Did the run get through its budget (C2)?

    A run that ended early is an execution failure, not a low outcome, and the
    difference is invisible in every outcome column — which is why this is asked
    before an outcome is read.

    The floor is the budget **minus** the teardown grace rather than the budget
    itself. The tool stops exploring up to ``TEARDOWN_GRACE_S`` before the budget
    expires so its teardown fits inside the command's timeout, so a literal
    "duration >= timeout" would be a predicate the tool is built never to satisfy
    from the exploration side. Measured on cmp162's 1486 task records the observed
    durations sit around a median of 366 s against a 300 s budget — install and
    teardown are inside the number — while the early deaths sit at 51-61 s, two
    populations the floor separates cleanly.

    Args:
        run: The run's facts.

    Returns:
        True when the observed duration reaches the floor. An unmeasured duration
        is False: a run whose duration nobody recorded has not been shown to have
        run its budget.
    """
    if _absent(run.execution_time_s):
        return False
    return float(run.execution_time_s) >= floor_for(run.budget_s)


def corpse_detectable(run: RunFacts) -> bool:
    """Were all three corpse facts measured for this run?

    A run with no trace size, no coverage and no exception name fires no signal —
    exactly like a healthy run. The two are not the same answer, and a caller that
    reported "no corpse" over runs nobody looked at would be reporting the absence
    of a measurement as the absence of a corpse.

    Args:
        run: The run's facts.

    Returns:
        True when the trace size, both coverage counters and the exception field
        were all supplied. The exception field is supplied as ``None`` by a caller
        that looked and found none, which is why it is asked of the coverage and
        size facts instead.
    """
    return not (
        _absent(run.trace_bytes)
        or _absent(run.method_coverage)
        or _absent(run.activities_coverage)
    )


def verdict(
    run: RunFacts, *, trace_floor_bytes: int = TRACE_FLOOR_BYTES
) -> Admissibility:
    """Judge one run.

    Args:
        run: The run's facts.
        trace_floor_bytes: The size below which a trace fires the corpse signal.
            Overridable because it is a property of the campaign's traces, not of
            the rule; the default is measured and documented on
            ``TRACE_FLOOR_BYTES``.

    Returns:
        The ``Admissibility``: the boolean, every failed criterion and fired signal
        as reasons, and the corpse class.
    """
    reasons: list[str] = []

    if run.task_state != "COMPLETED" or run.error_message:
        reasons.append("C1")
    if not full_budget(run):
        reasons.append("C2")
    if not (_positive(run.method_coverage) and _positive(run.activities_coverage)):
        reasons.append("C5")

    admissible = not reasons

    if not _absent(run.trace_bytes) and int(run.trace_bytes) < trace_floor_bytes:
        reasons.append(SIGNAL_TRACE_BELOW_FLOOR)
    if _zero(run.method_coverage) and _zero(run.activities_coverage):
        reasons.append(SIGNAL_COVERAGE_ALL_ZERO)
    if run.fatal_exception:
        reasons.append(SIGNAL_FATAL_EXCEPTION)

    return Admissibility(
        admissible=admissible,
        reasons=tuple(reasons),
        corpse_class=classify_last_line(run.last_trace_line),
    )


def _positive(value: Any) -> bool:
    """Strictly greater than zero, with an unmeasured value counting as not."""
    return not _absent(value) and float(value) > 0


def _zero(value: Any) -> bool:
    """Measured and exactly zero. An unmeasured value is not a zero."""
    return not _absent(value) and float(value) == 0


def judge_identities(
    tasks_glob: str,
    timeout_s: int,
    *,
    trace_floor_bytes: int = TRACE_FLOOR_BYTES,
) -> dict[tuple[str, str, int], list[str]]:
    """``(apk, arm, replica)`` -> the criteria it failed (empty means admissible).

    Judges by identity, never by record: a resume **appends** a record instead of
    overwriting, so a recovered identity holds two — the ``ERROR`` and the
    ``COMPLETED``. The identity's best record is the one that decides.

    Only the C-criteria appear in the returned lists. The corpse signals need facts
    ``tasks.json`` does not carry — the trace's size and its last line — so a caller
    that wants them assembles ``RunFacts`` and calls ``verdict`` directly.

    Args:
        tasks_glob: A glob over the campaign's ``tasks.json`` files.
        timeout_s: The declared budget, which the task record does not carry.
        trace_floor_bytes: Passed through to ``verdict``; it changes no C-criterion
            and is accepted so the two entry points cannot diverge.

    Returns:
        The verdict per identity, keyed as the campaign's consumers key it.
    """
    judged: dict[tuple[str, str, int], list[str]] = {}
    for path in sorted(glob.glob(tasks_glob)):
        document = json.loads(Path(path).read_text())
        records = document["tasks"] if isinstance(document, dict) else document
        best: dict[tuple[str, str, int], dict] = {}
        for task in records:
            config = task.get("config") or {}
            tool_config = config.get("tool_config") or {}
            key = (
                config.get("apk_name"),
                arm_label(tool_config.get("name"), tool_config.get("variant")),
                config.get("repetition"),
            )
            result = task.get("result") or {}
            if key not in best or result.get("state") == "COMPLETED":
                best[key] = result
        for key, result in best.items():
            coverage = result.get("coverage_metrics") or {}
            facts = RunFacts(
                identity=RunKey(
                    apk=key[0], repetition=key[2], timeout_s=timeout_s, arm=key[1]
                ),
                task_state=result.get("state"),
                error_message=result.get("error_message"),
                execution_time_s=result.get("execution_time_seconds") or 0,
                declared_timeout_s=timeout_s,
                method_coverage=coverage.get("method_coverage"),
                activities_coverage=coverage.get("activities_coverage"),
            )
            judged[key] = list(
                verdict(facts, trace_floor_bytes=trace_floor_bytes).failed_criteria
            )
    return judged


def select(
    judged: Mapping[tuple[str, str, int], Sequence[str]], arms: Sequence[str]
) -> dict:
    """Apply the exclusion rule. Returns what the reading has to report.

    Args:
        judged: The per-identity verdicts, as ``judge_identities`` returns them.
        arms: The campaign's arms, supplied as data.

    Returns:
        A mapping with:
            ``kept`` — the applications entering the paired analysis, sorted;
            ``excluded`` — ``{apk: {arm: [replica reasons]}}`` for those that left;
            ``good_reps`` — ``{(apk, arm): [admissible replicas]}``;
            ``dropped_reps`` — ``{(apk, arm): [(replica, reasons)]}`` discarded
            inside a cell that survived;
            ``partial_cells`` — surviving cells with fewer replicas than the
            maximum observed;
            ``max_reps`` — that maximum.
    """
    by_cell: dict[tuple[str, str], dict[int, list[str]]] = defaultdict(dict)
    for (apk, arm, replica), failed in judged.items():
        by_cell[(apk, arm)][replica] = list(failed)

    apks = sorted({apk for apk, _ in by_cell})
    max_reps = max((len(cell) for cell in by_cell.values()), default=0)

    kept: list[str] = []
    excluded: dict[str, dict[str, list[str]]] = {}
    good_reps: dict[tuple[str, str], list[int]] = {}
    dropped_reps: dict[tuple[str, str], list[tuple[int, list[str]]]] = {}

    for apk in apks:
        cells = {arm: by_cell.get((apk, arm), {}) for arm in arms}
        good = {
            arm: sorted(replica for replica, failed in cell.items() if not failed)
            for arm, cell in cells.items()
        }
        dead = {
            arm: [
                f"rep{replica}:{'+'.join(failed)}"
                for replica, failed in sorted(cell.items())
                if failed
            ]
            for arm, cell in cells.items()
            if not good[arm]
        }
        if dead or any(not replicas for replicas in good.values()):
            # An arm with no admissible replica — or with no execution at all. The
            # pair breaks, and the application leaves whole.
            excluded[apk] = {
                arm: dead.get(arm) or ["no execution"] for arm in arms if not good[arm]
            }
            continue
        kept.append(apk)
        for arm in arms:
            good_reps[(apk, arm)] = good[arm]
            bad = [
                (replica, cells[arm][replica])
                for replica in sorted(cells[arm])
                if cells[arm][replica]
            ]
            if bad:
                dropped_reps[(apk, arm)] = bad

    partial = {
        cell: len(replicas)
        for cell, replicas in good_reps.items()
        if len(replicas) < max_reps
    }
    return {
        "kept": kept,
        "excluded": excluded,
        "good_reps": good_reps,
        "dropped_reps": dropped_reps,
        "partial_cells": partial,
        "max_reps": max_reps,
    }


def report(
    selection: Mapping[str, Any], arms: Sequence[str], total_observed: int
) -> None:
    """Print the admissibility block. The same shape for every consumer."""
    print(f"applications observed: {total_observed}")
    print(f"applications in the paired analysis: {len(selection['kept'])}")
    if selection["excluded"]:
        print(
            f"excluded ({len(selection['excluded'])}) — arm with no admissible replica:"
        )
        for apk, dead_arms in sorted(selection["excluded"].items()):
            for arm, reasons in sorted(dead_arms.items()):
                print(f"  {apk:44s} {arm:24s} {', '.join(reasons)}")
    else:
        print(
            "no exclusions — every arm of every application has an admissible replica"
        )

    dropped = selection["dropped_reps"]
    n_dropped = sum(len(bad) for bad in dropped.values())
    print()
    print(
        f"replicas discarded inside a cell that SURVIVED: {n_dropped} "
        f"in {len(dropped)} cell(s)"
    )
    for (apk, arm), bad in sorted(dropped.items())[:15]:
        detail = ", ".join(f"rep{replica}:{'+'.join(f)}" for replica, f in bad)
        print(f"  {apk[:40]:40s} {arm:24s} {detail}")
    if len(dropped) > 15:
        print(f"  ... and {len(dropped) - 15} further cell(s)")

    partial = selection["partial_cells"]
    if partial:
        distribution: dict[int, int] = defaultdict(int)
        for count in partial.values():
            distribution[count] += 1
        summary = ", ".join(
            f"{cells} cell(s) with {count} replica(s)"
            for count, cells in sorted(distribution.items())
        )
        print()
        print(
            f"cells with fewer than {selection['max_reps']} replicas: "
            f"{len(partial)} — {summary}"
        )
        print("Their means are noisier than the complete cells'. That is asymmetry")
        print(
            "between cells, and it is here to be seen rather than absorbed in silence."
        )
