<!-- Subagent dispatch hints (this change touches ~18 files):
     - Group 1 (Unblock) has NO dependencies — must complete first and JAR rebuilt before any LLM test.
       This group is the critical prerequisite: wrong URL + no logging makes LLM invisible in tests.
     - Group 2 (Foundation) depends on Group 1 JAR being built. Groups 2, 3 are independent of each other
       and can run in parallel after Group 1.
     - Group 3 (ARRIVAL_FIRST) depends on Group 1 (Config.java changes are shared). Can run in parallel with Group 2.
     - Group 4 (V17 rich context) depends on Group 2 (PromptContext must exist before wiring data into it).
     - Group 5 (V17 prompt) depends on Group 4 (context data must flow before V17 template is useful).
     - Group 6 (Python tool variants) depends on Groups 2+3 (new config params must exist in Java first).
     - Group 7 (Diagnostic tests) depends on Group 1 only — run immediately after Group 1 to validate connectivity.
     - Group 8 (Verification) runs last after all groups.
     - Critical path: 1 → 2 → 4 → 5 → 8
     - Parallel opportunities: (2 ∥ 3) after 1; (4 ∥ 6) after 2+3. -->

## 1. Unblock — Fix URL, Add Variants, Add Logging (PREREQUISITE for all tests)

These four tasks must be done first. Without them, all LLM calls silently fail (wrong URL → connection
timeout → circuit breaker opens → looks like pure_algorithm) and we are blind to what the LLM does.
Rebuild rvsmart.jar after this group before running any LLM test.

- [x] 1.1 In `rvsec-android/rvsmart/src/main/java/br/unb/cic/rvsmart/core/Config.java`: change `DEFAULT_LLM_BASE_URL` from `"http://10.0.2.2:30000/v1"` to `"http://192.168.0.36:30000/v1"`
- [x] 1.2 In `PromptBuilder.buildExplorationPrompt()`: add `Log.d("RVSMART-PROMPT", fullPromptText)` after assembling the context string, before adding it to `userParts` — logs the complete text sent to the LLM
- [x] 1.3 In `ToolCallParser.parse()`: add `Log.d("RVSMART-LLM-RESP", rawContent)` at the start of parsing — logs the raw LLM response before any parsing attempt
- [x] 1.4 In `modules/rvsmart-tool/src/rvsmart_tool/tools/rvsmart/tool.py`: add `llm_only` variant, `arrival_first_v13`, `arrival_first_v17`; remove `hybrid` variant (P3: no alias)
- [x] 1.5 Rebuild rvsmart.jar: `cd $RVSEC_HOME/rvsec/rvsec-android/rvsmart && mvn package -DskipTests`
- [x] 1.5b (Docker only) If testing inside Docker container: rebuild Docker image after JAR changes — `docker build -t rv-android .` or equivalent; the JAR is baked into the image at build time — N/A: Docker not used in this deployment
- [x] 1.6 Connectivity test: `adb -s emulator-5554 shell 'CLASSPATH=/data/local/tmp/rvsmart.jar /system/bin/app_process /data/local/tmp/ br.unb.cic.rvsmart.Main --health-check'` — verify no connection error in output; if fails, check network routing from emulator to 192.168.0.36 — validated empirically: arrival_first_v17 experiment achieved 87.5% LLM actions, confirming full connectivity

## 2. Foundation — PromptVersion, PromptContext, PromptBuilder Refactor

This group builds the versioning infrastructure that all prompt work depends on. Complete before Groups 4 and 5.

- [x] 2.1 In `Config.java`: add `PromptVersion` static nested enum with values `V13`, `V17`; add `llm_prompt_version: PromptVersion` field (default `V13`); add `llm_new_screen_phase2_probability: float` field (default 0.30); add `llm_multimode_strategy: MultiModeStrategy` field if not already present — check whether `MultiModeStrategy` enum needs `ARRIVAL_FIRST` added (likely yes)
- [x] 2.2 Create `rvsec-android/rvsmart/src/main/java/br/unb/cic/rvsmart/llm/PromptContext.java`: value object with fields listed in design.md (base64Screenshot, uiElements, currentActivity, navigationHint, visitedActivities, iterationNumber, plus nullable V17 fields: elementInteractionCounts, directMopElements, indirectMopElements, elementScores, recentActions); include static inner `Builder` class
- [x] 2.3 Refactor `PromptBuilder.java`: replace current `buildExplorationPrompt(String, List<ScreenItem>, String, String, Set<String>)` signature with `build(PromptVersion version, PromptContext ctx)`; keep the existing logic as the V13 path initially (will be replaced in Group 5)
- [x] 2.4 Update `AgentLoop.tryLlmAction()` call site to use new `PromptContext.Builder` and `PromptBuilder.build()` — at this stage pass only the base fields (screenshot, elements, activity, null hint, visited, iteration); V17 fields all null for now
- [x] 2.5 Add unit tests for `PromptContext` builder: verify fields set, verify null V17 fields allowed (`PromptBuilderTest.java`)
- [x] 2.6 Run `/rv-test-run rvsmart` — verify existing PromptBuilderTest passes with new signature

## 3. ARRIVAL_FIRST Routing Strategy

Independent of Group 2 except for the `llm_multimode_strategy` field added in task 2.1. Can run in parallel with Group 2 after that field exists.

- [x] 3.1 In `RoutingManager.java`: add `ARRIVAL_FIRST` to `MultiModeStrategy` enum
- [x] 3.2 In `RoutingManager.java`: add `private String lastSeenHash = null` field; update `shouldUseLlm()` signature to `shouldUseLlm(String currentHash, boolean isOutOfApp)` — returns false immediately when `isOutOfApp`; for ARRIVAL_FIRST: returns true if `!currentHash.equals(lastSeenHash)` (arrival), else uses `random.nextDouble() < phase2Probability`; always sets `this.lastSeenHash = currentHash` before returning
- [x] 3.3 In `RoutingManager.java`: update `reset()` method to also clear `lastSeenHash = null`
- [x] 3.4 Update all `RoutingManager.shouldUseLlm()` call sites in `AgentLoop.java` to pass `(currentHash, outOfAppCount > 0)` — currently called as `shouldUseLlm(screen, isNewScreen, isStuck)`; remove the old parameters and replace with new signature
- [x] 3.5 Add unit tests in `RoutingManagerTest.java`: `testArrivalFirstFiresOnHashChange()` (different hash → true), `testArrivalFirstNoFireSameHash()` (same hash + seed at 1.0 → false), `testArrivalFirstPhase2Probabilistic()` (same hash + seeded random → probability matches phase2 ratio), `testOutOfAppGuardReturnsFalse()` (any mode + isOutOfApp=true → false)
- [x] 3.6 Run `/rv-test-run rvsmart` — verify RoutingManagerTest passes

## 4. V17 Rich Context Wiring

Depends on Group 2 (PromptContext must exist). Wires UICoverageTracker, StaticMap, and ActionSelector data into PromptContext. Must complete before Group 5 (V17 prompt template needs this data to be testable).

- [x] 4.1 Investigate `UICoverageTracker.java`: identify the method that returns per-element interaction counts; verify the element key format matches what `ScreenItem` can produce — if `ScreenItem.getKey()` does not exist, add it (a stable string hash of className + text + bounds center)
- [x] 4.2 Investigate `StaticMap.java`: verify whether it exposes activity-level MOP reachability (which activities directly/transitively reach a monitored operation) — note that element-level matching is approximated as "all elements on a MOP-reachable activity get the marker"; document the actual available API in a comment in AgentLoop
- [x] 4.3 Add `private final List<Action> recentActionsBuffer = new ArrayList<>(5)` to `AgentLoop`; after each successful action execution in `runIteration()`, prepend to the buffer and trim to 5 entries
- [x] 4.4 In `AgentLoop.tryLlmAction()`: populate V17 fields in `PromptContext.Builder` — call `uiCoverageTracker.getCountsForScreen(screen)` for interaction counts; call `staticMap.getDirectMopActivities()` and `staticMap.getTransitiveMopActivities()` (or equivalent) for MOP activity sets; call `actionSelector.getLastScoreBreakdown()` for element scores; pass `recentActionsBuffer` snapshot
- [x] 4.5 In `AgentLoop.tryLlmAction()`: compute `navigationHint` from StaticMap instead of passing null — find the highest-value activity (most MOP operations, fewest WTG hops from current activity); build hint string: `"Target: <ActivitySimpleName> (has <N> monitored operations, ~<K> transitions away)"` — if StaticMap is null or no targets found, pass null
- [x] 4.6 Unit tests: `PromptBuilderTest.testV17InteractionCountsInContext()` — verify that a PromptContext with interaction counts produces elements with correct test-status tags in output when V17 is used (even before the V17 template is complete, verify the data flows through)

## 5. Prompt V13 and V17 Templates

Depends on Group 2 (PromptBuilder refactored). Group 4 should ideally be done first so V17 is testable with real data, but V13 can proceed independently.

- [x] 5.1 In `PromptBuilder.java`: implement `buildSystemMessageV13()` — port the RVAgent v13 system prompt to Java: dialog detection instructions (permission dialogs: click Allow/Accept/OK; error/modal dialogs: dismiss before any other action), priority ordering (MOP targets > new screen navigation > [UNTESTED] elements > [TESTED] elements), available actions list, rule against consecutive same-position clicks
- [x] 5.2 In `PromptBuilder.java`: implement `buildUserMessageV13(PromptContext ctx)` — activity name, numbered elements (class + text/desc + coords), navigation hint section (if non-null), visited activities count, iteration number, closing instruction
- [x] 5.3 In `PromptBuilder.java`: implement `buildSystemMessageV17()` — extends V13 with explicit PRIORITY block: `Elements reaching monitored operations (MOP) > actions leading to NEW screens > [UNTESTED] > [TESTED-Nx]`; add REASONING STEPS section matching RVAgent v17: (1) screen type, (2) dialog check, (3) MOP CHECK, (4) navigation, (5) element selection, (6) action call
- [x] 5.4 In `PromptBuilder.java`: implement `buildUserMessageV17(PromptContext ctx)` — screen info line (`SCREEN: <Activity> | <coverage%> coverage (<K>/<N> actions) | visit #<V>`); elements enriched with test-status tag, MOP marker ([DM]/[M]), and score (`[score:N]`), sorted by score descending; recent actions section (if non-empty); MOP NAVIGATION section (if navigationHint non-null); closing instruction `"Select action. Prioritize elements reaching monitored operations, then navigation to new screens."`
- [x] 5.5 Wire `build()` dispatch: `if (version == V13) → buildSystemMessageV13() + buildUserMessageV13(ctx)`; `if (version == V17) → buildSystemMessageV17() + buildUserMessageV17(ctx)`
- [x] 5.5b In `PromptBuilder.build()` dispatch: add fallback — `case V12: case V14: case V15: case V16:` all fall through to V13 template (the enum has all 6 versions for parity with RVAgent, but only V13 and V17 are fully implemented)
- [x] 5.6 Unit tests in `PromptBuilderTest.java`: `testV13SystemMessageContainsDialogInstructions()`, `testV13UserMessageElementFormat()`, `testV17ElementWithAllAnnotations()` (untested + direct MOP + score → correct tag string), `testV17ElementDegradationNullMopSets()`, `testV17RecentActionsSection()`, `testV17ScreenInfoLine()`, `testV17NoMopNavigationWhenHintNull()`
- [x] 5.7 Run `/rv-test-run rvsmart`

## 6. Python Tool Variants and Config Passthrough

Depends on Group 2 (new Java config params must exist before adding Python variants that set them). Can run in parallel with Groups 4 and 5.

- [x] 6.1 In `tool.py`: add `arrival_first_v13` variant — `{"mode": "multimode", "llm_multimode_strategy": "arrival_first", "llm_prompt_version": "v13", "llm_new_screen_phase2_probability": "0.30", "llm_base_url": "http://192.168.0.36:30000/v1"}`
- [x] 6.2 In `tool.py`: add `arrival_first_v17` variant — same as above but `"llm_prompt_version": "v17"`
- [x] 6.3 In `tool.py`: verify that `_push_config_properties()` passes all new keys through to the Java properties file without filtering — it should already since it iterates `self._tool_config` keys generically
- [x] 6.4 In `Config.java` property parsing: verify that `llm_prompt_version` (string "v13"/"v17") is parsed and converts to `PromptVersion.V13`/`V17`; same for `llm_multimode_strategy` ("arrival_first" → `MultiModeStrategy.ARRIVAL_FIRST`); add parsing if missing
- [x] 6.5 Unit tests in `test_rvsmart_tool.py`: `test_llm_only_variant()` (mode=llm_only, correct URL), `test_arrival_first_v13_variant()` (all 5 expected keys present), `test_arrival_first_v17_variant()`, `test_hybrid_variant_removed()` (assert "hybrid" not in get_variants())
- [x] 6.6 Run `/rv-test-run rvsmart-tool`

## 7. Diagnostic Tests (run after Group 1 — validate connectivity and observe LLM behavior)

These are manual experiment runs. Run as soon as Group 1 is done and JAR is rebuilt — don't wait for Groups 2-6.

- [x] 7.1 Connectivity test: run `rv-experiment run --tools rvsmart:llm_only --apks-dir apks_examples/ --timeout 30`; check experiment log for `RVSMART-PROMPT` lines (proves prompts are being sent); if no LLM lines appear, check circuit breaker status in log — indicates connection failure
- [x] 7.2 Prompt quality review: on the HOST machine, run `adb -s emulator-5554 logcat -c` to clear the buffer, then start rvsmart, then capture with `adb -s emulator-5554 logcat -s RVSMART-PROMPT:D > /tmp/rvsmart_prompts.log`; review first 3 prompts — check element formatting, activity name, visited activities, no obvious formatting bugs
- [x] 7.3 Response quality review: from the same logcat capture (or `adb -s emulator-5554 logcat -s RVSMART-LLM-RESP:D > /tmp/rvsmart_responses.log`); check which parser level fired (native / XML / inline JSON), whether coordinates are in [0,1000) range, and whether action types are valid
- [x] 7.4 After Groups 2-5: run `rv-experiment run --tools rvsmart:arrival_first_v17 --apks-dir apks_examples/ --timeout 300`; compare `llm_actions` count in RVSMART_METRICS vs `algorithm_actions`; verify V17 elements appear in RVSMART-PROMPT logs with test-status tags and MOP markers
- [x] 7.5 After Group 7.4: run `rv-experiment run --tools rvsmart:default --apks-dir apks_examples/ --timeout 300` for baseline; compare method coverage and MOP coverage vs arrival_first_v17 run; document findings in `docs/20260308_rvsmart_llm.md` (add a "Results" section)

## 8. Final Verification

- [x] 8.1 Rebuild rvsmart.jar with all changes: `cd $RVSEC_HOME/rvsec/rvsec-android/rvsmart && mvn package`
- [x] 8.2 Run `/rv-qa-lint-fix rvsmart-tool`
- [x] 8.3 Run `/rv-verify rvsmart-tool`
- [x] 8.4 Run all Java tests: `cd $RVSEC_HOME/rvsec/rvsec-android/rvsmart && mvn test` — all tests must pass
- [x] 8.5 Verify `rvsmart:hybrid` variant no longer exists (removed in 1.4): `grep -r "hybrid" modules/rvsmart-tool/src/` should return zero rvsmart results
- [x] 8.6 Verify spec delta covers all implemented invariants: cross-check INV-RSM-LLM-01 through INV-RSM-LLM-06 against implementation
- [x] 8.7 Invoke `/rv-code-reviewer` via Skill tool
