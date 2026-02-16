# Change Plan: Refactoring Cleanup (Magic Numbers, Duplicates, TODOs)

**Date**: 2026-02-15
**Track**: Quick Path
**Priority**: High
**GitHub Issue**: [#17](https://github.com/PAMunb/rvsec/issues/17)
**PRD Reference**: N/A (internal refactoring, no behavior changes)
**Domains**: agent, experiment, analysis, core

## 1. Context

Codebase analysis (documented in `docs/20260215_plano_refatoracao.md`) identified four categories of code quality issues across multiple modules. None of these require design decisions — they are mechanical cleanup tasks aligned with principles P1 (Simplicity) and P3 (No backward compatibility).

The issues are:
- **R1**: Coordinate conversion math (`704/1080`, `1248/1920`) copy-pasted 8+ times in rv-agent when `coordinate_utils.device_to_optimized()` already exists and does the same calculation
- **R2**: `get_rv_instrumentation_config()` defined twice in rv-experiment's `config.py` — the second definition shadows the first
- **R3**: 25 TODO/FIXME markers across 15 files — 3 obsolete (empty or already resolved), 4 dead config fields, ~10 resolvable inline, ~7 that should become GitHub Issues
- **R4**: 4 detector classes in rv-screen-parser with identical 5-line init pattern — evaluate whether a `BaseDetector` abstraction is justified per P1

**Pre-condition**: gh16-unify-toolconfig must be committed first (Decision D8 in the ideation doc) because it modifies overlapping files in rv-experiment (`config.py`, `__main__.py`) and rv-android-core (`task.py`).

## 2. Scope

Four independent refactoring items grouped by module:

- **Group A (rv-agent)**: R1 — replace 8 magic number expressions with `device_to_optimized()` calls, add missing constants, replace 3 hardcoded `1794` navbar thresholds
- **Group B (rv-experiment)**: R2 — delete duplicate method; R3.3 — resolve inline TODOs in `config.py` and `__main__.py`
- **Group C (rv-agent config)**: R3.4 — delete dead config fields (`verbose_counters`, `enable_coordinate_enhancement`) and associated code
- **Group D (rv-screen-parser, rv-static-analysis, rv-android-core)**: R3.1 — delete 3 obsolete TODO comments; R3.3 — resolve inline TODOs
- **Group E (GitHub Issues)**: R3.2 — create ~7 GitHub Issues for legitimate future work TODOs
- **Group F (rv-screen-parser)**: R4 — evaluate `BaseDetector` abstraction (likely skip per P1)

## 3. File Inventory

**NOTE**: Line numbers below are approximate and must be verified post-gh16 before implementation.

### Group A — Magic Numbers (rv-agent)

| File | Action | Detail |
|------|--------|--------|
| `modules/rv-agent/src/rv_agent/constants.py` | Edit | Add `DEFAULT_DEVICE_WIDTH = 1080`, `DEFAULT_DEVICE_HEIGHT = 1920`, `NAVBAR_THRESHOLD_Y = 1794` |
| `modules/rv-agent/src/rv_agent/strategies/dfs_strategy.py` | Edit | Lines ~521-522: replace `int(x * 704 / 1080)` with `device_to_optimized()` call |
| `modules/rv-agent/src/rv_agent/strategies/bfs_strategy.py` | Edit | Lines ~523-524: replace inline math with `device_to_optimized()` call |
| `modules/rv-agent/src/rv_agent/strategies/rvagent_strategy/rvagent_strategy.py` | Edit | Lines ~829-830: replace fallback inline math with `device_to_optimized()` call |
| `modules/rv-agent/src/rv_agent/strategies/rvagent_strategy/ranking/scorers.py` | Edit | Lines ~213-214, ~338-339, ~483-484: replace 3 `_convert_to_optimized()` methods with `device_to_optimized()` calls |
| `modules/rv-agent/src/rv_agent/agent/nodes/learn_node.py` | Edit | Lines ~338-339: replace inline conversion in `_update_strategy_with_result()` |
| `modules/rv-agent/src/rv_agent/strategies/dfs_strategy.py` | Edit | Replace hardcoded `1794` with `NAVBAR_THRESHOLD_Y` constant |
| `modules/rv-agent/src/rv_agent/strategies/bfs_strategy.py` | Edit | Replace hardcoded `1794` with `NAVBAR_THRESHOLD_Y` constant |
| `modules/rv-agent/src/rv_agent/strategies/greedy_strategy.py` | Edit | Replace hardcoded `1794` with `NAVBAR_THRESHOLD_Y` constant (if present) |

### Group B — Duplicate Method + Inline TODOs (rv-experiment)

| File | Action | Detail |
|------|--------|--------|
| `modules/rv-experiment/src/rv_experiment/config.py` | Edit | Delete duplicate `get_rv_instrumentation_config()` (~lines 731-744, the shadow copy). Keep ~lines 498-527 (has full docstring) |
| `modules/rv-experiment/src/rv_experiment/config.py` | Edit | Line ~175: remove TODO from docstring (directory structure validation) |
| `modules/rv-experiment/src/rv_experiment/__main__.py` | Edit | Line ~867: resolve `# TODO remover esses "templates"` — verify if templates are used, delete TODO or delete dead code |

### Group C — Dead Config Fields (rv-agent)

| File | Action | Detail |
|------|--------|--------|
| `modules/rv-agent/src/rv_agent/config/agent_config.py` | Edit | Delete field `verbose_counters` (~line 128) and method `get_verbose_counters()` — zero callers (confirmed by grep) |
| `modules/rv-agent/src/rv_agent/config/agent_config.py` | Edit | Delete field `enable_coordinate_enhancement` (~line 140) and remove check in `validate()` (~line 410) — flag can only be True, so it's not a flag |
| `modules/rv-agent/src/rv_agent/config/agent_config.py` | Edit | Line ~50: delete `# TODO O que teremos de output?` (field `results_dir` IS used by CLI) |
| `modules/rv-agent/src/rv_agent/config/agent_config.py` | Edit | Line ~124: delete `# TODO qual a diferença para debug_mode?` and add clarifying comment: `debug_mode` is CLI shortcut, `log_level` is granular config |

### Group D — Obsolete TODOs (multi-module)

| File | Action | Detail |
|------|--------|--------|
| `modules/rv-screen-parser/src/rv_screen_parser/screenshot/screenshot_analyzer.py` | Edit | Line ~154: delete empty `# TODO` comment |
| `modules/rv-screen-parser/src/rv_screen_parser/screenshot/visitors/default_visitor.py` | Edit | Line ~624: delete empty `# TODO` comment |
| `modules/rv-experiment/src/rv_experiment/experiment/workflow/pre_processor.py` | Edit | Line ~157: delete resolved `# TODO salvar arquivo de erros json` (ResultManager handles this) |
| `modules/rv-screen-parser/src/rv_screen_parser/screenshot/visitors/abstract_visitor.py` | Edit | Line ~72: check if `device_info` field is used anywhere; if not, delete field + TODO |
| `modules/rv-screen-parser/src/rv_screen_parser/screenshot/visitors/default_visitor.py` | Edit | Line ~131: verify MOP checking logic; if correct, delete `# TODO rever` |
| `modules/rv-screen-parser/src/rv_screen_parser/screenshot/visitors/visitor_factory.py` | Edit | Line ~52: verify argument passing; if correct, delete `# TODO rever argumento` |
| `modules/rv-static-analysis/src/rv_static_analysis/parsers/gesda_parser.py` | Edit | Line ~161: verify Widget type; if correct, delete `# TODO rever tipo` |
| `modules/rv-static-analysis/src/rv_static_analysis/static_analysis.py` | Edit | Line ~383: delete `# TODO usar performance monitor` (P1: manual timing is adequate) |
| `modules/rv-android-core/src/rv_android_core/util/android/android.py` | Edit | Line ~10: delete `# TODO logging manager` or switch to LoggingManager |

### Group E — GitHub Issues for Future Work

| TODO Location | Action | Issue Title |
|---------------|--------|-------------|
| `rv-agent/.../screen_node.py:120` | Create Issue | "Connect failure detection to FailedActionScorer" |
| `rv-agent/.../learn_node.py:307` | Create Issue | "Improve action success detection beyond screen hash" |
| `rv-agent/.../screen_analyzer.py:271` | Create Issue | "Unify scoring between screen_analyzer and rvagent_strategy" |
| `rv-agent/.../device_interface.py:381` | Create Issue | "Implement press_keycode in DeviceInterface" |
| `rv-instrumentation/.../rvandroid.py:637,895,1027` | Create Issue | "Dynamic Android JAR selection based on target SDK" |
| `rv-android-core/.../dynamic_wtg.py:417` | Create Issue | "Fix type mismatch in DynamicWTG.record_transition()" |
| `rv-android-core/.../task.py:207,209` | Create Issue | "Remove deprecated fields from TaskConfiguration" |

### Group F — Evaluate BaseDetector (rv-screen-parser)

| File | Action | Detail |
|------|--------|--------|
| `modules/rv-screen-parser/src/rv_screen_parser/screenshot/detectors/button_detector.py` | Evaluate | 5-line init pattern — extract to BaseDetector? |
| `modules/rv-screen-parser/src/rv_screen_parser/screenshot/detectors/error_detector.py` | Evaluate | Same init pattern |
| `modules/rv-screen-parser/src/rv_screen_parser/screenshot/detectors/interactive_element_detector.py` | Evaluate | Same init pattern |
| `modules/rv-screen-parser/src/rv_screen_parser/screenshot/detectors/text_detector.py` | Evaluate | Same init pattern |

**Decision**: Likely skip per P1 ("three similar lines > premature abstraction"). 5 lines x 4 files does not justify a new base class with its own inheritance complexity.

## 4. Execution Order

Groups A, B, C, D are independent and can run in parallel via subagent dispatch:
- **Group A** (rv-agent magic numbers): 9 files, self-contained in rv-agent
- **Group B** (rv-experiment cleanup): 2 files, self-contained in rv-experiment
- **Group C** (rv-agent config): 1 file, self-contained in rv-agent config
- **Group D** (multi-module TODOs): 9 files across 4 modules, each edit is independent

**Group E** (GitHub Issues) has no code dependencies and can run anytime.

**Group F** (BaseDetector evaluation) is a decision point — evaluate during implementation, likely skip.

**Suggested dispatch**: Groups A+C as one subagent (both rv-agent), Group B as one subagent, Group D as one subagent, Group E as one subagent.

## 5. Acceptance Criteria

- [ ] `grep -rn "704 / 1080\|1248 / 1920\|\\* 704\|\\* 1248" modules/rv-agent/src/` returns 0 hits (excluding constants.py and coordinate_utils.py docstrings)
- [ ] `grep -rn "1794" modules/rv-agent/src/` returns 0 hits (excluding constants.py)
- [ ] `grep -n "def get_rv_instrumentation_config" modules/rv-experiment/src/rv_experiment/config.py` returns exactly 1 result
- [ ] `grep -rn "verbose_counters\|enable_coordinate_enhancement" modules/rv-agent/src/rv_agent/config/` returns 0 hits
- [ ] `grep -rn "TODO\|FIXME" modules/*/src/ --include="*.py" | wc -l` reduced from 25 to ≤5
- [ ] ~7 GitHub Issues created for legitimate future-work TODOs
- [ ] `uv run pytest modules/rv-agent/tests/unit/ -v` passes
- [ ] `uv run pytest modules/rv-experiment/tests/ -v` passes
- [ ] `uv run pytest modules/rv-screen-parser/tests/ -v` passes
