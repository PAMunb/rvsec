<!-- Scope: ~8 files in modules/aperv-tool (tool.py, tests/test_aperv_tool.py, three new
     tests/migration/ files, CLAUDE.md, docs/architecture.md). Below the 20-file threshold for
     subagent orchestration — a single session per group is the right granularity.

     Ordering is dependency order and is load-bearing, not cosmetic:
       - Group 1 captures the baseline from the UNMODIFIED tool.py. No arm may be edited before it.
       - Group 2 changes the mechanism; groups 3-4 change the arms it serves.
       - Groups 3-5 each END with the regeneration diff. A group is not done until its diff is empty.
       - Group 6 deletes the guards only after every arm has migrated.
     Critical path: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7.

     This change is OFFLINE. No task starts an emulator, runs adb, or executes the jar. The run that
     proves the deployed jar honours ape.preset belongs to gh97-rearch-ab-gate (owner decision,
     2026-08-04). The ape-side counterpart's group 10 (deleting stage 2's transitional test
     scaffolding) is work in the ape repository and is not part of this change. -->

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

- [ ] 7.1 Final full regeneration diff over all 8 surviving arms; produce the human-readable per-arm report — empty, or the owner-approved declared divergences with their new arm names — plus the documented retirements of `ape_pure` and `bfs`
- [ ] 7.2 Run `/rv-qa-lint-fix aperv-tool`. Leave the two pre-existing findings untouched: `tests/test_aperv_tool.py:439` E741 and the `black` reformat around `tests/test_aperv_tool.py:1422`; `tool.py`'s 67 pre-existing E501 are comment prose and are not this change's diff
- [ ] 7.3 Run `/rv-verify aperv-tool`
- [ ] 7.4 Invoke `/rv-code-reviewer` via the Skill tool over the `modules/aperv-tool` diff
- [ ] 7.5 Run `/rv-docs-sync aperv-tool`
- [ ] 7.6 **Owner sign-off**: present the final diff report and the task 1.6 finding. On approval, delete `tests/migration/test_arm_regeneration_diff.py` and archive `arm_effective_baseline.json`, the final diff output and the `ape` source provenance under `modules/aperv-tool/docs/` as the migration record (INV-APV-44 — the check is one-time and MUST NOT become a standing constant-vs-constant guard)
- [ ] 7.7 Mark task 8.5a of the `ape`-side `rearch-05-thin-python-arms` satisfied — this change is the rv-android counterpart it reserved to this repository's OpenSpec workflow
