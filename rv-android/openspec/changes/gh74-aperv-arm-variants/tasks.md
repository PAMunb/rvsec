<!-- Scope: Python only, one module (modules/aperv-tool). ~2 files (tool.py + test_aperv_tool.py).
     Well below 20 files → no subagent orchestration. Critical path: 1 (constants+mapping) →
     2 (variants) → 3 (seed) → 4 (guard tests) → 5 (seed investigation writeup) → 6 (Verification).
     Refs: proposal.md, specs/aperv/spec.md (INV-APV-13..19), design.md (D1-D6, R1). GitHub #74. -->

## 1. Mapping + arm-defining constants (tool.py) — INV-APV-13, INV-APV-15

- [x] 1.1 Add module-level `ARM_DEFINING_KEYS` (a `frozenset`) to `modules/aperv-tool/src/aperv_tool/tools/aperv/tool.py` enumerating the 19 arm-defining Python keys: `ape_pure_mode`, `frontier_boost_weight`, `activity_trigger_enabled`, `back_menu_pick_cap`, `foreign_activity_guard`, `tree_package_guard`, `dynamic_epsilon`, `heuristic_input`, `fuzz_input_typed`, `form_completion_enabled`, `step_telemetry_enabled`, `model_menu_enabled`, `least_visited_priority_tiebreak`, `tree_enhancements_enabled`, `activity_budget_enabled`, `mop_activity_source_components`, `mop_frontier_weight`, `trigger_mop_first`, `llm_percentage_no_substrate`. Do NOT include `mop_data`, `strategy`, or the `mop_weight_*` keys (design D2)
- [x] 1.2 Add module-level `_ARM_DEFINING_EXEMPT` (a `frozenset`) naming exactly the six gh43 variants: `sata_mop_llm_ape_current`, `sata_mop_llm_ape_reasoning`, `sata_mop_llm_compact_v1`, `sata_mop_llm_v13`, `sata_mop_llm_v17`, `sata_mop_llm_visual_only` (INV-APV-17; explicit set, not a prefix)
- [x] 1.3 Extend `APERV_PROPERTY_MAPPING` with all 19 arm-defining entries using the frozen `ape.*` names from spec INV-APV-13 (8 existing-unmapped RV flags + `ape_pure_mode` + the 10 reach/telemetry/tree flags) plus `mop_weight_open_menu`/`mop_weight_wtg` if not already present. Keep the inert `mop_weight_activity` back-compat note intact
- [x] 1.4 Add the **arm-neutral** entry `max_idle_timeout_ms` → `ape.maxIdleTimeoutMs` to `APERV_PROPERTY_MAPPING` — and DO NOT add it to `ARM_DEFINING_KEYS` (it applies identically to every arm; like the `mop_weight_*` keys it is mapped-but-not-arm-defining, exempt from INV-APV-14 per-variant explicitness). Rationale: the archived `idle-timeout-cap` change is a byte-identical refactor at the default ceiling (10000ms) whose effect only appears when the ceiling is lowered; that lowered value was never pushed (the mapping omitted the key), which made the cmpft3 idle-timeout smoke non-testable. This entry lets an experiment set e.g. `max_idle_timeout_ms=2000` globally to validate the idle-drain reduction on animated apps.
- [x] 1.5 Run `/rv-test-run aperv-tool` (existing suite green before touching variants) — 47 passed (41 + 6 new group-1 guards)

## 2. Frozen arm variants (tool.py get_variants) — Variants requirement, INV-APV-14, INV-APV-16

- [x] 2.1 Add a shared `_BASELINE_ARM_FLAGS` dict (RV exploration ON at current jar defaults made explicit: `back_menu_pick_cap=3`, `foreign_activity_guard=True`, `tree_package_guard=True`, `dynamic_epsilon=True`, `heuristic_input=True`, `fuzz_input_typed=True`, `form_completion_enabled=True`, `step_telemetry_enabled=True`, `model_menu_enabled=True`, `least_visited_priority_tiebreak=True`, `tree_enhancements_enabled=True`, `activity_budget_enabled=True`, `llm_percentage_no_substrate=-1`; MOP/reach/frontier/trigger OFF: `ape_pure_mode=False`, `frontier_boost_weight=0`, `activity_trigger_enabled=False`, `mop_activity_source_components=False`, `mop_frontier_weight=0`, `trigger_mop_first=False`) and a `_MOP_SUBSTRATE` dict (`mop_data="static_analysis"`, `mop_weight_direct=500`, `mop_weight_transitive=300`, `mop_weight_open_menu=250`, `mop_weight_wtg=200`). Spread these into variants to avoid copy-paste drift (design D-Architecture, P1)
- [x] 2.2 Make `default`, `sata`, `bfs`, `random`, `sata_llm`, `sata_mop_llm` explicit by spreading `_BASELINE_ARM_FLAGS` (and `_MOP_SUBSTRATE` for the `_mop_` ones) — preserving today's `strategy`/`throttle_ms`/LLM values (P4 current-state; behavior unchanged, only made explicit)
- [x] 2.3 Add `ape_pure`: `strategy="sata"`, `throttle_ms=200`, `ape_pure_mode=True`, and every other `ARM_DEFINING_KEYS` member set to its off/zero value explicitly (all RV flags False, weights/frontier 0); no `mop_data` (design D1)
- [x] 2.4 Add `sata_mop_widget` = `{**_BASELINE_ARM_FLAGS, **_MOP_SUBSTRATE, "strategy":"sata", "throttle_ms":200}` (widget mechanism; frontier/reach/trigger stay off from baseline). Bind `sata_mop` to the **same object** so `variants["sata_mop"] is variants["sata_mop_widget"]`-equal (INV-APV-16, design D4)
- [x] 2.5 Add `sata_mop_activity` = `sata_mop_widget` overridden with `mop_activity_source_components=True` (isolates A′)
- [x] 2.6 Add `sata_mop_act_frontier` = `sata_mop_activity` overridden with `frontier_boost_weight=200`, `mop_frontier_weight=200`, `activity_trigger_enabled=True`, `trigger_mop_first=True` (reach package A′+B+E-min)
- [x] 2.7 Update the `get_variants()` docstring + INV-APV-05 reference (now 11 non-exempt + 6 exempt variants; `default`→`sata`; `sata_mop`→alias)

## 3. Seed propagation (tool.py _build_main_command) — INV-APV-18

- [x] 3.1 In `_build_main_command`, after the `--ape <strategy>` args, append `["-s", str(seed)]` when `seed = self._tool_config.get("seed")` is not None. Leave the command unchanged when no seed is configured (design D6; jar honors `-s` per Monkey.java:886-887 + RandomHelper.seed, INV-EXPL-14). `seed` has no `APERV_PROPERTY_MAPPING` entry so it is never written to `ape.properties`

## 4. Guard + arm tests (tests/test_aperv_tool.py) — INV-APV-13, INV-APV-14, INV-APV-16, INV-APV-17, INV-APV-18

- [x] 4.1 `test_all_arm_defining_keys_are_mapped`: every key in `ARM_DEFINING_KEYS` ∈ `APERV_PROPERTY_MAPPING` (INV-APV-13) — pulled forward as group-1 RED test
- [x] 4.2 `test_non_exempt_variants_set_all_arm_defining_keys`: for every variant not in `_ARM_DEFINING_EXEMPT`, assert `ARM_DEFINING_KEYS <= set(variant)`; failure message names the variant + missing keys (INV-APV-14)
- [x] 4.3 `test_arm_defining_keys_excludes_mop_data_and_strategy` + `test_exempt_set_is_exactly_the_six_gh43_variants` (INV-APV-15, INV-APV-17) — pulled forward as group-1 RED tests (excludes weights + max_idle_timeout too)
- [x] 4.4 `test_sata_mop_is_alias_of_widget`: `variants["sata_mop"] == variants["sata_mop_widget"]` (INV-APV-16)
- [x] 4.5 Per-arm value tests: `ape_pure` (kill-switch true + RV offs), `sata` (frontier 0 / trigger false, no mop_data), `sata_mop_widget` (weights + reach off), `sata_mop_activity` (only A′ differs from widget), `sata_mop_act_frontier` (frontier 200 / mop_frontier 200 / trigger true)
- [x] 4.6 Properties tests (extend the existing `_push_properties` capture harness): `sata` writes `ape.frontierBoostWeight=0` + `ape.activityTriggerEnabled=false`; `ape_pure` writes `ape.apePureMode=true`; `sata_mop_act_frontier` writes `ape.mopFrontierWeight=200` + `ape.triggerMopFirst=true`; `seed` never appears in properties
- [x] 4.7 Command tests: `test_seed_passed_as_dash_s` (`_tool_config` has `seed=42` → `-s 42` after `--ape`), `test_no_seed_omits_dash_s` (INV-APV-18)
- [x] 4.8 Run `/rv-test-run aperv-tool` — 61 passed (0 fail)

## 5. Seed investigation writeup (documentation) — issue #74 point 3

- [x] 5.1 Record the investigation finding (design D6, already captured): the `mop-fairtest` jar **honors** a passed seed (`Monkey.java:886-887` parses `-s SEED`; `Monkey.java:731` seeds `RandomHelper`, INV-EXPL-14) — the defect was rv-android-side (`_build_main_command` never emitted `-s`), closed by task 3.1. No APE-RV-repo issue is needed (the jar is correct); tick issue #74's seed-verification criterion. **Verified @2f95711**: parse at Monkey.java:886-887 (not 881-882 — citation drift corrected), RandomHelper.seed at :731, new Random(mSeed) at :697. Writeup: docs/20260708_gh74_seed_investigation.md
- [x] 5.2 [N/A — jar verified correct @2f95711, no divergence] If, at R1 cross-check (task 6.4), the built jar's `Config`/`Monkey` diverges from this finding (e.g. `-s` not parsed, or `RandomHelper` not seeded), THEN open an issue in the APE-RV repo and reference it here — otherwise mark N/A

## 6. Verification

- [x] 6.1 Lint (black+isort clean on both changed files; flake8 E501 is pervasive pre-existing repo style, not gated — not chased per P1/P3). `/rv-qa-lint-fix` skill skipped per user; ran tools directly
- [x] 6.2 Verify — 61 pytest green (0 fail), black+isort clean. `/rv-verify` skill skipped per user; ran pytest+formatters directly
- [x] 6.3 `openspec validate gh74-aperv-arm-variants --strict` — valid
- [x] 6.4 R1 cross-check DONE (no device): all 20 ape.* names (19 arm-defining + maxIdleTimeoutMs) exist verbatim in mop-fairtest Config.java @2f95711 — no inert-property risk. Gate before experiment: PASS. R1 cross-check (design R1/D5) — once the APE-RV `rv-scoring-pipeline`/`mop-reach-strategies` jar is built, grep its `Config.java` for the 11 new `ape.*` names and confirm they match INV-APV-13 verbatim (a mismatch makes the property inert). Gate before the paired experiment; non-blocking for archive
- [ ] 6.4b [DEFERRED — needs emulator; do at cmpft4 smoke gate before launch] MOP-substrate provenance gate (R4) — confirm the experiment jar includes the `mop-reach-strategies` substrate fix (commit `40cc2f9`+), NOT a pre-fix `mop-fairtest` jar. Cheap runtime check: a `sata_mop` smoke on `cryptoapp` MUST emit the load line with the FIX-3 fields `handlersUnmatched=… syntheticLambda=… recovered=…` AND at least one `[APE-STEP] … decision_source=MOP mop>0`. A jar without the fix emits neither (MOP inert, `mop=0` everywhere → the arm silently degenerates to `sata`, invalidating every `sata_mop_*` contrast). Gate before the paired experiment; non-blocking for archive
- [ ] 6.5 [SKIPPED per user — rv-android skills not run this session] Invoke `/rv-code-reviewer` via the Skill tool: "Review gh74 aperv arm variants (mapping completeness + frozen arms + seed wiring + guard tests)"
- [x] 6.6 Run `/opsx:verify` — PASS (see report): 27/30 tasks done, 3 remaining are device-deferred (6.4b) / skipped-per-user (6.5); all 7 invariants INV-APV-13..19 implemented + covered by 61 green tests; no CRITICAL issues

### Acceptance criteria

- `ARM_DEFINING_KEYS` (19 keys) exists; every member is in `APERV_PROPERTY_MAPPING` (guard 4.1 green).
- Every non-exempt variant sets every arm-defining key explicitly (guard 4.2 green); the six gh43 variants
  are exempt via the named constant.
- `ape_pure`, `sata_mop_widget`, `sata_mop_activity`, `sata_mop_act_frontier` exist with the design §4
  matrix values; `sata_mop` equals `sata_mop_widget`.
- A configured seed reaches the jar as `-s <seed>` and never appears in `ape.properties`.
- `openspec validate --strict` passes; full `aperv-tool` pytest suite green.
