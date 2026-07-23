"""Tests for the ANALYZE state: multi-arm statistics and the gated analysis renderer.

Run with the CI flags (conftest puts experimento-cal/scripts/ on sys.path):

    uv run pytest experimento-cal/tests/test_analyze_stats.py --import-mode=importlib -o "addopts="

Covered:
  * test_multiarm_stats_selftest — a known-answer paired dataset where the trimmed-mean diff
    and the bootstrap CI sign are predictable; asserts BOTH the trimmed mean AND the raw mean
    are reported, and the bootstrap CI is deterministic under the fixed seed.
  * test_analyze_gate_order_and_prediction_section — a synthetic iteration (per_apk_paired.csv
    + tel_proxies.csv + minimal manifest.json) exercising analyze_iteration end to end;
    asserts the four gate sections appear IN ORDER, each arm's prediction and observed CI95
    appear side by side, and the temperature arm (role A6) is marked descriptive-only rather
    than eliminated by Gate 3.
"""

from __future__ import annotations

import json

import analyze_iteration
import multiarm_stats
import numpy as np


def test_multiarm_stats_selftest():
    """Known-answer mini paired dataset: arm strictly above anchor on every APK.

    With arm = anchor + 2 on all APKs, the difference of trimmed means is exactly +2.0, the
    raw-mean difference is exactly +2.0, and every bootstrap resample yields +2.0, so the CI
    is the degenerate [2.0, 2.0] with a strictly positive sign. Re-running with the same seed
    reproduces the CI bit-for-bit.
    """
    anchor = np.array([10.0, 12.0, 14.0, 16.0, 18.0, 20.0, 22.0, 24.0, 26.0, 28.0])
    arm = anchor + 2.0

    # Per-arm summary reports BOTH means.
    s = multiarm_stats.summarize_arm(arm)
    assert set(s) >= {"raw_mean", "trimmed_mean", "n", "sd"}
    assert s["n"] == 10
    assert s["raw_mean"] == 19.0 + 2.0  # mean(anchor)=19.0
    # 10% trim of 10 sorted points drops one per tail -> mean of the middle 8.
    assert abs(s["trimmed_mean"] - float(np.mean(np.sort(arm)[1:-1]))) < 1e-9

    # Paired bootstrap vs the anchor: predictable sign and degenerate CI under +2 shift.
    res_a = multiarm_stats.paired_bootstrap_vs_anchor(arm, anchor, B=2000, seed=42)
    assert res_a["n_pairs"] == 10
    assert res_a["trimmed_diff"] == 2.0
    assert res_a["raw_diff"] == 2.0
    assert res_a["ci_lo"] > 0.0 and res_a["ci_hi"] > 0.0  # sign is positive
    assert abs(res_a["ci_lo"] - 2.0) < 1e-9 and abs(res_a["ci_hi"] - 2.0) < 1e-9
    # Arm dominates anchor on every pair -> rank-biserial = +1.
    assert abs(res_a["rank_biserial"] - 1.0) < 1e-9

    # Determinism under the fixed seed: identical CI on a re-run.
    res_b = multiarm_stats.paired_bootstrap_vs_anchor(arm, anchor, B=2000, seed=42)
    assert (res_b["ci_lo"], res_b["ci_hi"]) == (res_a["ci_lo"], res_a["ci_hi"])

    # A non-degenerate case: a different seed on noisy data still yields a deterministic CI.
    rng = np.random.default_rng(0)
    noisy_anchor = rng.normal(20, 3, size=30)
    noisy_arm = noisy_anchor + rng.normal(1.5, 0.5, size=30)
    r1 = multiarm_stats.paired_bootstrap_vs_anchor(
        noisy_arm, noisy_anchor, B=5000, seed=7
    )
    r2 = multiarm_stats.paired_bootstrap_vs_anchor(
        noisy_arm, noisy_anchor, B=5000, seed=7
    )
    assert (r1["ci_lo"], r1["ci_hi"]) == (r2["ci_lo"], r2["ci_hi"])
    assert r1["ci_lo"] < r1["trimmed_diff"] < r1["ci_hi"]


def _write_fixture_iteration(tmp_path):
    """Craft a minimal but contract-shaped iteration under tmp_path/iter1.

    Arms: ANC1 (ape:default), ANC2 (aperv:sata_mop_act_frontier), A1 (aperv:cal_a1, temp 0),
    A6 (aperv:cal_a6, temp 0.7 — an H3 temperature arm). 12 APKs so the trim and Friedman
    omnibus are well defined.
    """
    iter_dir = tmp_path / "iter1"
    iter_dir.mkdir()

    tokens = {
        "ANC1": "ape:default",
        "ANC2": "aperv:sata_mop_act_frontier",
        "A1": "aperv:cal_a1",
        "A6": "aperv:cal_a6",
    }
    manifest = {
        "iteration": 1,
        "phase": "cala",
        "bootstrap_seed": 42,
        "image": {"tag": "phtcosta/rvandroid:0.9.3", "id": "87744cd58be9"},
        "arms": [
            {
                "role": "ANC1",
                "tool": "ape",
                "variant": "default",
                "rv_tools_token": tokens["ANC1"],
                "keys": {},
                "expected_config_ack": {},
            },
            {
                "role": "ANC2",
                "tool": "aperv",
                "variant": "sata_mop_act_frontier",
                "rv_tools_token": tokens["ANC2"],
                "keys": {},
                "expected_config_ack": {},
            },
            {
                "role": "A1",
                "tool": "aperv",
                "variant": "cal_a1",
                "rv_tools_token": tokens["A1"],
                "keys": {"llm_temperature": 0},
            },
            {
                "role": "A6",
                "tool": "aperv",
                "variant": "cal_a6",
                "rv_tools_token": tokens["A6"],
                "keys": {"llm_temperature": 0.7},
            },
        ],
    }
    (iter_dir / "manifest.json").write_text(json.dumps(manifest))

    # per_apk_paired.csv: one row per APK, {token}__{metric} columns. cov_mop is what the
    # analysis ranks; the LLM arms sit slightly above ANC2 to give a positive observed CI.
    n = 12
    rng = np.random.default_rng(1)
    metrics = ["cov_method", "cov_act", "cov_mop", "mop_unique", "mop_total", "crashes"]
    base = {
        tokens["ANC1"]: 30.0,
        tokens["ANC2"]: 35.0,
        tokens["A1"]: 38.0,
        tokens["A6"]: 37.0,
    }
    header = ["apk"] + [f"{tok}__{m}" for tok in tokens.values() for m in metrics]
    rows = [",".join(header)]
    for i in range(n):
        cells = [f"apk_{i:02d}"]
        for tok in tokens.values():
            for m in metrics:
                if m == "cov_mop":
                    val = base[tok] + rng.normal(0, 1.0)
                elif m in ("mop_unique", "mop_total", "crashes"):
                    val = float(rng.integers(0, 5))
                else:
                    val = base[tok] + rng.normal(0, 2.0)
                cells.append(f"{val:.4f}")
        rows.append(",".join(cells))
    (iter_dir / "per_apk_paired.csv").write_text("\n".join(rows) + "\n")

    # tel_proxies.csv: LLM arms only (A1, A6), one row per (arm, apk, rep). A1 deterministic
    # (identical reps -> temp 0), A6 stochastic (reps differ). Latency and parse-fail modest
    # so neither is eliminated by Gate 1.
    tel_header = [
        "arm",
        "apk",
        "rep",
        "calls",
        "time_ms",
        "matched",
        "llm_tap",
        "no_match",
        "no_match_parse_error",
        "mode_new_state",
        "mode_stagnation",
        "mode_random",
    ]
    tel_rows = [",".join(tel_header)]
    for i in range(n):
        apk = f"apk_{i:02d}"
        # A1: both reps identical (deterministic).
        for rep in (1, 2):
            tel_rows.append(
                ",".join(
                    str(x)
                    for x in [tokens["A1"], apk, rep, 20, 800, 12, 5, 3, 0, 10, 8, 2]
                )
            )
        # A6: reps differ (stochastic policy).
        tel_rows.append(
            ",".join(
                str(x) for x in [tokens["A6"], apk, 1, 18, 850, 10, 5, 3, 1, 9, 7, 2]
            )
        )
        tel_rows.append(
            ",".join(
                str(x) for x in [tokens["A6"], apk, 2, 22, 870, 13, 6, 3, 0, 11, 8, 3]
            )
        )
    (iter_dir / "tel_proxies.csv").write_text("\n".join(tel_rows) + "\n")

    return iter_dir


def test_analyze_gate_order_and_prediction_section(tmp_path):
    """analyze_iteration writes analysis.md with the four gates IN ORDER, prediction next to
    observed CI95, and the temperature arm (A6) marked descriptive-only (not eliminated).
    """
    iter_dir = _write_fixture_iteration(tmp_path)

    rc = analyze_iteration.main(["--iter-dir", str(iter_dir)])
    assert rc == 0

    md = (iter_dir / "analysis.md").read_text()

    # Four gate sections present, in the pre-declared order.
    markers = [
        "## Gate 1 — Proxy elimination",
        "## Gate 2 — Outcome ranking",
        "## Gate 3 — Mechanistic prediction vs observed",
        "## Gate 4 — Determinism",
    ]
    positions = [md.find(m) for m in markers]
    assert all(p >= 0 for p in positions), positions
    assert positions == sorted(positions), positions

    # Gate 2 reports BOTH raw and trimmed mean columns (INV-CAL-10).
    assert "raw mean" in md and "trimmed mean" in md

    # Gate 3 shows each arm's prediction and observed CI95 side by side (same table row).
    g3 = md[positions[2] : positions[3]]
    assert "Predicted Δcov_mop" in g3 and "Observed CI95" in g3
    # The A1 and A6 rows both carry a predicted value and a CI bracket.
    for tok in ("aperv:cal_a1", "aperv:cal_a6"):
        row = next(l for l in g3.splitlines() if f"`{tok}`" in l)
        assert "[" in row and "]" in row  # observed CI95 bracket
        # a numeric predicted Δcov_mop cell precedes the CI bracket
        assert row.count("|") >= 6

    # The temperature arm (A6) is descriptive-only, NOT eliminated by Gate 3.
    a6_row = next(l for l in g3.splitlines() if "`aperv:cal_a6`" in l)
    assert "descriptive only" in a6_row
    assert "do not promote without investigation" not in a6_row

    # Screening never concludes / declares a winner (wording check).
    assert "SCREENING" in md
    assert "does NOT conclude" in md
    assert "No arm is declared a winner" in md

    # Descriptive Friedman + Holm table present.
    assert "Descriptive Friedman + Holm" in md
    assert "Holm-adjusted pairwise Wilcoxon" in md
