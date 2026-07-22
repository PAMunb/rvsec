# Change Plan: gh19-remove-dead-failure-code

**Date**: 2026-02-17
**Track**: Quick Path
**Priority**: Medium
**GitHub Issue**: [#19](https://github.com/PAMunb/rvsec/issues/19)
**PRD Reference**: N/A
**Domains**: agent (rv-agent)

## 1. Context

Issue #19 was originally titled "Connect failure detection to FailedActionScorer" — it identified that `ScreenNode.record_action_failure()` exists but is never called from the agent workflow, making `FailedActionScorer` permanently return 0.

The issue assumed gh18 (error detection) would resolve this by connecting error detection to the failure tracking mechanism. However, gh18 took a completely different approach: it introduced `VisualErrorDetector` — a vision-based system that detects error messages on screen and triggers recovery actions. This design has no relationship to the coordinate-based action failure tracking in `ScreenNode.failed_actions`.

The entire failure tracking subsystem is dead code:
- `record_action_failure()` is never called from anywhere in the workflow
- `failed_actions` set is always empty
- `FailedActionScorer` always returns 0 (never penalizes anything)
- `is_action_failed()` always returns `False` in all 4 strategies
- The `_filter_safe_actions` pattern in each strategy (filtering by `is_action_failed`) does nothing

Per P3 (No Backward Compatibility), dead code must be deleted entirely.

## 2. Scope

**Module**: rv-agent only (single module, no cross-module impact)

**Groups**:
- **Group A (Source)**: Remove dead code from production source files (screen_node.py, dynamic_state_graph.py, scorers.py, rvagent_strategy.py, ranking/__init__.py, dfs/bfs/greedy strategies)
- **Group B (Tests)**: Remove tests that exercise dead code, update tests that mock `is_action_failed`
- **Group C (Docs)**: Remove `FailedActionScorer` references from CLAUDE.md and architecture.md

## 3. File Inventory

All paths relative to `modules/rv-agent/src/rv_agent/`.

### Group A: Source Files

| File | Action | Detail |
|------|--------|--------|
| `domain/screen_node.py:12-13` | Remove | `MAX_FAILURE_ATTEMPTS` constant |
| `domain/screen_node.py:60-62` | Remove | `failed_actions` and `action_failure_counts` fields from ScreenNode dataclass |
| `domain/screen_node.py:112-174` | Remove | 4 methods: `record_action_failure()`, `reset_action_failure()`, `is_action_failed()`, `get_action_failure_count()` |
| `agent/dynamic_state_graph.py:309-365` | Remove | 3 delegation methods: `record_action_failure()`, `reset_action_failure()`, `is_action_failed()` |
| `strategies/rvagent_strategy/ranking/scorers.py:311-349` | Remove | Entire `FailedActionScorer` class |
| `strategies/rvagent_strategy/ranking/__init__.py:8,23,42` | Edit | Remove `FailedActionScorer` from docstring, import, and `__all__` |
| `strategies/rvagent_strategy/rvagent_strategy.py:36` | Edit | Remove `FailedActionScorer` import |
| `strategies/rvagent_strategy/rvagent_strategy.py:194` | Edit | Remove `FailedActionScorer` instantiation from `ActionRanker` scorers list |
| `strategies/rvagent_strategy/rvagent_strategy.py:387` | Edit | Remove comment referencing `node.failed_actions` |
| `strategies/rvagent_strategy/rvagent_strategy.py:590-597` | Edit | Simplify `_select_continuous_action()`: remove `is_action_failed` filter, pass `actions` directly instead of building `safe_actions` |
| `strategies/rvagent_strategy/rvagent_strategy.py:627,636` | Edit | Update docstring: remove `FailedActionScorer` line, update scorer count from 8 to 7 |
| `strategies/dfs_strategy.py:452-463` | Edit | Same simplification: remove `is_action_failed` filter in `_select_continuous_action()` |
| `strategies/bfs_strategy.py:454-465` | Edit | Same simplification: remove `is_action_failed` filter in `_select_continuous_action()` |
| `strategies/greedy_strategy.py:514-525` | Edit | Same simplification: remove `is_action_failed` filter in `_select_continuous_action()` |

### Group B: Test Files

All paths relative to `modules/rv-agent/tests/`.

| File | Action | Detail |
|------|--------|--------|
| `unit/test_dynamic_state_graph.py:244-327` | Remove | Entire `TestActionFailureTracking` class (8 tests) |
| `unit/test_rvagent_strategy_comprehensive.py:304` | Edit | Remove `assert "FailedActionScorer" in scorer_types` |
| `unit/test_dfs_strategy.py:452` | Edit | Remove `mock_screen_node.is_action_failed = Mock(return_value=True)` — adjust test to not depend on failure tracking |
| `unit/test_bfs_strategy.py:566,592` | Edit | Remove `mock_screen_node.is_action_failed = Mock(return_value=True)` — adjust tests |

### Group C: Documentation

| File | Action | Detail |
|------|--------|--------|
| `CLAUDE.md:484` | Edit | Remove `FailedActionScorer` row from scorer table |
| `docs/architecture.md:433-435,442,454` | Edit | Remove `FailedActionScorer` from Mermaid diagram and scorer table |

## 4. Execution Order

All groups are independent — the changes don't conflict:

```
Group A (Source)  ─┐
Group B (Tests)   ─┼── parallel execution (no dependencies)
Group C (Docs)    ─┘
```

However, this is a small change (14 files, ~200 lines removed). Subagent orchestration is not warranted — direct execution is sufficient.

## 5. Acceptance Criteria

- [ ] `grep -r "record_action_failure\|FailedActionScorer\|is_action_failed\|failed_actions\|action_failure_counts\|reset_action_failure\|MAX_FAILURE_ATTEMPTS\|get_action_failure_count" modules/rv-agent/src/` returns zero matches
- [ ] `grep -r "FailedActionScorer" modules/rv-agent/` returns zero matches (source + tests + docs)
- [ ] `uv run pytest modules/rv-agent/tests/unit/ -v` passes (all remaining tests)
- [ ] `uv run pytest modules/rv-agent/tests/unit/test_dynamic_state_graph.py -v` passes with no failure tracking tests
- [ ] `uv run pytest modules/rv-agent/tests/unit/test_rvagent_strategy_comprehensive.py -v` passes
- [ ] `uv run pytest modules/rv-agent/tests/unit/test_dfs_strategy.py -v` passes
- [ ] `uv run pytest modules/rv-agent/tests/unit/test_bfs_strategy.py -v` passes
- [ ] No import errors when running `python -c "from rv_agent.strategies.rvagent_strategy.ranking import *"`
