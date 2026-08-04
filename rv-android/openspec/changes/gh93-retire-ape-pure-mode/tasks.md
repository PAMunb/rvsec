<!-- Sequential: Group 1 → Group 2 → Group 3 → Group 4. Four files, no subagent dispatch.
     Group 2's expected values are read off Group 1's result; Group 3's counts depend on both.
     The guard tests are expected to FAIL between Group 1 and Group 2 — that is the signal. -->

## 1. Remove the key from the arm surface (`tool.py`)

- [x] 1.1 Delete the `"ape_pure_mode": "ape.apePureMode",` entry of `APERV_PROPERTY_MAPPING` (`:120`) together with its preceding comment `# Kill-switch — arm-defining (rv-scoring-pipeline apePureMode baseline).` (`:119`), which documents only that entry
- [x] 1.2 Delete `"ape_pure_mode",` from `ARM_DEFINING_KEYS` (`:175`) — 18 → 17 members
- [x] 1.3 Delete `"ape_pure_mode": False,` from `_BASELINE_ARM_FLAGS` (`:256`) and correct the comment above the dict (`:241`) from "exactly the 18 ARM_DEFINING_KEYS" to 17
- [x] 1.4 Delete `"ape_pure_mode": True,` from `_APE_PURE_ARM_FLAGS` (`:280`) and rewrite the comment above it (`:263-265`): drop "+ the kill-switch ON" and "without trusting the jar's apePureMode to force RV off"; state the current reason — the arm is off by enumeration of its 17 flags, and no kill-switch exists jar-side to trust. Update "Also 18 keys → guard-clean" to 17
- [x] 1.5 Rewrite the `ape_pure` variant comment (`:496`) to describe the arm as original APE by every RV flag being off explicitly, with no kill-switch
- [x] 1.6 Confirm `_push_properties()` (`:1157-1168`) is untouched — it writes the intersection of `_tool_config` and the mapping, so removing the key from both is the whole mechanism; no value filter is added

## 2. Update the guard tests (`tests/test_aperv_tool.py`)

- [x] 2.1 Delete `"ape_pure_mode": "ape.apePureMode",` from `_EXPECTED_ARM_DEFINING_MAPPING` (`:480`) and correct the comment above it (`:474`) to 17 keys
- [x] 2.2 Rename `test_arm_defining_keys_count_is_18` → `test_arm_defining_keys_count_is_17` and assert `== 17` (`:576-578`); replace the trigger_mop_first note with the reason for this drop — the stage-2 APE-RV jar retired `ape.apePureMode`, so the key left the Python arm surface (issue #93)
- [x] 2.3 Correct the "pin the 18 python→java names" comment (`:596`) to 17
- [x] 2.4 Add a retired-key exclusion test near `:573`: `"ape_pure_mode"` is absent from both `ARM_DEFINING_KEYS` and `APERV_PROPERTY_MAPPING`, so the key cannot silently return (same defensive shape as the `max_idle_timeout_ms` test at `:608`)
- [x] 2.5 Rename `test_ape_pure_kill_switch_and_offs` → `test_ape_pure_sets_every_flag_off` (`:656-665`): drop `assert cfg["ape_pure_mode"] is True`, add `assert "ape_pure_mode" not in cfg`, keep every existing off-value assertion — they are now the whole definition of the arm
- [x] 2.6 Delete `assert cfg["ape_pure_mode"] is False` from `test_sata_baseline_disables_reach_explicitly` (`:673`)
- [x] 2.7 Rename `test_ape_pure_writes_kill_switch_lowercase` → `test_ape_pure_writes_no_kill_switch` (`:1026-1032`): replace `assert "ape.apePureMode=true" in props` with `assert "ape.apePureMode" not in props`, keeping the two off-flag assertions
- [x] 2.8 Add a properties test for `sata_mop_widget` via the `_capture_properties` harness (`:1000-1016`): the generated file contains no `ape.apePureMode` line — the campaign-arm case the stage-2 jar aborts on
- [x] 2.9 Run `/rv-test-run aperv-tool`

## 3. Sync the spec and the documentation

- [x] 3.1 `openspec/specs/aperv/spec.md` INV-APV-13 (`:106-113`): remove `ape_pure_mode`→`ape.apePureMode` from the mandated name list, leaving 17 pairs
- [x] 3.2 `openspec/specs/aperv/spec.md` baseline prose (`:223`): remove `ape_pure_mode=false` from the OFF list
- [x] 3.3 `openspec/specs/aperv/spec.md` base-variant table (`:228-234`): delete the `ape_pure_mode` column; `ape_pure`'s Notes cell becomes "Original APE — every RV flag off/0 explicitly"
- [x] 3.4 `openspec/specs/aperv/spec.md` `ape_pure` SHALL-clause (`:236-238`): drop "SHALL set `ape_pure_mode=true` **and**"; keep the explicit-offs requirement and restate its rationale — the arm is defined by its 17 explicit off values, and no kill-switch exists jar-side
- [x] 3.5 `openspec/specs/aperv/spec.md` scenario (`:332-336`): retitle to "ape_pure arm sets every RV flag off"; `THEN ape_pure_mode SHALL be True` becomes `SHALL NOT be present`
- [x] 3.6 `openspec/specs/aperv/spec.md` mapping table (`:586`): delete the `ape_pure_mode | ape.apePureMode | Kill-switch` row
- [x] 3.7 `openspec/specs/aperv/spec.md` properties scenario (`:623-627`): retitle to "No kill-switch property is written for ape_pure"; `SHALL contain ape.apePureMode=true` becomes `SHALL NOT contain ape.apePureMode`
- [x] 3.8 `modules/aperv-tool/CLAUDE.md` (`:36`): `ape_pure` Notes → "Original APE — all 17 arm-defining flags off explicitly"
- [x] 3.9 `docs/architecture/ape-rv.md`: correct the arm-defining counts at `:173` and `:393` to 17, drop `ape.apePureMode=false` from the sample properties list at `:214`, and drop the kill-switch clauses describing `ape_pure` at `:405` and `:626`

## 4. Verification

- [x] 4.1 Run `/rv-qa-lint-fix aperv-tool`
- [x] 4.2 Run `/rv-verify aperv-tool`
- [x] 4.3 `grep -rn "ape_pure_mode\|apePureMode" modules/aperv-tool` returns only the Group 2 negative assertions and their comments — no registry entry, no variant value, no property written
- [x] 4.4 Assert the three registries agree: `len(ARM_DEFINING_KEYS) == 17`, and `_BASELINE_ARM_FLAGS` / `_APE_PURE_ARM_FLAGS` each have exactly those 17 keys
- [x] 4.5 Confirm nothing outside the removed key moved: `get_variants()` still returns 29 variants and `sata_mop` is still the same object as `sata_mop_widget` (INV-APV-16)
- [x] 4.6 Verify acceptance criteria from plan.md §5
