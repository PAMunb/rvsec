# Change Plan: gh28-fix-scorer-bugs

**Date**: 2026-02-25
**Track**: Quick Path
**Priority**: High
**GitHub Issue**: [#28](https://github.com/PAMunb/rvsec/issues/28)
**PRD Reference**: FR21-FR32 (Agent exploration)
**Domains**: agent

## 1. Context

The rv-agent (`pure_algorithm` mode) underperforms APE and FastBot significantly, even with 30 minutes of execution. Analysis of baseline_v2 logs revealed 26.2% BACK/RESTART actions, scores of -4852 for legitimate buttons, and 19-22% coverage — all symptoms of the scoring system penalizing valid UI elements.

After validating 14+ hypotheses from Codex/Gemini analysis, 3 confirmed bugs were found in the action scoring/ranking subsystem:

1. **B1 (Critical)**: `SystemElementFilter` penalizes `package="android"` with -5000, but `SYSTEM_DIALOG_PACKAGES` in the same module explicitly allows `"android"` for system dialogs (permissions, alerts). This contradiction causes legitimate dialog buttons to receive massive negative scores.

2. **B2 (Medium)**: `_select_with_score_decay()` divides base scores by a decay factor. For negative scores, this makes them *less* negative (e.g., -5000 / 2.0 = -2500), which is the opposite of intended behavior — negative scores should become *more* negative with more executions.

3. **B3 (Low)**: `MopScorer` has a deferral block that checks `action.action_type`, but `ItemAction` has no `action_type` field. `getattr(action, "action_type", "")` always returns `""`, so the condition never triggers — dead code.

## 2. Scope

Single module: **rv-agent**. Two source files and three test files affected.

## 3. File Inventory

| File | Action | Detail |
|------|--------|--------|
| `modules/rv-agent/src/rv_agent/strategies/rvagent_strategy/ranking/scorers.py:336` | Edit | Remove `"android"` from `SYSTEM_PACKAGES`, keep only `"com.android.systemui"` |
| `modules/rv-agent/src/rv_agent/strategies/rvagent_strategy/ranking/scorers.py:87-91` | Delete | Remove dead deferral block in `MopScorer.score()` |
| `modules/rv-agent/src/rv_agent/strategies/rvagent_strategy/ranking/scorers.py:9` | Edit | Update docstring — remove "(with form-context deferral)" from MopScorer description |
| `modules/rv-agent/src/rv_agent/strategies/rvagent_strategy/rvagent_strategy.py:1029-1033` | Edit | Fix score decay: multiply negative scores by decay_factor instead of dividing |
| `modules/rv-agent/tests/unit/test_scorer_bugfixes.py` | Create | New test file covering all 3 fixes (13 tests) |
| `modules/rv-agent/tests/unit/strategies/ranking/test_mop_scorer_deferral.py` | Rewrite | Replace phantom deferral tests with actual MopScorer behavior tests |
| `modules/rv-agent/tests/unit/test_group25_fixes.py:98-165` | Edit | Replace `TestMopScorerDeferral` class with `TestMopScorerScoring` reflecting corrected behavior |

## 4. Execution Order

All changes are independent and touch different code sections — no ordering dependency. However, this is a small change (5 files), so no subagent orchestration needed.

Sequential: B1 fix → B3 fix → B2 fix → test updates → new tests → verification.

## 5. Acceptance Criteria

- [x] `SystemElementFilter.SYSTEM_PACKAGES` contains only `"com.android.systemui"`
- [x] Score decay multiplies negative scores by decay_factor (more negative = less attractive)
- [x] MopScorer deferral dead code removed
- [x] New test file `test_scorer_bugfixes.py` with 13 tests covering all 3 fixes
- [x] Existing tests updated to reflect corrected behavior (no phantom deferral tests)
- [x] All rv-agent unit tests pass (1500+, zero failures)
