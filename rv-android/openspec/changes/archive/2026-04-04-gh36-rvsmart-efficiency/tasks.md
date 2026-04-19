<!-- All changes are in Java source at $RVSEC_HOME/rvsec-android/rvsmart/.
     Groups 1-3 are independent and can run in parallel after reading design.md.
     Group 4 depends on all previous groups.
     Group 5 (validation) requires Docker rebuild + experiment.
     This change touches ~10-12 Java files — no subagent orchestration needed. -->

## 1. Adaptive Retry Budget (highest impact — 52.6% waste)

- [ ] 1.1 Modify `AgentLoop.executeIteration()`: replace fixed `MAX_RETRIES_PER_CYCLE=3` with adaptive logic — query current screen saturation from `DynamicStateGraph`, set retry limit to 1 if saturation < 0.8, 0 if ≥ 0.8 (INV-RSM-07 replacement)
- [ ] 1.2 Add `DynamicStateGraph.getSaturation(String hash)` method if not already exposed — return tested_actions / total_actions for the screen
- [ ] 1.3 Add unit tests: `test_retry_budget_zero_on_saturated`, `test_retry_budget_one_on_fresh`, `test_retry_budget_respects_3_consecutive_skip`
- [ ] 1.4 Build with `mvn package -DskipTests=false`

## 2. Faster Stuck Detection (saves ~15 wasted iters per episode)

- [ ] 2.1 Modify `StuckDetector`: change same-hash-for-BACK threshold from 10 to 5 iterations (INV-RSM-14)
- [ ] 2.2 Modify `StuckDetector`: change BACK-failure-for-RESTART threshold from 5 to 3 (INV-RSM-14)
- [ ] 2.3 Add unit tests: `test_force_back_after_5_same_hash`, `test_force_restart_after_3_back_failures`
- [ ] 2.4 Build with `mvn package -DskipTests=false`

## 3. Sterile Screen Blacklist (eliminates SKIP revisitation)

- [ ] 3.1 Add `Set<String> sterileHashes` field to `DynamicStateGraph` with methods: `markSterile(hash)`, `isSterile(hash)`, `clearSterileSet()`
- [ ] 3.2 Modify `AgentLoop` or `Learner`: after recording a visit, check if hash has ≥2 visits ALL producing SKIP — if so, call `markSterile(hash)`
- [ ] 3.3 Modify `ActionSelector.selectTier3()` (or BFS navigation): exclude sterile hashes from navigation targets
- [ ] 3.4 Modify RESTART handling: call `clearSterileSet()` on every RESTART
- [ ] 3.5 Add unit tests: `test_mark_sterile_after_2_skip_visits`, `test_sterile_excluded_from_tier3`, `test_sterile_cleared_on_restart`
- [ ] 3.6 Build with `mvn package -DskipTests=false`

## 4. Frontier Navigation (reduces 93.9% revisitation)

- [ ] 4.1 Add `DynamicStateGraph.findNearestFrontier(String currentHash, int maxHops)` — BFS over nav_map edges to find nearest state with saturation < 0.8 and not sterile, returns path (list of actions) or null if no frontier within maxHops
- [ ] 4.2 Modify `ActionSelector.selectTier3()`: before BFS-to-ancestor, try `findNearestFrontier(current, 5)` — if path found, buffer actions into `PathBuffer`; if not, fall back to existing BFS-to-ancestor
- [ ] 4.3 Add unit tests: `test_frontier_found_within_hops`, `test_frontier_fallback_when_too_far`, `test_frontier_excludes_sterile`
- [ ] 4.4 Build with `mvn package -DskipTests=false`

## 5. Content-Aware Hash (increases state discovery)

- [ ] 5.1 Modify `UiCapture.computeHash()`: after computing structural SHA-256[:12], append `_{textNodeCount}_{SHA-256[:4] of first text value}` to create extended hash (INV-RSM-03 extension)
- [ ] 5.2 Handle edge case: no text nodes → suffix `_0_0000`
- [ ] 5.3 Update `DynamicStateGraph` and `TraceWriter` to handle the new hash format (longer string, same type)
- [ ] 5.4 Add unit tests: `test_hash_differs_on_different_text`, `test_hash_same_on_identical_content`, `test_hash_no_text_nodes`
- [ ] 5.5 Build with `mvn package -DskipTests=false`

## 6. Adaptive Throttle on Known Screens (throughput improvement)

- [ ] 6.1 Modify `AgentLoop.throttle()`: if current hash exists in `DynamicStateGraph` (revisit), use `throttle_ms / 2`; otherwise use full `throttle_ms`
- [ ] 6.2 Add unit test: `test_throttle_halved_on_revisit`
- [ ] 6.3 Build with `mvn package -DskipTests=false`

## 7. New Efficiency Metrics

- [ ] 7.1 Add counters to `MetricsCollector`: `retry_waste_count`, `revisitation_count`, `transition_count`, `sterile_screen_count`, `frontier_nav_count`, `frontier_fallback_count`
- [ ] 7.2 Instrument `AgentLoop` and `ActionSelector` to increment these counters at appropriate points
- [ ] 7.3 Add `efficiency` section to final metrics JSON output (see delta spec for format)
- [ ] 7.4 Update `modules/rvsmart-tool/src/rvsmart_tool/tools/rvsmart/tool.py` — extract new `efficiency` metrics from `rvsmart_metrics.json` if present (backward-compatible: ignore if absent)
- [ ] 7.5 Build with `mvn package -DskipTests=false`

## 8. Integration & Validation

- [ ] 8.1 Full `mvn package` build with all tests passing
- [ ] 8.2 Copy new `rvsmart.jar` to `modules/rvsmart-tool/src/rvsmart_tool/tools/rvsmart/rvsmart.jar`
- [ ] 8.3 Rebuild Docker image: `docker build -t phtcosta/rvandroid:0.9.0 .`
- [ ] 8.4 Smoke test: single APK (biz.gyrus.yaab_30.apk), rvsmart:mvp, 300s timeout — verify new metrics appear and efficiency numbers improve
- [ ] 8.5 Full experiment: 159 APKs, rvsmart:mvp + ape, 600s, 3 reps, JCA specs — compare with exp-rvsmart-ape baseline
- [ ] 8.6 Run validation protocol (9 areas) on results
- [ ] 8.7 Update `openspec/specs/rvsmart/spec.md` with delta spec changes (sync via `/opsx:sync`)
- [ ] 8.8 Invoke `/rv-code-reviewer`
