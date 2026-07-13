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

- [x] 4.1 Implement pre-ranking candidate filters: foreign-activity guard, foreign-tree guard, BACK/MENU consecutive-pick cap, MOP-target revisit cap (stops MOP boost only, base scorers unaffected)
- [x] 4.2 Implement node-level policy: idle-timeout cap, dynamic epsilon, per-activity action budget — in the LangGraph `execute`/`validation` nodes (`agent/nodes/`)
  - Delivered as `agent/nodes/exploration_policy.py::NodeExplorationPolicy`, applied from `learn_node` (Phase 4b, gated per flag). Ported APE-RV formulas: epsilon `0.02 + 0.13·coverage_gap`, budget `50 + 5·widgets` (frozen, no reset), idle bounded wait → escape. `learn_node` (post-execution) is the node seam that carries the required state (hashes, activity, coverage); `execute`/`validation` are per-action pass-throughs without it.
- [x] 4.3 Add per-guard telemetry counters (each rejection counted)
- [x] 4.4 Add unit tests per guard/cap (foreign escape, BACK cap lift, revisit cap boost-stop, budget deprioritization)
  - `tests/unit/test_gh77_guards_caps.py` (21 tests). NOTE: the BACK/MENU cap is implemented with the delta-spec's **consecutive + lift** semantics (INV-AGT-51 scenario), which diverges from APE-RV's monotonic-per-activity `backMenuPicks` (never lifts) — the spec is the binding contract for rv-agent.
- [x] 4.5 Run `/rv-test-run rv-agent`
  - Full offline suite green: 1841 passed, 76 skipped. Pure-arm parity green (byte-identical with all guards off). rvagent-tool regression: 19 passed.

## 5. Fair-test items (INV-AGT-52..53 + scorers C/D/F)

- [x] 5.1 Thread deterministic `seed` through all stochastic choices (stochastic mode draw, Gumbel-max, epsilon, tie-breaks) (INV-AGT-53, fair-test A)
  - One seeded `random.Random(config.seed)` owned by `RVAgentStrategy` (`self._rng`), threaded into `ActionRanker` via `ScoringPipeline.from_config(config, rng=...)`. Consumed at the two rvagent stochastic sites: the mode draw (`_select_priority_action`) and Gumbel-max (`ActionRanker.select_stochastic`). Replaced global `random.seed`. `rank()`/tie-breaks are already deterministic (stable sort), so no extra RNG there. Epsilon (dynamic_epsilon in NodeExplorationPolicy) adjusts `stochastic_probability` deterministically — the draw it feeds is the seeded mode draw. `seed=None` → unseeded Random (non-reproducible, base behavior).
- [x] 5.2 Implement `StateMopDensityScorer` (fair-test C): density over MOP-flagged widgets only; register with pipeline
  - `scorers.py::StateMopDensityScorer`, gated by `state_mop_density_enabled`, registered in `pipeline.py` candidates. density = flagged/total over current screen items (widget flagged iff any action `reaches_target`/`directly_reaches_target`). Diverges from APE-RV raw `1+count` → rv-agent spec ratio (INV-MOP-24 scenario 4/10=0.4). Per-state scalar (weight*density) applied to all candidates; `DEFAULT_WEIGHT=100`, calibrated in 7.7.
- [x] 5.3 Implement `FormCompletionScorer` (fair-test D): convergent filled-form predicate over real widget text; submit excluded from boost until converged; register with pipeline
  - `scorers.py::FormCompletionScorer`, gated by `form_completion_enabled`, registered. FILL_WEIGHT=150 to empty EditText actions; submit (label matches submit-word) gets 0 while `_has_unfilled` (any on-screen EditText with empty `view["text"]`), SUBMIT_WEIGHT=100 once converged. Convergence over real widget text (port of `FormCompletion.hasUnfilledEditText`).
- [x] 5.4 Implement typed input generation in `strategies/rvagent_strategy/input_value_generator.py` (fair-test F): containment ±2 levels, token-based keyword matching, WebView thresholds over actionable nodes only, per-step artifact caps
  - `input_value_generator.py::infer_input_type(target_view, nearby_labels)` + `tokenize()`: token-based matching (camelCase + separator split → token set; keyword matches only whole tokens, subset for multi-token keywords) — fixes substring false-positives (`account_number`→number not via "count"; `telephone`→text). Own attrs first, then nearby labels (INV-MOP-23 own-id-first). `_INPUT_TYPE_PATTERNS` moved out of rvagent_strategy (P3). Containment ±2 realized as spatial proximity: `_nearby_labels`/`_widget_center` gather nearest on-screen label texts (radius 400px, ≤2), threaded via `_prepare_input_action(screen_desc)`. Note: WebView actionability thresholds (rv-screen-parser tree builder, INV-TREE-11) and per-step artifact caps are OUT of `input_value_generator.py` scope — Java item F.4 (artifact cap) not present as a named constant per Explore; kept to the two in-scope sub-features (tokens + containment).
- [x] 5.5 Add `decision_source` attribution (fair-test E): exactly one value per executed decision, taxonomy and precedence (MOP > WTG > Menu > Form > Coverage; plus `component_trigger`, `llm`, `base`) identical to the aperv `.trace`; wire through `metrics/exporter.py` and the per-step trace CSV
  - New `metrics/step_trace.py`: `attribute_decision_source(action, context, scorers, override)` (pure precedence; `mop←MopScorer`, `wtg←MopFrontier/WtgScorer` (frontier folds into wtgBoost in aperv), `form←FormCompletion`, `coverage←CoverageDensity`; `StateMopDensity` excluded as flat/non-discriminative; `menu` reserved for row-compat; `base` fallback) + `scorer_boosts` + `StepTraceWriter` (lazy CSV, per-row flush). Taxonomy lowercased vs aperv enum (`base`=SATA, `component_trigger`=Component) per rv-agent spec scenarios. Wired at `_select_priority_action` (sets `last_decision_source`, writes row); agent creates the writer from `metrics_output_dir` as `*.trace.csv` (companion to RVTRACK `.trace`) and closes it. `llm` override deferred to Group 8 (task 8.3); `component_trigger` set in 5.8.
- [x] 5.6 Add per-step timing (`clock=`) to the trace
  - `clock_ms` column = `int((monotonic - _trace_start)*1000)`; `_trace_start` reset in `enable_step_trace`.
- [x] 5.7 Add unit tests: seed reproducibility (same fixture+seed ⇒ same sequence), density counting, form convergence, typed input, attribution precedence, pure-arm attribution = `base`
  - `tests/unit/test_gh77_fairtest.py` (35 tests, arm-neutral, uses `make_agent_config`): seed reproducibility + divergence (flat-score Gumbel probe), density 4/10=0.4, form fill/submit-exclusion/convergence, typed-input tokens-not-substring + nearby-label + password + own-beats-nearby, attribution precedence mop>wtg>form>coverage + mop_frontier→wtg + StateMopDensity-not-a-source + overrides + pure-arm=base, boost buckets, trace CSV header/row/clock/lazy, component-trigger wiring (fires on plateau + attributes + resets, no-fire without plateau/disabled/non-concrete-guard).
- [ ] 5.8 Wire `ComponentTriggerService` into the exploration loop (delivered as a unit in 3.5 but not yet instantiated or called — INV-AGT-48 is unit-verified but never exercised at runtime): instantiate it in `AgentFactory`/strategy and call `maybe_trigger(...)` gated on `PlateauDetector.is_plateau_reached()` in the `execute`/`learn` node; when it returns non-None (a dispatch happened) set `decision_source='component_trigger'` (match 5.5) and feed `PlateauDetector.record_iteration` as progress so a successful trigger resets stagnation. Include an E2E `am`-dispatch smoke gate via rv-experiment — a unit test with a mocked `DeviceInterface` does NOT catch the real `am start-service` background-start restriction on API ≥ 26/30
  - OFFLINE PART DONE: instantiated in `RVAgent.__init__` (device + `static_data.components` + config); `learn_node._maybe_trigger_component` (Phase 4c) reads `strategy.plateau_detector.is_plateau_reached()`, calls `maybe_trigger`, on dispatch sets `strategy.last_decision_source='component_trigger'` + `plateau_detector.record_iteration(discovered_new_state=True)`; concrete-type guard. `ComponentTriggerService.__init__` now getattr-defaults the two config flags (bare-mock safety, Group-4 pattern). Unit tests in test_gh77_fairtest.py. **E2E `am`-dispatch smoke gate DEFERRED into the Group 7 E2E (user decision 2026-07-12).** Two prerequisites are Group-7-shaped: (A) `build_agent_config_dict` (rvagent-tool `config.py`) whitelists variant keys and does NOT carry `component_trigger_enabled`/`component_percentage` — completing that mapping is task 7.1/7.2, so no variant can enable the trigger today; (B) the only `apks_examples/` APK (cryptoapp) has 0 services / 0 receivers (empty trigger catalog per fresh GATOR `out/gh60_cryptoapp_fresh/`), so the MOP-census gate 7.7 must supply a MOP-reaching-service APK before the live `am` dispatch can fire (candidates exist in `data/compat_dataset/`, e.g. `info.zamojski.soft.towercollector` `CollectorService reachesTarget=True`). Offline baselines reconfirmed here: rv-agent 1876 passed / 76 skipped; parity+pipeline+rvagent-tool 30 passed. 5.8 stays open; Group 5 not closed.
- [x] 5.9 Run `/rv-test-run rv-agent`
  - rv-agent offline: 1876 passed, 76 skipped (baseline 1841 + 35 new). Pure-arm parity + scoring pipeline: 11 passed. rvagent-tool regression: 19 passed. pyflakes clean on touched files.

## 6. Launcher with dose/denylist

- [x] 6.1 Extend the launch policy in `rvagent_strategy.py`: configurable launch cadence, per-run launch cap (dose), failed-launch denylist (never re-launch in-run) — port of `mop-activity-consumers`/`activity-trigger-dose`/`mop-census-launcher` from `ape-mop-fairtest`
  - `maybe_launch_activity` / `_launcher_should_fire` / `_select_launch_candidate` / `record_launch_failure` on `RVAgentStrategy` (delivered as a unit, no runtime caller — same pattern as 3.4/5.8). Config knobs `launch_cadence` (default 50, ge=1) + `launch_cap` (default 0=unlimited) added to `agent_config.py`, subordinate to `trigger_mop_first` so NOT arm_defining (mirrors `component_percentage`; matches APE-RV activity-trigger-dose sub-params exempt from `apePureMode` — `ApePureModeKillSwitchTest`). Nothing registered in `RV_STEERING_FLAGS`. `pure_mode` forces `trigger_mop_first` off → launcher is a byte-identical no-op. Per-run state cleared in `reset()`. Port of `SataAgent.selectNewActionNonnull` launcher block + `shouldFireLauncher`/`selectTriggerCandidate` seams.
- [x] 6.2 Add unit tests: denylist entry on failure, cap enforcement, cadence
  - `tests/unit/test_gh77_launcher.py` (14 tests, `make_agent_config`): denylist-on-failure + skip-on-reselect + empty-candidate-costs-no-budget; cap stop/unlimited/normal-exploration-unaffected; cadence period + re-arm; MOP-first selection + visited skipping (explicit + strategy-default); pure-arm no-op (dose off + pure_mode forces trigger_mop_first off via `from_config` kill-switch); reset clears dose state. rv-agent offline: 1890 passed / 76 skipped (1876 + 14). Pure-arm parity + pipeline: 11 passed.
- [x] 6.3 Run `/rv-verify rv-agent`
  - Verdict WARN, no blocking failures: unit 1626 + integration 227 green (offline selection), MI grade A. The FAIL rows (black/isort 4 files, flake8 185×E501) are pre-existing module-wide style debt (owned by Group 9.4 `/rv-qa-lint-fix`), NOT introduced here — the three files I touched are verified clean: `test_gh77_launcher.py` black+isort+flake8 clean; my new lines in `agent_config.py`/`rvagent_strategy.py` have zero E501. mypy skipped (module has no mypy config); dependency-security could not run (sandbox lacks network for `safety`). Full offline suite reconfirmed: 1890 passed / 76 skipped; pure-arm parity 11 green.

## 7. rvagent-tool variants policy + calibration (INV-RVA-01..06)

- [x] 7.1 Rework `RVAgentTool.get_variants()` (`modules/rvagent-tool/src/rvagent_tool/tools/rvagent/tool.py`): frozen variants set ALL arm-defining keys explicitly; `pure_algorithm` sets `pure_mode=True`; `llm_only`/`multimode` set all gh77 steering flags explicitly off; L2 pattern (defaults in variants, no `os.environ`)
  - `get_variants()` spreads `RV_STEERING_OFF` (pinned copy of the agent `RV_STEERING_FLAGS` registry, 15 arm-defining keys at off/0) into every variant; `pure_algorithm` adds `pure_mode=True`, LLM arms (`multimode`/`llm_only`/`default` alias/`thorough`) add `pure_mode=False`. No exemptions (Decision C). L2: defaults in variant dicts, no `os.environ`.
- [x] 7.2 Complete the variant→`RVAgentConfig` mapping for every arm-defining key (including `seed` pass-through and `@param=value` overrides)
  - `config.py` maps every `RV_STEERING_OFF` key + `RV_TUNING_PARAMS` (`pure_mode`, `seed`, `launch_cadence`, `launch_cap`, `component_percentage`) through `build_agent_config_dict`. Knobs mapped-but-not-arm-defining (aperv precedent).
- [x] 7.3 Implement teardown-in-`finally` in the tool execute path (INV-RVA-05) and static-data fail-fast at configure (before any device time)
  - `execute` wraps run in `try/finally` → `_teardown_agent` stops the app via `agent.device.stop_app` (idempotent, never masks caller error). Static-data fail-fast reuses `validate_static_data` before `AgentFactory.create_agent` (no device time on invalid data).
- [x] 7.4 Add guard pytest replicating the aperv-tool pattern (`modules/aperv-tool/tests/test_aperv_tool.py`): every variant sets every arm-defining key; every arm-defining key has a mapping entry; LLM/steering isolation; no LLM call-limit keys
  - `tests/unit/test_gh77_variants.py` (17 tests): SoT `RV_STEERING_OFF == RV_STEERING_FLAGS` drift guard; every variant sets every arm-defining key; pure kill-switch + LLM isolation; mapping completeness (each key flows through); seed pass-through; teardown on success/exception; static-data fail-fast before device.
- [x] 7.5 Run `/rv-test-run rvagent-tool`
  - rvagent-tool 36 passed (19 existing + 17 new), CI contract. Baseline reconfirmed at start: rv-agent 1890 passed / 76 skipped; parity+pipeline 11; rvagent-tool 19.
- [x] 7.6 E2E gate (pure arm): `uv run rv-experiment run --tools rvagent:pure_algorithm --apks-dir ./apks_examples --timeouts 60` — completes with trace containing only `decision_source=base`, `[RV-ARCH]` audit line present, teardown clean
  - Ran to completion (exit 0, 18 iterations). `[RV-ARCH]` line present: only the 7 base-policy scorers assembled (MOP/WtG/frontier/density/form excluded), all 15 flags off — kill-switch verified end-to-end. Teardown clean (`stopped br.unb.cic.cryptoapp`; emulator torn down by rv-platform). Trace: 17/17 rows `decision_source=coverage` with **mop=wtg=menu=form=0** (zero steering). `coverage` is a base-policy, non-arm-defining scorer (`CoverageDensityScorer`), identical to aperv's non-arm-defining coverage boost — user accepted this as satisfying the gate (the literal "only base" wording is imprecise: the pure arm emits base OR coverage, never steering). Trace: `results/cli_experiment_20260713_113554_621d851f/.../rvagent:pure_algorithm.trace.csv`.
- [x] 7.7 Local calibration smoke for `mop_frontier_weight` × `frontier_boost_weight` interaction (cryptoapp, both weights on): record chosen weights in design.md; freeze any additional steering arms (arm-neutral names) based on the result — MANDATORY before any comparison with aperv
  - Frontier pair corrected (Decision E): the generic frontier is `WtgScorer`/`wtg_guided_score`, not a nonexistent `frontier_boost_weight`. Smoke on cryptoapp (3 MOP-reaching activities via `reachability[].methods[]`): both weights on → `wtg` boost = 350 = 200+150 on unvisited MOP activities vs 150 generic (intended additive separation); 5 states vs 3 in the pure arm. **Frozen `mop_frontier_weight=200`, `wtg_guided_score=150`** in the arm-neutral `mop_frontier` variant (pure_algorithm base, no LLM, all other steering off) + guard test. Recorded in `docs/20260713_calibracao_frontier_gh77.md` AND design.md (Decision 6 + Risk line), per user decision. Result dir: `results/cli_experiment_20260713_115925_0b56f7d5`.
  - MOP census gate (E-ext reopening condition): during this calibration, measure the fraction of `apks_examples/` APKs with ≥1 MOP-reaching (`reaches_target=True`) service/receiver. E-ext (exported non-MOP components) was deliberately kept OUT — the port is a faithful census-only reading of aperv ("Exported status is NOT consulted"). If the census is too sparse (the component trigger almost never fires), reopen E-ext as its OWN `arm_defining` flag (e.g. `component_trigger_exported`), NEVER folded under `component_trigger_enabled` — a shared gate would contaminate the arm. Reopening is conditional on this empirical result, not assumed.
  - Census result: `apks_examples/` (only cryptoapp) has **0 MOP-reaching services/receivers** → component trigger never fires on this dataset → E-ext reopening condition met but **deferred by user decision** (new `arm_defining` field triggers INV-AGT-43, beyond Group 7 scope).
- [x] 7.8 Run `/rv-verify rvagent-tool`
  - Blocking checks PASS: unit 37 passed, flake8 0 issues, black/isort clean, MI all grade A. WARNs are pre-existing/non-scoped: `build_agent_config_dict` CC-D (pre-existing ~40-guard mapping; my added for-loop introduces no new flake8 violation — Group 9.4 debt) and a workspace-wide `safety` result. mypy skipped (no module config).

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
