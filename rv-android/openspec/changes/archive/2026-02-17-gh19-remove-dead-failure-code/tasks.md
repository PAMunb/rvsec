# Tasks: gh19-remove-dead-failure-code

**GitHub Issue**: [#19](https://github.com/PAMunb/rvsec/issues/19)

## 1. Source Cleanup

- [ ] 1.1 Remove `MAX_FAILURE_ATTEMPTS` constant from `domain/screen_node.py`
- [ ] 1.2 Remove `failed_actions` and `action_failure_counts` fields from `ScreenNode` dataclass
- [ ] 1.3 Remove 4 dead methods from `ScreenNode`: `record_action_failure()`, `reset_action_failure()`, `is_action_failed()`, `get_action_failure_count()`
- [ ] 1.4 Remove 3 delegation methods from `dynamic_state_graph.py`: `record_action_failure()`, `reset_action_failure()`, `is_action_failed()`
- [ ] 1.5 Remove `FailedActionScorer` class from `ranking/scorers.py`
- [ ] 1.6 Remove `FailedActionScorer` from `ranking/__init__.py` (import, docstring, `__all__`)
- [ ] 1.7 Remove `FailedActionScorer` from `rvagent_strategy.py` (import, instantiation, docstring, comments)
- [ ] 1.8 Simplify `_select_continuous_action()` in `rvagent_strategy.py` — remove `is_action_failed` filter, use `actions` directly
- [ ] 1.9 Simplify `_select_continuous_action()` in `dfs_strategy.py` — same pattern
- [ ] 1.10 Simplify `_select_continuous_action()` in `bfs_strategy.py` — same pattern
- [ ] 1.11 Simplify `_select_continuous_action()` in `greedy_strategy.py` — same pattern

## 2. Test Cleanup

- [ ] 2.1 Remove `TestActionFailureTracking` class from `test_dynamic_state_graph.py`
- [ ] 2.2 Remove `FailedActionScorer` assertion from `test_rvagent_strategy_comprehensive.py`
- [ ] 2.3 Update exhausted-state tests in `test_dfs_strategy.py` — remove `is_action_failed` mock
- [ ] 2.4 Update exhausted-state tests in `test_bfs_strategy.py` — remove `is_action_failed` mock

## 3. Documentation Cleanup

- [ ] 3.1 Remove `FailedActionScorer` row from scorer table in `modules/rv-agent/CLAUDE.md`
- [ ] 3.2 Remove `FailedActionScorer` from Mermaid diagram and scorer table in `modules/rv-agent/docs/architecture.md`

## 4. Verification

- [ ] 4.1 Run `grep -r "FailedActionScorer\|record_action_failure\|is_action_failed\|failed_actions\|action_failure_counts\|reset_action_failure\|MAX_FAILURE_ATTEMPTS\|get_action_failure_count" modules/rv-agent/src/` — expect zero matches
- [ ] 4.2 Run `uv run pytest modules/rv-agent/tests/unit/ -v` — all tests pass
- [ ] 4.3 Run `python -c "from rv_agent.strategies.rvagent_strategy.ranking import *"` — no import errors
