# Proposal: Compact Static Analysis JSON Before Device Push

GitHub Issue: #80

## Why

The MOP-guided `aperv` arms push the static analysis JSON to the device byte-for-byte. The Java side applies a pre-read footprint guard (`MopData.java:202`) that rejects any file larger than `maxMemory() / PARSE_FOOTPRINT_FACTOR` — roughly a 32 MB ceiling at the ~192 MB heap the emulator provides. In the `cmpma` campaign (181 APKs x 5 arms x 3 repetitions), `org.quantumbadger.redreader_117` ships a 50.6 MB JSON, is rejected, and **both MOP arms refuse to explore (0 steps)** while `ape`, `ape_pure`, and `sata` run normally and reach ~14pp coverage. This is a per-app fairness gap: on one app the MOP treatment zeroes coverage that the baselines obtain.

The guard is not the defect. Aborting rather than running without MOP data and mislabelling the arm is a deliberate and correct decision. The defect is that the JSON arrives large: 70.7% of the 24,300 WTG `transitions` edges are exact duplicates, and pretty-printing costs a further ~13 MB. Removing both losslessly yields 21.0 MB — under the ceiling — without dropping any field the tool consumes.

## What Changes

- `ApeRVTool` compacts the static analysis JSON into a temporary file before pushing it to the device. Compaction is two lossless operations: deduplicating exact-duplicate entries in `transitions` (preserving first-occurrence order) and serializing without pretty-print whitespace.
- The compacted temporary file is what reaches `/data/local/tmp/static_analysis.json`. The source file at `<results_dir>/<apk_name>.json` is never modified.
- Compaction runs unconditionally for every MOP-arm push, not only for oversized files.
- Any compaction failure falls back to pushing the original file, preserving today's behavior as a floor.
- No field projection: no section of the JSON is dropped or rewritten beyond the two operations above.

Not breaking: no interface, variant dict, or `ape.properties` key changes. The observable change is confined to the byte content of the device-side file.

## Capabilities

### New Capabilities

None. This change modifies the behavior of an existing capability.

### Modified Capabilities

- `aperv`: the delta ADDs one requirement ("Static Analysis JSON Compaction") and six invariants (INV-APV-20..25); MODIFIEs the "ApeRVTool Execution Flow" requirement so its step 4 covers compaction; and supersedes two pieces of existing text whose wording becomes false — INV-APV-06 ("SHALL locate and push the static analysis JSON", now a compacted copy) and the `static_analysis.json` Side-Effect line. Both supersessions are marked in the delta and must REPLACE, not append to, the main spec.

## Impact

**Modules**

- `aperv-tool` (written): `src/aperv_tool/tools/aperv/tool.py` gains the compaction step in `execute_tool_specific_logic()` Step 1c; `tests/test_aperv_tool.py` gains unit coverage; `CLAUDE.md` gains the compaction step in its Configuration Flow and the telemetry caveat in Gotchas.
- `rv-platform` (read-only, unaffected): `StaticAnalysisComponent.load_static_data()` parses the same `<results_dir>/<apk_name>.json` to build the per-method coverage denominator. That denominator is **not** sensitive to this transform — it derives from `reachability`, and parsing `org.quantumbadger.redreader_117.apk.json` before and after compaction yields an identical 1,796 classes / 9,333 methods. The source file is preserved for provenance (offline consolidation and resume re-parse it) and to keep the change confined to the device-push path, not to protect a computation that compaction would have broken.

**Requirements**

- FR19 (External Tool Support): the device-push path of the `aperv` plugin.
- FR04 (GATOR / Window Transition Graph): `transitions` is the WTG edge list this analysis produces.
- NFR04 (Resilience): compaction failure degrades to the current push rather than failing the task.
- NFR08 (Reproducibility): see the caveat below.

**Cross-repo dependency (read-only)**

The safety of deduplication rests on the six Java consumers of `getWtgTransitions` / `wtgTransitions` in the sibling `ape` repository: `MopScorer.scoreWtg` (`MopScorer.java:115`), `FrontierPass` (`FrontierPass.java:55`), `StatefulAgent.frontierBoost` (`StatefulAgent.java:1066`), `MopFrontierPass` (`MopFrontierPass.java:56,97,109`), `rekeyDialogsToHost` (`MopData.java:884`), and `hasWtgData()` (`MopData.java:1000`). None treats edge multiplicity as a signal — each is set-membership or first-match-fixed-weight — so all are idempotent to duplicates. This repository is not modified, but a future change to any of those consumers would invalidate the guarantee.

**Reproducibility caveat**

The `[APE-MOP-DATA] transitions=N` telemetry (`MopData.java:319`) will report the deduplicated count (7,124 instead of 24,300 for `redreader`). This is arguably more correct, but it breaks direct comparison of that field between campaigns run before and after this change.

**Scope**

Across the 181 APKs of the `cmpma` campaign, `redreader` is the only JSON above the ceiling; the next largest, `sdmse` at 23.7 MB and `email` at 20.8 MB, both carry `transitions=0` and already pass. This is verified over those 181, not over the full 219-APK dataset: the remaining 38 have no current-build JSON on this machine, so the scope claim does not extend to them.

The claim is also a property of the current static-analysis build, not of the dataset. `org.prauga.messages_8` measures 44.9 MB under the older `cmpmop` build — above the ceiling — and 18.9 MB under the `cmpma` build. A producer change can move any APK across the ceiling, which is an argument for compacting unconditionally rather than for treating `redreader` as a special case.

The change unblocks one app under the current build and closes the fairness gap. Every other JSON still shrinks, which lowers device-side heap pressure — relevant to the 8 OOM events observed across 8 concurrent emulators.

**Upstream root cause (out of scope)**

The producer (`jca_dexlib2`) emits the duplicate edges and the pretty-printing. Fixing it there would require re-running static analysis across all 219 APKs; this change is the decoupled fix at the consumer.

**Non-goal**

This change alters which file reaches the device on one app. It does not change how any arm scores, and it does not adjudicate any of the `cmpma` mechanism conclusions — that debate belongs to `docs/20260716_analise_critica_cmpma.md`, not here.

It is forward-looking only, and one consequence should be recorded rather than glossed. `redreader` **is** present in `cmpma`'s paired set (n=181) with both MOP arms at zero coverage, so that campaign's MOP-arm estimates already carry the fairness gap this change closes. Fixing the push path does not retroactively clean those numbers; it only prevents a recurrence. Whether the published `cmpma` figures warrant a threats-to-validity note, or a re-run of the affected arms on that one app, is a decision for the campaign report and is out of scope here.
