"""
Join the teardown UI-coverage dump onto a run's step timeline by state key.

An earlier reading of the artefacts concluded that UI coverage "is not in the
NDJSON stream and never joins a step record". That is refuted by measurement: the
`[APE-RV] UICOV state=` line and the NDJSON `STATE.key` carry byte-identical
strings, and over 120 recorded `aperv` runs the two sides matched **3801 states
against 3801 keys with zero orphans in either direction**. The join key is
mechanical, exact, and total — no normalisation, no fuzzy match.

**What the join buys is the rest of the dump line**, which exists nowhere in the
NDJSON: `discovered`, `interacted` and the per-action-type breakdown
`byType=<type>:<interacted>/<discovered>`, i.e. widget-level coverage per state,
attachable to the step that was standing on that state. What it does *not* buy is
`mopReach`: over 4719 state/activity pairs it agrees with the activity's own MOP
flag in 100 % of cases, because it is `activityHasMop(state.getActivity())`
replicated at state grain. It is carried because the dump carries it, and it is
not a state-level fact.

**Two properties of the dump decide the shape of everything here.**

*The payload is cumulative over the whole run and is emitted once, at teardown* —
never per visit. A state visited nine times contributes one dump line whose
counters cover all nine visits, so the joined `discovered` / `interacted` /
`byType` describe the run, not the step they are attached to. Every emitted row
therefore carries `uicov_scope` saying so, and no consumer may read a joined
counter as "what this step saw".

*The key is intra-run only* (INV-APV-36, INV-CAN-13). `StateKey.toString()`
embeds the JVM identity hash of an object that overrides neither `equals` nor
`hashCode`, and the measured cross-replica Jaccard between two runs of the same
(application, arm) is 0.000 at mean, median and maximum. So this module joins
inside one run and `combine_runs` refuses, by exception, to carry a state key
across runs: the honest cross-run grain is the Activity, and it is the one
`combine_runs` will produce.

Offline and read-only over recorded artefacts (INV-APV-35): no device, no
emulator, no `adb`, and nothing is written.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal, Mapping, Sequence

import pandas as pd

from aperv_tool.analysis.coverage_dump import RunCoverage, StateCoverage
from aperv_tool.analysis.trace_ndjson import StepRow

#: What a joined counter describes. The dump is written once at teardown with
#: counters accumulated over the whole run, so a joined value is a property of
#: the run and of the state — never of the step it rides on. The label travels in
#: the frame so that a reader who never saw this docstring still cannot mistake
#: it for a per-visit measurement.
CUMULATIVE_SCOPE = "cumulative_per_run"

#: The grains `combine_runs` will produce. `state` is absent by design, not by
#: omission: see `CrossRunStateKey`.
Grain = Literal["activity"]


class CrossRunStateKey(ValueError):
    """A caller asked for a state key to survive a run boundary.

    Raised rather than answered. A state key is a run-local identifier, so a
    frame that carried one across runs would look joinable and would silently
    pair unrelated screens — the measured cross-run agreement is zero, which
    means such a join produces no true matches at all, only plausible ones.
    """


@dataclass(frozen=True)
class JoinTotals:
    """What the join saw on both of its sides, for one run.

    The counts are the evidence that the join is total; they are reported rather
    than asserted, so a run where it is not total is visible instead of absent.

    Attributes:
        dump_states: `UICOV` rows the teardown dump carried.
        step_state_keys: Distinct state keys the step stream stood on.
        matched: Keys present on both sides.
        orphan_dump_states: Dump rows whose key no step ever stood on. Legitimate
            when a state was reached by a transition the agent never selected
            from; measured zero on the recorded corpus.
        orphan_step_keys: Step keys with no dump row — what a truncated teardown
            produces, and what makes `uicov_present` False on a step.
    """

    dump_states: int
    step_state_keys: int
    matched: int
    orphan_dump_states: int
    orphan_step_keys: int

    @property
    def total(self) -> bool:
        """Whether both sides matched completely, orphans on neither side."""
        return self.orphan_dump_states == 0 and self.orphan_step_keys == 0


#: The per-step frame's columns, declared so an empty run yields a frame of the
#: same shape as a populated one — a caller concatenating runs must not have the
#: schema depend on whether a particular run dumped.
COLUMNS = (
    "step",
    "t_rel_ms",
    "activity",
    "state_key",
    "uicov_present",
    "uicov_discovered",
    "uicov_interacted",
    "uicov_mop_reach",
    "uicov_scope",
)


def state_index(coverage: RunCoverage) -> Mapping[str, StateCoverage]:
    """
    Index one run's `UICOV` rows by their state key.

    This is the join's whole mechanism, exposed on its own because `step_bundle`
    attaches the same payload to a step record rather than to a frame row, and
    two indexes built two ways is how two consumers come to disagree about which
    state a step was on.

    Args:
        coverage: The run's parsed teardown dump. A run whose dump is absent or
            truncated yields a smaller index, never an error — the loss is the
            dump's, and `RunCoverage.status` already carries it.

    Returns:
        `{state_key: StateCoverage}`. A key repeated in the dump keeps its last
        row, which is the jar's own write order.
    """
    return {state.state_key: state for state in coverage.states}


def totals(state_keys: Iterable[str], coverage: RunCoverage) -> JoinTotals:
    """
    Measure both sides of the join for one run.

    Exposed beside `join` because `step_bundle` attaches the payload to step
    records rather than to frame rows and still owes the same accounting; two
    places counting orphans two ways is how a join reports itself total in one
    report and partial in another.

    Args:
        state_keys: The state keys the run's steps stood on. Duplicates are
            collapsed here, so a caller may pass the raw per-step sequence.
        coverage: The run's teardown dump.

    Returns:
        The counts on both sides and their orphans.
    """
    dump_keys = set(state_index(coverage))
    seen = set(state_keys)
    return JoinTotals(
        dump_states=len(dump_keys),
        step_state_keys=len(seen),
        matched=len(dump_keys & seen),
        orphan_dump_states=len(dump_keys - seen),
        orphan_step_keys=len(seen - dump_keys),
    )


def join(
    rows: Iterable[StepRow], coverage: RunCoverage
) -> tuple[pd.DataFrame, JoinTotals]:
    """
    Attach each step's `UICOV` payload to it, for one run.

    Args:
        rows: The run's steps, as `trace_ndjson.TraceReader` yields them. Read
            once; an iterator is consumed.
        coverage: The same run's teardown dump, from `coverage_dump.parse_run`.
            Pairing a dump with a different run's steps is the caller's error and
            shows up as a join with no matches, not as an exception — the keys of
            two runs are disjoint by construction.

    Returns:
        `(frame, totals)`. The frame carries one row per step in file order with
        the joined counters and `uicov_scope`, and it carries **no run identity
        column**: the state key it is keyed on has no meaning outside this run.
        `totals` reports both sides and their orphans.
    """
    index = state_index(coverage)
    records = []
    seen_keys: set[str] = set()
    for row in rows:
        seen_keys.add(row.state_key)
        state = index.get(row.state_key)
        records.append(
            {
                "step": row.step,
                "t_rel_ms": row.t_rel_ms,
                "activity": row.activity,
                "state_key": row.state_key,
                "uicov_present": state is not None,
                "uicov_discovered": None if state is None else state.discovered,
                "uicov_interacted": None if state is None else state.interacted,
                "uicov_mop_reach": None if state is None else state.mop_reach,
                "uicov_scope": CUMULATIVE_SCOPE,
            }
        )

    return pd.DataFrame(records, columns=list(COLUMNS)), totals(seen_keys, coverage)


def combine_runs(
    frames: Sequence[tuple[str, pd.DataFrame]], *, grain: Grain = "activity"
) -> pd.DataFrame:
    """
    Stack several runs' joined frames at a grain that survives a run boundary.

    Args:
        frames: `(run_id, frame)` pairs, each frame as `join` returned it. The
            run id is supplied here rather than carried in the frame, because a
            per-run frame that already had one would invite exactly the
            concatenation this function exists to police.
        grain: The only admissible value is `activity`. `state` is rejected —
            see Raises.

    Returns:
        One row per `(run_id, activity)` with the coverage counters summed over
        the run's distinct states and `uicov_scope` preserved. Activity names are
        plain class names and do survive a process boundary, which is what makes
        this grain comparable across runs.

    Raises:
        CrossRunStateKey: `grain="state"` was requested. The key embeds a JVM
            identity hash; pairing on it across runs matches nothing truthfully
            and matches plenty plausibly.
    """
    if grain != "activity":
        raise CrossRunStateKey(
            f"grain={grain!r}: a state key is run-local (INV-APV-36) and never "
            "joins across runs; the cross-run grain is the activity"
        )

    parts = []
    for run_id, frame in frames:
        # One row per distinct state, not per step: the counters are cumulative
        # per run, so summing them over steps would multiply each state's dump by
        # how many times the run stood on it.
        per_state = frame[frame["uicov_present"]].drop_duplicates(subset=["state_key"])
        grouped = (
            per_state.groupby("activity", as_index=False)[
                ["uicov_discovered", "uicov_interacted"]
            ]
            .sum()
            .assign(run_id=run_id, uicov_scope=CUMULATIVE_SCOPE)
        )
        parts.append(grouped)

    if not parts:
        return pd.DataFrame(
            columns=[
                "run_id",
                "activity",
                "uicov_discovered",
                "uicov_interacted",
                "uicov_scope",
            ]
        )
    combined = pd.concat(parts, ignore_index=True)
    return combined[
        ["run_id", "activity", "uicov_discovered", "uicov_interacted", "uicov_scope"]
    ]
