<!-- This change touches ~8 files inside a single module (aperv-tool), so it is implemented
     sequentially rather than by subagent dispatch. The dependency order is:
     Group 1 (generator skeleton + reachability index) → Group 2 (widget rules) →
     Group 3 (dialogs/WTG/activity sets/components) → Group 4 (serialization) →
     Group 5 (tool.py wiring) → Group 6 (audit + docs) → Group 7 (corpus gate, joint with `ape`) →
     Group 8 (verification). Groups 2 and 3 both extend the same module and must not run in parallel. -->

## 1. Generator foundation

- [x] 1.1 Create `modules/aperv-tool/src/aperv_tool/tools/aperv/derive_mop_artifact.py` with `DerivationError`, the module docstring stating that this file is the single authority for the relocated parse-time semantics, and the `derive(document) -> dict` entry point performing only the preconditions (`complete is True`, non-null `package`) and the artifact skeleton (`formatVersion`, `package`, `mainActivity`, `source`, empty sections, `stats`)
- [x] 1.2 Add module constants: `FORMAT_VERSION = 1`, `GENERATOR_ID = "aperv-derive/1"`, `DEVICE_ARTIFACT_PATH = "/data/local/tmp/mop-artifact.json"`, `ARTIFACT_SUFFIX = ".mop.json"`, `SYNTHETIC_LAMBDA_PATTERN`, and the metadata field tuple — no magic values in the rules below
- [x] 1.3 Implement `_normalize_event_type(value)` (lowercase, strip `_` and `-`, `None` passes through) and `_base_activity(window_name)` (truncate at the first `#`), mirroring the jar's helpers exactly
- [x] 1.4 Implement `_index_reachability(document)` returning `(by_signature, lambda_by_class, activity_classes)`: index every method carrying `reachesTarget or directlyReachesTarget` as the pair `(direct, transitive or direct)`, **merging duplicate signatures by OR** (design D4); index enclosing classes of reaching `lambda$…` methods; collect classes with `componentType == "activity"` carrying at least one reaching method (A′ source 3)
- [x] 1.5 Add unit tests for `_normalize_event_type`, `_base_activity`, and `_index_reachability` including the duplicate-signature OR merge and the `directlyReachesTarget && !reachesTarget` shape
- [x] 1.6 Add tests for the `derive()` preconditions: `complete` absent, `complete: false`, missing `package`, non-dict `components` — each raising `DerivationError` and producing no artifact
- [x] 1.7 Run `/rv-test-run aperv-tool`

## 2. Widget flags and widget map (INV-DRV-01, INV-DRV-02)

- [x] 2.1 Implement `_derive_listener_flags(listener, by_signature, lambda_by_class, stats)`: producer precedence when either handler-reach field is non-null; otherwise exact signature lookup; otherwise D8 synthetic-lambda recovery from the enclosing class; `transitive = reaches or direct` on **every** path so `direct` implies `transitive`; update `handlersUnmatched`/`syntheticLambda`/`recovered`
- [x] 2.2 Implement `_derive_widget_flags(widget, …)`: per-normalized-eventType OR-aggregation into a `mop` map with values `none|direct|transitive|both`, plus the widget aggregates; apply design D5 for a null `eventType` (folds into the aggregate, emits the `""` key only when it is the widget's sole flagged source)
- [x] 2.3 Implement `_build_widget_map(windows, …)` returning the widget map keyed `baseActivity → shortId`, the flagged-activity set, the `optionsMenus` records and the counters: mark the base activity from a flagged widget **before** evaluating the empty-short-id drop (INV-DRV-02); apply the `mopRank` collision policy with ties keeping the first occurrence; count `droppedFlaggedNoId`; compute `hasFlaggedWidget` over the window's parsed widgets, not the emitted map
- [x] 2.4 Implement the emission filter: a widget reaches the wire only when flagged or carrying at least one metadata field; `stats.widgetsTotal`/`stats.flagged` count the map before the filter
- [x] 2.5 Add named unit tests: `test_producer_precedence_wins`, `test_direct_implies_transitive`, `test_synthetic_lambda_recovered`, `test_synthetic_lambda_not_recovered_without_lambda`, `test_per_event_flags_independent`, `test_null_event_type_folds_into_aggregate`
- [x] 2.6 Add named unit tests: `test_flagged_empty_id_marks_activity` (the AC3 rule), `test_collision_keeps_strongest_flag`, `test_collision_tie_keeps_first`, `test_unflagged_metadataless_widget_projected_away`, `test_stats_count_map_not_wire`, `test_options_menu_record_uses_parsed_widgets`
- [x] 2.7 Run `/rv-test-run aperv-tool`

## 3. Dialogs, WTG, activity sets, components (INV-DRV-03, INV-DRV-07)

- [x] 3.1 Implement `_rekey_dialogs(windows, transitions, windows_by_id, widget_map, flagged_activities, stats)` with the five coupled sub-rules: first incoming transition with a named source wins; `mopRank` collision policy on merge; move the dialog key rather than copying; a flagged merge promotes the host; the dialog class keeps its own activity-set entry. Count `orphanDialogs`
- [x] 3.2 Implement `_build_wtg(transitions, windows_by_id, stats)`: click events only, keyed by base source activity, base target activities, `widget` defaulting to the empty string, exact `(widget, target)` duplicates removed and counted in `dedupedTransitions`, first-occurrence order preserved
- [x] 3.3 Implement `_augment_activities(flagged, components_activities, activity_classes)` producing the A′ union from the three sources, base-activity normalized, emitted sorted; assert by construction that it is a superset of the widget-derived set
- [x] 3.4 Implement `_derive_deep_link_uri(intent_filters)`: first filter declaring `android.intent.action.VIEW` with a non-empty scheme list yields `scheme + "://" + host + path`, host and path defaulting to the empty string; `None` otherwise
- [x] 3.5 Implement `_project_components(components)` emitting `activities`/`receivers`/`services`/`providers` with `reachesMop` (renamed from `reachesTarget`), `hasTargetMethods` as a boolean, `intentFilters` reduced to `actions` + `categories` on receivers and services, `authorities` on providers, `deepLinkUri` on activities — and no `data` block, `readPermission`, `writePermission` or signature list anywhere
- [x] 3.6 Add named unit tests: `test_dialog_merge_promotes_host`, `test_dialog_first_incoming_edge_wins`, `test_orphan_dialog_keeps_key`, `test_dialog_class_retained_in_activity_set`, `test_dialog_merge_uses_mop_rank`, `test_wtg_click_only_deduped_base_keyed`
- [x] 3.7 Add named unit tests: `test_augmented_union_three_sources`, `test_augmented_superset_of_widget_derived`, `test_deep_link_from_first_action_view`, `test_deep_link_absent_without_scheme`, `test_deep_link_absent_without_action_view`, `test_deep_link_absent_without_filters`, `test_deep_link_empty_host_and_path`
- [x] 3.8 Run `/rv-test-run aperv-tool`

## 4. Canonical serialization and the cryptoapp ground truth

- [x] 4.1 Implement `serialize_canonical(artifact) -> bytes` per design D8 (sorted keys, `,`/`:` separators, `ensure_ascii=False`, UTF-8)
- [x] 4.2 Copy `cryptoapp.apk.gh60-fresh.json` into `modules/aperv-tool/tests/fixtures/` as the ground-truth fixture and record its provenance in a fixture README line
- [x] 4.3 Add `test_derive_cryptoapp_ground_truth` asserting the spec's scenario values: `mopActivities == {MessageDigestActivity, CipherActivity, CryptographyActivity}` (the third enters through the D8 recovery, which the jar's own raw-fixture test confirms), the `MainActivity` `optionsMenus` record, the WTG edges to both MOP sub-activities, 4 activities, 1 provider with `authorities == "br.unb.cic.cryptoapp.androidx-startup"`, every component `reachesMop == false`, `stats.windows == 5`, `stats.flagged == 3`, `stats.recovered == 1`
- [x] 4.4 Add `test_no_target_keys_on_wire` (recursive walk asserting no key matching `*Target*` and no `reachability`/`windows`/`transitions`/`listeners` section), `test_serialize_canonical_is_byte_stable`, `test_key_order_independent_of_input_order`, `test_stats_do_not_affect_sets`
- [x] 4.5 Run `/rv-doc-code modules/aperv-tool/src/aperv_tool/tools/aperv/derive_mop_artifact.py`
- [x] 4.6 Run `/rv-test-run aperv-tool`

## 5. tool.py wiring (INV-APV-45, INV-APV-46, INV-APV-47)

- [x] 5.1 Back up `tool.py` to `backup/gh96-compaction/` before deleting anything (P3), then delete `_compact_static_analysis_json`, `_index_reaches_target` and `_enrich_listener_reach` entirely, together with the `tempfile`/`json` imports they alone justified
- [x] 5.2 Implement `_derive_mop_artifact(task)`: SHA-256 of the full JSON, cache hit when the cached `source.digest` matches, otherwise `derive` + `serialize_canonical` + atomic write (temp file in the same directory, `os.replace`); wrap `DerivationError`/`OSError`/`json.JSONDecodeError` in `RVToolExecutionError`; leave no partial file on any error path
- [x] 5.3 Rewrite execute step 1c: raise `RVToolExecutionError` naming the expected path when a MOP arm has no full JSON (delete the warn-and-continue), derive, push to `/data/local/tmp/mop-artifact.json`, set `mop_json_pushed`; no fallback-to-source push remains
- [x] 5.4 Update `_push_properties` to write `ape.mopDataPath=/data/local/tmp/mop-artifact.json`
- [x] 5.5 Update the existing tests that assert the old device path, the compaction behaviour, or the warn-and-continue path — rewriting them against the new contract rather than deleting them where the assertion still has a subject
- [x] 5.6 Add integration tests: `test_cache_hit_skips_derivation`, `test_stale_cache_regenerates`, `test_failed_derivation_leaves_no_file`, `test_mop_arm_without_json_raises`, `test_mop_arm_derivation_error_raises`, `test_full_json_never_pushed`, `test_properties_carry_new_mop_data_path`, `test_non_mop_arm_untouched`
- [x] 5.7 Run `/rv-test-run aperv-tool`

## 6. Audit, documentation and cross-repo coordination

- [x] 6.1 Add `test_no_module_outside_aperv_tool_reads_mop_json`: repository-wide search for the `.mop.json` suffix, permitting only `aperv-tool` sources and the assertion text of the test itself (INV-ANA-53; phrase the assertion so the test does not fail on its own occurrence)
- [x] 6.2 Update `modules/aperv-tool/CLAUDE.md`: replace the compaction paragraph and the 32 MB / redreader gotchas with the derivation, the cache, the new device path and the fail-fast rule; state the retired `INV-APV-32` and its measured effect
- [x] 6.3 Update `docs/architecture/ape-rv.md` for the new host↔device contract, verifying any count it states before reusing it (the document has carried stale counts before)
- [x] 6.4 Amend `rearch-07` on the `ape` side, item 1 (design D11): its `specs/aperv-tool/spec.md:42` deletes `INV-APV-20..25/31/32` as a shim "the derivation subsumes", and `design.md:7` calls the compaction a *lossless* shrink — both false for the enrichment. Restate the `INV-APV-32` retirement as a behaviour change with its measured effect, so the cutover commit does not claim identity it does not have
- [x] 6.5 Amend `rearch-07`, item 2: `INV-DRV-01` (`specs/static-analysis-entrypoints/spec.md:27`) gains the direct⇒transitive clause, and the scenario at `specs/mop-guidance/spec.md:74` asserting "no implication between the bits" is revised — under the rule the wire value `direct` alone is unreachable, so the scenario as written can never be satisfied
- [x] 6.6 Record design D6 (one `optionsMenus` record per activity, merged by OR) as a wire-format note for the `ape` side before its parser is written: `specs/static-analysis-entrypoints/spec.md:45` specifies one record per window while `specs/mop-guidance/spec.md:44` reads "its record" in the singular. The pinned corpus has zero apps with two OPTIONSMENU windows on one activity, so this is hardening against a shape the gate cannot exercise, not a live divergence
- [x] 6.7 Confirm no further corpus amendment is needed: `rearch-07` tasks 1.4/4.1/4.3 and the SHALL scenario already name `rvsec-dataset/static_analysis/` with 345 apps (the AC4 correction landed on their side); verify before assuming it still holds at cutover
- [x] 6.6 Run `/rv-qa-lint-fix aperv-tool`

## 7. Corpus equivalence gate (one-shot, joint with `ape`)

- [x] 7.1 Write the batch derivation driver over `<workspace>/rvsec-dataset/static_analysis/` (345 apps) emitting one `.mop.json` per app plus a summary of per-rule exercise counts: flagged-and-dropped empty-id widgets, recovered D8 handlers, re-keyed dialogs, and A′ sets differing from the widget-derived set
- [x] 7.2 Fail the driver when any of the four exercise counts is zero, and record the substitution when a count comes back zero (the rule's coverage moves to a synthetic fixture)
- [x] 7.3 Re-verify the `ape` audit claiming no consumer reads WTG edge multiplicity, so the set-based comparison of design D7 is justified rather than assumed
  - Re-verified first-hand against `ape` `src/main` on 2026-08-05, and the audit holds: **no production
    consumer reads WTG edge multiplicity.** Every one of the five call sites is either first-match or
    set-accumulating — `MopScorer.scoreWtg:117` returns `weightWtg` on the first matching edge;
    `StatefulAgent.frontierBoost:1199` returns `weight` on the first; `FrontierPass:58` and
    `MopFrontierPass:62` fold targets into a `HashSet`; `qualifyingMopTargets:115` and
    `matchesQualifyingTarget:128` do the same and return on first match. `hasWtgData()` tests
    non-emptiness. A repeated `(widget, target)` pair therefore cannot change a score, a boost, a
    frontier set or a routing decision.
  - This stopped being hypothetical while generating the `ape` fixture: the jar's load record on the
    raw cryptoapp fixture reports `wtgEdges=17`, the derivation emits `16` with
    `dedupedTransitions=1`. The one edge is an exact duplicate. Under the audit above the difference
    is invisible to behaviour, so the group-7 gate MUST compare WTG views **as sets** — a list
    comparison fails on cryptoapp alone, before any corpus app is reached — and `wtgEdges` is a pure
    counter under INV-DRV-04 that steers nothing. Recorded here because the number visibly changes in
    the trace across the cutover: a post-cutover `MOP_DATA` record echoes the generator's count.
- [x] 7.4 **Green, and confirmed from this side rather than re-run here.** Verified read-only in `ape-rearch` on 2026-08-05: `rearch-07` tasks 4.1–4.4 are all `[x]`, and the result recorded in that change's `gate-report.md` (8,241 bytes) is **green on the first run, with no divergence and therefore no generator fix** — six test methods × six members, suite **1,207 tests / 0 failures / 19 skipped**. The six members are the real `cryptoapp` pair (`cryptoapp.apk.gh60-fresh.json` → `cryptoapp.apk.mop.json`; `flagged=3` including `executeButton` via `recovered=1`, 30 widgets, 16 WTG edges against 17 pre-dedup, 4 activities + 1 provider) plus the five synthetics `gate-activity-union`, `gate-deep-link`, `gate-dialog-rekey`, `gate-empty-id`, `gate-synthetic-lambda`. **The generator half this task owed is delivered and was checked as an absence, not assumed**: each `.mop.json` was produced by running `derive_mop_artifact.derive()` over the `.sa.json` beside it — a read-only host command, with no edit to the `ape` repository — and none of the five carries the retired enrichment or `exported` (grepped over the preserved copies; zero hits). A green gate that has never failed proves nothing, and that objection was answered there rather than here: **ten mutations** were applied to the derived artifacts, one per relocated rule plus the obvious scalars, and each was caught by the intended test — including the two a weaker gate would have missed, INV-DRV-01's *negative* case and INV-DRV-02's ordering. One defect surfaced in the authoring itself and is worth carrying: widget ids came from Python's `hash()`, salted per process, so re-derivation produced different documents under the same names; fixed to an MD5-derived id before anything was checked in, after which deriving twice gave byte-identical artifacts. The fixtures and `MopArtifactEquivalenceTest` are no longer in that tree — `rearch-07` group 5 deleted them as planned, with the copies under its `backup/rearch-07-group5/`, which is why `gate-report.md` is written for a reader arriving after the oracle is gone. Original text: Run the gate jointly with the `ape` side (old parser on the **raw** full JSON as oracle) and require it green on every member before either repository cuts over. **Rescoped 2026-08-05 (owner)**: the "345/345" condition is withdrawn — that JVM run does not happen, because the APE-RV side executes once, in `gh97`, which gates the merge and not the cutover. The gate is `ape` task 4.2/4.3's fixture-scoped test over the cryptoapp pair plus one synthetic per relocated rule, and what this task owes it is the generator half: every synthetic derived through `derive_mop_artifact.derive()`, never hand-written, and none carrying the retired enrichment. Confirm green from this side rather than re-implementing the comparison here
- [x] 7.5 **Recorded, and re-measured rather than copied.** `stat` over the pair on 2026-08-05: `src/test/resources/cryptoapp.apk.mop.json` is **4,126 bytes** against a **69,977-byte** `cryptoapp.apk.gh60-fresh.json`, i.e. the artifact is **5.896 %** of its source — the figure this task carries, confirmed against the files rather than inherited from the text. **This is one application, and it is recorded as one application.** The design's claim about the corpus is qualitative — "call-graph data is the bulk of the bytes" (`proposal.md:11`), the artifact sized in "kilobytes" (`:99`) — and it stays qualitative: there is no corpus number here to upgrade it with, because the batch run that would have produced one was withdrawn with 7.4, and a single app cannot stand in for 345. A second copy of the artifact exists at `test-apks/cryptoapp.apk.mop.json` at **4,115 bytes**, and the 11-byte gap was chased rather than waved through: the two documents are identical except for the provenance field `source.file`, which names `cryptoapp.apk.json` in one and `cryptoapp.apk.gh60-fresh.json` in the other — 11 characters of difference — and the two sources are byte-identical (md5 `e4f7d9af53fe15270167ff0690c2b017` both). So the gap is the recorded filename, not a derivation difference, which is incidental corroboration of INV-DRV-05: same input, same bytes out. Original text: Record the measured byte-size reduction (full JSON vs artifact). **The corpus measurement this task asked for is withdrawn with 7.4** — it was to be produced by the same batch run. What replaces it is what is actually measured: the cryptoapp artifact at **4,126 bytes against a 69,977-byte source (5.9 %)**, generated by `ape` task 3.1 with the post-`exported` generator. Record it as a single-application measurement and say so; the design's order-of-magnitude claim about the corpus stays an order-of-magnitude claim rather than being upgraded by a number that never got measured
- [x] 7.6 **Deleted, and the evidence was verified to survive first — in that order, because this task's whole point is that the order matters.** Before removing anything, the numbers the driver produced were located in this change's own artifacts: `specs/aperv/spec.md:490-500` carries the executed record (the batch ran over all **345** documents with no crash and no refusal) together with the per-rule exercise counts — **19** apps with flagged widgets dropped for an empty short id, **10** with recoverable D8 synthetic-lambda handlers, **165** with DIALOG windows — and `:739` carries the flagged-widget totals **3,733 → 4,965**. `:33`, `:317` and `:744` restate the corpus facts in their own requirements. So the 345-app derivation, which after 7.4's rescope is the only evidence the generator ever met real-world variety, does not leave the repository with the file. Only then: `git rm rv-android/scripts/gh96_derive_corpus.py`, with a copy under `backup/gh96-gate-driver/` (6,021 bytes) — `backup/` is **not** gitignored in this repository, so it is never `git add`ed. Grepped the whole tree afterwards for `gh96_derive_corpus` and the only two survivors are inside this change: this task, and `design.md:418`'s verification-strategy table. **That table row is deliberately left naming the driver**, because it is the record of a mechanism marked "(executed, one-shot)" — describing what was run is not a dangling reference to something that should still exist, and rewriting the row would delete the evidence trail the paragraph above just took care to preserve. The same choice was made on the `ape` side, where group 5 deleted the equivalence gate and kept `gate-report.md` describing it. Original text: Delete the gate driver (`scripts/gh96_derive_corpus.py`) once the gate is green, keeping only its recorded results (P3). Those results are now load-bearing in a way they were not when this task was written — the 345-app derivation is the only evidence the generator ever met real-world variety, and after 7.4's rescope nothing else in either repository re-establishes it. Before deleting, verify the numbers it produced survive in this change's artifacts (the exercise counts and the 3,733 → 4,965 flagged-widget totals are in `specs/aperv/spec.md`); a deletion that takes the last copy of the evidence with it is not the P3 this task means

## 8. Verification

- [x] 8.1 Run `/rv-test-run aperv-tool` (full suite; expect ~140 s, run in the background)
- [x] 8.2 Run `/rv-qa-lint-fix aperv-tool`, leaving the three pre-existing HEAD lint findings untouched
- [x] 8.3 Run `/rv-verify aperv-tool`
- [x] 8.4 Invoke `/rv-code-reviewer` via the Skill tool
- [x] 8.5 **Run 2026-08-05. No critical issue in the implementation — and one critical issue in the delta, which is what this pass was for.** Implementation side is clean: all 11 `aperv` + 2 `analysis` requirements map to code (`derive_mop_artifact.py` with `derive()`/`serialize_canonical()`/`digest_of()`, `tool.py:675 _derive_mop_artifact` with digest-keyed caching at `:718`, `mop-artifact.json` push and `ape.mopDataPath` at `:807`), the REMOVED requirement is genuinely gone (`_compact_static_analysis_json` occurs 0 times), the `analysis` device-only-consumer requirement is guarded by `test_no_module_outside_aperv_tool_reads_mop_json` (`test_aperv_tool.py:1861`), and the suite is 304 passed / 32 skipped with 60 tests on the generator alone. INV-DRV-04 and INV-DRV-06 are the only two invariants not cited by ID in `src`/`tests`, and both are covered behaviourally rather than nominally — `test_stats_do_not_affect_sets` for -04, and `test_no_target_keys_on_wire` for -06, which asserts both of its clauses (the `*Target` universe reduced to the two documented `hasTargetMethods`, and `reachability`/`windows`/`transitions`/`listeners` absent from the artifact). **CRITICAL, and it is about archiving rather than about code**: this change's `MODIFIED` block for *ApeRVTool Execution Flow* was written before `gh94-ndjson-trace-reader` synced, so syncing it as it stands would silently revert what `gh94` just landed in `openspec/specs/aperv/spec.md`. Measured, not inferred: the block enumerates **9** steps where the main spec now has 10 — no step 10 gzip, no NDJSON note on step 7, step 8 back to the bare `re-raise` without the collection clause, and neither the INV-APV-52/53 paragraph nor the `No health-check` line. All four of `gh94`'s scenarios (`Collection leaves the NDJSON trace intact`, `Gzip failure is non-fatal and changes no status`, `Timeout during exploration still collects`, `No exit contract`) are absent. The collision is bounded to that one requirement and was checked to be: this delta does not touch *Offline Clock-to-Violation Join* and mentions none of INV-APV-48..58, so `gh94`'s invariants and its join requirement are not at risk. This is the mirror image of the choice made while archiving `gh94` — there, this change's step 4/5 was deliberately not applied — and it MUST be reconciled through `openspec-update-change` before this change is synced. Original text: Run `/opsx:verify gh96-mop-artifact-derivation`
- [x] 8.6 **Run 2026-08-05 through the skill. Four files updated, and the drift it found predates this change rather than being caused by it.** `docs/architecture.md` (ARCHITECTURE): the module tree predated the `analysis/` package and `derive_mop_artifact.py`, neither had a Core Components entry, `_gzip_trace`/`_capture_llm_provenance` were missing from the Process View, `corpus_basis` was undocumented, and a stale `expected_jar_*` reference plus "Single-class module"/"8 methods" survived. `CLAUDE.md` (STRUCTURAL): the files table was missing three test modules and `tests/migration/`, and the Configuration Flow lacked the provenance sidecar and trace compression. `README.md` (BEHAVIORAL): it still listed the two `expected_jar_*` declarations that `gh95` removed in `5dd9dfde`. `src/aperv_tool/tools/aperv/tool.py` — **module docstring only**, reviewed line by line before acceptance: it advertised "SATA, BFS, random, or DFS strategies" where `configure()` accepts two, and described properties injection as "throttle configuration" rather than preset + deltas; the derivation and the gzip copy were added. The numbers were re-derived from code rather than trusted: `APERV_PROPERTY_MAPPING` = 50 entries, `APERV_ORCHESTRATION_KEYS` = 8, strategies `["sata","random"]`, `get_variants()` = 8 names over 7 distinct configs with `default is sata`, `retirements.py` = 21. Suite green after the edits (304 passed, 32 skipped). No ADR exists for this module, so none needed revalidation. **Two findings raised and deliberately not fixed here**, both belonging to other changes: `openspec/specs/aperv/spec.md` still maps `step_telemetry_enabled` although the jar deleted `Feature.STEP_TELEMETRY` and `7902bab4` dropped the key from the mapping — that is `gh95` task 7.6 — and the same key sits in `gh95`'s own delta at `:618`. Noted separately, and **not** acted on: the main spec's `ConfigurationError` clause still names `["sata", "random", "bfs", "dfs"]` where the code accepts two; that drift is older than this change and is not its to close. Original text: Run `/rv-docs-sync aperv-tool`

## 9. Schema amendment from `rearch-07` group 1

Opened 2026-08-05. `rearch-07`'s consumption-inventory ratification audited the jar for readers of
every projected field and found `exported` has none — 25 occurrences in `src/main`, all of them the
declaration, the four `ComponentInfo` constructors and the parse site; 13 in `src/test`, all
positional constructor arguments. The `component-triggering` requirement independently forbids the
launcher from consulting it. The owner decided to drop it from the wire, which makes that prohibition
structural rather than merely stated. This group carries the generator's half.

- [x] 9.1 Stop `_project_component()` emitting `exported`; update its docstring, which names the field
      as part of the common projection
- [x] 9.2 Update the tests that assert `exported` on the wire, rewriting rather than deleting where the
      assertion still has a subject — the component-projection tests should now assert its **absence**,
      so a reinstatement fails instead of passing silently
  - The five `exported` occurrences were all *input* documents; nothing asserted it on the wire, so
    nothing pinned its absence either. `test_components_rename_reaches_target_and_compact_target_methods`
    now asserts it reaches none of the three component kinds, alongside the existing
    `readPermission`/`writePermission` absence checks. **Mutation-checked**: reinstating the field in
    `_project_component` fails that test and only that test; restoring it passes 67/67
- [x] 9.3 Run the module suite with the CI flags (`--import-mode=importlib -o "addopts="`)

## 10. Deep-link assertion migrated from `rearch-07` task 5.3a

Opened 2026-08-05, owner-authorized. `rearch-07` 5.3a deleted `MopLauncherStage.buildDeepLinkUri` from
the jar and migrated the six `ActivityFrontierTest` "Lever B" assertions to the side that now computes
the URI — this suite. Five landed on existing tests (`test_deep_link_from_first_action_view`,
`_absent_without_scheme`, `_absent_without_action_view`, `_absent_without_filters`,
`_empty_host_and_path`). **The sixth had no counterpart and was recorded as owed rather than counted
as migrated**: *scheme + host, no path*.

It is not redundant with the two cases that flank it, and that is the whole reason it was tracked. The
existing pair pins both extremes — everything present (`myapp://detail/x`) and nothing but the scheme
(`myapp://`) — and a rule that read `host` and `path` as a single optional unit satisfies both. Only
the asymmetric case separates them: with a host and no path, `host` must still reach the URI and
`path` must still default to empty independently of it (INV-DRV-07). Until this test exists, a
generator that dropped the host when no path was declared passes the suite, and the jar has no
assertion left to catch it — 5.3a deleted the one that used to.

- [x] 10.1 Add `test_deep_link_scheme_and_host_without_path` to `tests/test_derive_mop_artifact.py`,
      asserting `https://x.com` from a single `ACTION_VIEW` filter with a scheme and a host and no
      paths; mutation-check it, since a case added to close a coverage gap is decoration until it has
      been shown to fail on the omission it names
  - Added beside the five it completes, reusing their `_activity_with_filters`/`_filter` helpers so
    the case differs from its neighbours in exactly one respect — the absent `paths` — rather than in
    its scaffolding. Its docstring says what it is for, because a reader who finds six deep-link tests
    where five would look sufficient deserves the reason the sixth exists.
  - **Mutation-checked, and the result is the gap claim itself.** Mutating `_derive_deep_link_uri` to
    `host = hosts[0] if (hosts and paths) else ""` — a generator that keeps the host only when a path
    accompanies it — produces `https://` and fails **exactly one test: this one**. The other 67 pass
    under the mutation, which is the direct evidence that no pre-existing case covered it and that the
    two flanking extremes really are both satisfied by the wrong rule. The anchor was asserted to
    match exactly once before the mutation ran; the file was restored from a byte copy and `git
    status` confirms it unmodified.
- [x] 10.2 Run the module suite with the CI flags
  - `test_derive_mop_artifact.py`: **68 passed** (67 + this one). Full `modules/aperv-tool/tests/`:
    304 passed, 32 skipped. That total is **not attributable to this group alone** — the working tree
    carries another session's uncommitted `gh94` edits to `clock_logcat_join.py`/`trace_ndjson.py`,
    which is where the movement from the 299 measured an hour earlier comes from. Recorded with its
    caveat rather than as a clean before/after.
