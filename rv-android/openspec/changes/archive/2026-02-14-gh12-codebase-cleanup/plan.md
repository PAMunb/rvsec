# Codebase Cleanup: Obsolete Scripts, Duplicated Constants, Minor Fixes

**GitHub Issue**: #12
**Track**: Quick Path
**Date**: 2026-02-14
**Author**: Pedro Henrique Teixeira Costa (with Claude Code assistance)
**Status**: Active

## 1. Motivation

Deep codebase analysis by three LLMs (Gemini, Qwen, Claude) identified several mechanical cleanup items that do not require design decisions but improve codebase hygiene:

1. **15 obsolete test scripts** in root directory importing from discontinued `rvandroid` module — dead code polluting the workspace
2. **6 duplicated file extension constants** between rv-android-core and rv-experiment — violates single source of truth
3. **Log tag constants** in wrong location (`domain/log.py` instead of `util/logging/constants.py`)
4. **PerformanceProcessorComponent** has unnecessary lifecycle ceremony (initialize/cleanup are no-ops)
5. **Unused import** (`LOG_ERROR`) in result_processor.py

All items are independent and mechanical.

## 2. How This Plan Was Produced

1. Gemini CLI identified root test scripts and constants duplication
2. Qwen identified PerformanceProcessorComponent over-engineering
3. Claude independently verified all findings and triaged severity
4. Each `teste_*.py` file was inspected (first 30-40 lines) to determine import dependencies and relevance

## 3. Changes

### Item 1: Delete 15 Obsolete `teste_*.py` Scripts

These files import from the discontinued `rvandroid` module (superseded by the modular architecture). They are legacy exploration scripts from early development cycles.

**Delete:**
- `teste_parser_droidbot.py` — old DroidBot parser test (imports rvandroid)
- `teste_parser_droidbot_novo.py` — old DroidBot parser v2 (imports rvandroid)
- `teste_parser_droidbot_novo_02.py` — old DroidBot parser v3 (imports rvandroid)
- `teste_parser_gator.py` — old GATOR parser test (imports rvandroid)
- `teste_parser_gesda.py` — old GESDA parser test (imports rvandroid)
- `teste_parser_logcat.py` — old logcat parser test (imports rvandroid)
- `teste_parser_reach.py` — old REACH parser test (imports rvandroid)
- `teste_prompt_framework_02.py` — old LLM prompt test (imports rvandroid.llm)
- `teste_reachable.py` — old reachable methods test (imports rvandroid + settings)
- `teste_reachable_novo.py` — old reachable methods v2 (imports rvandroid + settings)
- `teste_results.py` — old results processing (imports rvandroid.analysis)
- `teste_results_merger.py` — old results merger (imports rvandroid.analysis)
- `teste_run_server.py` — old server startup (imports rvandroid server)
- `teste_run_server_novo.py` — old server startup v2 (imports rvandroid server)
- `teste_static_analysis.py` — old static analysis test (imports rvandroid + settings)

**Keep (current modules):**
- `teste_rvagent.py` — uses rv_agent, rv_android_core, rv_static_analysis (current)
- `teste_rv_platform.py` — uses rv_android_core, rv_platform (current)

**Migrate (update imports):**
- `teste_rv_instrument.py` — change `rvandroid.util.logging` → `rv_android_core.util.logging`
- `teste_rv_monitor.py` — change `rvandroid.util.logging` → `rv_android_core.util.logging`

**Backup:** Move deleted files to `backup/teste_scripts_legacy/` before deletion (P3 safety net).

### Item 2: Fix 6 Duplicated Extension Constants

**Problem:** `modules/rv-experiment/src/rv_experiment/constants.py` (lines ~40-50) duplicates 6 file extension constants already defined in `modules/rv-android-core/src/rv_android_core/constants.py`.

| Constant | Core Location | Experiment Location |
|----------|--------------|-------------------|
| `EXTENSION_APK` | core/constants.py:2 | experiment/constants.py:~40 |
| `EXTENSION_METHODS` | core/constants.py:13 | experiment/constants.py:~41 |
| `EXTENSION_GESDA` | core/constants.py:15 | experiment/constants.py:~42 |
| `EXTENSION_REACH` | core/constants.py:14 | experiment/constants.py:~44 |
| `EXTENSION_RVM` | core/constants.py:8 | experiment/constants.py:~48 |
| `EXTENSION_JAVA` | core/constants.py:5 | experiment/constants.py:~50 |

**Fix:**
- In `modules/rv-experiment/src/rv_experiment/constants.py`:
  - Delete the 6 local constant definitions
  - Add import: `from rv_android_core.constants import EXTENSION_APK, EXTENSION_METHODS, EXTENSION_GESDA, EXTENSION_REACH, EXTENSION_RVM, EXTENSION_JAVA`
- Verify all callers in rv-experiment still work (they import from `rv_experiment.constants`, which will now re-export from core)

### Item 3: Move Log Tag Constants to Logging Module

**Problem:** `TAG_RVSEC` and `TAG_RVSEC_COV` are defined in `modules/rv-android-core/src/rv_android_core/domain/log.py` (lines 17-18) but are logging constants, not domain model data.

**Fix:**
- Move both constants to `modules/rv-android-core/src/rv_android_core/util/logging/constants.py`
- Update imports in `domain/log.py` and any other files that reference these tags
- Search: `grep -r "TAG_RVSEC" modules/ --include="*.py"` to find all callers

### Item 4: Simplify PerformanceProcessorComponent

**Problem:** `PerformanceProcessorComponent` in rv-platform follows full component lifecycle (initialize/execute/cleanup) but `initialize()` and `cleanup()` are no-ops. The caller (`ResultProcessorComponent._generate_performance_csv()` at lines 620-629) makes three calls where one suffices.

**File:** `modules/rv-platform/src/rv_platform/components/result_processor.py` (lines 620-629)

**Current:**
```python
performance_processor = PerformanceProcessorComponent(completed_tasks, self.results_dir)
performance_processor.initialize({})        # no-op
performance_processor.execute({})           # does the work
performance_processor.cleanup()             # no-op
summary = performance_processor.get_performance_summary()
```

**After:**
```python
performance_processor = PerformanceProcessorComponent(completed_tasks, self.results_dir)
performance_processor.generate()
summary = performance_processor.get_performance_summary()
```

**Files to edit:**
- `modules/rv-platform/src/rv_platform/components/performance_processor.py` — remove `initialize()`, `cleanup()` no-ops; rename `execute()` → `generate()`
- `modules/rv-platform/src/rv_platform/components/result_processor.py` — update caller (lines 620-629)

### Item 5: Remove Unused Import

**File:** `modules/rv-platform/src/rv_platform/components/result_processor.py` (lines 18-22)
**Fix:** Remove `LOG_ERROR` from the import statement (confirmed unused via grep).

## 4. Task Groups

All items are independent. Can run in parallel.

### Group A: Root script cleanup (Items 1)
- 15 files to delete (backup first)
- 2 files to migrate (import update)
- 2 files to keep (no change)

### Group B: Constants and imports (Items 2, 3, 5)
- `rv-experiment/constants.py` — remove duplicates, add import
- `rv-android-core/domain/log.py` — move tag constants
- `rv-android-core/util/logging/constants.py` — receive tag constants
- `rv-platform/components/result_processor.py` — remove unused import
- Update all callers of moved constants

### Group C: PerformanceProcessor simplification (Item 4)
- `rv-platform/components/performance_processor.py` — simplify API
- `rv-platform/components/result_processor.py` — update caller

## 5. Verification

```bash
# Tests
poetry run pytest modules/rv-android-core/tests/ -v
poetry run pytest modules/rv-platform/tests/ -v
poetry run pytest modules/rv-experiment/tests/ -v

# Confirm no dangling references to rvandroid in root
grep -r "from rvandroid" teste_*.py 2>/dev/null  # should return nothing (files deleted)

# Confirm no duplicated constants
grep "EXTENSION_APK" modules/rv-experiment/src/rv_experiment/constants.py  # should show import, not definition

# Confirm LOG_ERROR not imported
grep "LOG_ERROR" modules/rv-platform/src/rv_platform/components/result_processor.py  # should return nothing
```

## 6. Acceptance Criteria

- [ ] Zero `teste_*.py` files importing from `rvandroid` in root directory
- [ ] Deleted scripts backed up to `backup/teste_scripts_legacy/`
- [ ] 2 migrated scripts (`teste_rv_instrument.py`, `teste_rv_monitor.py`) use `rv_android_core` imports
- [ ] No duplicated extension constants between core and experiment modules
- [ ] `TAG_RVSEC` and `TAG_RVSEC_COV` defined in `util/logging/constants.py`, not `domain/log.py`
- [ ] `PerformanceProcessorComponent` has `generate()` method, no `initialize()`/`cleanup()` no-ops
- [ ] `LOG_ERROR` not imported in result_processor.py
- [ ] All existing tests pass
