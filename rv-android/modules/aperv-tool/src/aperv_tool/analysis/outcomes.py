"""Outcome builders, with every convention supplied by the caller.

An outcome is what a run produced, reduced to the number an estimator will
consume: how many distinct violations, whether the run detected anything at all,
how long it took to detect the first one, how much of the corpus was captured by
a given budget. Each of those reductions hides a decision, and the decisions are
not interchangeable:

- **The dedup key.** ``mop_errors_unique`` is recomputed per run over the key
  ``(class, method, spec)``; the earlier message-level definition disagreed with
  it on **5,749 of 16,137 runs (35.6 %)**, and neither file said which key it
  held. Both keys are available here, both are labelled, and neither substitutes
  for the other.
- **The replica rule.** A cell with per-replica counts ``[0, 1, 1]`` is detected
  under ``union`` and ``majority`` and undetected under ``unanimity``. All three
  are defensible; only one of them was chosen, and the choice belongs in the
  output.
- **The estimand.** A mean over replicas and a median over replicas are
  different quantities. One campaign file carried a column that was a mean read
  by a later reader as a count, in a header that said neither.

So no builder here has a convention default. The convention arrives as a
parameter, it travels into the label of what comes back, and a caller who omits
one gets ``FreezeItemUnset`` naming it rather than a number computed under
someone else's decision (INV-CAN-10, INV-CAN-11). The error type is imported
from ``corpus`` rather than redeclared: a caller catching one unset freeze item
catches all of them.

Nothing here reads a file or knows what question it serves. The input is a tidy
frame at whatever grain the caller declares, and the output is a labelled frame,
series or small record.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Optional, Sequence, Union

import pandas as pd
from scipy.stats import trim_mean

from aperv_tool.analysis.corpus import FreezeItemUnset

#: How replicas of one cell are collapsed into a single binary verdict. Three
#: well-known answers, one function, no default.
ReplicaRule = Literal["majority", "union", "unanimity"]

#: How replicas of one cell are collapsed into a single continuous value. The
#: name travels into the output column, because two of these mixed in one ratio
#: are undetectable once the labels are gone.
Estimand = Literal["mean", "median", "trimmed_mean_10"]

#: Whether a capture curve accumulates within each run or across the campaign.
#: The same arithmetic answers "what does one run find by time t" and "what does
#: the campaign find by time t", and the two are one parameter apart.
CaptureScope = Literal["within_run", "cross_campaign"]

#: The signature key: one violation is the same violation as another when it
#: names the same operation under the same specification. This is the key the
#: sibling Android test-generation study computes its per-run unique count with,
#: and the one a new pipeline must reproduce for the two to be comparable.
DEDUP_KEY_SIGNATURE: tuple[str, ...] = ("class", "method", "spec")

#: The message key: one violation is the same violation as another when the
#: monitor printed the same text. Finer than the signature key — it separates
#: violations of one operation that differ only in their reported parameters —
#: and it is the key the two definitions disagree under.
DEDUP_KEY_MESSAGE: tuple[str, ...] = ("message",)

#: Both keys, by name, so a caller selects one from data and the selection is
#: visible in a configuration file rather than buried in a call site.
DEDUP_KEYS: dict[str, tuple[str, ...]] = {
    "signature": DEDUP_KEY_SIGNATURE,
    "message": DEDUP_KEY_MESSAGE,
}

#: The fraction trimmed from each tail by the ``trimmed_mean_10`` estimand.
TRIM_FRACTION = 0.10

#: The index level holding the replica number in a frame at the run grain. It is
#: the loader's column name, a structural fact of these frames rather than a
#: convention someone chose, so it has a default where the conventions do not.
REPLICA_LEVEL = "rep"


def _labelled(key: Sequence[str]) -> str:
    """The dedup key as it appears in a column name: ``class+method+spec``."""
    return "+".join(key)


def _require(value: Optional[Any], item: str) -> Any:
    """Return ``value``, or raise naming the freeze item that was not supplied.

    Args:
        value: What the caller passed, or None for "not supplied".
        item: The item's name, as the pre-registration calls it.

    Returns:
        ``value`` unchanged.

    Raises:
        FreezeItemUnset: ``value`` is None.
    """
    if value is None:
        raise FreezeItemUnset(
            f"{item}: this is a pre-registration freeze item and has no default; "
            "supply the decided value explicitly"
        )
    return value


def distinct_count(
    stream: pd.DataFrame,
    *,
    dedup_key: Optional[Sequence[str]] = None,
    group_by: Sequence[str],
) -> pd.Series:
    """Distinct events per group, under the dedup key the caller names.

    A group with no event in the stream is **absent from the result, not zero**.
    That is deliberate: this function sees an event stream and cannot know which
    runs existed, so inventing a zero for a run that never ran would be the
    library manufacturing a denominator. Reindex the result against the run
    frame to turn genuine absences into zeros (INV-CAN-04).

    Args:
        stream: Event-grain frame carrying the group columns and the key
            columns.
        dedup_key: The columns whose distinct combinations are counted — one of
            ``DEDUP_KEYS``, or any tuple the caller decides on.
        group_by: The grain the count is taken at, e.g. the run identity. Must
            name at least one column: a count with no grain is a different
            question, and ``capture_curve`` is where that one is asked.

    Returns:
        Counts indexed by ``group_by``, named
        ``distinct[class+method+spec]`` — the key that produced them, so two
        columns computed under different keys never look alike.

    Raises:
        FreezeItemUnset: ``dedup_key`` was not supplied.
        ValueError: ``group_by`` is empty, or a named column is missing.
    """
    key = list(_require(dedup_key, "dedup_key"))
    grain = list(group_by)
    if not grain:
        raise ValueError("distinct_count needs a grain; name the group_by columns")

    missing = [column for column in grain + key if column not in stream.columns]
    if missing:
        raise ValueError(f"stream has no column(s) {missing}; it has {list(stream)}")

    counts = (
        stream.drop_duplicates(subset=grain + key)
        .groupby(grain, dropna=False)
        .size()
        .astype(int)
    )
    counts.name = f"distinct[{_labelled(key)}]"
    return counts


@dataclass(frozen=True)
class BinaryOutcome:
    """A per-cell binary verdict, the rule that produced it, and the disagreement.

    The mixed census is part of the result rather than a diagnostic beside it.
    A cell whose replicas disagree is the only cell the replica rule can change,
    so the count of them is the size of the decision: with none mixed, all three
    rules return the same column and the choice is free; with many, the rule is
    the finding.

    Attributes:
        values: Boolean per cell, indexed by the identity with the replica level
            removed. Named for the threshold and the rule that produced it.
        rule: The replica rule applied.
        threshold: The count at or above which one replica counts as positive.
        mixed_cells: The cells whose replicas disagreed, by index label.
    """

    values: pd.Series
    rule: ReplicaRule
    threshold: int
    mixed_cells: tuple[Any, ...]

    @property
    def cells(self) -> int:
        """Cells the rule was applied to."""
        return len(self.values)

    @property
    def mixed(self) -> int:
        """Cells whose replicas disagreed — the ones the rule decided."""
        return len(self.mixed_cells)


def binarize(
    counts: pd.Series,
    *,
    threshold: Optional[int] = None,
    replica_rule: Optional[ReplicaRule] = None,
    replica_level: str = REPLICA_LEVEL,
) -> BinaryOutcome:
    """Collapse a cell's replicas into one boolean, by a rule the caller names.

    Args:
        counts: Per-replica counts, indexed by the full identity including
            ``replica_level``.
        threshold: The count at or above which a replica counts as positive.
            One is the usual choice and is still a choice.
        replica_rule: ``majority`` — more than half the replicas positive;
            ``union`` — any; ``unanimity`` — all.
        replica_level: Which index level holds the replica number.

    Returns:
        The ``BinaryOutcome``, carrying the values, the rule and the cells whose
        replicas disagreed.

    Raises:
        FreezeItemUnset: ``threshold`` or ``replica_rule`` was not supplied.
        ValueError: ``replica_level`` is not an index level, or it is the only
            one — a cell needs an identity apart from its replica number.
    """
    limit = int(_require(threshold, "threshold"))
    rule: ReplicaRule = _require(replica_rule, "replica_rule")

    names = list(counts.index.names)
    if replica_level not in names:
        raise ValueError(f"index has no level {replica_level!r}; levels are {names}")
    cell_levels = [name for name in names if name != replica_level]
    if not cell_levels:
        raise ValueError(
            f"{replica_level!r} is the only index level; the cell has no identity"
        )

    positive = counts >= limit
    grouped = positive.groupby(level=cell_levels, dropna=False)
    if rule == "union":
        values = grouped.any()
    elif rule == "unanimity":
        values = grouped.all()
    elif rule == "majority":
        values = grouped.mean() > 0.5
    else:
        raise ValueError(f"unknown replica rule {rule!r}")

    disagreed = grouped.nunique() > 1
    values.name = f"binary[threshold>={limit},replica_rule={rule}]"
    return BinaryOutcome(
        values=values,
        rule=rule,
        threshold=limit,
        mixed_cells=tuple(disagreed.index[disagreed]),
    )


def aggregate_replicas(
    values: Union[pd.Series, pd.DataFrame],
    *,
    estimand: Optional[Estimand] = None,
    replica_level: str = REPLICA_LEVEL,
) -> pd.DataFrame:
    """Collapse a cell's replicas into one value, with the estimand in the label.

    The label is the whole point. A campaign file once carried a per-application
    column that was a mean over three replicas, under a header that said only
    the metric's name; a later reader took it for a count. Here the column comes
    back as ``mop_unique__mean``, and a caller who mixes it into a ratio with a
    ``__median`` column can be caught by reading the header.

    Args:
        values: Per-replica values, indexed by the full identity including
            ``replica_level``. A frame aggregates every column at once.
        estimand: ``mean``, ``median``, or ``trimmed_mean_10`` — the mean after
            trimming 10 % from each tail.
        replica_level: Which index level holds the replica number.

    Returns:
        One row per cell, columns named ``<column>__<estimand>``, plus
        ``n_replicas`` — the number of replicas each value was computed over.
        An aggregate whose replica count is not reported cannot be read: three
        replicas and one replica produce the same column.

    Raises:
        FreezeItemUnset: ``estimand`` was not supplied.
        ValueError: ``replica_level`` is not an index level, or it is the only
            one.
    """
    chosen: Estimand = _require(estimand, "estimand")

    frame = values.to_frame() if isinstance(values, pd.Series) else values
    names = list(frame.index.names)
    if replica_level not in names:
        raise ValueError(f"index has no level {replica_level!r}; levels are {names}")
    cell_levels = [name for name in names if name != replica_level]
    if not cell_levels:
        raise ValueError(
            f"{replica_level!r} is the only index level; the cell has no identity"
        )

    grouped = frame.groupby(level=cell_levels, dropna=False)
    if chosen == "mean":
        aggregated = grouped.mean()
    elif chosen == "median":
        aggregated = grouped.median()
    elif chosen == "trimmed_mean_10":
        aggregated = grouped.agg(lambda column: trim_mean(column, TRIM_FRACTION))
    else:
        raise ValueError(f"unknown estimand {chosen!r}")

    aggregated.columns = [f"{column}__{chosen}" for column in frame.columns]
    aggregated["n_replicas"] = grouped.size()
    return aggregated


@dataclass(frozen=True)
class TimeToEvent:
    """When the first event arrived, or the horizon it never arrived within.

    ``censored`` is the field that keeps this readable. A run that never
    detected anything has no time-to-detection, and recording it as the budget
    would make a non-detection look like a very slow detection; recording it as
    missing would drop the run from the denominator. The pair
    ``(value=None, censored=True, horizon=budget)`` says exactly what happened.

    Attributes:
        value: Time from the clock origin to the first event, in the stream's
            own units. None when no event was observed.
        censored: Whether observation ended before an event arrived.
        horizon: How long the run was observed for, in the same units. The
            bound the censoring is at. None when the caller did not declare one.
    """

    value: Optional[float]
    censored: bool
    horizon: Optional[float]


def time_to_first_event(
    stream: pd.DataFrame,
    *,
    clock_origin: float,
    horizon: Optional[float],
    time_column: str = "t_rel_ms",
) -> TimeToEvent:
    """Time from an origin to the first event, with censoring made explicit.

    Args:
        stream: Event-grain frame for one unit — one run, one visit. An empty
            frame is the censored case, not an error.
        clock_origin: The instant the clock is measured from, in the same units
            as ``time_column``. Named by the caller because the run's own clock
            origin and the instant the tool actually started differ.
        horizon: How long the unit was observed for. Recorded on the result so
            a censored observation carries its bound; None when undeclared.
        time_column: The column holding the event instants.

    Returns:
        The ``TimeToEvent``.

    Raises:
        ValueError: The first event precedes the origin, which means the origin
            belongs to another clock.
    """
    if stream.empty:
        return TimeToEvent(value=None, censored=True, horizon=horizon)

    first = float(stream[time_column].min())
    value = first - clock_origin
    if value < 0:
        raise ValueError(
            f"first event at {first} precedes clock_origin {clock_origin}; "
            "the origin is from another clock"
        )
    return TimeToEvent(value=value, censored=False, horizon=horizon)


def capture_curve(
    stream: pd.DataFrame,
    *,
    budget_grid: Sequence[float],
    scope: Optional[CaptureScope] = None,
    dedup_key: Optional[Sequence[str]] = None,
    time_column: str = "t_rel_ms",
    run_column: str = "run",
) -> pd.DataFrame:
    """Cumulative distinct capture at each budget on the grid.

    ``scope`` is what separates two questions that share their arithmetic: what
    one run has found by time t, and what the campaign has found by time t. The
    second is not the sum of the first — two runs finding the same violation
    contribute one to the campaign and one each to themselves — so the parameter
    is not a formatting choice.

    Args:
        stream: Event-grain frame carrying the key columns, ``time_column`` and,
            for ``within_run``, ``run_column``.
        budget_grid: The instants the curve is evaluated at, in the units of
            ``time_column``. Events at exactly a budget are included.
        scope: ``within_run`` — one curve per run; ``cross_campaign`` — one
            curve over the pooled stream.
        dedup_key: The columns whose distinct combinations are accumulated.
        time_column: The column holding the event instants.
        run_column: The column identifying the run, used by ``within_run``.

    Returns:
        A long frame: ``budget``, the run identifier under ``within_run``, and
        the count under a column named for the key that produced it. A run with
        no event before a budget appears with a count of zero, because the run
        is named in the stream and its emptiness at that budget is the finding.

    Raises:
        FreezeItemUnset: ``scope`` or ``dedup_key`` was not supplied.
        ValueError: A named column is missing.
    """
    chosen: CaptureScope = _require(scope, "scope")
    key = list(_require(dedup_key, "dedup_key"))

    needed = key + [time_column] + ([run_column] if chosen == "within_run" else [])
    missing = [column for column in needed if column not in stream.columns]
    if missing:
        raise ValueError(f"stream has no column(s) {missing}; it has {list(stream)}")

    label = f"cumulative_distinct[{_labelled(key)}]"
    rows: list[dict[str, Any]] = []
    for budget in budget_grid:
        seen = stream[stream[time_column] <= budget]
        if chosen == "cross_campaign":
            rows.append(
                {
                    "budget": budget,
                    label: int(len(seen.drop_duplicates(subset=key))),
                }
            )
            continue
        counted = (
            seen.drop_duplicates(subset=[run_column] + key)
            .groupby(run_column, dropna=False)
            .size()
        )
        for run in stream[run_column].drop_duplicates():
            rows.append(
                {
                    "budget": budget,
                    run_column: run,
                    label: int(counted.get(run, 0)),
                }
            )
    return pd.DataFrame(rows)


def restrict_window(
    stream: pd.DataFrame,
    *,
    reference_instant: float,
    window: tuple[float, float],
    time_column: str = "t_rel_ms",
) -> pd.DataFrame:
    """The part of a stream inside a window measured from a reference instant.

    Phase-restricted outcomes — what happened in the first minute, what happened
    in the ten seconds after an arrival — are the same filter with different
    offsets, and the offsets belong to the caller. The window is half-open so
    that adjacent windows partition the stream instead of double-counting the
    event on their shared boundary.

    Args:
        stream: Event-grain frame carrying ``time_column``.
        reference_instant: The instant the offsets are measured from.
        window: ``(start_offset, end_offset)``, in the units of ``time_column``.
        time_column: The column holding the event instants.

    Returns:
        The rows whose instant lies in
        ``[reference_instant + start, reference_instant + end)``, re-indexed.

    Raises:
        ValueError: The window ends before it starts.
    """
    start, end = window
    if end < start:
        raise ValueError(f"window {window} ends before it starts")

    instants = stream[time_column]
    inside = (instants >= reference_instant + start) & (
        instants < reference_instant + end
    )
    return stream.loc[inside].reset_index(drop=True)
