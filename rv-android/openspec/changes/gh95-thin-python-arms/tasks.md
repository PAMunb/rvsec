<!-- Scope: ~8 files in modules/aperv-tool (tool.py, tests/test_aperv_tool.py, three new
     tests/migration/ files, CLAUDE.md, docs/architecture.md). Below the 20-file threshold for
     subagent orchestration — a single session per group is the right granularity.

     Ordering is dependency order and is load-bearing, not cosmetic:
       - Group 1 captures the baseline from the UNMODIFIED tool.py. No arm may be edited before it.
       - Group 2 changes the mechanism; groups 3-7 change the arms it serves.
       - Groups 3-7 each END with the regeneration diff. A group is not done until its diff is empty.
       - Group 9 deletes the guards only after every arm has migrated.
     Critical path: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8 -> 9 -> 10.

     This change is OFFLINE. No task starts an emulator, runs adb, or executes the jar. The run that
     proves the deployed jar honours ape.preset belongs to gh97-rearch-ab-gate (owner decision,
     2026-08-04). The ape-side counterpart's group 10 (deleting stage 2's transitional test
     scaffolding) is work in the ape repository and is not part of this change. -->

## 1. Preconditions, jar tables and baseline capture (BEFORE any edit)

- [ ] 1.1 Record the stage-2 dependency as a deployment precondition in `modules/aperv-tool/CLAUDE.md`: the installed `ape-rv.jar` (2026-07-31) predates `rearch-02-runspec` (archived 2026-08-04), so it must be rebuilt from branch `rearch` before any campaign runs the re-expressed arms — a pre-stage-2 jar treats `ape.preset` as an unknown key and every arm collapses to jar defaults. No rebuild and no run happens in this change
- [ ] 1.2 Re-verify the inventory at HEAD by executing the module: 29 variants, 51 `APERV_PROPERTY_MAPPING` pairs, 17 `ARM_DEFINING_KEYS`, 11 `LLM_ARM_KEYS`, 6 `_ARM_DEFINING_EXEMPT`, 17-key `_APE_PURE_ARM_FLAGS`. Correct `design.md` if the tree has moved
- [ ] 1.3 Write `tests/migration/jar_tables.py` (design D8): parse `Presets.java`, `KeyOwnership.java` from `$APE_REPO` (fallback `$RVSEC_HOME/ape`) into the four preset vectors, the accepted-key set, the retired-key set, and per-key `ValueType`/default; record the `ape` commit and file digests as provenance. Hard error on a parse failure, never a degraded mode
- [ ] 1.4 Add unit tests for `jar_tables.py` against the checked-out `ape` source: 4 presets sized 18/22/25/29, 111 accepted keys, `ape.mopWeightActivity` in the retired set
- [ ] 1.5 Sweep every mapped `ape.*` key against the accepted vocabulary and the retired list; record the dead-key list. Expected from the design's sweep: exactly `ape.mopWeightActivity`. `ape_pure_mode` is NOT expected — `gh93` already removed it. Report any further dead entry rather than deleting silently
- [ ] 1.6 **Resolve design Open Question 1** (blocks group 5, nothing earlier): read `Config.java` at the `ape` revision the gh43 campaign ran and confirm `frontierBoostWeight` defaulted to `200` and `activityTriggerEnabled` to `true`. If confirmed, the INV-APV-39 overrides are a preservation; if not, the six frozen arms carry a declared divergence for the owner (INV-APV-42) and group 5 stops for a decision
- [ ] 1.7 Write `tests/migration/capture_arm_baseline.py` and generate `tests/migration/arm_effective_baseline.json` covering all **29** arms' typed effective configurations from the **unmodified** `tool.py`; commit both
- [ ] 1.8 Write `tests/migration/test_arm_regeneration_diff.py`: per-arm typed empty-diff assertion against the baseline, with `ape_pure`/`bfs` on an explicit retirement list and an arm missing from both mapping and list failing the check. Not-yet-migrated arms compare via their current expansion, so the test is green from day one
- [ ] 1.9 Run `/rv-doc-code modules/aperv-tool/tests/migration/jar_tables.py`
- [ ] 1.10 Run `/rv-test-run aperv-tool` (suite + migration test green pre-change)

## 2. Properties writer and configure() — mechanism before arms

- [ ] 2.1 Restate `_push_properties()` per design D4: `ape.preset` first, `ape.mopDataPath` when the MOP artifact was pushed, then one line per `overrides` entry in mapping order; `ConfigurationError` on an unmapped override key, raised before any push; bool serialization unchanged. Delete the 51-pair expansion loop
- [ ] 2.2 Extend `configure()`: validate `preset` present and non-empty and `overrides` a dict, in the check order fixed by the design's API section; shrink `APERV_AVAILABLE_STRATEGIES` to `["sata", "random"]`
- [ ] 2.3 Restate `TestPushProperties` / `TestArmProperties` / `TestConfigure` for the new contract: preset line first, deltas only, lowercase bools, Python-only keys excluded, seed not in properties, `bfs`/`dfs` rejected before device interaction, missing preset and non-dict overrides raise
- [ ] 2.4 Run `/rv-test-run aperv-tool`

## 3. Arm re-expression — baseline arms and the two retirements

- [ ] 3.1 Re-express `default`, `sata`, `random` as `preset="aperv"` with empty `overrides` (design D2); drop `throttle_ms`, which the preset already states
- [ ] 3.2 Delete the `ape_pure` variant and its `_APE_PURE_ARM_FLAGS` constant; delete the `bfs` variant. Add both to the migration retirement list with the reason recorded (no structural-purity preset exists; `bfs` was never an agent type)
- [ ] 3.3 Re-run the regeneration diff — empty for every migrated arm, with the two retirements listed as documented removals
- [ ] 3.4 Run `/rv-test-run aperv-tool`

## 4. Arm re-expression — MOP arms

- [ ] 4.1 Re-express `sata_mop_widget` as `preset="mop"` with empty `overrides`, `mop_data` kept top-level, and `sata_mop` bound to the same object. `sata_mop` is the primary name — 4,096 traces and 1,066 consolidation files carry it, `sata_mop_widget` has produced none — so it is the one that must not move (INV-APV-42)
- [ ] 4.2 Re-express `sata_mop_activity` (one override) and `sata_mop_act_frontier` (the four reach deltas)
- [ ] 4.3 Re-run the regeneration diff — empty for every surviving arm
- [ ] 4.4 Run `/rv-test-run aperv-tool`

## 5. Arm re-expression — LLM arms and the frozen gh43 six

- [ ] 5.1 Re-express `sata_llm` (`preset="llm"`, override `llm_url`) and `sata_mop_llm` (`preset="llm_mop"`, override `llm_url`)
- [ ] 5.2 Re-express the six gh43 prompt arms as `preset="llm_mop"` + `llm_url`, `llm_percentage=0.7`, `llm_prompt_variant=<variant>`, **plus** the INV-APV-39 restorations `frontier_boost_weight=200` and `activity_trigger_enabled=True` justified by task 1.6. Carry the reason in a comment at the definition site: the preset states `0`/`false` where these arms inherited the jar defaults, and under the stage-2 `Feature` model those preset values deactivate `FRONTIER` and `ACTIVITY_TRIGGER`
- [ ] 5.3 Add a test asserting the restorations are load-bearing: removing either override makes the regeneration diff non-empty, naming the two keys
- [ ] 5.4 Re-run the regeneration diff — empty for every surviving arm
- [ ] 5.5 Run `/rv-test-run aperv-tool`

## 6. Arm re-expression — calibration arms

- [ ] 6.1 Re-express `cal_a1`…`cal_a9` as `preset="llm_mop"` + the four frontier deltas + `llm_url` + their per-arm LLM deltas (design D2 table: 8 overrides each, 9 for `cal_a3`, 10 for `cal_a5`). Keys equal to the preset value are omitted, not restated
- [ ] 6.2 Carry the per-arm hypothesis comments (H1/H2/H3, the control lineage of `cal_a1`, the ANC2 anchor rationale) onto the new dicts — they are semantics of the experiment, not of the retired guard machinery
- [ ] 6.3 Restate the calibration structural tests on `overrides`: `cal_a3` is the stagnation-only regime, `cal_a5` vs `cal_a6` differ exactly in `llm_top_p`/`llm_top_k` (present vs absent), every `cal_*` carries the frontier substrate
- [ ] 6.4 Re-run the regeneration diff — empty for every surviving arm
- [ ] 6.5 Run `/rv-test-run aperv-tool`

## 7. Arm re-expression — decisive-run arms

- [ ] 7.1 Re-express `mop_on_llm_off`, `mop_off_llm_off` and `mop_on_llm_70` per the design D2 table; keep the INV-APV-29/30 rationale comments (MOP-off keeps `mop_data` and frontier navigation) and the normative-name comment at the definition site
- [ ] 7.2 Keep `llm_snap_tolerance_px=150` as an ordinary `overrides` entry of `mop_on_llm_70`, and `expected_jar_git_sha`/`expected_jar_sha256` Python-only at the top level (INV-APV-34 pairing untouched)
- [ ] 7.3 Restate the single-factor contrast tests to diff effective configurations: reference vs control differs in exactly the five MOP weight keys plus `ape.activityTriggerEnabled`; reference vs LLM arm differs only in `ape.llm*` keys; neither declaration key is in `APERV_PROPERTY_MAPPING`
- [ ] 7.4 Re-run the regeneration diff — empty for every surviving arm
- [ ] 7.5 Run `/rv-test-run aperv-tool`

## 8. Dead key and substrate dict removal

- [ ] 8.1 Delete `mop_weight_activity` from `APERV_PROPERTY_MAPPING`, plus any further dead entry found by the 1.5 sweep; assert the mapping has 50 entries and that `llm_max_tokens` / `llm_snap_tolerance_px` survive
- [ ] 8.2 Delete the substrate spread dicts `_BASELINE_ARM_FLAGS`, `_MOP_SUBSTRATE`, `_LLM_FLAGS`, `_FRONTIER_SUBSTRATE`, `_MOP_OFF_OVERRIDES`, `_CAL_LLM_COMMON` (`_APE_PURE_ARM_FLAGS` went with task 3.2)
- [ ] 8.3 Grep `modules/aperv-tool/src` for `mopWeightActivity` and each deleted constant name — zero hits, no commented-out remnant (P3)
- [ ] 8.4 Re-run the regeneration diff — empty for every surviving arm
- [ ] 8.5 Run `/rv-test-run aperv-tool`

## 9. Guard retirement and documentation

- [ ] 9.1 Delete `ARM_DEFINING_KEYS`, `_ARM_DEFINING_EXEMPT` and `LLM_ARM_KEYS` from `tool.py`; rewrite the module docstring and the `get_variants()` docstring to the preset+overrides contract, current-state only (P4 — no "migrated from", no "replaces")
- [ ] 9.2 Retire the constant-vs-constant guard tests in `tests/test_aperv_tool.py`: `TestArmDefiningGuard`, the INV-APV-14 explicitness and table-pin tests in `TestFrozenArmVariants`, the INV-APV-26/27 tests, the calibration plan-table pins, and the gh90 expansion-diff tests; delete `_EXPECTED_ARM_DEFINING_MAPPING` and companions
- [ ] 9.3 Add `test_retired_guards_are_gone` asserting the three constants no longer exist, so a future revert is caught rather than merged
- [ ] 9.4 Verify by grep that `tool.py` contains no `RUN_START` parsing and no echo-vs-intent logic (INV-APV-43, owner decision D1)
- [ ] 9.5 Update `modules/aperv-tool/CLAUDE.md`: the variant table becomes preset + overrides, the `ape_pure` and `bfs` rows die with the variants, the `LLM_ARM_KEYS` guard paragraph is removed, and the count becomes 27
- [ ] 9.6 Update `modules/aperv-tool/docs/architecture.md` for the preset+overrides arm surface and the reduced properties-generation path
- [ ] 9.7 Run `/rv-test-run aperv-tool`

## 10. Final verification and owner sign-off

- [ ] 10.1 Final full regeneration diff over all 27 surviving arms; produce the human-readable per-arm report — empty, or the owner-approved declared divergences with their new arm names — plus the documented retirements of `ape_pure` and `bfs`
- [ ] 10.2 Run `/rv-qa-lint-fix aperv-tool`. Leave the two pre-existing findings untouched: `tests/test_aperv_tool.py:439` E741 and the `black` reformat around `tests/test_aperv_tool.py:1422`; `tool.py`'s 67 pre-existing E501 are comment prose and are not this change's diff
- [ ] 10.3 Run `/rv-verify aperv-tool`
- [ ] 10.4 Invoke `/rv-code-reviewer` via the Skill tool over the `modules/aperv-tool` diff
- [ ] 10.5 Run `/rv-docs-sync aperv-tool`
- [ ] 10.6 **Owner sign-off**: present the final diff report and the task 1.6 finding. On approval, delete `tests/migration/test_arm_regeneration_diff.py` and archive `arm_effective_baseline.json`, the final diff output and the `ape` source provenance under `modules/aperv-tool/docs/` as the migration record (INV-APV-44 — the check is one-time and MUST NOT become a standing constant-vs-constant guard)
- [ ] 10.7 Mark task 8.5a of the `ape`-side `rearch-05-thin-python-arms` satisfied — this change is the rv-android counterpart it reserved to this repository's OpenSpec workflow
