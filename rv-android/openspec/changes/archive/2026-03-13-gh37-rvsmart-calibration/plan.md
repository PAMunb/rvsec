# Change Plan: gh37-rvsmart-calibration

**Date**: 2026-03-13
**Track**: Quick Path
**Priority**: High
**GitHub Issue**: [#37](https://github.com/PAMunb/rvsec/issues/37)
**PRD Reference**: FR18 (tool execution), NFR01 (coverage effectiveness)
**Domains**: tools

## 1. Context

In the 100-APK experiment (`docs/20260310_comparacao_resultados.md`), rvsmart:mvp achieved 24.04% method coverage vs APE's 28.38% (gap: -4.39pp, p<0.001). gh35 fixed 17 critical bugs (BACK disabled, ping-pong cycles, saturation loops) but hasn't been experimentally validated yet. Estimated gh35 impact: +3-5pp.

This change (Track A from `docs/20260313_rvsmart_refatoracao.md`) applies calibration changes and adds one new scorer to close the remaining gap. The approach is minimal-risk: 4 constant changes + 1 new scorer class + 1 routing adjustment. No architectural changes, no class deletions, no interface modifications.

All changes are in the rvsmart Java module at `$RVSEC_HOME/rvsec/rvsec-android/rvsmart/`. No Python module changes are needed — the defaults are compiled into the JAR.

## 2. Scope

All files are in `$RVSEC_HOME/rvsec/rvsec-android/rvsmart/src/main/java/br/unb/cic/rvsmart/`.

**Group A — Config calibration (1 file)**
Change 4 default constants + add `DEFAULT_UCB_C` constant in Config.java. All Config.java edits are in this group to avoid merge conflicts when dispatching parallel subagents.

**Group B — UCB scorer (2 files: 1 new, 1 edit)**
Add UCBScorer.java implementing the Scorer interface (constructor takes `float c` directly). Register it in ActionSelector's scorer chain (reads C from Config via `config.getUcbC()`).

**Group C — LLM first-visit invocation (1 file)**
Add first-visit detection in RoutingManager.java so LLM is always invoked the first time a screen appears (in MULTIMODE only — LLM_ONLY already invokes 100%). The default routing strategy is already PROBABILISTIC; first-visit adds a `visitedScreens` HashSet check in the MULTIMODE branch of `shouldUseLlm()`, before delegating to `shouldUseLlmMultimode()`. First-ever visit to a contentHash → LLM (via circuit breaker). Subsequent visits → existing strategy (PROBABILISTIC by default).

**Group D — Integration verification (after A+B+C)**
Run full test suite, check cross-group wiring. Tests for UCBScorer and RoutingManager are created inside Groups B and C via TDD (RED-GREEN-REFACTOR).

## 3. File Inventory

All paths relative to `$RVSEC_HOME/rvsec/rvsec-android/rvsmart/src/main/java/br/unb/cic/rvsmart/`.

| File | Action | Detail |
|------|--------|--------|
| `core/Config.java:26` | Edit | `DEFAULT_THROTTLE_MS`: 100 → **50** |
| `core/Config.java:59` | Edit | `DEFAULT_BACK_BASE_SCORE`: -100.0f → **50.0f** |
| `core/Config.java:61` | Edit | `DEFAULT_BACK_DECAY_PER_REPEAT`: 100.0f → **30.0f** |
| `core/Config.java:86` | Edit | `DEFAULT_STUCK_MAX_BLOCKS`: 10 → **7** |
| `core/Config.java` | Edit | Add `DEFAULT_UCB_C = 150.0f` constant + `getUcbC()` getter (Group A — all Config edits in one group) |
| `strategy/scorers/UCBScorer.java` | **New** | UCB exploration bonus: `C × sqrt(ln(N_state) / N_action)`. Constructor takes `float c`. Uses `ContentNode.getVisitCount()` for N_state and `ContentNode.getExecutionCount(signature)` for N_action. Returns `(int)(C * Math.sqrt(Math.log(N_state) / N_action))`. C=150 is scaled to match other scorers' magnitude (GradualDecay=200, MOP=500). Never-visited actions get max exploration bonus (N_action=0 → capped score). Null node → 0. |
| `strategy/ActionSelector.java:176` | Edit | Add `this.scorers.add(new UCBScorer(config.getUcbC()));` after WtgScorer line |
| `core/RoutingManager.java` | Edit | Add `private final Set<String> visitedScreens = new HashSet<>()` field. In `shouldUseLlm()` MULTIMODE branch (line 89-90): before calling `shouldUseLlmMultimode()`, check if `currentHash` is in `visitedScreens`. If not → add it, return `circuitBreaker.shouldAttempt()` (100% LLM on first-ever visit). Default strategy is already PROBABILISTIC — no strategy change needed. Also add `visitedScreens.clear()` in `reset()`. |

Test files (relative to `$RVSEC_HOME/rvsec/rvsec-android/rvsmart/src/test/java/br/unb/cic/rvsmart/`):

| File | Action | Detail |
|------|--------|--------|
| `strategy/scorers/UCBScorerTest.java` | **New** | Test: never-visited action gets max bonus, visited action gets decaying bonus, N_action=0 capped, null node returns 0, formula correctness with known values |
| `core/RoutingManagerFirstVisitTest.java` | **New** | Test: first visit returns true (hybrid mode), second visit falls to probability, non-hybrid mode ignores first-visit, visitedScreens accumulation |

## 4. Execution Order

```
Group A (Config calibration) ──┐
Group B (UCBScorer)            ├── All independent, can run in parallel
Group C (LLM first-visit)     ┘
         │
         ▼
Group D (Tests) ── depends on A+B+C
```

Groups A, B, C are independent — they touch disjoint files (no merge conflicts). Groups B and C include their own tests via TDD. Group D runs the full suite and verifies cross-group wiring.

Total files: 3 edited + 3 new = 6 files. Main context acts as orchestrator; each group dispatched to a subagent.

## 5. Acceptance Criteria

- [ ] Config defaults match target values (throttle=50, back_score=+50, back_decay=30, stuck_blocks=7, ucb_c=150)
- [ ] UCBScorer implements Scorer interface with correct UCB exploration bonus formula
- [ ] UCBScorer registered in ActionSelector scorer chain
- [ ] RoutingManager invokes LLM on first-ever screen visit (MULTIMODE only — LLM_ONLY already invokes 100%)
- [ ] All existing tests pass (`mvn test` — 565+ tests, 0 failures)
- [ ] New UCBScorer tests pass (formula correctness, edge cases)
- [ ] New RoutingManager first-visit tests pass
- [ ] `mvn package` produces rvsmart.jar without errors
- [ ] Local smoke test with cryptoapp (300s) shows BACK actions >0%, UCB scores in log output
- [ ] Note: after archive, consider `/opsx:sync` to update rvsmart/tools spec with UCBScorer and new Config defaults
