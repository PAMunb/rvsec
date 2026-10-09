<!-- Dispatch hints:
     - One module (aperv-tool), about six files. No subagent orchestration is needed.
     - Groups 1–3 are self-contained and testable now. Group 4 is gated (design D8): it needs an ape
       checkout carrying `llm-coordinate-single-base` Part B (group 13: the six keys in
       KeyOwnership.java), because the mapping sweep reads that file. Until then the six mapping
       entries and the two arms stay out.
     - Group 5 needs the gh120 corpus analysis. It is the Study 03 v2 static analysis run by the
       `rep-pack-e03` session: round A (92 documents, complete and final) at
       `rvsec-study03-replication-package/data/raw/e6-static-analysis/A/<apk>/<apk>.json`. Copy, never
       alter, move or delete them; do not read `C/` before its run.log says "round C: collected".
     - Rules: never start emulators; no recursive search over `/`, `~` or `rvsec-dataset` (use `git grep`
       or bounded paths); commits use `refs #122`, never Co-Authored-By. -->

## 1. Derive: indices, merge and cut (design D1, D2, D4, D5)

- [x] 1.1 RED: in `tests/test_derive_mop_artifact.py`, add the new "MOP Artifact Projection Contents" scenarios that need only synthetic documents: minimum over handlers and the cut at three; distances of an unlisted wrapper taken from the recovered lambdas; the handler table with a class that reaches nothing and with `invoke(java.lang.Object)`; a document without distances. Add the INV-DRV-10 property test for `_cut_pairs`/`_merge_minima` over seeded random minima, and a malformed-pair test: a non-pair entry, an index ≥ `targets`, a negative `d` and a bool are all skipped
- [x] 1.2 GREEN: `FORMAT_VERSION = 2`, `GENERATOR_ID = "aperv-derive/2"`, `DIST_K = 3`. Add:
  - `_read_pairs`, `_merge_minima` and `_cut_pairs`;
  - `targets` read through `_require_section(document, "distanceTargets", list, [])`;
  - in `_index_reachability`: `dist_by_signature`, `lambda_dist_by_class`, `activity_class_dist` (no `<init>`/`<clinit>`), the handler records from the D4 signature pattern, and the source-3 constructor exclusion;
  - `_derive_listener_flags` returns flags and minima from the same tier, and `_derive_widget_flags` keeps per-event minima under the same keys as `mop` (the `""` key only when `mop` carries it).

  Update the module docstring's format statements and `derive()`'s Returns block
- [x] 1.3 Run `/rv-test-run aperv-tool`

## 2. Derive: widget map, dialogs, activities, emission (design D2, D3)

- [x] 2.1 RED: scenarios "colliding widgets merge their distances by the minimum", "an activity's own constructor does not count toward its distance", a dialog whose widget pairs move to the host widget and the host's `activityDist`, an empty-id widget whose pairs still reach its activity's `activityDist`, and "an activity reaching only through its constructor stays out of source 3"
- [x] 2.2 GREEN: in `_build_widget_map`, merge minima on a collision whichever widget wins, and fold every parsed widget's minima (all events) into `activity_minima` before the empty-id drop. In `_rekey_dialogs`, move the minima with the widgets and the activity entry. At emission:
  - `_emit_widgets` adds `dist` (cut, empty events omitted);
  - a new `_emit_activity_dist` merges `activity_minima` with `activity_class_dist` and cuts;
  - a new `_emit_handlers` emits the records;
  - `derive()` returns `targets`, `activityDist` and `handlers`.
- [x] 2.3 Replace `tests/fixtures/cryptoapp.apk.json` with a byte copy of the gh120 baseline `modules/rv-static-analysis/tests/resources/cryptoapp.apk.json` and update its provenance in `tests/fixtures/README.md`; the gh60 copy carried no `distanceTargets`. Update the cryptoapp ground-truth test to the format-2 values of the spec scenario (targets 27, the three `click` pair lists, the two `handlers` keys, `activityDist`, `MainActivity` out of `mopActivitiesAugmented`, `wtg` edges to three sub-activities). Extend the wire-hygiene test (INV-DRV-06 amended: no `distanceTargets`, no signature-shaped string, only `hasTargetMethods` contains `Target`). Move the format-1 assertions to format 2: `test_derive_mop_artifact.py:388` (`formatVersion`), `:400` and `:1591` (`aperv-derive/1`)
- [x] 2.4 Re-run the byte-identical regeneration test on the format-2 fixture output
- [x] 2.5 Run `/rv-doc-code modules/aperv-tool/src/aperv_tool/tools/aperv/derive_mop_artifact.py`
- [x] 2.6 Run `/rv-test-run aperv-tool`

## 3. Host cache keyed on the format (design D6)

- [x] 3.1 RED: in `tests/test_aperv_tool.py`, add the scenario "cached artifact of an older format regenerates" (a format-1 artifact whose digest matches is re-derived and the pushed artifact carries `formatVersion: 2`). Move the format assertions at `:1500`, `:1547` and `:1926` to 2
- [x] 3.2 GREEN: replace `_cached_artifact_digest` with `_cached_artifact_identity` returning `(source.digest, formatVersion)`; `_derive_mop_artifact` reuses the file only when it equals `(digest, FORMAT_VERSION)`; update the method docstrings
- [x] 3.3 Run `/rv-test-run aperv-tool`

## 4. Keys and arms (design D7; GATED on an ape checkout carrying Part B, design D8)

- [x] 4.1 Confirm the gate: `$APE_REPO` points to an ape checkout whose `KeyOwnership.java` declares `ape.mopScoring`, `ape.mopWeightD1`, `ape.mopWeightD2`, `ape.mopWeightD3`, `ape.mopRetireAfter` and `ape.mopLauncherDmax` (`llm-coordinate-single-base` task 13.2 done). Record the ape commit in this task. Confirmed 2026-10-08 on ape master `61642793` (`KeyOwnership.java:197-202`; `ape.mopScoring` is declared through `MopScoring.KEY`, which `tests/migration/jar_tables.py` now resolves)
- [x] 4.2 RED: mapping test (56 entries, the six keys and `corpus_basis` present, no `step_telemetry_enabled`). Variants test (ten keys; `mopd_on_llm_off` and `mopd_on_llm_90` per "Decisive Run Arm Set", the latter equal key by key to `e6_mop_on_llm_90`'s overrides plus `mop_scoring`). Properties test ("Distance arm writes the scoring mode"). In `tests/migration/test_decisive_contrasts.py`, add the two contrasts: `mopd_on_llm_off` minus `mop_on_llm_off` is exactly `ape.mopScoring`, and `mopd_on_llm_90` minus `mopd_on_llm_off` is only `ape.llm*`
- [x] 4.3 GREEN: add `mop_scoring`, `mop_weight_d1`, `mop_weight_d2`, `mop_weight_d3`, `mop_retire_after` and `mop_launcher_dmax` to `APERV_PROPERTY_MAPPING` beside the MOP weights. Add the two arms to `get_variants()`, each with a comment stating its contrast. Update the class docstring's variant count ("ten names carrying nine configurations")
- [x] 4.4 Run `tests/migration/` with `APE_REPO` set (`test_mapping_sweep.py`, `test_decisive_contrasts.py`), then `/rv-test-run aperv-tool`

## 5. Real data check (needs the night gh120 corpus analysis)

- [x] 5.1 With a read-only script kept in this change folder, derive a sample of at least 10 `.apk.json` copied from `rvsec-study03-replication-package/data/raw/e6-static-analysis/A/` in memory (the originals are never written). Report:
  - `targets > 0` on every document;
  - INV-DRV-10 holds on every pair list;
  - the size of `mopActivitiesAugmented` with and without the source-3 exclusion;
  - the number of `handlers` records and how many of them carry `dist`;
  - the share of flagged widgets that carry a `click` pair.

  Record the output beside the script

## 6. Verification and close

- [x] 6.1 Run `/rv-qa-lint-fix aperv-tool`
- [x] 6.2 Run `/rv-verify aperv-tool`. Ran 2026-10-08: tests, black and isort pass. flake8 fails on 40 E501 comment lines in `tool.py` that predate gh122 (HEAD had 43; this change removed 3 and added none); the CI runs no flake8. The migration tier the skill skips without `APE_REPO` was run separately against ape `61642793`: 773 passed, 0 skipped
- [x] 6.3 Invoke `/rv-code-reviewer` via the Skill tool. Verdict 2026-10-08: approve, no critical finding. Applied: README and `docs/architecture.md` synced (ten names, 56 entries, the `mopd_*` arms and the keys they set, the format-2 contents, the cache key), two test docstrings. Accepted: the complexity of `_index_reachability` (CC 14 → 23); the suggested split moves the per-method body into a one-use helper with seven accumulators. Deferred to 6.6: the delta scenario title "Source components flag is explicit in all three arms", whose body iterates five. Raised to the author: the deployment window (`modules` is pushed with format 2 while ape `origin/master` still builds a format-1 jar)
- [ ] 6.4 Check the acceptance criteria of #122 against the evidence and tick them in the issue body; criteria that left the scope (the campaign instrumentation, which the Study 03 replication-package side runs) are struck through with a note
- [x] 6.5 Tell the `ape` side that the derive is ready: the fixtures of `llm-coordinate-single-base` task 10.1 are derived from this generator, never hand-edited, and that change replaces every `gh<N>` with `gh122`
- [ ] 6.6 Sync the invariants by hand at archive: INV-DRV-06, INV-APV-05, INV-APV-42 and INV-APV-47 replaced, INV-DRV-10 added to `openspec/specs/aperv/spec.md` `## Invariants`, and the `## Data Contracts` output line for `*.mop.json` set to format 2

## 7. Per-key cut and source read (author's decisions of 2026-10-09; design D9, D10)

<!-- Group 7 runs before 6.4 and 6.6. 7.6 and 7.7 read the round-A documents, now flat files in
     `rvsec-study03-replication-package/data/raw/e6-static-analysis/final/` (163, `<apk>.apk.json`):
     copy them, never alter, move or delete them. 7.7 runs one process at a time; the documents are
     large and the host's memory is shared. -->

- [x] 7.1 RED (derive): in `tests/test_derive_mop_artifact.py`:
  - replace `test_cut_pairs_keeps_the_nearest_three_by_distance_then_index` with tests of `_cut_weighed` (`{7: 4, 2: 2, 5: 1, 9: 2, 4: 3, 8: 0}` → `[[8,0],[5,1],[2,2],[9,2],[4,3]]`; only pairs at `d ≥ 4` → `[]`) and of `_cut_nearest` (the three nearest);
  - move the INV-DRV-10 property test to both cuts: `_cut_weighed` keeps exactly the minima at `d ≤ 3`, `_cut_nearest` at most three;
  - rewrite the scenario "a widget's distance is the minimum over its handlers, every target within three calls" and add "a widget whose targets are all four calls or more away carries no pair" and "activityDist keeps the three nearest targets";
  - in the cryptoapp ground truth: `btn_cipher_encrypt` emitted with no `dist`, `CipherActivity$1` with no `dist`, `executeButton` and its handler unchanged, `activityDist` unchanged
- [x] 7.2 GREEN (derive): `DIST_WEIGHED_MAX = 3` beside `DIST_K`. Replace `_cut_pairs` with `_cut_weighed` (used by `_emit_widgets` and `_emit_handlers`) and `_cut_nearest` (used by `_emit_activity_dist`). Omit an event whose list is empty after the cut, and a `dist` map left empty. Update the module docstring, the constants' comments and the docstrings of the three emitters
- [x] 7.3 RED (source read): a `digest_of_file` test (equal to `"sha256:" + sha256(bytes)` on a file longer than one read chunk). In `tests/test_aperv_tool.py`, extend "cache hit skips derivation" so that `json.load` is never called on a hit. Move the callers of `digest_of(bytes)` (`tests/test_aperv_tool.py:1672,1699,2113`, `tests/test_derive_mop_artifact.py:2032,2245,2267`) to `digest_of_file`
- [x] 7.4 GREEN (source read): replace `digest_of(payload)` with `digest_of_file(path)` (`hashlib.file_digest`). In `_derive_mop_artifact`, compute the digest, check the cache, and on a miss parse with `json.load` from a UTF-8 text handle; no `bytes` copy of the file stays referenced. Update the method's docstring. Move `real_data_check.py` and `reach_without_distance.py` off `digest_of` if they use it, and update `real_data_check.py`'s INV-DRV-10 check to the two cuts
- [x] 7.5 Run the full suite with `APE_REPO` set (`APE_REPO=<ape> uv run pytest --import-mode=importlib -o "addopts=" modules/aperv-tool/tests -q`) and record the ape commit. Ran 2026-10-09 against ape master `469269e9` (one commit past `4516cf93`, touching no `KeyOwnership.java` or `Presets.java`; its working tree carries uncommitted Part B edits to neither): 777 passed, 0 skipped
- [x] 7.6 Re-run `real_data_check.py` on the same 23 round-A documents (copies), and overwrite `real_data_check.out.md` with the run date and the derive it ran at. The handler and click-pair counts change with the cut
- [x] 7.7 Measure the peak RSS of the derive path on `at.techbee.jtx_216000015.apk.json` (a copy), once with the read before D10 and once with D10, each in a fresh process under `/usr/bin/time -v`. Record the file's size in bytes, because the aperv session's 1.92 GB does not match the 2,017,546,684 bytes listed on 2026-10-09. Keep the script and its output in this change folder, and replace the estimate in design D10 and the proposal with the measured saving
- [x] 7.8 Tell the `aperv` session that the derive implements the cut, so it re-derives the `ape` fixtures with `evidence/derive_fixtures.py` (its task 18.6)
- [x] 7.9 Run `/rv-qa-lint-fix aperv-tool`, `/rv-verify aperv-tool` (no new flake8 violation on lines this group touches), and `/rv-code-reviewer` on this group's diff. Ran 2026-10-09: the fixers changed nothing in `src/`; black then rewrapped group-7 lines in `tests/test_derive_mop_artifact.py`. flake8: 0 on `derive_mop_artifact.py` and on that test file, and `tool.py` keeps its 40 older E501 comment lines. The verify run (no `APE_REPO`) passed 752 tests and skipped 25. The review verdict was approve, with no correctness finding. Applied: a long Raises line in `tool.py`, two docstring wraps, and a test where one event is cut to nothing while another keeps its pairs. Still open, through `/opsx:update` together with 7.7: `design.md` D6 still names `digest_of(raw)`, and the error table could mention that a source starting with a UTF-8 BOM now fails the parse. Folded into design.md on 2026-10-09
