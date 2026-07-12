<!-- Subagent dispatch hints:
     - Group ordering is BINDING (user decision): all pure_algorithm-mode work (Groups 1-7) before the LLM block (Group 8).
     - Group 1 (Reactivation) must complete first — it makes every later group CI-guarded.
     - Group 2 (ScoringPipeline + kill-switch) must complete before Groups 3-7 (scorers/strategies register flags with the pipeline; config key names freeze here).
     - Groups 3, 4, 5 are largely independent of each other after Group 2 and can be dispatched to parallel subagents (different files); Group 5.5-5.7 (decision_source) touches metrics/exporter.py only.
     - Group 6 (dose launcher) depends on Group 3 (A' predicate, launch policy).
     - Group 7 (variants + calibration) integrates all flags — after Groups 2-6.
     - Group 8 (LLM block) is LAST by decision, after Group 7.
     - Group 9 closes the change — after all other groups.
     - Critical path: 1 -> 2 -> 3 -> 6 -> 7 -> 8 -> 9.
     - Port source for all concept groups: APE-RV branch mop-fairtest (working dir ape-mop-fairtest/), NEVER master.
     - Commits use `refs #77`; final commit uses `closes #77`. No Co-Authored-By. Never start/manage emulators manually — E2E gates go through rv-experiment. -->

## 1. Reactivation (CI + test hygiene)

- [x] 1.1 Re-include rv-agent in the per-module CI loop in `.github/workflows/ci.yml` (at the **rvsec reactor root**, one level above `rv-android/`; the file's per-module loop excludes only `rv-agent` and `rv-agent-validation` — revert the `rv-agent` exclusion from commit `674642a0`), keeping the CI contract `--import-mode=importlib -o "addopts="`. `rvagent-tool` is NOT in the exclusion list — confirm its tests already run green in the loop and fix if red (no exclusion revert needed for it)
- [x] 1.2 Remove the obsolete recovery-mode tests in `modules/rv-agent/tests/performance/test_multimode_proportion.py::TestRecoveryMode` (they reference `recovery_mode_active`/`RECOVERY_FAILURE_THRESHOLD`, deleted from `RoutingManager`); back up removed test code to `backup/` per P3
- [x] 1.3 Mark the 13 SGLang-dependent tests (`tests/smoke/test_sglang_connectivity.py`, `tests/performance/test_llm_latency.py`, `tests/smoke/test_tool_binding.py`) with a server-availability skip condition so the offline suite is green
- [x] 1.4 Confirm `tests/online/` (39 emulator-dependent errors) is excluded from the offline CI selection
- [x] 1.5 Run `uv run pytest modules/rv-agent/tests --import-mode=importlib -o "addopts=" -q` — offline suite must be green
- [x] 1.6 Run `/rv-test-run rvagent-tool`

## 2. ScoringPipeline + pure-arm kill-switch (INV-AGT-42..44)

- [x] 2.1 Add new `RVAgentConfig` fields (Pydantic, defaults off/0, per design API section): `pure_mode`, `mop_frontier_weight`, `mop_activity_source_components`, `trigger_mop_first`, `component_trigger_enabled`, `component_percentage`, `state_mop_density_enabled`, `form_completion_enabled`, `seed`, guard/cap fields — in `modules/rv-agent/src/rv_agent/config/agent_config.py`
- [x] 2.2 Add `Scorer.is_enabled(config) -> bool` to the ABC in `ranking/scorers.py` (default True; steering scorers return their flag)
- [x] 2.3 Create `ranking/pipeline.py` with `ScoringPipeline.from_config(config) -> ActionRanker`: single assembly point, `[RV-ARCH] scorers=[...] flags={...}` startup audit line, RV-steering-flag registry, `ConfigurationError` on unregistered arm-defining flag
- [x] 2.4 Implement `pure_mode` enforcement: force all registered flags off/0 before assembly, log each forced key (INV-AGT-43); replace all ad-hoc scorer instantiation call sites with `ScoringPipeline.from_config` (grep for `ActionRanker(` constructions)
- [x] 2.5 Add unit tests: assembly audit log, kill-switch forcing + logging, registry completeness (new arm-defining field without registration fails), `ConfigurationError` fail-fast
- [x] 2.6 Add pure-arm parity test (INV-AGT-44): golden ranking on cryptoapp fixtures with fixed seed, all flags off ≡ `pure_mode=True` ≡ documented base policy
- [x] 2.7 Run `/rv-doc-code modules/rv-agent/src/rv_agent/strategies/rvagent_strategy/ranking/pipeline.py`
- [x] 2.8 Run `/rv-test-run rv-agent`

## 3. MOP-reach strategies + component triggering (INV-AGT-45..50)

- [x] 3.1 Implement A′ in `services/transition_manager.py`: `activity_has_mop(activity)` sourcing from `StaticAnalysisData.components.activities[].reaches_target` when `mop_activity_source_components=True`, additive to the existing widget/method source (port `MopData.java:385-389` from `ape-mop-fairtest`)
- [x] 3.2 Implement DIALOG→host-activity re-key in `TransitionManager` via WTG edges, applied before any MOP predicate/navigation lookup (INV-AGT-50, port of INV-MOP-25 semantics)
- [x] 3.3 Implement `MopFrontierScorer` in `ranking/scorers.py` (INV-AGT-46): `mop_frontier_weight` added only when target activity `activity_has_mop` AND unvisited in `DynamicStateGraph`; register with the pipeline (port `MopFrontierPass`)
- [x] 3.4 Implement E-mín MOP-first launch-queue ordering in `strategies/rvagent_strategy/rvagent_strategy.py` gated by `trigger_mop_first` (INV-AGT-47, port `SataAgent.selectTriggerCandidate:650-666`)
- [x] 3.5 Create `services/component_trigger.py`: plateau-gated (existing `PlateauDetector`) trigger of MOP-reaching services/receivers via `am start-service`/`am broadcast` through DeviceInterface; activities excluded; `component_percentage` cadence; dispatch-failure denylist (INV-AGT-48; assess E-ext exported-components inclusion here — open question in design.md)
- [x] 3.6 Implement static-data fail-fast at load (INV-AGT-49): structural validation of `classes`/`windows`/`wtg`/`components`, explicit error naming the invalid field; absent data keeps graceful degradation
- [x] 3.7 Add unit tests for 3.1-3.6 using `tests/fixtures/static_analysis/cryptoapp/` fixtures (extend fixture with `components` entries as needed)
- [x] 3.8 Run `/rv-doc-code modules/rv-agent/src/rv_agent/services/component_trigger.py`
- [x] 3.9 Run `/rv-test-run rv-agent`

## 4. Exploration guards and caps (INV-AGT-51)

- [ ] 4.1 Implement pre-ranking candidate filters: foreign-activity guard, foreign-tree guard, BACK/MENU consecutive-pick cap, MOP-target revisit cap (stops MOP boost only, base scorers unaffected)
- [ ] 4.2 Implement node-level policy: idle-timeout cap, dynamic epsilon, per-activity action budget — in the LangGraph `execute`/`validation` nodes (`agent/nodes/`)
- [ ] 4.3 Add per-guard telemetry counters (each rejection counted)
- [ ] 4.4 Add unit tests per guard/cap (foreign escape, BACK cap lift, revisit cap boost-stop, budget deprioritization)
- [ ] 4.5 Run `/rv-test-run rv-agent`

## 5. Fair-test items (INV-AGT-52..53 + scorers C/D/F)

- [ ] 5.1 Thread deterministic `seed` through all stochastic choices (stochastic mode draw, Gumbel-max, epsilon, tie-breaks) (INV-AGT-53, fair-test A)
- [ ] 5.2 Implement `StateMopDensityScorer` (fair-test C): density over MOP-flagged widgets only; register with pipeline
- [ ] 5.3 Implement `FormCompletionScorer` (fair-test D): convergent filled-form predicate over real widget text; submit excluded from boost until converged; register with pipeline
- [ ] 5.4 Implement typed input generation in `strategies/rvagent_strategy/input_value_generator.py` (fair-test F): containment ±2 levels, token-based keyword matching, WebView thresholds over actionable nodes only, per-step artifact caps
- [ ] 5.5 Add `decision_source` attribution (fair-test E): exactly one value per executed decision, taxonomy and precedence (MOP > WTG > Menu > Form > Coverage; plus `component_trigger`, `llm`, `base`) identical to the aperv `.trace`; wire through `metrics/exporter.py` and the per-step trace CSV
- [ ] 5.6 Add per-step timing (`clock=`) to the trace
- [ ] 5.7 Add unit tests: seed reproducibility (same fixture+seed ⇒ same sequence), density counting, form convergence, typed input, attribution precedence, pure-arm attribution = `base`
- [ ] 5.8 Wire `ComponentTriggerService` into the exploration loop (delivered as a unit in 3.5 but not yet instantiated or called — INV-AGT-48 is unit-verified but never exercised at runtime): instantiate it in `AgentFactory`/strategy and call `maybe_trigger(...)` gated on `PlateauDetector.is_plateau_reached()` in the `execute`/`learn` node; when it returns non-None (a dispatch happened) set `decision_source='component_trigger'` (match 5.5) and feed `PlateauDetector.record_iteration` as progress so a successful trigger resets stagnation. Include an E2E `am`-dispatch smoke gate via rv-experiment — a unit test with a mocked `DeviceInterface` does NOT catch the real `am start-service` background-start restriction on API ≥ 26/30
- [ ] 5.9 Run `/rv-test-run rv-agent`

## 6. Launcher with dose/denylist

- [ ] 6.1 Extend the launch policy in `rvagent_strategy.py`: configurable launch cadence, per-run launch cap (dose), failed-launch denylist (never re-launch in-run) — port of `mop-activity-consumers`/`activity-trigger-dose`/`mop-census-launcher` from `ape-mop-fairtest`
- [ ] 6.2 Add unit tests: denylist entry on failure, cap enforcement, cadence
- [ ] 6.3 Run `/rv-verify rv-agent`

## 7. rvagent-tool variants policy + calibration (INV-RVA-01..06)

- [ ] 7.1 Rework `RVAgentTool.get_variants()` (`modules/rvagent-tool/src/rvagent_tool/tools/rvagent/tool.py`): frozen variants set ALL arm-defining keys explicitly; `pure_algorithm` sets `pure_mode=True`; `llm_only`/`multimode` set all gh77 steering flags explicitly off; L2 pattern (defaults in variants, no `os.environ`)
- [ ] 7.2 Complete the variant→`RVAgentConfig` mapping for every arm-defining key (including `seed` pass-through and `@param=value` overrides)
- [ ] 7.3 Implement teardown-in-`finally` in the tool execute path (INV-RVA-05) and static-data fail-fast at configure (before any device time)
- [ ] 7.4 Add guard pytest replicating the aperv-tool pattern (`modules/aperv-tool/tests/test_aperv_tool.py`): every variant sets every arm-defining key; every arm-defining key has a mapping entry; LLM/steering isolation; no LLM call-limit keys
- [ ] 7.5 Run `/rv-test-run rvagent-tool`
- [ ] 7.6 E2E gate (pure arm): `uv run rv-experiment run --tools rvagent:pure_algorithm --apks-dir ./apks_examples --timeouts 60` — completes with trace containing only `decision_source=base`, `[RV-ARCH]` audit line present, teardown clean
- [ ] 7.7 Local calibration smoke for `mop_frontier_weight` × `frontier_boost_weight` interaction (cryptoapp, both weights on): record chosen weights in design.md; freeze any additional steering arms (arm-neutral names) based on the result — MANDATORY before any comparison with aperv
  - MOP census gate (E-ext reopening condition): during this calibration, measure the fraction of `apks_examples/` APKs with ≥1 MOP-reaching (`reaches_target=True`) service/receiver. E-ext (exported non-MOP components) was deliberately kept OUT — the port is a faithful census-only reading of aperv ("Exported status is NOT consulted"). If the census is too sparse (the component trigger almost never fires), reopen E-ext as its OWN `arm_defining` flag (e.g. `component_trigger_exported`), NEVER folded under `component_trigger_enabled` — a shared gate would contaminate the arm. Reopening is conditional on this empirical result, not assumed.
- [ ] 7.8 Run `/rv-verify rvagent-tool`

## 8. LLM mode block (LAST by decision)

- [ ] 8.1 Revalidate SGLang default URL/model (`http://192.168.0.36:30000/v1`, Qwen3-VL-4B) and hybrid tool calling (native `bind_tools` + XML fallback via `rv_agent/llm/tools/tool_call_parser.py`) against the SGLang version pinned by APE-RV (v0.5.6.post2)
- [ ] 8.2 Revalidate `llm_only` and `multimode` variants end-to-end (routing proportions, prompt v13/v17 selection); confirm LLM arms remain isolated from steering flags (INV-RVA-04) and no artificial call limits exist
- [ ] 8.3 Add LLM observability: screenshot-failure counters in routing telemetry; `decision_source="llm"` attribution for LLM-decided actions
- [ ] 8.4 Add/adapt tests (skip-conditioned on SGLang availability, offline-green per Group 1)
- [ ] 8.5 E2E gate (LLM arm, local): `uv run rv-experiment run --tools rvagent:multimode --apks-dir ./apks_examples --timeouts 60` with SGLang up
- [ ] 8.6 Run `/rv-test-run rv-agent`

## 9. Close-out & verification

- [ ] 9.1 Revert DEPRECATED status: update rv-android `CLAUDE.md` module map, `modules/rv-agent/CLAUDE.md`, `modules/rvagent-tool/CLAUDE.md` and any docs stating rv-agent is deprecated (project memory updated at archive time)
- [ ] 9.2 Full offline suites green: `uv run pytest modules/rv-agent/tests --import-mode=importlib -o "addopts=" -q` and same for `modules/rvagent-tool/tests`
- [ ] 9.3 Final E2E gate + side-by-side smoke with `aperv` on cryptoapp (local, via rv-experiment; platform manages emulator) — compare `decision_source` taxonomies row-compatibility
- [ ] 9.4 Run `/rv-qa-lint-fix rv-agent` and `/rv-qa-lint-fix rvagent-tool`
- [ ] 9.5 Run `/rv-verify rv-agent`
- [ ] 9.6 Invoke `/rv-code-reviewer` via Skill tool ("Review gh77-revive-rvagent implementation")
- [ ] 9.7 Run `/rv-docs-sync rv-agent` (CLAUDE.md/architecture docs)
- [ ] 9.8 `openspec validate gh77-revive-rvagent --strict`; verify acceptance criteria on issue #77 and check off satisfied boxes
