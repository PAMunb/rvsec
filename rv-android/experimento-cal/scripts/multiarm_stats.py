#!/usr/bin/env python3
"""Multi-arm statistics for the calibration ANALYZE state.

This module implements the descriptive N-arm statistics the ANALYZE gate consumes
(spec "Gated Analysis", INV-CAL-10): per-arm trimmed-mean 10% summaries reported
*alongside* the raw arithmetic mean, paired bootstrap confidence intervals (B >= 10,000,
fixed seed from the phase config) of each arm against BOTH anchors, matched-pairs
rank-biserial effect sizes, and a descriptive Friedman + Holm ranking across all arms.

Estimand and primitives are the campaign's pinned choices, so the statistical kernel is
the scaffold's VENDORED `stats_utils.py` (imported LOCALLY from the same `scripts/`
directory — no sys.path insertion, no sibling-repo dependency; see the provenance header
in `stats_utils.py` and gh88 design decision 6). The pinned estimand is the DIFFERENCE OF
10%-TRIMMED MEANS recomputed per bootstrap resample (never the trimmed mean of the
differences, never the simple mean); pairs are resampled per APK.

Everything here is DESCRIPTIVE. Screening SELECTS candidate arms for the next phase; it
never declares a winner by a p-value (INV-CAL-10). The Friedman + Holm table and the
bootstrap CIs are decision *inputs*, not verdicts.

Input datasets follow the contracts-doc `per_apk_paired.csv` schema: a column `apk`
followed by `{arm_label}__{metric}` columns, where `arm_label` is the arm's RV_TOOLS token
(e.g. `ape:default`, `aperv:cal_a1`) and reps are already averaged per (apk, arm).
"""

from __future__ import annotations

from itertools import combinations
from typing import Dict, List, Sequence

import numpy as np

# Local, same-directory import of the vendored kernel (design decision 6). The provenance
# header lives in stats_utils.py; this is a plain top-level import that works both when the
# scripts/ dir is sys.path[0] (CLI) and when conftest prepends it (tests).
import stats_utils
from scipy.stats import friedmanchisquare, wilcoxon

# The campaign trims 10% from each tail (pinned estimand).
TRIM = 0.10


def _clean_pair(arm_vals: Sequence[float], anchor_vals: Sequence[float]):
    """Listwise-drop APK pairs where either arm is NaN, returning aligned float arrays.

    `stats_utils.paired_bootstrap_ci` asserts equal shapes and does not itself handle NaN
    (its docstring requires broken pairs removed *before* the call), so completeness is
    enforced here — the caller reports how many pairs survived.
    """
    a = np.asarray(arm_vals, dtype=float)
    b = np.asarray(anchor_vals, dtype=float)
    mask = ~(np.isnan(a) | np.isnan(b))
    return a[mask], b[mask]


def summarize_arm(values: Sequence[float], trim: float = TRIM) -> Dict[str, float]:
    """Per-arm location summary: raw mean AND trimmed mean side by side (INV-CAL-10).

    The raw arithmetic mean is ALWAYS reported alongside the trimmed mean so a tail-driven
    effect (a difference that lives in the extremes the trim discards) is never hidden — the
    exact failure mode the cmp_llm post-mortem flagged. NaN entries are ignored.
    """
    v = np.asarray(values, dtype=float)
    v = v[~np.isnan(v)]
    if v.size == 0:
        return {
            "n": 0,
            "raw_mean": float("nan"),
            "trimmed_mean": float("nan"),
            "sd": float("nan"),
        }
    from scipy.stats import trim_mean

    return {
        "n": int(v.size),
        "raw_mean": float(np.mean(v)),
        "trimmed_mean": float(trim_mean(v, trim)),
        "sd": float(np.std(v, ddof=1)) if v.size > 1 else 0.0,
    }


def paired_rank_biserial(
    arm_vals: Sequence[float], anchor_vals: Sequence[float]
) -> float:
    """Matched-pairs rank-biserial correlation of (arm - anchor).

    r = (W+ - W-) / (W+ + W-), where W+ / W- are the sums of positive / negative signed
    ranks of the paired differences (Kerby 2014). +1 means the arm dominates the anchor on
    every APK, -1 the reverse, 0 no directional tendency. Zero differences are dropped
    (standard Wilcoxon handling). Returns 0.0 when no non-zero pair survives.
    """
    a, b = _clean_pair(arm_vals, anchor_vals)
    d = a - b
    d = d[d != 0]
    if d.size == 0:
        return 0.0
    ranks = _rankdata(np.abs(d))
    w_pos = float(ranks[d > 0].sum())
    w_neg = float(ranks[d < 0].sum())
    total = w_pos + w_neg
    if total == 0:
        return 0.0
    return (w_pos - w_neg) / total


def _rankdata(x: np.ndarray) -> np.ndarray:
    """Average-rank of x (ties share the mean of the 1-based ranks they span).

    Each unique value occupies a contiguous block of 1-based ranks [start+1 .. start+count]
    in sorted order; its average rank is `start + (count + 1) / 2`. `np.unique` returns the
    sorted uniques with an inverse index that maps every element back to its block.
    """
    _, inv, counts = np.unique(x, return_inverse=True, return_counts=True)
    csum = np.cumsum(counts)
    start = csum - counts
    avg = (start + csum + 1) / 2.0
    return np.asarray(avg)[np.asarray(inv).ravel()]


def paired_bootstrap_vs_anchor(
    arm_vals: Sequence[float],
    anchor_vals: Sequence[float],
    B: int = 10_000,
    seed: int = 42,
    trim: float = TRIM,
    alpha: float = 0.05,
) -> Dict[str, float]:
    """Paired bootstrap CI of (arm - anchor) on the pinned estimand (diff of trimmed means).

    Broken pairs are dropped listwise first; the surviving pair count is reported. The point
    estimate and CI come from the vendored `stats_utils.paired_bootstrap_ci` (B resamples of
    APKs with replacement, fixed seed → deterministic). The raw-mean difference is reported
    alongside the trimmed-mean difference (INV-CAL-10). `rank_biserial` is the paired effect
    size on the same cleaned pairs.
    """
    a, b = _clean_pair(arm_vals, anchor_vals)
    n = int(a.size)
    if n == 0:
        return {
            "n_pairs": 0,
            "trimmed_diff": float("nan"),
            "ci_lo": float("nan"),
            "ci_hi": float("nan"),
            "raw_diff": float("nan"),
            "rank_biserial": float("nan"),
        }
    point, lo, hi = stats_utils.paired_bootstrap_ci(
        a, b, B=B, seed=seed, trim=trim, alpha=alpha
    )
    return {
        "n_pairs": n,
        "trimmed_diff": float(point),
        "ci_lo": float(lo),
        "ci_hi": float(hi),
        "raw_diff": float(np.mean(a) - np.mean(b)),
        "rank_biserial": paired_rank_biserial(a, b),
    }


def friedman_holm(arm_values: Dict[str, Sequence[float]]) -> Dict[str, object]:
    """Descriptive Friedman omnibus + Holm-adjusted pairwise Wilcoxon across all arms.

    Uses complete cases only: APKs present (non-NaN) for EVERY arm — Friedman requires
    aligned repeated measures. Returns the omnibus statistic/p-value, the per-arm mean rank
    (1 = worst on cov_mop convention where higher is better; see caller), and Holm-adjusted
    pairwise p-values. Descriptive: no arm is eliminated by any p-value here (INV-CAL-10).
    Returns `{"available": False, ...}` when fewer than 3 arms or fewer than 3 complete APKs
    make the omnibus undefined.
    """
    labels = list(arm_values)
    mat = np.array(
        [np.asarray(arm_values[l], dtype=float) for l in labels]
    )  # arms x apks
    complete = ~np.isnan(mat).any(axis=0)
    mat = mat[:, complete]
    n_complete = int(mat.shape[1])
    if len(labels) < 3 or n_complete < 3:
        return {
            "available": False,
            "reason": f"{len(labels)} arms, {n_complete} complete APKs",
            "labels": labels,
            "n_complete": n_complete,
        }

    stat, p = friedmanchisquare(*[mat[i] for i in range(mat.shape[0])])

    # Mean rank per arm across APKs (higher value -> higher rank; ties averaged).
    ranks = np.vstack(
        [_rankdata(mat[:, j]) for j in range(mat.shape[1])]
    ).T  # arms x apks
    mean_rank = {labels[i]: float(ranks[i].mean()) for i in range(len(labels))}

    # Holm over all pairwise Wilcoxon signed-rank tests (descriptive).
    pairs = list(combinations(range(len(labels)), 2))
    raw = []
    for i, j in pairs:
        d = mat[i] - mat[j]
        if np.all(d == 0):
            pval = 1.0
        else:
            try:
                pval = float(wilcoxon(mat[i], mat[j], zero_method="wilcox").pvalue)
            except ValueError:
                pval = 1.0
        raw.append(((labels[i], labels[j]), pval))
    holm = _holm_adjust(raw)

    return {
        "available": True,
        "statistic": float(stat),
        "pvalue": float(p),
        "n_complete": n_complete,
        "labels": labels,
        "mean_rank": mean_rank,
        "pairwise_holm": holm,  # list of (a, b, p_raw, p_holm)
    }


def _holm_adjust(pairs: List[tuple]) -> List[tuple]:
    """Holm step-down adjustment of a list of ((a, b), p_raw) → [(a, b, p_raw, p_holm)]."""
    m = len(pairs)
    order = sorted(range(m), key=lambda k: pairs[k][1])
    adj = [0.0] * m
    running = 0.0
    for rank, k in enumerate(order):
        p_raw = pairs[k][1]
        val = min(1.0, (m - rank) * p_raw)
        running = max(
            running, val
        )  # enforce monotonic non-decreasing adjusted p-values
        adj[k] = running
    return [(pairs[k][0][0], pairs[k][0][1], pairs[k][1], adj[k]) for k in range(m)]


def multiarm_summary(
    per_apk: Dict[str, Sequence[float]],
    arm_labels: Sequence[str],
    anchor_labels: Sequence[str],
    B: int = 10_000,
    seed: int = 42,
) -> Dict[str, object]:
    """Assemble the per-metric multi-arm result the ANALYZE renderer consumes.

    `per_apk` maps each arm label to its per-APK value vector (already rep-averaged) for ONE
    metric. For every arm it computes the raw+trimmed summary and, for each anchor label, the
    paired bootstrap CI + rank-biserial. Also runs the descriptive Friedman + Holm across all
    arms. Anchors are summarized too but never compared against themselves.
    """
    summaries = {a: summarize_arm(per_apk[a]) for a in arm_labels if a in per_apk}
    comparisons: Dict[str, Dict[str, Dict[str, float]]] = {}
    for arm in arm_labels:
        if arm in anchor_labels or arm not in per_apk:
            continue
        comparisons[arm] = {}
        for anc in anchor_labels:
            if anc not in per_apk:
                continue
            comparisons[arm][anc] = paired_bootstrap_vs_anchor(
                per_apk[arm], per_apk[anc], B=B, seed=seed
            )
    friedman = friedman_holm({a: per_apk[a] for a in arm_labels if a in per_apk})
    return {"summaries": summaries, "comparisons": comparisons, "friedman": friedman}
