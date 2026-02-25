# Tasks: gh28-fix-scorer-bugs

**Change**: [gh28-fix-scorer-bugs](plan.md)
**GitHub Issue**: [#28](https://github.com/PAMunb/rvsec/issues/28)

## 1. Fix Source Code

- [x] 1.1 Remove `"android"` from `SystemElementFilter.SYSTEM_PACKAGES` in `scorers.py:336`, keeping only `"com.android.systemui"`
- [x] 1.2 Remove MopScorer deferral dead code block (`scorers.py:87-91`)
- [x] 1.3 Update MopScorer docstring in module header (`scorers.py:9`) — remove "(with form-context deferral)"
- [x] 1.4 Fix score decay sign in `rvagent_strategy.py:1029-1033` — multiply negative scores by `decay_factor` instead of dividing

## 2. Update Existing Tests

- [x] 2.1 Rewrite `test_mop_scorer_deferral.py` — replace phantom deferral tests with actual MopScorer behavior tests
- [x] 2.2 Replace `TestMopScorerDeferral` in `test_group25_fixes.py:98-165` with `TestMopScorerScoring`

## 3. Add New Tests

- [x] 3.1 Create `test_scorer_bugfixes.py` with:
  - `TestSystemElementFilterPackageFix` (6 tests): android→0.0, systemui→-5000, app→0.0, no target→0.0, empty pkg→0.0, set contents
  - `TestScoreDecaySign` (4 tests): negative more negative, positive smaller, zero unchanged, no exec no decay
  - `TestMopScorerDeferralRemoved` (3 tests): direct MOP scored, transitive scored, non-MOP zero

## 4. Verification

- [x] 4.1 Run new tests: `uv run pytest modules/rv-agent/tests/unit/test_scorer_bugfixes.py -v` — 13 passed
- [x] 4.2 Run all unit tests: `uv run pytest modules/rv-agent/tests/unit/ -v -m "not slow"` — 1523 passed
- [x] 4.3 Confirm zero failures across all 1500+ tests — 0 failures
