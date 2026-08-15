"""PARITY, not correctness: the campaign's own Wilcoxon table, reproduced.

This test reproduces ``consolidado/wilcoxon.csv`` — 15 rows, three arm pairs by
five metrics — from the campaign's per-replica file, through this library's
estimator, in the mode the campaign ran: the normal approximation without the
continuity correction, which is ``scipy``'s default and therefore what the
campaign's script got.

**What it proves and what it does not.** Passing means the pipeline that produced
those numbers is unchanged: the same per-application aggregation, the same
pairing, the same test, the same statistic. It does **not** mean the estimator is
right. The campaign's mode is an approximation, ``per_apk_paired.csv`` holds
means over replicas, and reproducing a number says nothing about whether the
number should have been computed that way. Correctness for every estimator in
this library comes from FIXTURE-SYNTH and from there only (INV-CAN-21).

The inputs are pinned by ``cmp162_manifest.json`` and their digests are checked
before anything is computed, so a refactor cannot quietly change what "passing"
means by changing what was read.

One detail is load-bearing and is the reason the parity runs from
``per_rep.csv`` rather than from ``per_apk_paired.csv``: the latter rounds each
per-application mean to four decimals, and that rounding creates ties. Two of the
three pairs then disagree with the published table on the ranked statistic — the
``cov_mop`` row alone gains two ties and moves ``W`` from 3896.0 to 3793.0. The
published table was computed from unrounded means, so the parity has to start
where they are still unrounded.
"""

from __future__ import annotations

import csv
import itertools
import statistics
from collections import defaultdict
from pathlib import Path

import pytest
from fixture_gate import sha256_of

from aperv_tool.analysis.estimators import paired_continuous

#: The arms in the order the campaign's manifest lists them, which is the order
#: its pairwise table is written in.
ARMS = ("ape", "aperv:mop_off_llm_off", "aperv:mop_on_llm_off")

#: The metrics the campaign tests, in its own order.
METRICS = ("cov_mop", "mop_unique", "cov_method", "cov_act", "mop_total")

#: Every metric the per-replica file carries, needed to average a run.
ALL_METRICS = (
    "cov_method",
    "cov_act",
    "cov_mop",
    "mop_unique",
    "mop_total",
    "crashes",
)


def per_application_means(per_rep: Path) -> dict[tuple[str, str], dict[str, float]]:
    """Mean over replicas per (application, arm), unrounded.

    Args:
        per_rep: The campaign's per-replica file.

    Returns:
        ``{(apk, arm): {metric: mean}}``.
    """
    collected: dict[tuple[str, str], dict[str, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    with per_rep.open(newline="") as handle:
        for row in csv.DictReader(handle):
            for metric in ALL_METRICS:
                collected[(row["apk"], row["tool"])][metric].append(float(row[metric]))
    return {
        key: {metric: statistics.mean(values[metric]) for metric in ALL_METRICS}
        for key, values in collected.items()
    }


@pytest.fixture(scope="module")
def parity_inputs(cmp162_manifest: dict, cmp162_root: Path) -> dict:
    """The two pinned files, digest-checked, with the published table parsed."""
    digests = cmp162_manifest["files"]
    for relative in ("consolidado/per_rep.csv", "consolidado/wilcoxon.csv"):
        assert relative in cmp162_manifest["parity_files"], relative
        path = cmp162_root / relative
        assert path.is_file(), f"pinned parity file missing: {path}"
        assert (
            sha256_of(path) == digests[relative]
        ), f"{relative} is not the pinned copy"

    with (cmp162_root / "consolidado/wilcoxon.csv").open(newline="") as handle:
        published = list(csv.DictReader(handle))
    return {
        "means": per_application_means(cmp162_root / "consolidado/per_rep.csv"),
        "published": published,
    }


def reproduced(means: dict[tuple[str, str], dict[str, float]]) -> list[dict[str, str]]:
    """The 15 rows, recomputed through this library in the campaign's mode."""
    applications = sorted({apk for apk, _ in means})
    rows: list[dict[str, str]] = []
    for first, second in itertools.combinations(ARMS, 2):
        for metric in METRICS:
            left, right = [], []
            for apk in applications:
                if (apk, first) in means and (apk, second) in means:
                    left.append(means[(apk, first)][metric])
                    right.append(means[(apk, second)][metric])
            differences = [a - b for a, b in zip(left, right)]

            envelope = paired_continuous.wilcoxon(
                differences,
                exact_max_n=0,
                continuity_correction=False,
            )
            statistic = envelope.estimate["statistic"]
            p_value = envelope.estimate["p_approx"]
            rows.append(
                {
                    "A": first,
                    "B": second,
                    "metric": metric,
                    "n": str(len(left)),
                    "median_A": str(round(statistics.median(left), 3)),
                    "median_B": str(round(statistics.median(right), 3)),
                    "median_diff": str(
                        round(envelope.estimate["median_difference"], 3)
                    ),
                    "wins_A": str(sum(1 for d in differences if d > 0)),
                    "losses_A": str(sum(1 for d in differences if d < 0)),
                    "ties": str(len(differences) - envelope.estimate["n_nonzero"]),
                    "W": str(round(statistic, 1)),
                    "p_value": str(round(p_value, 5)),
                    "significant": "sim" if p_value < 0.05 else "nao",
                }
            )
    return rows


def test_parity_wilcoxon(parity_inputs: dict) -> None:
    """All 15 published rows, field for field. PARITY, not correctness."""
    published = parity_inputs["published"]
    recomputed = reproduced(parity_inputs["means"])

    assert len(published) == 15, "the pinned table is not the 3-pair by 5-metric one"
    assert len(recomputed) == len(published)

    differences: list[str] = []
    for expected, actual in zip(published, recomputed):
        for field, want in expected.items():
            got = actual[field]
            try:
                same = float(got) == float(want)
            except ValueError:
                same = got == want
            if not same:
                differences.append(
                    f"{expected['A']} vs {expected['B']} / {expected['metric']} / "
                    f"{field}: reproduced {got}, published {want}"
                )

    assert differences == [], "the pipeline no longer reproduces the campaign:\n" + (
        "\n".join(differences)
    )


def test_the_parity_ran_against_the_pinned_bytes(parity_inputs: dict) -> None:
    """Non-vacuity: a parity over an absent tree would prove nothing."""
    means = parity_inputs["means"]

    assert len({apk for apk, _ in means}) == 162
    assert {arm for _, arm in means} == set(ARMS)


def test_the_campaign_mode_is_not_the_reporting_mode() -> None:
    """The mode reproduced here omits a correction a report would carry.

    Stated as a test so the distinction is not lost with the docstring: the
    campaign ran ``scipy``'s default, and this library's reporting default is the
    caller's declaration, not that one.
    """
    differences = [1.0, 1.0, -1.0, 2.0, 3.0, -2.0, 4.0, 5.0]

    campaign_mode = paired_continuous.wilcoxon(
        differences, exact_max_n=0, continuity_correction=False
    )
    reporting_mode = paired_continuous.wilcoxon(
        differences, exact_max_n=25, continuity_correction=True
    )

    assert campaign_mode.estimate["p_approx"] != reporting_mode.estimate["p_approx"]
    assert campaign_mode.estimate["exact_available"] is False
    assert reporting_mode.estimate["exact_available"] is True
