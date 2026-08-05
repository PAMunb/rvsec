<!-- Scope: ~8 files in modules/aperv-tool (tool.py, tests/test_aperv_tool.py, three new
     tests/migration/ files, CLAUDE.md, docs/architecture.md). Below the 20-file threshold for
     subagent orchestration — a single session per group is the right granularity.

     Ordering is dependency order and is load-bearing, not cosmetic:
       - Group 1 captures the baseline from the UNMODIFIED tool.py. No arm may be edited before it.
       - Group 2 changes the mechanism; groups 3-4 change the arms it serves.
       - Groups 3-5 each END with the regeneration diff. A group is not done until its diff is empty.
       - Group 6 deletes the guards only after every arm has migrated.
     Critical path: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7. Group 8 was added on 2026-08-05, after group 7
     closed, and hangs off none of it: it deletes a declaration that never reached ape.properties,
     so no arm's effective configuration moves and the regeneration diff stays empty.

     This change is OFFLINE. No task starts an emulator, runs adb, or executes the jar. The run that
     proves the deployed jar honours ape.preset belongs to gh97-rearch-ab-gate (owner decision,
     2026-08-04). The ape-side counterpart's group 10 (deleting stage 2's transitional test
     scaffolding) is work in the ape repository and is not part of this change.

     Consequence of that decision for the close: the change stays OPEN until gh97-rearch-ab-gate has
     executed. Group 7 completes the implementation, but no spec sync and no archive happen before
     gh97's run, and commits stay "refs #95". If the deployed jar turns out not to resolve a preset
     the way the tables here say, the fix belongs to the change that caused it rather than to a
     follow-up on an archived one. -->

## 1. Preconditions, jar tables and baseline capture (BEFORE any edit)

- [x] 1.1 Record the stage-2 dependency as a deployment precondition in `modules/aperv-tool/CLAUDE.md`: the installed `ape-rv.jar` (2026-07-31) predates `rearch-02-runspec` (archived 2026-08-04), so it must be rebuilt from branch `rearch` before any campaign runs the re-expressed arms — a pre-stage-2 jar treats `ape.preset` as an unknown key and every arm collapses to jar defaults. No rebuild and no run happens in this change
- [x] 1.2 Re-verify the inventory at HEAD by executing the module: 29 variants, 51 `APERV_PROPERTY_MAPPING` pairs, 17 `ARM_DEFINING_KEYS`, 11 `LLM_ARM_KEYS`, 6 `_ARM_DEFINING_EXEMPT`, 17-key `_APE_PURE_ARM_FLAGS`. Correct `design.md` if the tree has moved
- [x] 1.3 Write `tests/migration/jar_tables.py` (design D8): parse `Presets.java`, `KeyOwnership.java` from `$APE_REPO` (fallback `$RVSEC_HOME/ape`) into the four preset vectors, the accepted-key set, the retired-key set, and per-key `ValueType`/default; record the `ape` commit and file digests as provenance. Hard error on a parse failure, never a degraded mode
- [x] 1.4 Add unit tests for `jar_tables.py` against the checked-out `ape` source: 4 presets sized 18/22/25/29, 111 accepted keys, `ape.mopWeightActivity` in the retired set
- [x] 1.5 Sweep every mapped `ape.*` key against the accepted vocabulary and the retired list; record the dead-key list. Expected from the design's sweep: exactly `ape.mopWeightActivity`. `ape_pure_mode` is NOT expected — `gh93` already removed it. Report any further dead entry rather than deleting silently
- [x] 1.6 Write the retirement list the migration test reads: 21 names, each with its kind (*never distinct* / *name consolidated* / *finished campaign*) and its reason, with `sata_mop_act_frontier` naming `mop_on_llm_off` as the surviving configuration
- [x] 1.7 Write `tests/migration/capture_arm_baseline.py` and generate `tests/migration/arm_effective_baseline.json` covering all **29** arms' typed effective configurations from the **unmodified** `tool.py`; commit both
- [x] 1.8 Write `tests/migration/test_arm_regeneration_diff.py`: per-arm typed empty-diff assertion against the baseline; retired names read from the 1.6 list and excluded from the diff; an arm missing from both the variants and the list fails the check; for the *name consolidated* entry, assert that `mop_on_llm_off` regenerates `sata_mop_act_frontier`'s baseline. Not-yet-migrated arms compare via their current expansion, so the test is green from day one
- [x] 1.9 Run `/rv-doc-code modules/aperv-tool/tests/migration/jar_tables.py`
- [x] 1.10 Run `/rv-test-run aperv-tool` (suite + migration test green pre-change)

## 2. Properties writer and configure() — mechanism before arms

- [x] 2.1 Restate `_push_properties()` per design D4: `ape.preset` first, `ape.mopDataPath` when the MOP artifact was pushed, then one line per `overrides` entry in mapping order; `ConfigurationError` on an unmapped override key, raised before any push; bool serialization unchanged. Delete the 51-pair expansion loop
- [x] 2.2 Extend `configure()`: validate `preset` present and non-empty and `overrides` a dict, in the check order fixed by the design's API section; shrink `APERV_AVAILABLE_STRATEGIES` to `["sata", "random"]`
- [x] 2.3 Implement the DSL fold in `configure()` (design D3, INV-APV-39): move every top-level key with an `APERV_PROPERTY_MAPPING` entry into `overrides` with the DSL value winning, and raise `ConfigurationError` for any top-level key that is neither mapped nor one of `preset`/`overrides`/`strategy`/`mop_data`/`seed`/`expected_jar_git_sha`/`expected_jar_sha256`. Without it `aperv:sata_mop@frontier_boost_weight=200` writes no property line and reports no error
- [x] 2.4 Add tests for the fold: the DSL override reaches `ape.properties`, a DSL value overrides the arm's own entry for the same key, and a typo'd key raises instead of vanishing
- [x] 2.5 Restate `TestPushProperties` / `TestArmProperties` / `TestConfigure` for the new contract: preset line first, deltas only, lowercase bools, Python-only keys excluded, seed not in properties, `bfs`/`dfs` rejected before device interaction, missing preset and non-dict overrides raise
- [x] 2.6 Run `/rv-test-run aperv-tool`

## 3. Arm re-expression — the four preset-identity arms and the never-distinct retirements

- [x] 3.1 Re-express `sata` as `preset="aperv"` with empty `overrides`, bind `default` to the same object, and re-express `sata_mop` (`preset="mop"`, empty), `sata_llm` (`preset="llm"`, `llm_url`) and `sata_mop_llm` (`preset="llm_mop"`, `llm_url`); drop `throttle_ms`, which the preset already states. `sata_mop` is the frozen-corpus name — 4,096 traces and 1,066 consolidation files carry it — so it is the one that must not move (INV-APV-42)
- [x] 3.2 Delete the never-distinct variants: `ape_pure` (with its `_APE_PURE_ARM_FLAGS` constant), `bfs`, and `sata_mop_widget` (the alias binding dies with it, retiring INV-APV-16); delete `random` and `sata_mop_activity`
- [x] 3.3 Re-run the regeneration diff — empty for every migrated arm, with the five retirements of this group listed as documented removals
- [x] 3.4 Run `/rv-test-run aperv-tool`

## 4. Arm re-expression — decisive-run arms and the consolidated name

- [x] 4.1 Re-express `mop_on_llm_off`, `mop_off_llm_off` and `mop_on_llm_70` per the design D2 table, and delete `sata_mop_act_frontier` — its configuration is byte-identical to `mop_on_llm_off` and survives under that name, which task 4.4's diff proves rather than assumes; keep the INV-APV-29/30 rationale comments (MOP-off keeps `mop_data` and frontier navigation) and the normative-name comment at the definition site
- [x] 4.2 Keep `llm_snap_tolerance_px=150` as an ordinary `overrides` entry of `mop_on_llm_70`, and `expected_jar_git_sha`/`expected_jar_sha256` Python-only at the top level (INV-APV-34 pairing untouched)
- [x] 4.3 Restate the single-factor contrast tests to diff effective configurations: reference vs control differs in exactly the five MOP weight keys plus `ape.activityTriggerEnabled`; reference vs LLM arm differs only in `ape.llm*` keys; neither declaration key is in `APERV_PROPERTY_MAPPING`
- [x] 4.4 Delete the six gh43 prompt arms and `cal_a1`…`cal_a9` (finished campaigns), then re-run the regeneration diff — empty for every surviving arm, all 21 retirements listed with their kinds, and `mop_on_llm_off` shown to reproduce `sata_mop_act_frontier`'s baseline
- [x] 4.5 Run `/rv-test-run aperv-tool`

## 5. Dead key and substrate dict removal

- [x] 5.1 Delete `mop_weight_activity` from `APERV_PROPERTY_MAPPING`, plus any further dead entry found by the 1.5 sweep; assert the mapping has 50 entries and that `llm_max_tokens` / `llm_snap_tolerance_px` survive
- [x] 5.2 Delete the substrate spread dicts `_BASELINE_ARM_FLAGS`, `_MOP_SUBSTRATE`, `_LLM_FLAGS`, `_FRONTIER_SUBSTRATE`, `_MOP_OFF_OVERRIDES`, `_CAL_LLM_COMMON` (`_APE_PURE_ARM_FLAGS` went with task 3.2)
- [x] 5.3 Grep `modules/aperv-tool/src` for `mopWeightActivity` and each deleted constant name — zero hits, no commented-out remnant (P3)
- [x] 5.4 Re-run the regeneration diff — empty for every surviving arm
- [x] 5.5 Run `/rv-test-run aperv-tool`

## 6. Guard retirement and documentation

- [x] 6.1 Delete `ARM_DEFINING_KEYS`, `_ARM_DEFINING_EXEMPT` and `LLM_ARM_KEYS` from `tool.py`; rewrite the module docstring and the `get_variants()` docstring to the preset+overrides contract, current-state only (P4 — no "migrated from", no "replaces")
- [x] 6.2 Retire the constant-vs-constant guard tests in `tests/test_aperv_tool.py`: `TestArmDefiningGuard`, the INV-APV-14 explicitness and table-pin tests in `TestFrozenArmVariants`, the INV-APV-26/27 tests, the calibration plan-table pins, and the gh90 expansion-diff tests; delete `_EXPECTED_ARM_DEFINING_MAPPING` and companions
- [x] 6.3 Add `test_retired_guards_are_gone` asserting the three constants no longer exist, so a future revert is caught rather than merged
- [x] 6.4 Verify by grep that `tool.py` contains no `RUN_START` parsing and no echo-vs-intent logic (INV-APV-43, owner decision D1)
- [x] 6.5 Update `modules/aperv-tool/CLAUDE.md`: the variant table becomes preset + overrides, the `ape_pure` and `bfs` rows die with the variants, the `LLM_ARM_KEYS` guard paragraph is removed, and the count becomes 8
- [x] 6.6 Update `modules/aperv-tool/docs/architecture.md` for the preset+overrides arm surface and the reduced properties-generation path
- [x] 6.7 Run `/rv-test-run aperv-tool`

## 7. Final verification and owner sign-off

- [x] 7.1 Final full regeneration diff over all 8 surviving arms; produce the human-readable per-arm report — empty, or the owner-approved declared divergences with their new arm names — plus the documented retirements of `ape_pure` and `bfs`
- [x] 7.2 Run `/rv-qa-lint-fix aperv-tool`. Exactly one pre-existing finding survives groups 1-6 and MUST be left untouched: the `black` reformat at `tests/test_aperv_tool.py:1435` (the `_FakeResponse(json.dumps(...))` line in `TestLlmProvenance`). The E741 formerly at `:439` is gone — it lived inside a test retired with the mechanism it covered, so it went with the code — and `flake8 --max-line-length=100` now reports nothing over `src` and `tests`. Check before fixing: `black --diff modules/aperv-tool/tests/test_aperv_tool.py | grep -E "^@@"` may show only `@@ -1435`; any other hunk is this change's and should be fixed
- [x] 7.3 Run `/rv-verify aperv-tool`
- [x] 7.4 Invoke `/rv-code-reviewer` via the Skill tool over the `modules/aperv-tool` diff
- [x] 7.4a Close the defect 7.4 found: `APERV_ORCHESTRATION_KEYS` accepts `device_port`, `device_serial` and `device_id`, which `ExecutionController` injects into every tool's parameters whenever `--device-port` is set. Without them `configure()` rejects every containerized and parallel run — including `gh97`'s A/B gate — inside `Platform._load_tool`. Add the regression test that configures an arm carrying all three and asserts no `ape.*` line names them
- [x] 7.4b Move the unmapped-`overrides` rejection from `_push_properties()` into `configure()`, so "before any `adb push`" holds for the run and not merely for the properties push; restate the test against `configure()`
- [x] 7.4c Delete `KNOWN_DEAD` from `tests/migration/test_mapping_sweep.py` — the entry it tolerated is gone, so the assertion was vacuous and would have accepted the dead key's return; assert no mapped key is dead instead
- [x] 7.4d Delete the orphaned INV-APV-13 comment block above `_DECISIVE_ARMS` in `tests/test_aperv_tool.py` (P3/P4: it describes a deleted constant and carries migration history), and the unreachable not-yet-migrated path in `test_arm_regeneration_diff.py` (`_from_explicit_keys` and its branch), whose "green from day one" narrative describes a state that no longer exists
- [x] 7.5 Run `/rv-docs-sync aperv-tool`
- [ ] 7.6 **Owner sign-off**: present the final diff report and the task 1.6 finding. The sign-off approves the *migration*, not the retirement of its evidence: deleting `tests/migration/test_arm_regeneration_diff.py` and archiving `arm_effective_baseline.json`, the final diff output and the `ape` source provenance under `modules/aperv-tool/docs/` as the migration record are gated on `gh97-rearch-ab-gate` having executed. Everything this change does is offline, so `gh97`'s run is the first time a device honours `ape.preset`, and the diff plus the baseline are exactly what a mismatch there would need. When that deletion happens, only `test_arm_regeneration_diff.py` goes — `jar_tables.py`, `retirements.py`, `test_jar_tables.py`, `test_mapping_sweep.py` and `test_decisive_contrasts.py` stay, because INV-APV-41 and the decisive-run contrasts are standing checks (INV-APV-44 — the diff is one-time and MUST NOT become a standing constant-vs-constant guard). Name one residual risk in the sign-off: the whole migration tier skips silently without `$APE_REPO` (47 skips, by design — CI has no `ape` checkout), so a green module run is not evidence the gate ran; the executed result and the `ape` commit it ran against belong in the sign-off record, not merely in the baseline's provenance
- [x] 7.7 Close the counterpart obligation the `ape`-side `rearch-05-thin-python-arms` reserved to this repository's OpenSpec workflow. There is nothing to tick over there: its task 1.3 records that **no task 8.5a exists and none will be created**, because the obligation — "open a change in rv-android carrying this stage's counterpart delta rather than hand-editing that repo's `openspec/specs/`" — is discharged structurally by `gh95` existing, and a numbered task to receive the pointer would re-import the coupling that rewrite removed. So this closes against that change as a whole, and no file in the `ape` worktree is touched

## 8. Retirement of the in-source jar-identity declaration (owner directive, 2026-08-05)

<!-- Added after group 7 by owner directive: source code may not name the revision or digest of a
     binary built in another repository (INV-APV-59, design D9). Independent of the open 7.6 — it
     changes no arm's effective configuration, so the regeneration diff stays empty and the sign-off
     is unaffected. It is, however, a precondition for deploying the stage-4 `ape-rv.jar` of the
     `ape`-side `rearch-04`, which is what made the pin visible: with the declaration in place that
     redeploy would fail the smoke gate on a correct jar. -->

- [ ] 8.1 Delete `expected_jar_git_sha` and `expected_jar_sha256` from `get_variants()["mop_on_llm_70"]` in `modules/aperv-tool/src/aperv_tool/tools/aperv/tool.py`, with the comment block that justified them. Rewrite the `llm_snap_tolerance_px` comment to current state (P4): why the radius is raised, without the sentence making it conditional on a declared build — the dead-pair-ban rationale stays, the pin does not
- [ ] 8.2 Remove both names from `APERV_ORCHESTRATION_KEYS`, so `configure()` rejects them like any other unhonourable top-level key and experiment YAML cannot reintroduce the declaration through the DSL
- [ ] 8.3 Drop the INV-APV-34 pairing sentence from the `llm_snap_tolerance_px` comment in `APERV_PROPERTY_MAPPING` (`:188-190`), and rewrite the `jar_sha256` paragraph of `_capture_llm_provenance()`'s docstring (`:924-928`): it records which binary ran, full stop — no "runtime half of the B3 gate", no comparison against a declared digest
- [ ] 8.4 Delete `_SNAP_TOLERANCE_RAISED`, `_JAR_SHA_KEY`, `_JAR_DIGEST_KEY`, `_JAR_DECLARATION_KEYS`, `_snap_tolerance_offenders` and the whole `TestSnapToleranceGate` class from `modules/aperv-tool/tests/test_aperv_tool.py`, plus the two declaration keys wherever the orchestration-key and Python-only-key tests enumerate them (`:295-300`, `:809-820`). Deleted, not skipped or renamed (P3); back up the file to `backup/` first
- [ ] 8.5 Restate the reference-vs-LLM-arm contrast test: every differing effective key is an `ape.llm*` key and the two arms' top-level key sets are identical. The assertion that the declaration keys are absent from `APERV_PROPERTY_MAPPING` goes with them — there is no exemption left to license
- [ ] 8.6 Add `test_no_external_artifact_identity_is_declared_in_source` (INV-APV-59): no file under `modules/aperv-tool/src` contains a 40- or 64-hex-character string literal, and no variant returned by `get_variants()` carries a top-level key matching `expected_*`. The guard is what stops the pin coming back in a different name — without it this group is a deletion rather than a rule
- [ ] 8.7 Re-run the regeneration diff (`tests/migration/test_arm_regeneration_diff.py`) — still empty for all 8 arms. The deleted keys never reached `ape.properties`, so an effective-configuration change here would mean the diff was measuring the wrong thing. **Ticked on evidence, and the evidence is a comparison rather than a green run — 2026-08-05.** With `$APE_REPO` pointed at the `ape-rearch` worktree the migration tier reports **13 failures, identical before and after this group**: the same run with only these two files reverted (`git stash push` on `tool.py` and `test_aperv_tool.py`) fails the same 13. So this group moves nothing the diff measures, which is what the task asks. The 13 belong to `gh95` as a whole and to task 7.6: the `ape` source has advanced past the baseline capture, and `rearch-04` group 6 removed `ape.stepTelemetryEnabled` from the preset vectors — every preset lost exactly one key (18/22/25/29 → 17/21/24/28) and every arm's diff is the single entry `ape.stepTelemetryEnabled: (True, '<absent>')`. The baseline was captured against a pre-stage-4 `ape`; re-capturing it is the owner's call at sign-off, not this group's to make silently
- [ ] 8.8 Record the retirement in `modules/aperv-tool/CLAUDE.md` and `docs/architecture.md`: the orchestration-key count drops from ten to eight, and the module states which jar ran by measuring it (`jar_sha256` in the run provenance), never by declaring it
- [ ] 8.9 Run `/rv-qa-lint-fix aperv-tool` (the 7.2 pre-existing `black` finding stays untouched) and `/rv-test-run aperv-tool`
