# Proposal: gh90-e3-decisive-run-setup

GitHub Issue: #90

## Why

The E3 thesis study must prove the chain *decision → action → MOP screen → violation*, and today that chain is broken at both ends. At the measurement end, only 2.06% [2.00; 2.13] of steps are causally attributable to MOP guidance — the sister change in the `ape` repository (`telemetry-proof-llm-efficacy`) fixes that by making the jar emit the missing per-step fields. At the **experimental-design** end, which is this change, the problem is different and cannot be fixed by any amount of telemetry: **the experiment has never had a control arm**. Every APE-RV run ever executed had MOP guidance switched on. Without a MOP-off arm there is no contrast, and therefore no claim about the effect of MOP guidance is attributable — however good the telemetry gets.

Three further defects bias the reading of whatever the decisive run produces. First, the direct/transitive axis of the scoring pipeline is noise: `[DM]` is 0 across all 181 apps of the corpus because `directlyReachesTarget` means 0-hop (only methods whose own body invokes JCA) while UI handlers delegate, so `mop_weight_direct=500` is unreachable by construction of the data and calibrating it measures nothing. Second, the LLM backend actually serving each run is not recorded anywhere, so a run's results cannot be tied to the model and sampling parameters that produced them. Third, `mop_activity_source_components` sits at its `false` default in the substrates that inherit it, suppressing the MOP-activity signal (measured effect: 20.0% → 85.0% of activities flagged on the subset40, 17.7% → 86.2% offline across the 181 apps).

All design decisions below were fixed by the project author on 2026-07-29 and are recorded in `docs/20260729_propostas_melhorias_e3.md` §0, which is the source of record for this change. They feed a decisive run (3 arms × 40 APKs × 1800 s × 1 rep = 120 runs, ≈ 8 h on 8 containers) that decides whether the LLM stays in the design at all.

## What Changes

- **A1 — the decisive run's arm set, enumerated.** The MOP-off arm is defined as `mop_data` **present** + `mop_weight_*=0` + `mop_frontier_weight=0` + `activity_trigger_enabled=false`. This specific shape is forced by two verified jar behaviours: leaving `ape.mopDataPath` set while the load fails **aborts the run** (`StatefulAgent.java:216-223`, INV-MOP-22), and removing `mop_data` altogether would also disable the generic WTG and frontier passes (`WtgPass:29` and `FrontierPass:35` both require `mopData != null`), turning the intended "MOP guidance off" contrast into "most of the navigation substrate off". The standing rule *sempre modo frontier* holds: `sata_mop_act_frontier` remains the substrate of every aperv arm.
  **This change also closes a gap in the record**: the decisive run's three arms are enumerated here for the first time, and named — (1) `mop_on_llm_off`, the shared reference; (2) `mop_off_llm_off`, isolating the MOP contrast; (3) `mop_on_llm_70`, isolating the LLM contrast. The ledger fixed the MOP-off arm's internal design but never wrote down the arm set, and the names matter beyond bookkeeping: the variant string is the resume identity key (`platform.py:308-318`) and the consolidation column key (`{arm}__{metric}`), so it must be decided before any manifest is generated. The names encode both factors, which is what makes each contrast readable straight off the results CSV.
  **The LLM dose of arm 3 is `llm_percentage=0.7`** — the dose is what fixes what "LLM on" means in the result, and its rationale is `design.md` D8.
- **A9 — offline clock ↔ logcat join**, as a utility of the `aperv_tool` package. Correlates the trace clock with `RVSEC:` violation lines to test the premise "reaching a MOP screen is enough to fire the monitor" — the premise on which the whole MOP-frontier mechanism rests. It also supplies the evidence for the deferred N5 decision (runtime logcat).
- **N6 — a direct/transitive axis that means something**, computed offline inside `_compact_static_analysis_json` (`modules/aperv-tool/src/aperv_tool/tools/aperv/tool.py:801-875`). The compaction step already loads the analysis JSON and rewrites it in memory before pushing to the device; it will additionally populate `listeners[].handlerReachesTarget` / `handlerDirectlyReachesTarget` from the document's own `reachability` section. Redefined semantics: **direct = the handler of *this* widget reaches JCA at any depth**; transitive = containment. Source `.apk.json` files are never modified, the static analysis is never re-run, and `rvsec-gator` is not touched. The consumer already parses both fields with precedence over its local join (`MopData.java:516-517,531-533`).
- **N4 — per-run backend provenance.** At the start of each run the tool queries `/v1/models` (it already holds `llm_url`) and records backend, model, and sampling parameters in the task output. Applies to any experiment, calibration and real alike.
- **B2 — `mop_activity_source_components` forced ON** in the arms that inherit the `false` default (`Config.java:159`).
- **B3 — `llm_snap_tolerance_px=150`**, property-only and **gated**: applied only when the jar in use contains the B1 dead-pair ban from the sister change. Without B1, a wider snap radius amplifies repeated dead taps instead of rescuing near-misses.
- **N2 — measurement rule, not code.** Any future grounding measurement reports both centre distance and containment. Recorded in `design.md`; no script is created (the offline harness that would host one is frozen).
- **Pre-registered stratification.** UI toolkit (Compose / View) becomes a declared analysis axis of the decisive run, because in ~30% of Compose apps every activity is MOP-flagged, making `activity_has_mop` constant and leaving the MOP-guided arm with no contrast to exhibit there (`docs/20260730_compose_gator_substrato_estatico.md` §5.2).

Subset stays at the current 40 APKs — `bitbanana` does not enter (author's decision).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `aperv`: arm definitions and their configuration keys (A1, B2, B3); offline enrichment of the pushed static-analysis document (N6); per-run backend provenance in the task output (N4); the clock↔logcat join utility and its validation gate (A9).

No other capability's requirements change. `analysis` is untouched: N6 consumes the `reachability` section that FR06 already specifies and rewrites only the in-memory copy the tool pushes, never the artifact the analysis produces.

## Impact

- **Modules**: `aperv-tool` (all code changes live here — variants, `_compact_static_analysis_json`, the new join utility, the preflight provenance query). `rv-experiment` and `rv-platform` are read-only consumers: they gain no new interface, and the arm set reaches them through the existing variant mechanism.
- **Requirements**: FR20 (per-tool variant system — the arms), FR06 (REACH analysis output consumed by N6), FR11 and FR13 (logcat capture and violation detection — the substrate A9 joins against), FR19 (external tool support), NFR03 (testability — the offline pytest layer), NFR06 (observability — N4 provenance).
- **Cross-repository dependency**: B3 is gated on the `ape` jar containing B1; the arm-3 contrast is only interpretable once the jar emits `pick_channel` and `activity_has_mop` (sister change items A4/A5). This change can be implemented and unit-tested independently of the jar, but the decisive run requires both halves. The new jar reaches the container by the same bind-mount the campaign scaffold already uses for `tool.py`, over the image's baked copy.
- **Data**: no schema migration. `.apk.json` corpora are read-only; iter0 recorded traces are read-only test fixtures.
- **Deadline**: implemented and tested by 2026-07-31 09:00 (hard max 2026-08-01 09:00), feeding the decisive run.
