## 1. Prerequisites

- [ ] 1.1 Verify gh16-unify-toolconfig is committed and line numbers are stable
- [ ] 1.2 Verify current line numbers match plan.md file inventory (adjust if needed post-gh16)

## 2. Group A — Magic Numbers (rv-agent) (parallel)

- [ ] 2.1 Add constants to `constants.py`: `DEFAULT_DEVICE_WIDTH`, `DEFAULT_DEVICE_HEIGHT`, `NAVBAR_THRESHOLD_Y`
- [ ] 2.2 Replace 8 inline coordinate conversions (`704/1080`, `1248/1920`) with `device_to_optimized()` calls in dfs_strategy.py, bfs_strategy.py, rvagent_strategy.py, scorers.py (3 methods), learn_node.py
- [ ] 2.3 Replace 3 hardcoded `1794` values with `NAVBAR_THRESHOLD_Y` in dfs_strategy.py, bfs_strategy.py, greedy_strategy.py

## 3. Group B — Duplicate Method + Inline TODOs (rv-experiment) (parallel)

- [ ] 3.1 Delete duplicate `get_rv_instrumentation_config()` (shadow copy ~line 731) in config.py
- [ ] 3.2 Resolve TODO in config.py docstring (~line 175): remove or implement directory validation
- [ ] 3.3 Resolve `# TODO remover esses "templates"` in __main__.py (~line 867): verify usage, delete dead code or TODO

## 4. Group C — Dead Config Fields (rv-agent) (parallel with Group A)

- [ ] 4.1 Delete `verbose_counters` field and `get_verbose_counters()` method from agent_config.py
- [ ] 4.2 Delete `enable_coordinate_enhancement` field and its check in `validate()` from agent_config.py
- [ ] 4.3 Clean up remaining TODOs in agent_config.py: delete TODO on `results_dir`, replace TODO on `debug_mode` with clarifying comment

## 5. Group D — Obsolete TODOs (multi-module) (parallel)

- [ ] 5.1 Delete 3 empty/resolved TODOs: screenshot_analyzer.py:154, default_visitor.py:624, pre_processor.py:157
- [ ] 5.2 Investigate and resolve ~6 inline TODOs: abstract_visitor.py:72, default_visitor.py:131, visitor_factory.py:52, gesda_parser.py:161, static_analysis.py:383, android.py:10
- [ ] 5.3 Resolve memory_coordinator.py:219 `success=True # TODO` and rvandroid.py:794 `# TODO: Implement zipalign`

## 6. Group E — GitHub Issues for Future Work

- [ ] 6.1 Create ~7 GitHub Issues for legitimate future-work TODOs (see plan.md Group E table)
- [ ] 6.2 Update TODO comments in source to reference the created issue numbers (e.g., `# TODO(#N): description`)

## 7. Group F — Evaluate BaseDetector

- [ ] 7.1 Evaluate whether BaseDetector abstraction for 4 detector classes is justified per P1 (likely skip — document decision inline)

## 8. Verification

- [ ] 8.1 Run `uv run pytest modules/rv-agent/tests/unit/ -v` — all tests pass
- [ ] 8.2 Run `uv run pytest modules/rv-experiment/tests/ -v` — all tests pass
- [ ] 8.3 Run `uv run pytest modules/rv-screen-parser/tests/ -v` — all tests pass
- [ ] 8.4 Verify acceptance criteria from plan.md (grep checks for magic numbers, duplicates, TODO count)
- [ ] 8.5 Run `/rv-verify` on affected modules (tests + lint)
