"""A convention that is not supplied is an error, and one that is travels.

The synthetic cases here are the smallest ones on which the conventions
disagree, because a convention that changes nothing on the fixture is not being
tested. The replica cell is ``[0, 1, 1]`` — the only shape on which the three
rules split — and the two dedup keys are exercised on a stream where they give
different counts.

The last test is a **parity** test (INV-CAN-21): it reproduces the campaign's own
per-application aggregate under the campaign's own convention. Passing it proves
the pipeline is unchanged. It proves nothing about whether the mean over
replicas was the right estimand — that file's unlabelled ``mop_unique`` column
is a mean over three replicas, and it has already been read as a count.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from aperv_tool.analysis.corpus import FreezeItemUnset
from aperv_tool.analysis.loader import load
from aperv_tool.analysis.outcomes import (
    DEDUP_KEY_MESSAGE,
    DEDUP_KEY_SIGNATURE,
    DEDUP_KEYS,
    aggregate_replicas,
    binarize,
    capture_curve,
    distinct_count,
    restrict_window,
    time_to_first_event,
)

#: cmp162's roster, supplied as data exactly as a caller must supply it.
CMP162_ARMS = {
    "ape": ("ape", ""),
    "aperv:mop_off_llm_off": ("aperv", "mop_off_llm_off"),
    "aperv:mop_on_llm_off": ("aperv", "mop_on_llm_off"),
}

#: The campaign's per-application file, column stem → the frame column the same
#: quantity arrives under. The campaign takes coverage and the unique count from
#: the task record and the violation total from the logcat; both reach the
#: loader's frame, so the parity test needs no second reader.
PARITY_METRICS = {
    "cov_method": "method_coverage",
    "cov_act": "activities_coverage",
    "cov_mop": "methods_mop_reachable_coverage",
    "mop_unique": "total_errors",
    "mop_total": "mop_errors_total",
    "crashes": "detected_errors_count",
}


def replica_counts(values: list[int]) -> pd.Series:
    """One cell's per-replica counts, indexed as a run-grain frame is."""
    index = pd.MultiIndex.from_tuples(
        [
            ("com.example.app_1.apk", "aperv:mop_on_llm_off", rep + 1)
            for rep in range(len(values))
        ],
        names=["apk", "arm", "rep"],
    )
    return pd.Series(values, index=index, name="violations")


def violation_stream() -> pd.DataFrame:
    """Four violations across two runs on which the two dedup keys disagree.

    Both violations of run one name the same operation under the same
    specification and differ only in the parameter their message reports. The
    signature key sees one violation; the message key sees two.
    """
    return pd.DataFrame(
        [
            {
                "run": "run-1",
                "class": "javax.crypto.Cipher",
                "method": "getInstance",
                "spec": "CipherSpec",
                "message": "CipherSpec, transformation DES/ECB",
                "t_rel_ms": 1_000,
            },
            {
                "run": "run-1",
                "class": "javax.crypto.Cipher",
                "method": "getInstance",
                "spec": "CipherSpec",
                "message": "CipherSpec, transformation AES/ECB",
                "t_rel_ms": 9_000,
            },
            {
                "run": "run-2",
                "class": "java.security.MessageDigest",
                "method": "getInstance",
                "spec": "MessageDigestSpec",
                "message": "MessageDigestSpec, algorithm MD5",
                "t_rel_ms": 2_000,
            },
            {
                "run": "run-2",
                "class": "java.security.MessageDigest",
                "method": "getInstance",
                "spec": "MessageDigestSpec",
                "message": "MessageDigestSpec, algorithm MD5",
                "t_rel_ms": 8_000,
            },
        ]
    )


def test_three_replica_rules() -> None:
    """`[0, 1, 1]` at threshold 1: majority true, union true, unanimity false."""
    counts = replica_counts([0, 1, 1])
    cell = ("com.example.app_1.apk", "aperv:mop_on_llm_off")

    verdicts = {
        rule: binarize(counts, threshold=1, replica_rule=rule)
        for rule in ("majority", "union", "unanimity")
    }

    assert bool(verdicts["majority"].values.loc[cell]) is True
    assert bool(verdicts["union"].values.loc[cell]) is True
    assert bool(verdicts["unanimity"].values.loc[cell]) is False

    for rule, outcome in verdicts.items():
        assert outcome.cells == 1, rule
        assert outcome.mixed == 1, rule
        assert outcome.mixed_cells == (cell,), rule
        assert rule in str(outcome.values.name)
        assert "threshold>=1" in str(outcome.values.name)


def test_agreeing_replicas_are_not_in_the_mixed_census() -> None:
    """With no cell mixed, the rule changed nothing — and the census says so."""
    counts = replica_counts([2, 3, 4])

    outcome = binarize(counts, threshold=1, replica_rule="unanimity")

    assert outcome.mixed == 0
    assert outcome.mixed_cells == ()
    assert bool(outcome.values.iloc[0]) is True


def test_estimand_labelled() -> None:
    """The estimand is in the column name, so two of them cannot be confused."""
    index = pd.MultiIndex.from_tuples(
        [("com.example.app_1.apk", rep) for rep in (1, 2, 3)], names=["apk", "rep"]
    )
    values = pd.DataFrame({"cov_method": [10.0, 20.0, 60.0]}, index=index)

    trimmed = aggregate_replicas(values, estimand="trimmed_mean_10")
    mean = aggregate_replicas(values, estimand="mean")

    assert list(trimmed.columns) == ["cov_method__trimmed_mean_10", "n_replicas"]
    assert list(mean.columns) == ["cov_method__mean", "n_replicas"]
    assert set(trimmed.columns) & set(mean.columns) == {"n_replicas"}
    assert int(trimmed["n_replicas"].iloc[0]) == 3


def test_replica_count_travels_with_the_aggregate() -> None:
    """Three replicas and one replica produce the same column otherwise."""
    index = pd.MultiIndex.from_tuples(
        [("a.apk", 1), ("a.apk", 2), ("b.apk", 1)], names=["apk", "rep"]
    )
    values = pd.Series([4.0, 6.0, 5.0], index=index, name="cov_method")

    aggregated = aggregate_replicas(values, estimand="mean")

    assert list(aggregated["cov_method__mean"]) == [5.0, 5.0]
    assert list(aggregated["n_replicas"]) == [2, 1]


def test_censoring_flag() -> None:
    """A run that never detected anything is censored, not missing and not slow."""
    stream = violation_stream()

    observed = time_to_first_event(
        stream[stream["run"] == "run-1"], clock_origin=0.0, horizon=300_000.0
    )
    never = time_to_first_event(stream.iloc[0:0], clock_origin=0.0, horizon=300_000.0)

    assert observed.value == 1_000.0
    assert observed.censored is False
    assert never.value is None
    assert never.censored is True
    assert never.horizon == 300_000.0


def test_origin_from_another_clock_raises() -> None:
    """An event before the origin means the origin belongs to another clock."""
    with pytest.raises(ValueError, match="another clock"):
        time_to_first_event(violation_stream(), clock_origin=5_000.0, horizon=None)


def test_both_dedup_keys_available_and_labelled() -> None:
    """Both keys are reachable by name, and the counts they give differ."""
    stream = violation_stream()

    assert DEDUP_KEYS == {
        "signature": DEDUP_KEY_SIGNATURE,
        "message": DEDUP_KEY_MESSAGE,
    }

    signature = distinct_count(stream, dedup_key=DEDUP_KEY_SIGNATURE, group_by=["run"])
    message = distinct_count(stream, dedup_key=DEDUP_KEY_MESSAGE, group_by=["run"])

    assert list(signature) == [1, 1]
    assert list(message) == [2, 1]
    assert signature.name == "distinct[class+method+spec]"
    assert message.name == "distinct[message]"
    assert signature.name != message.name


def test_a_group_with_no_event_is_absent_not_zero() -> None:
    """The stream cannot invent a denominator; the caller reindexes it."""
    counts = distinct_count(
        violation_stream(), dedup_key=DEDUP_KEY_SIGNATURE, group_by=["run"]
    )

    assert "run-3" not in counts.index
    assert int(counts.reindex(["run-1", "run-2", "run-3"], fill_value=0)["run-3"]) == 0


def test_capture_curve_scope_changes_the_question() -> None:
    """Pooled distinct capture is not the sum of the per-run curves."""
    stream = violation_stream().assign(run=["run-1", "run-1", "run-2", "run-2"])
    grid = [1_500, 10_000]

    pooled = capture_curve(
        stream,
        budget_grid=grid,
        scope="cross_campaign",
        dedup_key=("method",),
        time_column="t_rel_ms",
    )
    per_run = capture_curve(
        stream,
        budget_grid=grid,
        scope="within_run",
        dedup_key=("method",),
        time_column="t_rel_ms",
    )

    label = "cumulative_distinct[method]"
    assert list(pooled[label]) == [1, 1]
    assert list(per_run[label]) == [1, 0, 1, 1]
    assert list(per_run["run"]) == ["run-1", "run-2", "run-1", "run-2"]


def test_restrict_window_is_half_open() -> None:
    """Adjacent windows partition the stream instead of sharing their boundary."""
    stream = violation_stream()

    early = restrict_window(
        stream, reference_instant=0.0, window=(0.0, 2_000.0), time_column="t_rel_ms"
    )
    late = restrict_window(
        stream, reference_instant=0.0, window=(2_000.0, 9_000.0), time_column="t_rel_ms"
    )

    assert list(early["t_rel_ms"]) == [1_000]
    assert list(late["t_rel_ms"]) == [2_000, 8_000]


def test_freeze_item_unset() -> None:
    """Every convention names itself when it is missing, before computing."""
    stream = violation_stream()
    counts = replica_counts([0, 1, 1])

    with pytest.raises(FreezeItemUnset, match="dedup_key"):
        distinct_count(stream, group_by=["run"])
    with pytest.raises(FreezeItemUnset, match="threshold"):
        binarize(counts, replica_rule="union")
    with pytest.raises(FreezeItemUnset, match="replica_rule"):
        binarize(counts, threshold=1)
    with pytest.raises(FreezeItemUnset, match="estimand"):
        aggregate_replicas(counts)
    with pytest.raises(FreezeItemUnset, match="scope"):
        capture_curve(stream, budget_grid=[1], dedup_key=("method",))
    with pytest.raises(FreezeItemUnset, match="dedup_key"):
        capture_curve(stream, budget_grid=[1], scope="cross_campaign")


def test_parity_per_apk_paired(cmp162_root: Path) -> None:
    """PARITY (INV-CAN-21): the campaign's 162-row per-application aggregate.

    The campaign's value for a cell is the mean of its replicas, rounded to four
    decimals, over `COMPLETED` records only. Running the loader and
    `aggregate_replicas(estimand="mean")` under exactly that convention
    reproduces every cell of the file, including the application whose third arm
    died and whose cells are therefore `nan` over zero replicas.

    Reproducing it proves the pipeline unchanged. It does not endorse the file:
    the header says `mop_unique`, the column holds a mean over three replicas,
    and nothing in the file says so — which is why `aggregate_replicas` labels
    the estimand and this test has to rename the columns to compare.
    """
    frame, _ = load(cmp162_root / "results", CMP162_ARMS)
    completed = frame[frame["state"] == "COMPLETED"]

    aggregated = aggregate_replicas(
        completed.set_index(["apk", "arm", "rep"])[list(PARITY_METRICS.values())],
        estimand="mean",
    )

    expected = pd.read_csv(cmp162_root / "consolidado" / "per_apk_paired.csv")
    assert len(expected) == 162

    applications = list(expected["apk"])
    for arm in CMP162_ARMS:
        for stem, column in PARITY_METRICS.items():
            ours = np.array(
                [
                    aggregated[f"{column}__mean"].get((apk, arm), np.nan)
                    for apk in applications
                ],
                dtype=float,
            ).round(4)
            theirs = expected[f"{arm}__{stem}"].to_numpy(dtype=float)
            same = (ours == theirs) | (np.isnan(ours) & np.isnan(theirs))
            assert same.all(), f"{arm}__{stem}: {ours[~same]} != {theirs[~same]}"

        replicas = np.array(
            [aggregated["n_replicas"].get((apk, arm), 0) for apk in applications],
            dtype=int,
        )
        assert (replicas == expected[f"{arm}__n_reps"].to_numpy(dtype=int)).all()
