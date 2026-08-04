#!/usr/bin/env python3
"""COMPARE — evaluate G1, G2 and G3 against the frozen plan, and report every outcome.

Leg A is `experimento-e3-decisiva/per_apk_paired.csv`, executed on the pre-rearch jar and
frozen. Leg B is this campaign's own `per_apk_paired.csv`. Both are read, never rewritten.

The estimand is the one the E3 analysis used and it is NOT the mean of the paired
differences: `stats_utils.paired_bootstrap_ci` estimates the **difference of 10% trimmed
means**, recomputed on each resample, with APKs resampled in pairs (B=10,000, seed 42).
That routine is copied byte-identical from the calibration scaffold precisely so this
comparison and the one it is compared against compute the same thing.

    G1  BLOCKING — leg B against leg A on the control arm alone, paired by application.
        The control zeroes the five MOP weights and disables the activity trigger, so
        gh96's intentional substrate change cannot reach its behaviour: what moves in this
        contrast is the rewrite. Reported over all six outcomes; three of them gate.

    G2  BLOCKING — the within-campaign contrast reference - control on `cov_act`, stated
        ONE-SIDED. Both of its terms are measured on the same substrate, so it is immune to
        the confound G1 is shaped around, and it covers what G1 by construction cannot see:
        the MOP-weighted scoring path the rewrite actually rewrote. One-sided because
        `cov_act` is at ceiling in both guided arms — regression is detectable, improvement
        is not (declared premise).

    G3  DESCRIPTIVE — the guided arms' monitored-operation levels, reported beside the
        substrate displacement computed host-side before the freeze. gh96 broadens the
        flagged surface while flattening the ranking among flagged widgets, so its net
        effect on detection has no defensible predicted sign and none is asserted.

A blocking finding requires BOTH conditions, never either alone: a CI excluding zero in the
harmful direction AND |Δ| above the outcome's margin. "CI excludes zero" alone fails the
gate on campaign noise — the documented run-level drift is -0.743 pp of `cov_mop` at
p=0.0099 with no code change at all.

Usage, from the campaign directory:
    uv run python scripts/compare.py --leg-b per_apk_paired.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import stats_utils

# --- the frozen decision rule ----------------------------------------------------------
# Margins derived from leg A's replica dispersion before the freeze and signed off by the
# owner on 2026-08-04: max(1.5 pp, 2 x the median replica SD of the three-replica mean on
# the control arm). The 1.5 pp floor is twice the documented between-campaign drift; the
# doubling of the dispersion applies the same conservatism to a quantity that is a LOWER
# bound on between-campaign variability. Derivation:
# docs/20260804_gh97_notas_de_trabalho.md §3.2.
G1_MARGINS: Dict[str, float] = {
    "cov_method": 1.92,
    "cov_act": 1.50,
    "cov_mop": 2.09,
}

# Reported with their CIs, never blocking on their own, decided before the campaign rather
# than after seeing which outcome moved:
#   crashes     median 0 in all three arms of E3 — a CI over a constant zero vector decides
#               nothing, and gating on it would manufacture a verdict from noise.
#   mop_unique  flat enough in E3 that the McNemar primary had n_discordante = 0.
#   mop_total   counts violation lines rather than distinct violations, and is the noisiest
#               of the five: replica SD median 6.01 against a level of 40.5 on the control
#               arm. Owner decision of 2026-08-04, on the dispersion evidence.
DESCRIPTIVE_OUTCOMES = ("mop_unique", "mop_total", "crashes")

OUTCOMES = ("cov_method", "cov_act", "cov_mop", "mop_unique", "mop_total", "crashes")

CONTROL_ARM = "aperv:mop_off_llm_off"
REFERENCE_ARM = "aperv:mop_on_llm_off"
LLM_ARM = "aperv:mop_on_llm_70"

# Every outcome here is "more is better", so the harmful direction of Delta = B - A is
# negative. Stated once, as data, rather than reasoned about at each call site.
HARMFUL_DIRECTION = -1

# The substrate displacement G3 is read against, computed host-side over the pinned corpus
# before the freeze (notes §3.4). Context for the reader, not a prediction.
G3_DISPLACEMENT = {
    "flagged_widgets_old": 104,
    "flagged_widgets_new": 159,
    "flagged_activities_old": 38,
    "flagged_activities_new": 49,
    "applications_moved": 4,
    "applications_total": 40,
}


def read_paired(path: Path) -> Dict[str, Dict[str, float]]:
    """`{apk: {"<arm>__<metric>": value}}` from a `per_apk_paired.csv`.

    Empty cells — an arm absent for an application — are dropped rather than zeroed. A
    zero would enter the trimmed mean as a measurement.
    """
    table: Dict[str, Dict[str, float]] = {}
    with open(path, newline="") as handle:
        for row in csv.DictReader(handle):
            apk = row["apk"]
            cells: Dict[str, float] = {}
            for column, value in row.items():
                if column == "apk" or value in (None, ""):
                    continue
                try:
                    cells[column] = float(value)
                except ValueError:
                    continue
            table[apk] = cells
    return table


def paired_vectors(
    left: Dict[str, Dict[str, float]],
    right: Dict[str, Dict[str, float]],
    left_column: str,
    right_column: str,
) -> Tuple[List[float], List[float], List[str]]:
    """Two vectors over the applications present on BOTH sides, in a stable order.

    Listwise: an application missing either side is dropped from the pair rather than
    imputed, and the returned application list is what the report states as n.
    """
    apks = sorted(
        apk
        for apk in left
        if apk in right and left_column in left[apk] and right_column in right[apk]
    )
    return (
        [left[apk][left_column] for apk in apks],
        [right[apk][right_column] for apk in apks],
        apks,
    )


def contrast(
    a: Sequence[float], b: Sequence[float], apks: Sequence[str]
) -> Dict[str, Any]:
    """One paired bootstrap contrast, `a - b`, with its point estimate and CI95."""
    point, lo, hi = stats_utils.paired_bootstrap_ci(list(a), list(b))
    return {
        "n": len(apks),
        "point": round(point, 4),
        "ci_lo": round(lo, 4),
        "ci_hi": round(hi, 4),
        "excludes_zero": lo > 0 or hi < 0,
    }


def verdict(result: Dict[str, Any], margin: Optional[float]) -> Dict[str, Any]:
    """Apply the frozen rule to one contrast.

    Both conditions are required for a block, and the harmful direction is checked on the
    CI rather than on the point estimate: a point estimate below zero whose CI straddles it
    is exactly the noise this rule exists not to act on.
    """
    if margin is None:
        return {
            **result,
            "gates": False,
            "blocking": False,
            "rule": "descriptive — reported, never blocking on its own",
        }
    harmful_ci = result["ci_hi"] < 0 if HARMFUL_DIRECTION < 0 else result["ci_lo"] > 0
    beyond_margin = abs(result["point"]) > margin
    return {
        **result,
        "gates": True,
        "margin": margin,
        "harmful_ci": harmful_ci,
        "beyond_margin": beyond_margin,
        "blocking": harmful_ci and beyond_margin,
        "rule": f"blocks when the CI excludes zero harmfully AND |delta| > {margin} pp",
    }


def evaluate_g1(
    leg_a: Dict[str, Dict[str, float]], leg_b: Dict[str, Dict[str, float]]
) -> Dict[str, Any]:
    """G1: leg B - leg A on the control arm, every outcome, three of them gating."""
    outcomes: Dict[str, Any] = {}
    for metric in OUTCOMES:
        column = f"{CONTROL_ARM}__{metric}"
        b_values, a_values, apks = paired_vectors(leg_b, leg_a, column, column)
        if not apks:
            outcomes[metric] = {"n": 0, "error": "no application paired on both legs"}
            continue
        outcomes[metric] = verdict(
            contrast(b_values, a_values, apks), G1_MARGINS.get(metric)
        )
    return {
        "arm": CONTROL_ARM,
        "direction": "leg B - leg A",
        "outcomes": outcomes,
        "blocking": [m for m, r in outcomes.items() if r.get("blocking")],
    }


def evaluate_g2(leg_b: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
    """G2: reference - control on `cov_act`, within leg B, one-sided.

    Passes when the contrast keeps its sign and its CI excludes zero. A rewrite that broke
    monitored-operation guidance collapses this contrast toward zero; a substrate that
    shifted the flagged surface does not change its sign.
    """
    reference, control, apks = paired_vectors(
        leg_b, leg_b, f"{REFERENCE_ARM}__cov_act", f"{CONTROL_ARM}__cov_act"
    )
    if not apks:
        return {"error": "no application carries both arms in leg B"}
    result = contrast(reference, control, apks)
    passes = result["point"] > 0 and result["ci_lo"] > 0
    return {
        **result,
        "contrast": f"{REFERENCE_ARM} - {CONTROL_ARM} on cov_act",
        "one_sided": True,
        "leg_a_reference": {"point": 14.916, "ci_lo": 7.754, "ci_hi": 22.039},
        "passes": passes,
        "blocking": not passes,
        "rule": "blocks when the contrast loses its sign or its CI includes zero",
    }


def evaluate_g3(
    leg_a: Dict[str, Dict[str, float]], leg_b: Dict[str, Dict[str, float]]
) -> Dict[str, Any]:
    """G3: the guided arms' monitored-operation levels, descriptive, both legs side by side.

    Not a gate and not a prediction. It is reported so the substrate change is read as the
    declared confound it is, rather than discovered afterwards in the numbers.
    """
    levels: Dict[str, Any] = {}
    for arm in (REFERENCE_ARM, LLM_ARM):
        for metric in ("cov_mop", "mop_unique", "mop_total"):
            column = f"{arm}__{metric}"
            b_values, a_values, apks = paired_vectors(leg_b, leg_a, column, column)
            if not apks:
                continue
            levels[f"{arm}__{metric}"] = contrast(b_values, a_values, apks)
    return {
        "expected_displacement": G3_DISPLACEMENT,
        "levels": levels,
        "note": (
            "gh96 broadens the flagged surface and flattens the tier ranking; its net "
            "effect on detection has no defensible predicted sign, so none is asserted"
        ),
    }


def render(report: Dict[str, Any]) -> str:
    """The report as text: G1's table, G2's contrast, G3's levels, then the verdict."""
    lines = ["# Gate verdict — leg B against leg A\n"]

    lines.append("## G1 (blocking) — control arm, leg B - leg A\n")
    lines.append(
        f"{'outcome':<12}{'n':>4}{'delta':>10}{'ci95':>22}" f"{'margin':>9}  verdict"
    )
    for metric, result in report["g1"]["outcomes"].items():
        if result.get("error"):
            lines.append(f"{metric:<12}{0:>4}  {result['error']}")
            continue
        ci = f"[{result['ci_lo']:>8.3f}, {result['ci_hi']:>8.3f}]"
        margin = f"{result['margin']:.2f}" if result.get("gates") else "-"
        if not result.get("gates"):
            note = "descriptive"
        elif result["blocking"]:
            note = "BLOCKING"
        elif result["harmful_ci"]:
            note = "harmful CI, within margin"
        else:
            note = "no blocking finding"
        lines.append(
            f"{metric:<12}{result['n']:>4}{result['point']:>10.3f}{ci:>22}"
            f"{margin:>9}  {note}"
        )
    lines.append("")

    g2 = report["g2"]
    lines.append("## G2 (blocking, one-sided) — guidance still guides, within leg B\n")
    if g2.get("error"):
        lines.append(g2["error"])
    else:
        lines.append(
            f"{g2['contrast']}: {g2['point']:.3f} "
            f"[{g2['ci_lo']:.3f}, {g2['ci_hi']:.3f}] over n={g2['n']}"
        )
        lines.append(
            f"leg A measured {g2['leg_a_reference']['point']} "
            f"[{g2['leg_a_reference']['ci_lo']}, "
            f"{g2['leg_a_reference']['ci_hi']}]"
        )
        lines.append(
            "PASS" if g2["passes"] else "BLOCKING — sign lost or CI includes zero"
        )
    lines.append("")

    g3 = report["g3"]
    disp = g3["expected_displacement"]
    lines.append("## G3 (descriptive) — monitored-operation levels, guided arms\n")
    lines.append(
        f"expected substrate displacement over the corpus: "
        f"{disp['flagged_widgets_old']} -> {disp['flagged_widgets_new']} flagged widgets, "
        f"{disp['flagged_activities_old']} -> {disp['flagged_activities_new']} flagged "
        f"activities, concentrated in {disp['applications_moved']} of "
        f"{disp['applications_total']} applications"
    )
    for column, result in g3["levels"].items():
        lines.append(
            f"  {column:<40}{result['point']:>10.3f}  "
            f"[{result['ci_lo']:>8.3f}, {result['ci_hi']:>8.3f}]  n={result['n']}"
        )
    lines.append("")

    blocking = report["g1"]["blocking"] + (["G2"] if g2.get("blocking") else [])
    lines.append(
        "VERDICT: no blocking finding — the gate does not oppose the merge."
        if not blocking
        else f"VERDICT: BLOCKING — {', '.join(blocking)}."
    )
    lines.append(
        "A tie is a valid outcome and is reported as one; the verdict states what was "
        "measured, not what was hoped for."
    )
    return "\n".join(lines) + "\n"


def build_report(leg_a_path: Path, leg_b_path: Path) -> Dict[str, Any]:
    """Read both legs and evaluate the three groups against the frozen plan.

    Neither CSV is written back: leg A is frozen, and leg B is the campaign's own record.

    Returns:
        Dictionary with keys:
        - "leg_a", "leg_b" (str): the two CSVs read, so a report names its own inputs.
        - "estimand" (str): what every CI below estimates. Carried in the report rather
          than left to the reader, because the mean of the paired differences is a
          different number from the difference of trimmed means.
        - "g1", "g2", "g3" (dict): the groups, as the corresponding `evaluate_*` returns.
    """
    leg_a = read_paired(leg_a_path)
    leg_b = read_paired(leg_b_path)
    return {
        "leg_a": str(leg_a_path),
        "leg_b": str(leg_b_path),
        "estimand": "difference of 10% trimmed means, paired bootstrap B=10000 seed=42",
        "g1": evaluate_g1(leg_a, leg_b),
        "g2": evaluate_g2(leg_b),
        "g3": evaluate_g3(leg_a, leg_b),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--leg-a",
        default=str(
            Path(__file__).resolve().parents[2]
            / "experimento-e3-decisiva/per_apk_paired.csv"
        ),
    )
    parser.add_argument("--leg-b", default="per_apk_paired.csv")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = build_report(Path(args.leg_a), Path(args.leg_b))
    print(json.dumps(report, indent=2) if args.json else render(report), end="")
    blocking = bool(report["g1"]["blocking"] or report["g2"].get("blocking"))
    return 1 if blocking else 0


if __name__ == "__main__":
    sys.exit(main())
