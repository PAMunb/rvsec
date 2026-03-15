<!-- SUBAGENT DISPATCH HINTS
File inventory: ~12 files modified/created (Java), ~10 test files
Groups A, B, C are independent (no shared files) → dispatch in parallel
Group D depends on A+B+C → sequential after all complete
Group E (verification) → sequential after D

Critical path: A+B+C (parallel) → D → E

Group A: Config + retry + hash (Config.java, AgentLoop.java retry loop, ScreenState.java + 3 test files) — LOW complexity
Group B: Sterile blacklist (ContentGraph.java, BacktrackBfs.java + 2 test files) — MEDIUM complexity
Group C: FrontierFinder + StuckDetector (FrontierFinder.java NEW, StuckDetector.java + 3 test files) — MEDIUM-HIGH complexity
  NOTE: Task 4.5 (pass sterileHashes in StuckDetector.recover) is in Group C because it modifies StuckDetector.recover() alongside 4.3
Group D: Integration wiring in AgentLoop only — MEDIUM (depends on A+B+C)
Group E: Verification — sequential

All Java files at: $RVSEC_HOME/rvsec/rvsec-android/rvsmart/
Source: src/main/java/br/unb/cic/rvsmart/
Tests: src/test/java/br/unb/cic/rvsmart/
Use /superpowers:test-driven-development for Groups B and C (new classes)
-->

# Tasks: gh39-rvsmart-track-b

GitHub Issue: #39

## 1. Config + Retry Budget (Group A — independent)

- [x] 1.1 Add 3 new config parameters to `Config.java`: `retry_saturation_threshold` (default 0.8f), `sterile_threshold` (default 3), `frontier_coverage_threshold` (default 0.8f)
- [x] 1.2 Change `DEFAULT_MAX_RETRIES_PER_CYCLE` from 3 to 1 in `Config.java`
- [x] 1.3 Update `ConfigTest.java`: assert new defaults (retries=1, retry_saturation=0.8, sterile=3, frontier=0.8)
- [x] 1.4 Add saturation gate to retry loop in `AgentLoop.java:659`: skip retries when `graph.getSaturation(hash) >= config.getRetrySaturationThreshold()`
- [x] 1.5 Test the saturation gate: write unit tests for `ContentGraph.getSaturation()` returning correct values for saturated/unsaturated screens, and verify `Config.getRetrySaturationThreshold()` default (INV-RSM-45). Testing AgentLoop retry behavior directly is impractical (15+ constructor deps) — rely on smoke test for integration.

## 2. Content Hash — content-description (Group A continued)

- [x] 2.1 Modify `ScreenState.contentSignature()` to include truncated contentDescription (≤50 chars) for interactive non-EditText widgets. New format: `className|resourceId|text|contentDesc|enabled|checkable`
- [x] 2.2 Write `ScreenStateContentDescTest.java`: ImageButton with different content-desc → different hash, non-interactive widget content-desc excluded, null content-desc → empty string, EditText content-desc excluded (INV-RSM-47)

## 3. Sterile Screen Blacklist (Group B — independent, TDD)

- [x] 3.1 Add `sterileHashes: Set<String>` and sterile counter `Map<String, Integer>` to `ContentGraph.java`. Methods: `incrementSterileCounter(hash)`, `resetSterileCounter(hash)`, `markSterile(hash)`, `isSterile(hash)`, `getSterileHashes()`
- [x] 3.2 Write `SterileBlacklistTest.java` (TDD): mark after 3 failures, reset on success, isSterile returns false before threshold, getSterileHashes returns unmodifiable set, null hash is ignored
- [x] 3.3 Modify `BacktrackBfs.findPathToUnsaturated()` to accept `Set<String> sterileHashes` parameter and skip sterile hashes as candidate targets
- [x] 3.4 Update `BacktrackBfsTest.java`: add test where sterile hash is excluded from BFS result

## 4. Forward Navigation — FrontierFinder (Group C — independent, TDD)

- [x] 4.1 Create `recovery/FrontierFinder.java`: BFS forward through `ContentNode.getTransitions()`, find nearest node with `getCoverage() < coverageThreshold` and not sterile. Returns hash or null.
- [x] 4.2 Write `FrontierFinderTest.java` (TDD): frontier found via 2-hop path, no frontier when all saturated, sterile nodes excluded, null when graph empty, start node not returned as frontier, nearest (shortest path) returned (INV-RSM-46) — ≥6 tests
- [x] 4.3 Modify `StuckDetector.recover()`: (a) pass `graph.getSterileHashes()` to BacktrackBfs, (b) add FrontierFinder as nullable constructor dependency, (c) after BacktrackBfs fails, call FrontierFinder — if frontier found return RESTART (UCB bias guides toward frontier), if not found return RESTART. Recovery priority: BacktrackBfs→BACK, FrontierFinder→RESTART, none→RESTART
- [x] 4.4 Update `StuckDetectorTest.java`: test frontier fallback returns RESTART when no ancestor, test RESTART when no frontier either, test sterile hashes passed to BacktrackBfs

## 5. Integration Wiring (Group D — depends on A+B+C)

- [x] 5.1 Add `lastKnownHash` field to `AgentLoop.java`. Update at end of each successful iteration (`lastKnownHash = hash` after step 14). On null root (line 270), call `graph.incrementSterileCounter(lastKnownHash)` only if `lastKnownHash != null`; when counter reaches `config.getSterileThreshold()`, call `graph.markSterile(lastKnownHash)`. On successful parse, call `graph.resetSterileCounter(hash)`.
- [x] 5.2 Wire FrontierFinder in `AgentLoop.java`: instantiate alongside BacktrackBfs, pass to StuckDetector constructor. Pass `config.getFrontierCoverageThreshold()` for StuckDetector to forward to FrontierFinder.
- [x] 5.3 Update existing tests that construct StuckDetector or BacktrackBfs to match new signatures (add null/empty sterile sets where needed)

## 6. Verification (Group E — sequential after D)

- [x] 6.1 Run `mvn test` — 607 tests, 0 failures, 0 errors
- [x] 6.2 Run `mvn install -q` — JAR built
- [x] 6.3 Smoke test passed: Methods 23.73%, Activities 100%, MOP 26.23%, 3 errors
- [x] 6.4 Update INV-RSM-32 in delta spec: scorer chain now has 8 scorers (UCBScorer added by gh37) — spec debt from gh37
