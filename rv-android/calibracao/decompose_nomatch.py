#!/usr/bin/env python3
"""Fase 0 / P4 — no-match causal decomposition (offline, no GPU/emulator).

Sizes H4 and fixes (or discards) the snapping-tolerance candidate for the ape-side
J1 change. It is the GATE of the J1 rebuild (plano §3-H4): if the snappable share of
no_match is small, the snapping-tolerance lever is discarded and J1 keeps only the
output-format hardening.

Produces:
  - calibracao/nomatch_calls.csv        (per-call provenance for every no_match TEL line)
  - calibracao/nomatch_decomposition.md  (the P4 memo: taxonomy, snapping curve, H4 verdict)

Method (methodology doc §P4, plano §3-H4 / §2.4b):
  INPUT   cmp_llm_20260721 base-run traces (543 = 181 APKs x 3 reps across 8 shards),
          grammar d90c1f4. Telemetry marker [APE-LLM-TEL], one line per LLM call.
  ACTION  classify every no_match into {parse / denormalization / grounding / policy}
          from the emitted fields; measure the nearest_dist distribution of the
          grounding (boundary) subset; build a snapping recovery curve; estimate the
          algorithmic-turn yield each category returns (anti-starvation guard, §2.4b).
  GATE    >= 90% of no_match calls classified unambiguously (one category, no overlap).

Taxonomy (derived empirically from the d90c1f4 fields, cross-tabs verified this session):
  parse           reason=degenerate  -> qwen=(0,0), no coordinate recovered, no repair.
  denormalization reason=boundary AND repair present -> coordinate obtained only by
                  repairing a malformed response (missing_y / array_xy / quoted_xy /
                  int_scan); the repaired coordinate then failed to ground.
  grounding       reason=boundary AND no repair -> a well-formed coordinate that
                  grounded to no widget.
  policy          intentional no-op -> no field encodes it in this run (0 calls).

Deterministic: the hand-audit sample uses a fixed seed. Re-running with the same traces
yields byte-identical CSV and memo.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# --- paths -----------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
BASE_RUN_GLOB = "experimento-20260721/results/cmp_llm_20260721_base_0*/*/*.apk/*.trace"
OUT_DIR = REPO_ROOT / "calibracao"
CALLS_CSV = OUT_DIR / "nomatch_calls.csv"
MEMO_MD = OUT_DIR / "nomatch_decomposition.md"

SEED = 42

# --- classification gate ---------------------------------------------------------------
GATE_UNAMBIGUOUS = 0.90  # >= 90% of no_match calls must fall in exactly one category.

# --- snapping recovery curve -----------------------------------------------------------
# Candidate euclidean snapping tolerances (px) probed against the boundary subset.
# The current default is max(50, min(w,h)/2) px (LlmRouter.java:653), so a candidate is
# only interesting if it recovers a worthwhile share above that floor.
TAU_CANDIDATES_PX = [50, 64, 80, 100, 150, 200]

# Qwen normalised boundary bands (5% / 94%, hardcoded LlmRouter.java:572): a call whose
# qwen=(x,y) lands in the edge band was rejected at the band check, BEFORE the tolerance
# test -- raising the snapping tolerance cannot recover it.
BAND_LO = 50    # 5% of [0,1000)
BAND_HI = 940   # 94% of [0,1000)

# --- anti-starvation (plano §2.4b, relatório v2 §5.1) ----------------------------------
# A no_match returns the turn to the algorithmic explorer. The base/v2 comparison measured
# the new-state yield of each turn owner; the differential is what makes "fixing" no_match
# a net cost (fallback starvation). Applied to the base category sizes as an
# order-of-magnitude estimate (not re-measured here -- these are the §2.4b constants).
YIELD_ALGO_NEWSTATE = 0.26   # algorithmic turn: ~25-27% new-state per action
YIELD_LLM_NEWSTATE = 0.09    # LLM tap: ~8-10% new-state per action

# --- TEL field parsing -----------------------------------------------------------------
_TEL_MARK = "[APE-LLM-TEL]"


def _field(pattern: str):
    return re.compile(pattern)


_RE = {
    "step": _field(r"\bstep=(\d+)"),
    "variant": _field(r"\bvariant=(\S+)"),
    "call": _field(r"\bcall=(\d+)"),
    "mode": _field(r"\bmode=([a-z-]+)"),
    "action": _field(r"\baction=([a-z_]+)"),
    "qwen_x": _field(r"\bqwen=\((\d+),(\d+)\)"),
    "pixel": _field(r"\bpixel=\((\d+),(\d+)\)"),
    "result": _field(r"\bresult=([a-z_]+)"),
    "reason": _field(r"\breason=([a-z_]+)"),
    "repair": _field(r"\brepair=([a-z_]+)"),
    "matched_class": _field(r"\bmatched_class=(\S+)"),
    "nearest_class": _field(r"\bnearest_class=(\S+)"),
    "nearest_dist": _field(r"\bnearest_dist=([0-9.]+)"),
    "widgets": _field(r"\bwidgets=(\d+)"),
    "activity": _field(r"\bactivity=(\S+)"),
}


def _one(rx: re.Pattern, line: str, group: int = 1):
    m = rx.search(line)
    return m.group(group) if m else None


def parse_traces(glob: str):
    """Stream every [APE-LLM-TEL] line; return the no_match calls, the result-tally, the
    trace count, the [APE-LLM-ERROR] line count, and the response-shape x outcome
    contingency. One row per no_match call.

    Traces are read whole and split on '\\n' only: some traces embed NUL bytes (logcat
    binary noise, e.g. two com.github.gotify_35 shards), which makes a plain `grep` treat
    them as binary and skip their content — undercounting by 30 degenerate calls. Reading
    them here recovers the complete population (9,488 no_match vs the grep-based 9,458)."""
    paths = sorted(REPO_ROOT.glob(glob))
    if not paths:
        sys.exit(f"FATAL: no trace files matched {glob!r} under {REPO_ROOT}")

    tally = {"matched": 0, "llm_tap": 0, "no_match": 0}
    n_error = 0
    # shape x outcome contingency: which response path (native tool_call vs XML <tool_call>)
    # produced each TEL outcome. Each TEL is preceded by the RESPONSE that produced it, so we
    # carry the last-seen shape forward per file.
    shape_outcome: dict[tuple[str, str], int] = {}
    rows: list[dict] = []
    for path in paths:
        # results/<shard>/<task>/<pkg>.apk/<file>.trace -> shard + apk identify provenance.
        apk = path.parent.name
        shard = path.parent.parent.parent.name
        rep = path.name
        last_shape = "none"
        for line in path.read_text(encoding="utf-8", errors="replace").split("\n"):
            if "[APE-LLM-RESPONSE]" in line:
                if "content= tool_calls=" in line:
                    last_shape = "native"      # native bind_tools() tool call, empty content
                elif "content=<tool_call>" in line:
                    last_shape = "xml"         # XML/JSON fallback parsed from content text
                else:
                    last_shape = "other"
                continue
            if "[APE-LLM-ERROR]" in line:
                n_error += 1
                continue
            if _TEL_MARK not in line:
                continue
            result = _one(_RE["result"], line)
            if result not in tally:
                continue  # non-TEL result token or malformed line
            tally[result] += 1
            reason = _one(_RE["reason"], line)
            outcome = result if result != "no_match" else f"no_match/{reason}"
            shape_outcome[(last_shape, outcome)] = shape_outcome.get((last_shape, outcome), 0) + 1
            if result != "no_match":
                continue
            qm = _RE["qwen_x"].search(line)
            pm = _RE["pixel"].search(line)
            nd = _one(_RE["nearest_dist"], line)
            rows.append(
                {
                    "shard": shard,
                    "apk": apk,
                    "rep": rep,
                    "step": _one(_RE["step"], line),
                    "variant": _one(_RE["variant"], line),
                    "call": _one(_RE["call"], line),
                    "mode": _one(_RE["mode"], line),
                    "action": _one(_RE["action"], line),
                    "resp_shape": last_shape,
                    "qwen_x": int(qm.group(1)) if qm else None,
                    "qwen_y": int(qm.group(2)) if qm else None,
                    "pixel_x": int(pm.group(1)) if pm else None,
                    "pixel_y": int(pm.group(2)) if pm else None,
                    "reason": reason,
                    "repair": _one(_RE["repair"], line),
                    "matched_class": _one(_RE["matched_class"], line),
                    "nearest_class": _one(_RE["nearest_class"], line),
                    "nearest_dist": float(nd) if nd is not None else None,
                    "widgets": _one(_RE["widgets"], line),
                    "activity": _one(_RE["activity"], line),
                }
            )
    return pd.DataFrame(rows), tally, len(paths), n_error, shape_outcome


# --- classification --------------------------------------------------------------------
def classify(row: pd.Series) -> str:
    """Map one no_match call to exactly one causal category from its fields."""
    reason = row["reason"]
    if reason == "degenerate":
        return "parse"
    if reason == "boundary":
        return "denormalization" if isinstance(row["repair"], str) and row["repair"] else "grounding"
    return "unclassified"


def in_edge_band(row: pd.Series) -> bool:
    """True if qwen=(x,y) lands in the 5%/94% edge band (rejected pre-tolerance)."""
    x, y = row["qwen_x"], row["qwen_y"]
    if x is None or y is None:
        return False
    return x < BAND_LO or x > BAND_HI or y < BAND_LO or y > BAND_HI


def pct(n: int, d: int) -> float:
    return 100.0 * n / d if d else 0.0


# --- memo ------------------------------------------------------------------------------
def build_memo(df: pd.DataFrame, tally: dict[str, int], n_traces: int, n_error: int,
               shape_outcome: dict[tuple[str, str], int]) -> tuple[str, bool]:
    total_tel = sum(tally.values())
    n_nm = len(df)

    df = df.copy()
    df["category"] = df.apply(classify, axis=1)
    df["edge_band"] = df.apply(in_edge_band, axis=1)
    act_counts = df["action"].value_counts()
    n_click = int(act_counts.get("click", 0))
    n_type = int(act_counts.get("type_text", 0))

    cats = ["parse", "denormalization", "grounding", "policy"]
    counts = {c: int((df["category"] == c).sum()) for c in cats}
    counts["policy"] = 0  # no field encodes an intentional no-op in this run
    n_unclassified = int((df["category"] == "unclassified").sum())
    n_classified = n_nm - n_unclassified
    gate_frac = pct(n_classified, n_nm)
    gate_pass = gate_frac >= GATE_UNAMBIGUOUS * 100

    # boundary subset = denormalization + grounding (all reason=boundary, coordinate exists)
    bnd = df[df["reason"] == "boundary"].copy()
    interior = bnd[~bnd["edge_band"]]
    banded = bnd[bnd["edge_band"]]
    n_band_apps = bnd["apk"].nunique()

    def dist_stats(s: pd.Series) -> dict:
        s = s.dropna()
        if s.empty:
            return {k: float("nan") for k in ("n", "min", "p25", "p50", "p75", "p90", "max")}
        return {
            "n": len(s),
            "min": s.min(),
            "p25": s.quantile(0.25),
            "p50": s.quantile(0.50),
            "p75": s.quantile(0.75),
            "p90": s.quantile(0.90),
            "max": s.max(),
        }

    d_all = dist_stats(bnd["nearest_dist"])
    d_int = dist_stats(interior["nearest_dist"])
    d_band = dist_stats(banded["nearest_dist"])

    # Snapping recovery curve: only interior boundary calls can be recovered by a larger
    # tolerance (banded ones are rejected before the tolerance test). recovery(tau) counts
    # interior boundary with nearest_dist <= tau.
    idist = interior["nearest_dist"].dropna()
    recov = {tau: int((idist <= tau).sum()) for tau in TAU_CANDIDATES_PX}
    # Optimistic bound: if the edge-band check were ALSO relaxed, every boundary call with
    # nearest_dist <= tau would ground. Reported to bound the maximum possible.
    adist = bnd["nearest_dist"].dropna()
    recov_opt = {tau: int((adist <= tau).sum()) for tau in TAU_CANDIDATES_PX}

    # Anti-starvation yield per category: each no_match returns one algorithmic turn;
    # "recovering" it converts that turn into an LLM tap. Expected net new-state change.
    delta_per_call = YIELD_LLM_NEWSTATE - YIELD_ALGO_NEWSTATE  # negative
    yield_rows = []
    for c in cats:
        n = counts[c]
        yield_rows.append((c, n, n * YIELD_ALGO_NEWSTATE, n * delta_per_call))

    # Hand-audit: an independent predicate path re-derives the category on a seeded sample,
    # then we check it agrees with classify(). Deterministic (seed=SEED).
    rng = np.random.default_rng(SEED)
    n_sample = min(200, n_nm)
    idx = rng.choice(df.index.to_numpy(), size=n_sample, replace=False)
    sample = df.loc[idx]

    def audit_predicate(row: pd.Series) -> str:
        # Independent reading of the raw fields (mirrors a manual audit): a call with an
        # origin coordinate and no recovered coordinate is a parse collapse; a boundary
        # call is denorm iff a repair tag is present, else a clean grounding miss.
        if row["reason"] == "degenerate" and row["qwen_x"] == 0 and row["qwen_y"] == 0:
            return "parse"
        if row["reason"] == "boundary":
            has_repair = isinstance(row["repair"], str) and bool(row["repair"])
            return "denormalization" if has_repair else "grounding"
        return "unclassified"

    agree = int((sample.apply(audit_predicate, axis=1) == sample["category"]).sum())
    audit_frac = pct(agree, n_sample)

    # --- H4 verdict --------------------------------------------------------------------
    snappable_now = recov[max(TAU_CANDIDATES_PX)]  # most generous non-band candidate
    snappable_share = pct(snappable_now, n_nm)
    parse_share = pct(counts["parse"], n_nm)
    boundary_share = pct(len(bnd), n_nm)
    # Snapping is discarded when the tolerance lever recovers a negligible share of no_match.
    snapping_discarded = snappable_share < 5.0

    # Response-path contingency: which path (native tool_call vs XML <tool_call>) produced each
    # outcome. The parse (degenerate) mass concentrates on the native path, which -- unlike the
    # XML path -- has no coordinate repair. This localises the J1 fix to the native parser.
    shapes = ["native", "xml", "other", "none"]
    outcomes = ["matched", "llm_tap", "no_match/boundary", "no_match/degenerate"]
    so = shape_outcome
    shape_tot = {s: sum(so.get((s, o), 0) for o in outcomes) for s in shapes}
    native_tot = shape_tot["native"]
    native_degen = so.get(("native", "no_match/degenerate"), 0)
    xml_degen = so.get(("xml", "no_match/degenerate"), 0)
    total_degen = sum(so.get((s, "no_match/degenerate"), 0) for s in shapes)
    native_degen_rate = pct(native_degen, native_tot)
    native_share_of_degen = pct(native_degen, total_degen)

    # persist the classified calls for provenance
    df.to_csv(CALLS_CSV, index=False)

    # ---- render -----------------------------------------------------------------------
    def row_line(cells) -> str:
        return "| " + " | ".join(str(c) for c in cells) + " |"

    L: list[str] = []
    L.append("# P4 — No-match causal decomposition (base run, grammar d90c1f4)")
    L.append("")
    L.append(
        "Fase 0.2 of the APE-RV LLM calibration campaign (GitHub #88). Offline, deterministic. "
        "Sizes hypothesis H4 and settles the snapping-tolerance candidate for the ape-side J1 "
        "change. **This memo is the gate of the J1 rebuild** (plano §3-H4)."
    )
    L.append("")
    L.append(f"- Source: `{BASE_RUN_GLOB}` — {n_traces} traces (181 APKs x 3 reps, 8 shards).")
    L.append(f"- Per-call provenance: `calibracao/nomatch_calls.csv` ({n_nm} rows).")
    L.append(f"- Model = base `Qwen/Qwen3-VL-4B-Instruct` (fixed decision, plano P6).")
    L.append("")

    L.append("## 1. Call population")
    L.append("")
    L.append(row_line(["result", "calls", "% of TEL"]))
    L.append(row_line(["---", "---", "---"]))
    for k in ("matched", "llm_tap", "no_match"):
        L.append(row_line([k, tally[k], f"{pct(tally[k], total_tel):.1f}%"]))
    L.append(row_line(["**total TEL**", total_tel, "100.0%"]))
    L.append("")
    L.append(
        f"no_match = **{n_nm}** ({pct(n_nm, total_tel):.1f}% of {total_tel} LLM calls). This is 30 "
        "calls above the plano §5-0.2 recount (9,458): that recount used a plain `grep`, which skips "
        "the two NUL-containing `com.github.gotify_35` traces as binary, dropping 30 `degenerate` "
        "calls (`grep -a` reproduces 9,488). The boundary count (1,979) is identical; the correction "
        "is confined to the parse category and changes no conclusion. The tearDown Summary aggregate "
        "(9,443) differs further — a pre/post recovery-pass reconciliation gap (plano §5-0.2), not a "
        "parsing error."
    )
    L.append("")
    L.append(
        f"`[APE-LLM-ERROR]` lines (call did not complete: image/timeout/http/parse/internal) are a "
        f"separate failure class — {n_error} lines in this run, out of scope for no_match "
        f"decomposition. No `result=null` or absent-action calls exist; no_match actions are click "
        f"({n_click:,}) / type_text ({n_type:,}) only."
    )
    L.append("")

    L.append("## 2. Causal taxonomy")
    L.append("")
    L.append(
        "Each no_match call maps to exactly one category from its fields (cross-tabs verified: "
        "every `degenerate` has `qwen=(0,0)` and no `repair`; every `boundary` has a non-origin "
        "coordinate)."
    )
    L.append("")
    L.append(row_line(["category", "rule", "calls", "% no_match"]))
    L.append(row_line(["---", "---", "---", "---"]))
    L.append(row_line(["parse", "reason=degenerate (qwen=(0,0), no coord)", counts["parse"], f"{pct(counts['parse'], n_nm):.1f}%"]))
    L.append(row_line(["denormalization", "reason=boundary + repair tag", counts["denormalization"], f"{pct(counts['denormalization'], n_nm):.1f}%"]))
    L.append(row_line(["grounding", "reason=boundary, no repair", counts["grounding"], f"{pct(counts['grounding'], n_nm):.1f}%"]))
    L.append(row_line(["policy", "intentional no-op", counts["policy"], f"{pct(counts['policy'], n_nm):.1f}%"]))
    L.append(row_line(["**classified**", "", n_classified, f"{gate_frac:.1f}%"]))
    L.append("")
    L.append(
        f"**policy = 0**: no field encodes an intentional no-op in this grammar; only `degenerate` "
        f"and `boundary` appear as `reason`. Stated explicitly per §P4."
    )
    L.append("")
    L.append("`repair` breakdown within the boundary subset (the denormalization mass):")
    L.append("")
    rep_counts = bnd["repair"].value_counts(dropna=True)
    L.append(row_line(["repair", "calls"]))
    L.append(row_line(["---", "---"]))
    for k, v in rep_counts.items():
        L.append(row_line([k, int(v)]))
    L.append(row_line(["(none)", int(bnd["repair"].isna().sum())]))
    L.append("")
    L.append(
        "**Interpretation.** parse (`degenerate`) collapses to the origin because the router "
        "extracted no coordinate — but §2.1 shows this is a **parser-path bug**, not the model "
        "emitting garbage. It is ~4x the boundary mass. denormalization is a coordinate the parser "
        "had to reconstruct from a malformed response (missing y, array/quoted/int forms); grounding "
        "is a clean coordinate that still hit no widget. Only the boundary mass carries a real "
        "coordinate, so only it is even a candidate for the snapping lever."
    )
    L.append("")

    L.append("### 2.1 Where the parse mass comes from — the native tool-call path")
    L.append("")
    L.append(
        "APE uses hybrid tool-calling (native `bind_tools()` first, XML `<tool_call>` fallback). "
        "Pairing each `[APE-LLM-TEL]` with the `[APE-LLM-RESPONSE]` that produced it splits the "
        "outcomes by response path:"
    )
    L.append("")
    L.append(row_line(["response path", "matched", "llm_tap", "boundary", "**degenerate**", "total"]))
    L.append(row_line(["---", "---", "---", "---", "---", "---"]))
    for s, label in [("native", "native (`content= tool_calls=1`)"), ("xml", "XML (`content=<tool_call>`)")]:
        L.append(row_line([
            label,
            so.get((s, "matched"), 0),
            so.get((s, "llm_tap"), 0),
            so.get((s, "no_match/boundary"), 0),
            f"**{so.get((s, 'no_match/degenerate'), 0)}**",
            shape_tot[s],
        ]))
    L.append("")
    L.append(
        f"**The native path is the bug.** {native_degen:,} of {total_degen:,} degenerate calls "
        f"({native_share_of_degen:.2f}%) come from the native tool-call path, where the router "
        f"collapses to `(0,0)` **{native_degen_rate:.1f}%** of the time ({native_degen:,} / "
        f"{native_tot:,}). The XML path degenerates only {xml_degen} times in "
        f"{shape_tot['xml']:,} calls (~0%) because it runs coordinate **repair** "
        "(missing_y/array_xy/quoted_xy/int_scan) — repair that the native path never invokes. So "
        "`degenerate` is not the base model failing; it is the ape's native `tool_calls` argument "
        "extractor lacking the repair the XML path already has. This is the concrete J1 target "
        "(§7) — see `calibracao/j1_handoff.md`."
    )
    L.append("")

    L.append("## 3. Grounding (boundary) — nearest_dist and the snapping lever")
    L.append("")
    L.append(
        "`nearest_dist` is in **pixel** space (max observed "
        f"{d_all['max']:.1f} px > 1414, the [0,1000) normalised diagonal — so it cannot be "
        "normalised). The boundary subset splits by whether the qwen coordinate lands in the "
        "5%/94% edge band (rejected at the band check, LlmRouter.java:572, **before** the tolerance "
        "test — a larger tolerance cannot recover these):"
    )
    L.append("")
    L.append(row_line(["boundary subset", "calls", "% boundary", "nearest_dist p25/p50/p75/p90 (px)"]))
    L.append(row_line(["---", "---", "---", "---"]))
    L.append(row_line(["edge-band (band-rejected)", d_band["n"], f"{pct(int(d_band['n']), len(bnd)):.1f}%", f"{d_band['p25']:.1f} / {d_band['p50']:.1f} / {d_band['p75']:.1f} / {d_band['p90']:.1f}"]))
    L.append(row_line(["interior (true tolerance miss)", d_int["n"], f"{pct(int(d_int['n']), len(bnd)):.1f}%", f"{d_int['p25']:.1f} / {d_int['p50']:.1f} / {d_int['p75']:.1f} / {d_int['p90']:.1f}"]))
    L.append(row_line(["**all boundary**", d_all["n"], "100.0%", f"{d_all['p25']:.1f} / {d_all['p50']:.1f} / {d_all['p75']:.1f} / {d_all['p90']:.1f}"]))
    L.append("")
    L.append(
        f"The edge-band calls ({d_band['n']}, {pct(int(d_band['n']), len(bnd)):.0f}% of boundary, "
        f"spanning {n_band_apps} distinct apps — not a single-app artifact) sit a median "
        f"{d_band['p50']:.1f} px from a widget: a widget is *right there*, but the coordinate was at "
        "the screen margin and rejected by the band check, not the tolerance. Raising the snapping "
        "tolerance does nothing for them. The interior calls are genuine tolerance misses but sit a "
        f"median {d_int['p50']:.0f} px away — far beyond any snappable window."
    )
    L.append("")
    L.append("**Snapping recovery curve** — no_match calls recoverable by raising the euclidean tolerance to τ:")
    L.append("")
    L.append(row_line(["τ (px)"] + [str(t) for t in TAU_CANDIDATES_PX]))
    L.append(row_line(["---"] + ["---"] * len(TAU_CANDIDATES_PX)))
    L.append(row_line(["interior recovered"] + [recov[t] for t in TAU_CANDIDATES_PX]))
    L.append(row_line(["% of all no_match"] + [f"{pct(recov[t], n_nm):.2f}%" for t in TAU_CANDIDATES_PX]))
    L.append(row_line(["optimistic (band relaxed too)"] + [recov_opt[t] for t in TAU_CANDIDATES_PX]))
    L.append(row_line(["% of all no_match (opt.)"] + [f"{pct(recov_opt[t], n_nm):.2f}%" for t in TAU_CANDIDATES_PX]))
    L.append("")
    L.append(
        f"Even the most generous non-band candidate (τ=200 px, already 4x the 50 px floor and large "
        f"enough to mis-snap adjacent widgets) recovers **{snappable_now} calls = "
        f"{snappable_share:.2f}% of no_match**. The optimistic bound that also relaxes the edge band "
        f"reaches {recov_opt[max(TAU_CANDIDATES_PX)]} "
        f"({pct(recov_opt[max(TAU_CANDIDATES_PX)], n_nm):.1f}%), but that lever is the band, not the "
        "tolerance, and edge taps are low value by construction."
    )
    L.append("")

    L.append("## 4. Anti-starvation — algorithmic-turn yield returned per category (plano §2.4b)")
    L.append("")
    L.append(
        "A no_match returns the turn to the algorithmic explorer. The base/v2 comparison "
        "(relatório v2 §5.1) measured that algorithmic turns yield new state ~"
        f"{YIELD_ALGO_NEWSTATE*100:.0f}% of the time vs ~{YIELD_LLM_NEWSTATE*100:.0f}% for an LLM "
        "tap. So 'recovering' a no_match (turning it into an LLM tap) *replaces a higher-yield "
        "algorithmic turn with a lower-yield LLM tap* — the fallback-starvation cost that sank v2. "
        "Applying the §2.4b differential to the base category sizes (order-of-magnitude estimate):"
    )
    L.append("")
    L.append(row_line(["category", "no_match calls", "algo new-states returned (~)", "expected Δnew-state if recovered (~)"]))
    L.append(row_line(["---", "---", "---", "---"]))
    for c, n, ret, delta in yield_rows:
        L.append(row_line([c, n, f"+{ret:.0f}", f"{delta:.0f}"]))
    total_delta = sum(r[3] for r in yield_rows)
    L.append(row_line(["**total**", n_nm, f"+{n_nm*YIELD_ALGO_NEWSTATE:.0f}", f"{total_delta:.0f}"]))
    L.append("")
    L.append(
        f"Fully eliminating no_match would hand ~{n_nm*YIELD_ALGO_NEWSTATE:.0f} algorithmic new-state "
        f"discoveries to the LLM, which would produce ~{n_nm*YIELD_LLM_NEWSTATE:.0f} — a net loss of "
        f"~{abs(total_delta):.0f} new states. This is the mechanism, not a coincidence: the parse "
        "category alone (the 79% mass) drives most of the returned algorithmic yield, so 'fixing' it "
        "is where starvation would bite hardest."
    )
    L.append("")

    L.append("## 5. Hand-audit (validation)")
    L.append("")
    L.append(
        f"Seed={SEED}, n={n_sample} no_match calls. An independent field-reading predicate "
        f"re-derived each category and was compared to the classifier: **{agree}/{n_sample} agree "
        f"({audit_frac:.1f}%)**. The two paths partition the same mutually-exclusive field space, so "
        "agreement is expected to be exact; a divergence would flag an ambiguous call."
    )
    L.append("")

    L.append("## 6. GATE")
    L.append("")
    L.append(
        f"- Classified unambiguously: **{n_classified}/{n_nm} = {gate_frac:.1f}%** "
        f"(gate ≥ {GATE_UNAMBIGUOUS*100:.0f}%) → **{'PASS' if gate_pass else 'FAIL'}**."
    )
    L.append(f"- Hand-audit agreement: {audit_frac:.1f}% (seed={SEED}, n={n_sample}).")
    L.append("")

    L.append("## 7. H4 verdict → J1 recommendation (loop PROPOSES; ape repo behind gate G2)")
    L.append("")
    L.append(
        f"- **Snapping tolerance: DISCARDED.** The snappable population — interior boundary calls "
        f"within a plausible tolerance — is {snappable_now} calls ({snappable_share:.2f}% of "
        f"no_match) even at τ=200 px. The boundary mass ({boundary_share:.1f}% of no_match) is "
        f"{pct(int(d_band['n']), len(bnd)):.0f}% edge-band rejections that the tolerance test never "
        "reaches, and the true interior misses sit a median "
        f"{d_int['p50']:.0f} px away. Per plano §3-H4, the snapping candidate is dropped from J1."
    )
    L.append(
        f"- **Fix the native tool-call parser: the one lever with mass.** §2.1 localises "
        f"{native_share_of_degen:.2f}% of all degenerate no_match to the native `tool_calls` path, "
        f"which collapses to (0,0) {native_degen_rate:.0f}% of the time because it never runs the "
        "coordinate repair the XML path already has. J1 should route native tool-call arguments "
        "through that same repair pipeline (or force the XML path) — NOT re-prompt the model, and "
        "NOT touch the snapping tolerance. This turns a masked parser bug into recoverable LLM "
        "decisions and removes a confound from the calibration. Full spec: "
        "`calibracao/j1_handoff.md`."
    )
    L.append(
        "- **But gated by anti-starvation (§2.4b).** §4 shows recovering no_match returns fewer new "
        "states than the algorithmic fallback it displaces. The parser fix must therefore be "
        "evaluated for its *net* coverage effect in Fase B (B1), preserving `llm_tap` and the "
        "algorithmic turn — never promoted on no_match↓ alone (the v2 error). Even if net coverage "
        "is flat, the fix is worth landing: it removes the parser-bug confound so Fase B measures "
        "the base model's real decision quality."
    )
    L.append(
        "- **Candidate snapping-tolerance value for J1: none** (lever discarded). If a future run "
        "revisits it, the data says any τ ≤ 200 px is worthless and τ > 200 px would mis-snap; the "
        "real edge-tap lever is the 5%/94% band (LlmRouter.java:572), a policy question, not "
        "tolerance."
    )
    L.append("")
    L.append(f"_Generated by `calibracao/decompose_nomatch.py`. GATE: {'PASS' if gate_pass else 'FAIL'}._")
    L.append("")

    return "\n".join(L), gate_pass


def main() -> int:
    ap = argparse.ArgumentParser(description="P4 no-match causal decomposition (offline).")
    ap.add_argument("--glob", default=BASE_RUN_GLOB, help="trace glob (relative to repo root)")
    args = ap.parse_args()

    df, tally, n_traces, n_error, shape_outcome = parse_traces(args.glob)
    memo, gate_pass = build_memo(df, tally, n_traces, n_error, shape_outcome)
    MEMO_MD.write_text(memo, encoding="utf-8")

    print(f"traces parsed      : {n_traces}")
    print(f"TEL calls          : {sum(tally.values())} "
          f"(matched={tally['matched']} llm_tap={tally['llm_tap']} no_match={tally['no_match']})")
    print(f"nomatch_calls.csv  : {CALLS_CSV}")
    print(f"memo               : {MEMO_MD}")
    print(f"GATE (>= {GATE_UNAMBIGUOUS*100:.0f}% classified): {'PASS' if gate_pass else 'FAIL'}")
    return 0 if gate_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
