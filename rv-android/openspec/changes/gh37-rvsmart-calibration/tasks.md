<!-- Subagent Dispatch Plan:
     - Groups 1, 2, 3 are INDEPENDENT — dispatch 3 subagents in parallel.
       - Group 1: ALL Config.java edits (avoids merge conflicts between subagents).
       - Group 2: UCBScorer new file + ActionSelector registration. Uses TDD.
       - Group 3: RoutingManager first-visit logic. Uses TDD.
     - Group 4 (Integration) depends on Groups 1+2+3 — dispatch after all three complete.
     - Group 5 (Verification) runs sequentially in main context after Group 4.
     - All Java source paths relative to $RVSEC_HOME/rvsec/rvsec-android/rvsmart/.
     - IMPORTANT: `source /etc/profile` before any mvn command (sets JAVA_HOME, RVSEC_HOME).
     - Scope boundary: Track A ONLY. Track B items (retry budget, forward nav, sterile
       blacklist, component budget, anti-tarpit, RewardPropagator, dual hash, PhaseController
       simplification) are NOT part of this change — they go in a future change if Track A
       does not reach ≥28% method coverage (see docs/20260313_rvsmart_refatoracao.md §6).
-->

## 1. Config Calibration — Group A (subagent)

Dispatch as subagent. Single file: `core/Config.java`. Includes UCB_C constant to avoid
merge conflicts (Groups 2+3 do NOT edit Config.java).

- [x] 1.1 Edit `Config.java:26`: change `DEFAULT_THROTTLE_MS` from 100 to **50**
- [x] 1.2 Edit `Config.java:59`: change `DEFAULT_BACK_BASE_SCORE` from -100.0f to **50.0f**
- [x] 1.3 Edit `Config.java:61`: change `DEFAULT_BACK_DECAY_PER_REPEAT` from 100.0f to **30.0f**
- [x] 1.4 Edit `Config.java:86`: change `DEFAULT_STUCK_MAX_BLOCKS` from 10 to **7**
- [x] 1.5 Add `DEFAULT_UCB_C = 150.0f` constant (near other scorer constants, scaled to match GradualDecay=200 / MOP=500 range) + `getUcbC()` getter
- [x] 1.6 Run `source /etc/profile && cd $RVSEC_HOME/rvsec/rvsec-android/rvsmart && mvn compile -q` — verify compilation

## 2. UCB Scorer — Group B (subagent, use `/superpowers:test-driven-development`)

Dispatch as subagent. Files: `UCBScorer.java` (new), `UCBScorerTest.java` (new), `ActionSelector.java` (edit).
UCBScorer constructor takes `float c` directly — no Config.java dependency in this group.

- [x] 2.1 **RED**: Create `src/test/java/br/unb/cic/rvsmart/strategy/scorers/UCBScorerTest.java`. Test cases: (a) never-visited action (N_action=0) → capped max exploration bonus, (b) visited action → decaying bonus following UCB exploration formula, (c) null ContentNode → 0, (d) N_state=0 (first visit to state) → 0, (e) formula correctness with known values (e.g., C=150, N_state=10, N_action=2 → expected `(int)(150 * sqrt(ln(10)/2))` = `(int)(150 * 1.073)` = 160)
- [x] 2.2 **GREEN**: Create `src/main/java/br/unb/cic/rvsmart/strategy/scorers/UCBScorer.java` implementing `Scorer`. Constructor: `UCBScorer(float c)`. UCB exploration bonus formula: `(int)(c * Math.sqrt(Math.log(N_state) / N_action))`. C=150 produces scores ~200 for untried actions (matching GradualDecay scale), decaying as actions are explored. Edge cases: N_action=0 → `(int)(c * Math.sqrt(Math.log(Math.max(1, N_state))))`, null node or N_state≤0 → return 0.
- [x] 2.3 Edit `strategy/ActionSelector.java:176`: add `this.scorers.add(new UCBScorer(config.getUcbC()));` after WtgScorer line
- [x] 2.4 **REFACTOR**: Review scorer for edge cases, verify imports, check naming consistency with other scorers
- [x] 2.5 Run `source /etc/profile && cd $RVSEC_HOME/rvsec/rvsec-android/rvsmart && mvn test -q` — all tests pass

## 3. LLM First-Visit Invocation — Group C (subagent, use `/superpowers:test-driven-development`)

Dispatch as subagent. Files: `RoutingManager.java` (edit), `RoutingManagerFirstVisitTest.java` (new).

- [x] 3.1 **RED**: Create `src/test/java/br/unb/cic/rvsmart/core/RoutingManagerFirstVisitTest.java`. Test cases: (a) MULTIMODE + first-ever visit to hash → returns true (via circuit breaker), (b) MULTIMODE + second visit to same hash → falls through to PROBABILISTIC strategy, (c) MULTIMODE + first visit to different hash → returns true, (d) PURE_ALGORITHM mode → first-visit ignored (returns false), (e) LLM_ONLY mode → returns true regardless (existing behavior), (f) `reset()` clears visitedScreens so next call is first-visit again
- [x] 3.2 **GREEN**: Edit `core/RoutingManager.java`: add `private final Set<String> visitedScreens = new HashSet<>();` field. In `shouldUseLlm()` MULTIMODE branch (line 89-90), before `return shouldUseLlmMultimode(currentHash)`: add `if (!visitedScreens.contains(currentHash)) { visitedScreens.add(currentHash); return circuitBreaker.shouldAttempt(); }`. Add `visitedScreens.clear()` in `reset()` method (line 138).
- [x] 3.3 Run `source /etc/profile && cd $RVSEC_HOME/rvsec/rvsec-android/rvsmart && mvn test -q` — all tests pass

## 4. Integration — Group D (subagent, after Groups 1+2+3)

Dispatch after Groups 1-3 complete. Verify cross-group integration.

- [x] 4.1 Run full test suite: `source /etc/profile && cd $RVSEC_HOME/rvsec/rvsec-android/rvsmart && mvn test` — 576 tests, 0 failures, 0 errors
- [x] 4.2 Check for compilation warnings: `mvn compile 2>&1 | grep -i "warning\|error"` — clean, no project warnings
- [x] 4.3 Read ActionSelector.java — confirmed UCBScorer registered at line 178 using `config.getUcbC()`
- [x] 4.4 Read RoutingManager.java — confirmed first-visit check in MULTIMODE branch only (lines 92-98)

## 5. Verification — Main Context (use `/superpowers:verification-before-completion`)

Run in main context sequentially. Do NOT claim completion before evidence.

- [x] 5.1 `mvn package -q` — rvsmart.jar builds without errors
- [x] 5.2 Grep Config defaults: throttle=50, back_score=50.0f, back_decay=30.0f, stuck_blocks=7, ucb_c=150.0f — all confirmed
- [x] 5.3 Grep UCBScorer registered: ActionSelector.java:178 `new UCBScorer(config.getUcbC())`
- [x] 5.4 Grep first-visit logic: RoutingManager.java:93-96 `visitedScreens` in MULTIMODE branch only
- [x] 5.5 Local smoke test with cryptoapp (300s): rvsmart executed successfully — 15.25% method cov, 75% activity cov, 3 MOP violations detected (partial run, interrupted after ~2min)
- [ ] 5.6 Commit changes to rvsec repo (`$RVSEC_HOME/rvsec/rvsec-android/rvsmart/`) with `refs #37`
