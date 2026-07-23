# J1 — Handoff to the `ape` repo (Fase B lever, gate G2)

**This is a PROPOSAL produced by the rvsec-side calibration loop (P4). It is implemented in a
separate `ape`-repo session, behind gate G2. Nothing here is edited from the rvsec side.**

- Source of evidence: `calibracao/nomatch_decomposition.md` + `calibracao/nomatch_calls.csv`
  (cmp_llm_20260721 base run, 543 traces, grammar d90c1f4).
- Model is fixed = base `Qwen/Qwen3-VL-4B-Instruct` (plano P6). J1 does NOT change the model.
- Consumed by: Fase B (`calb`) via `:ro` bind-mount of the locally-built `ape-rv.jar` into the
  per-iteration `iterN/artifacts/` snapshot (precedent: `docker-compose.cmpft*_smoke.yml`).

---

## 0. The one-line diagnosis (revised from "prompt hardening" to a concrete parser bug)

The APE hybrid tool-calling has two response paths (CLAUDE.md: native `bind_tools()` first, XML
`<tool_call>` fallback). Empirically, over the 543-trace base run:

| response path | matched | llm_tap | no_match/boundary | no_match/degenerate | total |
|---|---|---|---|---|---|
| **native** (`content= tool_calls=1`) | 4,355 | 741 | 364 | **7,506** | 12,966 |
| **XML** (`content=<tool_call>`) | 33,584 | 6,320 | 1,615 | **3** | 41,522 |

- The XML path applies coordinate **repair** (missing_y / array_xy / quoted_xy / int_scan) and
  almost never fails: 3 degenerate in 41,522 (0.007%).
- The native path has **no repair** and collapses to `(0,0)` **57.9%** of the time
  (7,506 / 12,966), producing **99.96% of all `degenerate` no_match** (7,506 / 7,509).
- `repair=` tags appear on 41,527 of 54,497 calls (76.2%) — but essentially **only on the XML
  path** (native `matched` are all clean, native failures get no repair at all).

**Root cause: the native `tool_calls` argument extractor does not feed the same
coordinate-extraction/repair pipeline the XML text path uses.** When SGLang returns a native tool
call whose arguments are malformed for Qwen3-VL's dialect (most often only `x` present → the
`missing_y` case), the native path yields no coordinate → `(0,0)` → `degenerate` → the turn falls
back to the algorithm. This is a **parser gap in the ape**, not a model deficiency, and it masks
the base model's true decision on ~24% of responses.

---

## 1. J1a — PRIMARY: unify the native path with the XML repair pipeline

**Goal.** Route native `tool_calls[].arguments` through the exact same coordinate
extraction + repair logic (`missing_y`, `array_xy`, `quoted_xy`, `int_scan`) the XML
`<tool_call>` path already runs, OR force all responses through the XML path (disable native
`bind_tools()` for this model). Either eliminates the ~7,506 native-path `degenerate` collapses.

- Two acceptable implementations (choose the lower-risk one in the `ape` worktree):
  - **(a) unify:** normalise native tool-call arguments into the same intermediate the XML parser
    emits, then run the shared repair heuristics. Preserves native tool-calling.
  - **(b) force-XML:** stop offering / consuming native tool calls for Qwen3-VL so every response
    is parsed by the robust XML+repair path. Simpler; the XML path already handles 41,522 calls at
    0.007% degenerate.
- Likely code area: the response handler / hybrid tool-call parser
  (`rv_agent/llm/tools/tool_call_parser.py` is the rvsec-side analogue described in CLAUDE.md; the
  ape has its own Java equivalent inside `LlmRouter` / the tool-call handling). **Verify the actual
  native-vs-XML branch in the current `ape` HEAD before editing** — the line numbers below come
  from the plano §3-H4 investigation snapshot and must be re-confirmed.

**Acceptance (offline, post-rebuild):** re-parse the new run's traces with
`calibracao/decompose_nomatch.py` and confirm `degenerate` drops to ~0 and the native path now
carries `repair=` tags / `matched` outcomes like the XML path. No emulator needed for the parser
check; the coverage effect is the Fase B run itself (§4).

---

## 2. J1b / J1c — expose-as-property, do NOT change the value

Per P4 (`nomatch_decomposition.md` §3, §7), the snapping-tolerance lever is **DISCARDED**: the
snappable population is 0.80% of no_match even at τ=200 px, and 91% of `boundary` are 5%/94%
edge-band rejections the tolerance test never reaches. So:

| target (plano §3-H4, verify in ape HEAD) | action in J1 | value in B1 |
|---|---|---|
| euclidean snap tolerance `max(50, min(w,h)/2)` — `LlmRouter.java:653` | expose as property `ape.llmSnapTolerancePx` | **keep default** (not swept) |
| boundary bands `5% / 94%` — `LlmRouter.java:572` | expose as property | **keep default** (policy lever, optional later probe) |
| `max_tokens=1024` — `LlmRouter.java:105` | expose as property | **keep default** — NOT causal: `tokens_out` ≈ 24–26 ≪ 1024, no truncation |

Exposure is for configurability/reproducibility only; **B1 changes only J1a**, so the Fase-B
contrast isolates the native-parser fix.

---

## 3. Hard constraints (must hold or the calibration pipeline breaks)

1. **Do NOT change the `[APE-LLM-TEL]` telemetry grammar (d90c1f4).** The consolidation parsers
   (`calibracao/decompose_nomatch.py`, `experimento-20260721/scripts/analyze_cmpv2_llm.py`) depend
   on the exact field set. New fields must be **additive** only.
2. **Preserve `llm_tap` and the algorithmic fallback turn.** J1 must not turn the router into a
   pure clicker (the v2 action-collapse failure). `llm_tap` stays enabled and off-tree.
3. Keep the emitters at the documented sites (plano: `LlmRouter.java:125-137, 377-380, 488-512,
   708-723`) firing on the same events.

---

## 4. Success criterion — NET coverage, never `degenerate`↓ alone (anti-starvation, plano §2.4b)

This is the trap. Each `degenerate` currently returns a **high-yield algorithmic turn** (~26%
new-state vs ~9% for an LLM tap). Fixing the native parser converts ~7,506 algorithmic fallback
turns into LLM taps — which the P4 estimate says could **lose** ~1,200 net new states if fidelity
does not pay for itself (this is exactly the v2 paradox, this time caused by the parser bug rather
than the model). Therefore:

- **B1 is promoted only if `cov_mop` is net-neutral-or-better** vs the winner-A arm **re-run with
  the new jar mounted** (the jar↔jar bridge). Not on no_match↓.
- Report per-arm, from the Fase-B traces: no_match rate + degenerate/boundary split, `repair` rate,
  and the `mode` (algorithmic vs LLM turn) distribution — the §9 starvation dashboard.
- Value of J1 even if `cov_mop` is flat: it **removes a parser-bug confound**, so Fase B measures
  the base model's real decision quality instead of a masked 58%-native-loss artifact.

---

## 5. What the rvsec side needs back to unblock Fase B

1. The rebuilt `ape-rv.jar` (from the `ape` worktree with J1a).
2. Its **sha256**, to record in the iteration manifest.
3. A **bytecode diff audit** vs the current jar confirming the change is confined to the native
   tool-call path (+ property plumbing) and the TEL grammar is untouched — the cmp_llm audit
   standard.

Until those arrive, the rvsec-side loop is **blocked at the Fase-A→B boundary** (gate G2). Fase A
itself does not need J1 and can proceed independently (it runs the current jar).
