# Change Plan: Retire `ape_pure_mode` from the aperv-tool arm surface

**Date**: 2026-08-04
**Track**: Quick Path
**Priority**: High
**GitHub Issue**: [#93](https://github.com/PAMunb/rvsec/issues/93)
**PRD Reference**: N/A (experiment-arm configuration; no FR/NFR governs the arm key set)
**Domains**: tools (`modules/aperv-tool`)

## 1. Context

This is the rv-android counterpart of **stage 2 of the APE-RV re-architecture** (`phtcosta/ape`,
change `rearch-02-runspec`, executed in the `ape-rearch` worktree on branch `rearch`). The roadmap
that coordinates both repositories is `ape/docs/plans/20260802_rearchitecture_roadmap.md`; the
finding that produced this change is **AC1** of
`docs/20260803_rearch_artifact_vs_code_verification.md`.

### What changed on the jar side

`rearch-02` classifies `ape.apePureMode` as a **retired key**. The stage-2 jar resolves its
`RunSpec` at bootstrap, *before* touching the device, and aborts the process with
`[APE-RUNSPEC-ABORT] reason=retired_key` whenever a retired key appears in `ape.properties`. The
same spec mandates that the `apePureMode` forcing mechanism "SHALL NOT exist" — purity became
structural (a preset), not a runtime switch that forces other flags off. The mechanism was deleted
in `8a8b880` (`feat(rearch-02): delete the device input channels, the persistence protocol and the
kill-switch`).

### Why that breaks this repository

`rearch-02` was written believing no experiment arm pushes the key. That premise is false, and the
verification confirmed it in the tree: `ape_pure_mode` is a member of `ARM_DEFINING_KEYS`, so
INV-APV-13/14/15 *require* every non-exempt variant to set it explicitly. It sits in
`_BASELINE_ARM_FLAGS`, which **23 of the 29 arms** spread — including all four campaign arms of the
E3 decisive run. `_push_properties()` writes every key present in both the arm dict and
`APERV_PROPERTY_MAPPING`, with no value filter, so `ape.apePureMode=false` reaches the device on
every one of those arms.

Deploying the stage-2 jar against the current `tool.py` therefore aborts every campaign arm before
step 1: coverage 0, MOP violations 0, on every arm, on every APK.

### The decision, and why it is a removal rather than a tolerance

The owner decided on 2026-08-03 (AC1) to **remove the key from the Python side** rather than narrow
the jar's retired-key abort to `true` and admit `false` as an inert value. The reasoning: the same
spec states the forcing mechanism SHALL NOT exist, and keeping a live Python key for a deleted
mechanism is the weaker of the two options — it leaves a property that means nothing, that a future
arm could set to `true` with no effect and no error. The key leaves.

### Ordering is the point of this change

Only one direction is safe, and it is the reason AC1 pulled this edit forward from stage 5 into
stage 2:

- **Python first, old jar still deployed** — `Config.apePureMode` already defaults to `false`
  (`ape/src/main/java/com/android/commands/monkey/ape/utils/Config.java:287`), so for the 23 arms
  that pushed `false` explicitly, the absent key resolves to exactly the same value. Zero
  behavioral delta on every arm; the `ape_pure` arm is the single arm that pushed `true`, and it is
  retired on the jar side by the same stage.
- **Jar first, `tool.py` untouched** — every campaign arm aborts.

So this change lands on `rearch-counterparts` and is **merged into `modules` before the stage-2 jar
reaches any device**. Its merge is early and separate from the final merge of the counterpart line
(roadmap, "Standing constraints").

### What survives the edit

The `ape_pure` **arm survives intact**. `_APE_PURE_ARM_FLAGS` already sets all 17 remaining
arm-defining flags to their off values explicitly, and the comment above it says why: the
original-APE baseline must be auditable from `ape.properties` "without trusting the jar's
`apePureMode` to force RV off" (design D1 of gh74, defense-in-depth). Its purity was already
structural on this side. This change only makes the jar agree — the arm's configuration is
unchanged except that one line no longer appears in its properties file.

## 2. Scope

One module, `modules/aperv-tool`, in three groups:

- **Group A — production code** (`tool.py`): remove the four `ape_pure_mode` sites and correct the
  three comments that count keys or describe the kill-switch.
- **Group B — guard tests** (`tests/test_aperv_tool.py`): the arm-defining count drops from **18 to
  17**; the pinned mapping loses one entry; the three `ape_pure`/`sata` assertions on the key are
  replaced by assertions on what actually defines the arm; one new negative assertion proves no
  campaign arm emits the property.
- **Group C — documentation and spec**: `openspec/specs/aperv/spec.md` (INV-APV-13, the base-variant
  table, two scenarios, the mapping table), plus the two prose documents that state the 18-key count
  or describe `ape_pure` via the kill-switch.

Explicitly **out of scope**:

- `_push_properties()` itself, every other entry of every arm dict, and the `preset + overrides`
  contract — that is stage 5 (`gh95-thin-python-arms`).
- `mop_weight_activity`, the sibling retired key. It is mapped but set by no arm, so the stage-2
  jar does not abort on it; its removal belongs to `gh95` (`rearch-05` task 7.1).
- `modules/rv-agent/src/rv_agent/config/agent_config.py:466`. That comment mentions `apePureMode`
  as an **analogy** for rv-agent's own independent `pure_mode` kill-switch (gh77). It names no
  Python key of this module and no property pushed to any device; rewriting it would be an
  unrelated edit to an unrelated subsystem.

## 3. File Inventory

### Group A — production code

| File | Action | Detail |
|------|--------|--------|
| `modules/aperv-tool/src/aperv_tool/tools/aperv/tool.py` | Edit `:119-120` | Delete the `"ape_pure_mode": "ape.apePureMode",` entry of `APERV_PROPERTY_MAPPING` **and** its preceding comment line `# Kill-switch — arm-defining (rv-scoring-pipeline apePureMode baseline).` — the comment documents only that entry |
| `modules/aperv-tool/src/aperv_tool/tools/aperv/tool.py` | Edit `:175` | Delete `"ape_pure_mode",` from `ARM_DEFINING_KEYS` (18 → 17 members) |
| `modules/aperv-tool/src/aperv_tool/tools/aperv/tool.py` | Edit `:256` | Delete `"ape_pure_mode": False,` from `_BASELINE_ARM_FLAGS` (18 → 17 entries) |
| `modules/aperv-tool/src/aperv_tool/tools/aperv/tool.py` | Edit `:241` | Comment above `_BASELINE_ARM_FLAGS` says "This dict enumerates exactly the 18 ARM_DEFINING_KEYS" → **17** |
| `modules/aperv-tool/src/aperv_tool/tools/aperv/tool.py` | Edit `:263-265` | Comment above `_APE_PURE_ARM_FLAGS`: drop "+ the kill-switch ON" and the clause "without trusting the jar's apePureMode to force RV off"; state the current reason — the arm is off by enumeration, and the jar no longer has a switch to trust. Update "Also 18 keys → guard-clean" → **17** |
| `modules/aperv-tool/src/aperv_tool/tools/aperv/tool.py` | Edit `:280` | Delete `"ape_pure_mode": True,` from `_APE_PURE_ARM_FLAGS` (18 → 17 entries) |
| `modules/aperv-tool/src/aperv_tool/tools/aperv/tool.py` | Edit `:496` | Variant comment `# ape_pure — original APE via the apePureMode kill-switch; every RV flag off.` → describe the arm as original APE by every RV flag being off explicitly, with no kill-switch |

`_push_properties()` (`:1157-1168`) is **not edited**. It writes the intersection of `_tool_config`
and the mapping; once the key is out of both, no arm can emit the property. That is the mechanism
this change relies on, and it is why the removal needs no value filter.

### Group B — guard tests

| File | Action | Detail |
|------|--------|--------|
| `modules/aperv-tool/tests/test_aperv_tool.py` | Edit `:474` | Comment "The 18 arm-defining Python keys" → **17** |
| `modules/aperv-tool/tests/test_aperv_tool.py` | Edit `:480` | Delete `"ape_pure_mode": "ape.apePureMode",` from `_EXPECTED_ARM_DEFINING_MAPPING` |
| `modules/aperv-tool/tests/test_aperv_tool.py` | Edit `:576-578` | Rename `test_arm_defining_keys_count_is_18` → `_is_17`; assert `== 17`; replace the trigger_mop_first note with the reason for this drop (jar retired the key, stage 2) |
| `modules/aperv-tool/tests/test_aperv_tool.py` | Edit `:596` | Comment "pin the 18 python→java names" → **17** |
| `modules/aperv-tool/tests/test_aperv_tool.py` | Add near `:573` | New assertion: `"ape_pure_mode" not in ARM_DEFINING_KEYS` and `not in APERV_PROPERTY_MAPPING` — a retired key must not come back (same defensive shape as the existing `max_idle_timeout_ms` / `activity_trigger_stagnation_step` exclusion tests at `:608`/`:622`) |
| `modules/aperv-tool/tests/test_aperv_tool.py` | Edit `:656-665` | `test_ape_pure_kill_switch_and_offs` → rename to `test_ape_pure_sets_every_flag_off`; drop `assert cfg["ape_pure_mode"] is True`; add `assert "ape_pure_mode" not in cfg` and keep every existing off-value assertion (they are now the whole definition of the arm) |
| `modules/aperv-tool/tests/test_aperv_tool.py` | Edit `:673` | `test_sata_baseline_disables_reach_explicitly`: delete `assert cfg["ape_pure_mode"] is False` |
| `modules/aperv-tool/tests/test_aperv_tool.py` | Edit `:1026-1032` | `test_ape_pure_writes_kill_switch_lowercase` → rename to `test_ape_pure_writes_no_kill_switch`; replace `assert "ape.apePureMode=true" in props` with `assert "ape.apePureMode" not in props`; keep the two off-flag assertions |
| `modules/aperv-tool/tests/test_aperv_tool.py` | Add near `:1032` | New test: `_push_properties` for `sata_mop_widget` emits no `ape.apePureMode` line — the campaign-arm case from the issue, and the one the stage-2 jar aborts on |

The properties-generation harness is `_capture_properties` (`:1000-1016`); both new/edited property
tests use it unchanged.

### Group C — spec and documentation

| File | Action | Detail |
|------|--------|--------|
| `openspec/specs/aperv/spec.md` | Edit `:106-113` | INV-APV-13: remove `ape_pure_mode`→`ape.apePureMode` from the mandated name list (17 pairs remain) |
| `openspec/specs/aperv/spec.md` | Edit `:223` | Baseline-arm prose: remove `ape_pure_mode=false` from the OFF list |
| `openspec/specs/aperv/spec.md` | Edit `:228-234` | Base-variant table: delete the `ape_pure_mode` column; `ape_pure`'s Notes cell becomes "Original APE — every RV flag off/0 explicitly" |
| `openspec/specs/aperv/spec.md` | Edit `:236-238` | `ape_pure` SHALL-clause: drop "SHALL set `ape_pure_mode=true` **and**"; keep the explicit-offs requirement and restate the rationale (the arm is defined by its 17 explicit off values; no kill-switch exists jar-side) |
| `openspec/specs/aperv/spec.md` | Edit `:332-336` | Scenario "ape_pure arm sets the kill-switch and every RV flag off" → retitle to "ape_pure arm sets every RV flag off"; `THEN ape_pure_mode SHALL be True` becomes `THEN ape_pure_mode SHALL NOT be present` |
| `openspec/specs/aperv/spec.md` | Edit `:586` | Mapping table: delete the `ape_pure_mode \| ape.apePureMode \| Kill-switch` row |
| `openspec/specs/aperv/spec.md` | Edit `:623-627` | Scenario "Kill-switch flag appears in properties for ape_pure" → "No kill-switch property is written for ape_pure"; `SHALL contain ape.apePureMode=true` becomes `SHALL NOT contain ape.apePureMode` |
| `modules/aperv-tool/CLAUDE.md` | Edit `:36` | Variant-table Notes for `ape_pure`: "Original APE via `apePureMode` kill-switch (all RV flags off)" → "Original APE — all 17 arm-defining flags off explicitly" |
| `docs/architecture/ape-rv.md` | Edit `:173`, `:214`, `:393`, `:405`, `:626` | The four "18 arm-defining flags" counts → **17**; `:214` drops `ape.apePureMode=false` from the sample properties list; `:405` and `:626` drop the kill-switch clauses describing `ape_pure` |

**On editing the main spec directly**: Quick Path defines no delta-spec artifact, so
`openspec/specs/aperv/spec.md` is edited in place. This is correct here rather than deferred to
archive-time sync: the spec documents *current* behavior, and after Group A the existing text is
false in four places (it mandates a mapping entry that no longer exists and requires a property no
arm writes). The archive therefore runs `--skip-specs` because the spec is already current, not
because it was skipped.

## 4. Execution Order

**A → B → C, strictly sequential.** No subagent dispatch: 4 files, and B's expected values are read
off A's result.

1. **Group A** first. The guard tests fail between A and B — that is the intended signal, and
   `test_arm_defining_keys_count_is_18` failing is the proof the removal reached
   `ARM_DEFINING_KEYS`.
2. **Group B** next, restoring green. The two new assertions (retired key absent from both
   registries; `sata_mop_widget` emits no `ape.apePureMode`) are what lets a reviewer confirm the
   cross-repo hazard is closed without deploying the jar.
3. **Group C** last, once the code is settled and the counts are known to be 17.

**Cross-repo ordering** (outside this change's tasks, but the reason it exists): this change is
merged from `rearch-counterparts` into `modules` **before** the stage-2 jar is deployed to any
device. The roadmap's checkbox for this precondition is in
`ape/docs/plans/20260802_rearchitecture_roadmap.md`, stage 2.

## 5. Acceptance Criteria

- [ ] `ape_pure_mode` is removed from `APERV_PROPERTY_MAPPING`, `ARM_DEFINING_KEYS`,
      `_BASELINE_ARM_FLAGS` and `_APE_PURE_ARM_FLAGS`
- [ ] `grep -rn "ape_pure_mode\|apePureMode" modules/aperv-tool` returns no *live* use — no
      registry entry, no variant value, no property written. The surviving matches are the
      negative assertions added by Group B and their comments, which is what the issue's
      "returns nothing" criterion means once tests must prove the absence
- [ ] `ARM_DEFINING_KEYS` has 17 members; `_BASELINE_ARM_FLAGS` and `_APE_PURE_ARM_FLAGS` each have
      17 entries, matching it exactly
- [ ] INV-APV-13/14/15 guard tests pass at 17 keys; `/rv-test-run aperv-tool` green with
      `--import-mode=importlib -o "addopts="`
- [ ] A test asserts the `_push_properties()` output for `sata_mop_widget` contains no
      `ape.apePureMode` line
- [ ] A test asserts `ape_pure` still resolves to a fully-off configuration, from its 17 explicit
      flags rather than from the removed key
- [ ] A test asserts `ape_pure_mode` is absent from both `ARM_DEFINING_KEYS` and
      `APERV_PROPERTY_MAPPING`, so the key cannot silently return
- [ ] `get_variants()` still returns 29 variants and `sata_mop` is still the same object as
      `sata_mop_widget` (INV-APV-16) — nothing outside the removed key moved
- [ ] `openspec/specs/aperv/spec.md` carries no requirement or scenario referencing
      `ape_pure_mode`/`ape.apePureMode`
- [ ] `docs/architecture/ape-rv.md` and `modules/aperv-tool/CLAUDE.md` state 17 arm-defining flags
      and describe `ape_pure` without the kill-switch
