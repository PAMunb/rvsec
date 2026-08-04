# Proposal: Host-side MOP artifact derivation

GitHub Issue: #96

## Why

The `ape-rv.jar` parses the **full** static-analysis JSON on the device: a whole-file DOM parse of
`reachability[]` + `windows[]` + `transitions[]` + `components{}`, of which the explorer reads
nothing directly. Those sections are parse-time inputs to a small set of derived projections (widget
MOP flags, MOP-activity sets, the WTG click view, OPTIONSMENU gateways, the component trigger
surface). Call-graph data is the bulk of the bytes, and on call-graph-heavy apps the parse is
rejected before it starts by a footprint guard — the MOP arm then aborts with 0 steps while the
`sata` baseline explores normally. That is a per-app fairness gap that biases every MOP-vs-baseline
comparison, not a crash, and it is invisible in the aggregate.

A second silent path lives on this side: when the static-analysis JSON is absent for a MOP arm,
`tool.py` warns and continues, so the run executes as pure SATA while still being labelled a MOP arm
(V21).

This change is the rv-android counterpart of stage 7 of the APE-RV re-architecture (`ape`, change
`rearch-07-compact-static-artifact`). It moves the parse-time semantics host-side into a pure Python
generator that emits a compact, explorer-shaped artifact; the jar consumes only that, and its
full-JSON parser, its footprint guard and its `too-large` reject class are deleted on the `ape` side.

## What Changes

- **New**: `aperv_tool/tools/aperv/derive_mop_artifact.py` — `derive(document) -> dict` and
  `serialize_canonical(artifact) -> bytes`. This is where the parse-time semantics of `MopData.load`
  relocate: the listener × reachability cross-reference, D8 synthetic-lambda recovery, widget-collision
  ranking, the empty-short-id drop, DIALOG re-keying, base-activity WTG keying with deduplication, the
  A′ activity-set union, the OPTIONSMENU flagged-widget test, and the per-activity deep-link URI.
  Derivation is deterministic at the byte level and records the SHA-256 of the full JSON it derived from.
- **BREAKING (wire format)**: the device receives `/data/local/tmp/mop-artifact.json`
  (`formatVersion: 1`) instead of `/data/local/tmp/static_analysis.json`, and `ape.mopDataPath`
  follows. The full JSON is never pushed again. Landing is a single coordinated cut with the `ape`
  side — the Docker image rebuilds the jar from source, so one image rebuild deploys both halves.
- **BREAKING (widget-flag semantics)**: `_compact_static_analysis_json` and its listener enrichment
  are deleted, retiring `INV-APV-32`. Today that enrichment writes
  `handlerReachesTarget = handlerDirectlyReachesTarget = reachesTarget(handler)` onto every listener,
  which makes the jar take its producer-precedence branch unconditionally — so `directMop` currently
  means "reaches at any depth" rather than "calls a target in its own body", and the D8 synthetic-lambda
  recovery is dead code in production. The generator restores the two axes as the producer defines
  them (`direct` = 0-hop, `transitive` = any depth, with `direct` implying `transitive`) and applies
  the D8 recovery to both. Measured over the pinned corpus (345 apps): every currently flagged widget
  moves from the `mopWeightDirect` tier to `mopWeightTransitive` uniformly — the ranking *among* MOP
  widgets is unchanged, the weight of the MOP signal against other signals is not — and the recovered
  handlers add 1,232 flagged widgets across 8 apps. This is a behavior change, recorded as one.
- **Modified**: `tool.py` gains `_derive_mop_artifact(task)` with a digest-checked cache at
  `<results_dir>/<apk_name>.mop.json`, written atomically and regenerated when the source digest no
  longer matches. The warn-and-continue on a missing static-analysis JSON becomes a raised
  `RVToolExecutionError` (V21 dies): a MOP arm that cannot arm is a failed task, symmetrical with the
  jar-side abort.
- **Unchanged and asserted**: the full static-analysis JSON stays byte-identical where it is. The
  frozen metric definitions keep reading it, and no metric or analysis pipeline may read a
  `*.mop.json`.
- **Verification**: a one-shot corpus equivalence gate over the pinned
  `rvsec-dataset/static_analysis/` (345 `.apk.json`), run jointly with the `ape` side, comparing the
  old parser on the full JSON against the new parser on the derived artifact. The gate is deleted
  once green, so the permanent protection is this module's pytest suite, which carries a named test
  per relocated rule on synthetic fragments where the corpus is thin.

## Capabilities

### New Capabilities

None. The derivation is a new component inside an existing capability (`aperv`), not a new
capability surface.

### Modified Capabilities

- `aperv`: the execution flow's static-analysis step, `ape.properties` generation, and the removal of
  the JSON-compaction requirement (`Static Analysis JSON Compaction`, FR19/FR04/NFR04) in favour of an
  added derivation-and-caching requirement. Adds the artifact's derivation semantics as normative
  rules, since this repository is now their single authority.
- `analysis`: adds the derived compact artifact as a downstream, device-only consumer of the
  static-analysis chain, and states normatively that the full JSON remains the sole input of every
  metric and analysis pipeline (the producer and its schema are untouched).

## Impact

**Modules**: `aperv-tool` only. No change to `rv-static-analysis`, `rv-platform`, `rv-experiment`,
`rv-coverage`, or any other workspace module — the producer, the pre-processing pipeline and the
result-processing path are untouched.

**Cross-repository**: coordinated with `ape` change `rearch-07-compact-static-artifact`. The wire
format is defined jointly; this repository owns the generator and the derivation semantics, the `ape`
repository owns the reader. Two amendments to that change follow from this proposal and must land with
it: the retirement of the listener enrichment must be recorded as a behaviour change rather than as a
shim "the derivation subsumes", and `INV-DRV-01` must state that `direct` implies `transitive` (which
also invalidates a jar-side scenario asserting the two wire bits imply nothing about each other). The
gate's oracle is the old parser on the **raw** full JSON, which is what the pinned corpus already
holds; its path and count need no amendment.

**Requirements**: FR04 (method reachability), FR05 (WTG), FR06 (GUI elements) — consumed, not
changed; FR18/FR19/FR20 (tool execution, configuration, variants); NFR02 (completion sentinel becomes
a host-side generation precondition); NFR04 (artifact size); NFR06 (observability — the generator's
`stats` block replaces counters the jar used to compute).

**Data**: one additional cached file per app (`<apk_name>.mop.json`, kilobytes) next to the full JSON
in `results_dir`. Archived experiment artifacts from earlier campaigns are unaffected; the
`[APE-MOP-DATA] transitions=N` field, already non-comparable across the compaction change, is
superseded by `wtgEdges` on the `ape` side (NFR08 caveat carried forward).
