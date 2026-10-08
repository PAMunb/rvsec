<!-- Dispatch hints:
     - One module (aperv-tool), about six files. No subagent orchestration is needed.
     - Groups 1–3 are self-contained and testable now. Group 4 is gated (design D8): it needs an ape
       checkout carrying `llm-coordinate-single-base` Part B (group 13: the six keys in
       KeyOwnership.java), because the mapping sweep reads that file. Until then the six mapping
       entries and the two arms stay out.
     - Group 5 needs the night gh120 corpus analysis (`rvsec-dataset/jca_android/static_analysis_20261007_gh120/`).
     - Rules: never start emulators; no recursive search over `/`, `~` or `rvsec-dataset` (use `git grep`
       or bounded paths); commits use `refs #122`, never Co-Authored-By. -->

## 1. Derive: indices, merge and cut (design D1, D2, D4, D5)

- [ ] 1.1 RED: in `tests/test_derive_mop_artifact.py`, add the new "MOP Artifact Projection Contents" scenarios that need only synthetic documents: minimum over handlers and the cut at three; distances of an unlisted wrapper taken from the recovered lambdas; the handler table with a class that reaches nothing and with `invoke(java.lang.Object)`; a document without distances. Add the INV-DRV-10 property test for `_cut_pairs`/`_merge_minima` over seeded random minima, and a malformed-pair test: a non-pair entry, an index ≥ `targets`, a negative `d` and a bool are all skipped
- [ ] 1.2 GREEN: `FORMAT_VERSION = 2`, `GENERATOR_ID = "aperv-derive/2"`, `DIST_K = 3`. Add:
  - `_read_pairs`, `_merge_minima` and `_cut_pairs`;
  - `targets` read through `_require_section(document, "distanceTargets", list, [])`;
  - in `_index_reachability`: `dist_by_signature`, `lambda_dist_by_class`, `activity_class_dist` (no `<init>`/`<clinit>`), the handler records from the D4 signature pattern, and the source-3 constructor exclusion;
  - `_derive_listener_flags` returns flags and minima from the same tier, and `_derive_widget_flags` keeps per-event minima under the same keys as `mop` (the `""` key only when `mop` carries it).

  Update the module docstring's format statements and `derive()`'s Returns block
- [ ] 1.3 Run `/rv-test-run aperv-tool`

## 2. Derive: widget map, dialogs, activities, emission (design D2, D3)

- [ ] 2.1 RED: scenarios "colliding widgets merge their distances by the minimum", "an activity's own constructor does not count toward its distance", a dialog whose widget pairs move to the host widget and the host's `activityDist`, an empty-id widget whose pairs still reach its activity's `activityDist`, and "an activity reaching only through its constructor stays out of source 3"
- [ ] 2.2 GREEN: in `_build_widget_map`, merge minima on a collision whichever widget wins, and fold every parsed widget's minima (all events) into `activity_minima` before the empty-id drop. In `_rekey_dialogs`, move the minima with the widgets and the activity entry. At emission:
  - `_emit_widgets` adds `dist` (cut, empty events omitted);
  - a new `_emit_activity_dist` merges `activity_minima` with `activity_class_dist` and cuts;
  - a new `_emit_handlers` emits the records;
  - `derive()` returns `targets`, `activityDist` and `handlers`.
- [ ] 2.3 Update the cryptoapp ground-truth test to the format-2 values of the spec scenario (targets 27, the three `click` pair lists, the two `handlers` keys, `activityDist`, `MainActivity` out of `mopActivitiesAugmented`, `wtg` edges to three sub-activities). Extend the wire-hygiene test (INV-DRV-06 amended: no `distanceTargets`, no signature-shaped string, only `hasTargetMethods` contains `Target`). Move the format-1 assertions to format 2: `test_derive_mop_artifact.py:388` (`formatVersion`), `:400` and `:1591` (`aperv-derive/1`)
- [ ] 2.4 Re-run the byte-identical regeneration test on the format-2 fixture output
- [ ] 2.5 Run `/rv-doc-code modules/aperv-tool/src/aperv_tool/tools/aperv/derive_mop_artifact.py`
- [ ] 2.6 Run `/rv-test-run aperv-tool`

## 3. Host cache keyed on the format (design D6)

- [ ] 3.1 RED: in `tests/test_aperv_tool.py`, add the scenario "cached artifact of an older format regenerates" (a format-1 artifact whose digest matches is re-derived and the pushed artifact carries `formatVersion: 2`). Move the format assertions at `:1500`, `:1547` and `:1926` to 2
- [ ] 3.2 GREEN: replace `_cached_artifact_digest` with `_cached_artifact_identity` returning `(source.digest, formatVersion)`; `_derive_mop_artifact` reuses the file only when it equals `(digest, FORMAT_VERSION)`; update the method docstrings
- [ ] 3.3 Run `/rv-test-run aperv-tool`

## 4. Keys and arms (design D7; GATED on an ape checkout carrying Part B, design D8)

- [ ] 4.1 Confirm the gate: `$APE_REPO` points to an ape checkout whose `KeyOwnership.java` declares `ape.mopScoring`, `ape.mopWeightD1`, `ape.mopWeightD2`, `ape.mopWeightD3`, `ape.mopRetireAfter` and `ape.mopLauncherDmax` (`llm-coordinate-single-base` task 13.2 done). Record the ape commit in this task
- [ ] 4.2 RED: mapping test (56 entries, the six keys and `corpus_basis` present, no `step_telemetry_enabled`). Variants test (ten keys; `mopd_on_llm_off` and `mopd_on_llm_90` per "Decisive Run Arm Set", the latter equal key by key to `e6_mop_on_llm_90`'s overrides plus `mop_scoring`). Properties test ("Distance arm writes the scoring mode"). In `tests/migration/test_decisive_contrasts.py`, add the two contrasts: `mopd_on_llm_off` minus `mop_on_llm_off` is exactly `ape.mopScoring`, and `mopd_on_llm_90` minus `mopd_on_llm_off` is only `ape.llm*`
- [ ] 4.3 GREEN: add `mop_scoring`, `mop_weight_d1`, `mop_weight_d2`, `mop_weight_d3`, `mop_retire_after` and `mop_launcher_dmax` to `APERV_PROPERTY_MAPPING` beside the MOP weights. Add the two arms to `get_variants()`, each with a comment stating its contrast. Update the class docstring's variant count ("ten names carrying nine configurations")
- [ ] 4.4 Run `tests/migration/` with `APE_REPO` set (`test_mapping_sweep.py`, `test_decisive_contrasts.py`), then `/rv-test-run aperv-tool`

## 5. Real data check (needs the night gh120 corpus analysis)

- [ ] 5.1 With a read-only script kept in this change folder, derive a sample of at least 10 `.apk.json` from `rvsec-dataset/jca_android/static_analysis_20261007_gh120/` in memory (no file written next to them). Report:
  - `targets > 0` on every document;
  - INV-DRV-10 holds on every pair list;
  - the size of `mopActivitiesAugmented` with and without the source-3 exclusion;
  - the number of `handlers` records and how many of them carry `dist`;
  - the share of flagged widgets that carry a `click` pair.

  Record the output beside the script

## 6. Verification and close

- [ ] 6.1 Run `/rv-qa-lint-fix aperv-tool`
- [ ] 6.2 Run `/rv-verify aperv-tool`
- [ ] 6.3 Invoke `/rv-code-reviewer` via the Skill tool
- [ ] 6.4 Check the acceptance criteria of #122 against the evidence and tick them in the issue body; criteria that left the scope (the campaign instrumentation, which the Study 03 replication-package side runs) are struck through with a note
- [ ] 6.5 Tell the `ape` side that the derive is ready: the fixtures of `llm-coordinate-single-base` task 10.1 are derived from this generator, never hand-edited, and that change replaces every `gh<N>` with `gh122`
- [ ] 6.6 Sync the invariants by hand at archive: INV-DRV-06, INV-APV-05, INV-APV-42 and INV-APV-47 replaced, INV-DRV-10 added to `openspec/specs/aperv/spec.md` `## Invariants`, and the `## Data Contracts` output line for `*.mop.json` set to format 2
