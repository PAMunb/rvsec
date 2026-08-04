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
- [ ] 7.3 Re-verify the `ape` audit claiming no consumer reads WTG edge multiplicity, so the set-based comparison of design D7 is justified rather than assumed
- [ ] 7.4 Run the gate jointly with the `ape` side (old parser on the **raw** full JSON as oracle) and require 345/345 green before either repository cuts over
- [ ] 7.5 Record the measured byte-size reduction (full JSON vs artifact) over the corpus, replacing the design's order-of-magnitude claim with a measurement
- [ ] 7.6 Delete the gate driver once green, keeping only its recorded results (P3)

## 8. Verification

- [x] 8.1 Run `/rv-test-run aperv-tool` (full suite; expect ~140 s, run in the background)
- [x] 8.2 Run `/rv-qa-lint-fix aperv-tool`, leaving the three pre-existing HEAD lint findings untouched
- [x] 8.3 Run `/rv-verify aperv-tool`
- [x] 8.4 Invoke `/rv-code-reviewer` via the Skill tool
- [ ] 8.5 Run `/opsx:verify gh96-mop-artifact-derivation`
- [ ] 8.6 Run `/rv-docs-sync aperv-tool`
