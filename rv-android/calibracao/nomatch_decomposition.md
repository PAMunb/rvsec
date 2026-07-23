# P4 — No-match causal decomposition (base run, grammar d90c1f4)

Fase 0.2 of the APE-RV LLM calibration campaign (GitHub #88). Offline, deterministic. Sizes hypothesis H4 and settles the snapping-tolerance candidate for the ape-side J1 change. **This memo is the gate of the J1 rebuild** (plano §3-H4).

- Source: `experimento-20260721/results/cmp_llm_20260721_base_0*/*/*.apk/*.trace` — 543 traces (181 APKs x 3 reps, 8 shards).
- Per-call provenance: `calibracao/nomatch_calls.csv` (9488 rows).
- Model = base `Qwen/Qwen3-VL-4B-Instruct` (fixed decision, plano P6).

## 1. Call population

| result | calls | % of TEL |
| --- | --- | --- |
| matched | 37943 | 69.6% |
| llm_tap | 7066 | 13.0% |
| no_match | 9488 | 17.4% |
| **total TEL** | 54497 | 100.0% |

no_match = **9488** (17.4% of 54497 LLM calls). This is 30 calls above the plano §5-0.2 recount (9,458): that recount used a plain `grep`, which skips the two NUL-containing `com.github.gotify_35` traces as binary, dropping 30 `degenerate` calls (`grep -a` reproduces 9,488). The boundary count (1,979) is identical; the correction is confined to the parse category and changes no conclusion. The tearDown Summary aggregate (9,443) differs further — a pre/post recovery-pass reconciliation gap (plano §5-0.2), not a parsing error.

`[APE-LLM-ERROR]` lines (call did not complete: image/timeout/http/parse/internal) are a separate failure class — 9 lines in this run, out of scope for no_match decomposition. No `result=null` or absent-action calls exist; no_match actions are click (9,309) / type_text (179) only.

## 2. Causal taxonomy

Each no_match call maps to exactly one category from its fields (cross-tabs verified: every `degenerate` has `qwen=(0,0)` and no `repair`; every `boundary` has a non-origin coordinate).

| category | rule | calls | % no_match |
| --- | --- | --- | --- |
| parse | reason=degenerate (qwen=(0,0), no coord) | 7509 | 79.1% |
| denormalization | reason=boundary + repair tag | 1615 | 17.0% |
| grounding | reason=boundary, no repair | 364 | 3.8% |
| policy | intentional no-op | 0 | 0.0% |
| **classified** |  | 9488 | 100.0% |

**policy = 0**: no field encodes an intentional no-op in this grammar; only `degenerate` and `boundary` appear as `reason`. Stated explicitly per §P4.

`repair` breakdown within the boundary subset (the denormalization mass):

| repair | calls |
| --- | --- |
| missing_y | 1372 |
| quoted_xy | 182 |
| array_xy | 49 |
| int_scan | 12 |
| (none) | 364 |

**Interpretation.** parse (`degenerate`) collapses to the origin because the router extracted no coordinate — but §2.1 shows this is a **parser-path bug**, not the model emitting garbage. It is ~4x the boundary mass. denormalization is a coordinate the parser had to reconstruct from a malformed response (missing y, array/quoted/int forms); grounding is a clean coordinate that still hit no widget. Only the boundary mass carries a real coordinate, so only it is even a candidate for the snapping lever.

### 2.1 Where the parse mass comes from — the native tool-call path

APE uses hybrid tool-calling (native `bind_tools()` first, XML `<tool_call>` fallback). Pairing each `[APE-LLM-TEL]` with the `[APE-LLM-RESPONSE]` that produced it splits the outcomes by response path:

| response path | matched | llm_tap | boundary | **degenerate** | total |
| --- | --- | --- | --- | --- | --- |
| native (`content= tool_calls=1`) | 4355 | 741 | 364 | **7506** | 12966 |
| XML (`content=<tool_call>`) | 33584 | 6320 | 1615 | **3** | 41522 |

**The native path is the bug.** 7,506 of 7,509 degenerate calls (99.96%) come from the native tool-call path, where the router collapses to `(0,0)` **57.9%** of the time (7,506 / 12,966). The XML path degenerates only 3 times in 41,522 calls (~0%) because it runs coordinate **repair** (missing_y/array_xy/quoted_xy/int_scan) — repair that the native path never invokes. So `degenerate` is not the base model failing; it is the ape's native `tool_calls` argument extractor lacking the repair the XML path already has. This is the concrete J1 target (§7) — see `calibracao/j1_handoff.md`.

## 3. Grounding (boundary) — nearest_dist and the snapping lever

`nearest_dist` is in **pixel** space (max observed 1626.5 px > 1414, the [0,1000) normalised diagonal — so it cannot be normalised). The boundary subset splits by whether the qwen coordinate lands in the 5%/94% edge band (rejected at the band check, LlmRouter.java:572, **before** the tolerance test — a larger tolerance cannot recover these):

| boundary subset | calls | % boundary | nearest_dist p25/p50/p75/p90 (px) |
| --- | --- | --- | --- |
| edge-band (band-rejected) | 1801 | 91.0% | 2.2 / 7.1 / 445.0 / 839.7 |
| interior (true tolerance miss) | 178 | 9.0% | 105.2 / 233.3 / 426.6 / 534.9 |
| **all boundary** | 1979 | 100.0% | 2.2 / 27.0 / 431.1 / 815.2 |

The edge-band calls (1801, 91% of boundary, spanning 144 distinct apps — not a single-app artifact) sit a median 7.1 px from a widget: a widget is *right there*, but the coordinate was at the screen margin and rejected by the band check, not the tolerance. Raising the snapping tolerance does nothing for them. The interior calls are genuine tolerance misses but sit a median 233 px away — far beyond any snappable window.

**Snapping recovery curve** — no_match calls recoverable by raising the euclidean tolerance to τ:

| τ (px) | 50 | 64 | 80 | 100 | 150 | 200 |
| --- | --- | --- | --- | --- | --- | --- |
| interior recovered | 7 | 9 | 26 | 39 | 53 | 76 |
| % of all no_match | 0.07% | 0.09% | 0.27% | 0.41% | 0.56% | 0.80% |
| optimistic (band relaxed too) | 1011 | 1037 | 1057 | 1109 | 1181 | 1242 |
| % of all no_match (opt.) | 10.66% | 10.93% | 11.14% | 11.69% | 12.45% | 13.09% |

Even the most generous non-band candidate (τ=200 px, already 4x the 50 px floor and large enough to mis-snap adjacent widgets) recovers **76 calls = 0.80% of no_match**. The optimistic bound that also relaxes the edge band reaches 1242 (13.1%), but that lever is the band, not the tolerance, and edge taps are low value by construction.

## 4. Anti-starvation — algorithmic-turn yield returned per category (plano §2.4b)

A no_match returns the turn to the algorithmic explorer. The base/v2 comparison (relatório v2 §5.1) measured that algorithmic turns yield new state ~26% of the time vs ~9% for an LLM tap. So 'recovering' a no_match (turning it into an LLM tap) *replaces a higher-yield algorithmic turn with a lower-yield LLM tap* — the fallback-starvation cost that sank v2. Applying the §2.4b differential to the base category sizes (order-of-magnitude estimate):

| category | no_match calls | algo new-states returned (~) | expected Δnew-state if recovered (~) |
| --- | --- | --- | --- |
| parse | 7509 | +1952 | -1277 |
| denormalization | 1615 | +420 | -275 |
| grounding | 364 | +95 | -62 |
| policy | 0 | +0 | -0 |
| **total** | 9488 | +2467 | -1613 |

Fully eliminating no_match would hand ~2467 algorithmic new-state discoveries to the LLM, which would produce ~854 — a net loss of ~1613 new states. This is the mechanism, not a coincidence: the parse category alone (the 79% mass) drives most of the returned algorithmic yield, so 'fixing' it is where starvation would bite hardest.

## 5. Hand-audit (validation)

Seed=42, n=200 no_match calls. An independent field-reading predicate re-derived each category and was compared to the classifier: **200/200 agree (100.0%)**. The two paths partition the same mutually-exclusive field space, so agreement is expected to be exact; a divergence would flag an ambiguous call.

## 6. GATE

- Classified unambiguously: **9488/9488 = 100.0%** (gate ≥ 90%) → **PASS**.
- Hand-audit agreement: 100.0% (seed=42, n=200).

## 7. H4 verdict → J1 recommendation (loop PROPOSES; ape repo behind gate G2)

- **Snapping tolerance: DISCARDED.** The snappable population — interior boundary calls within a plausible tolerance — is 76 calls (0.80% of no_match) even at τ=200 px. The boundary mass (20.9% of no_match) is 91% edge-band rejections that the tolerance test never reaches, and the true interior misses sit a median 233 px away. Per plano §3-H4, the snapping candidate is dropped from J1.
- **Fix the native tool-call parser: the one lever with mass.** §2.1 localises 99.96% of all degenerate no_match to the native `tool_calls` path, which collapses to (0,0) 58% of the time because it never runs the coordinate repair the XML path already has. J1 should route native tool-call arguments through that same repair pipeline (or force the XML path) — NOT re-prompt the model, and NOT touch the snapping tolerance. This turns a masked parser bug into recoverable LLM decisions and removes a confound from the calibration. Full spec: `calibracao/j1_handoff.md`.
- **But gated by anti-starvation (§2.4b).** §4 shows recovering no_match returns fewer new states than the algorithmic fallback it displaces. The parser fix must therefore be evaluated for its *net* coverage effect in Fase B (B1), preserving `llm_tap` and the algorithmic turn — never promoted on no_match↓ alone (the v2 error). Even if net coverage is flat, the fix is worth landing: it removes the parser-bug confound so Fase B measures the base model's real decision quality.
- **Candidate snapping-tolerance value for J1: none** (lever discarded). If a future run revisits it, the data says any τ ≤ 200 px is worthless and τ > 200 px would mis-snap; the real edge-tap lever is the 5%/94% band (LlmRouter.java:572), a policy question, not tolerance.

_Generated by `calibracao/decompose_nomatch.py`. GATE: PASS._
