# Change Plan: Project Finalization — Quality, Documentation, and Cleanup

**Date**: 2026-04-03
**Track**: Quick Path
**Priority**: High (thesis deadline 2026-04-13)
**GitHub Issue**: [#48](https://github.com/PAMunb/rvsec/issues/48)
**PRD Reference**: NFR1 (Maintainability), NFR6 (Documentation), NFR8 (Reproducibility)
**Domains**: core, platform, experiment, agent, instrumentation, analysis, tools

## 1. Context

RV-Android is functionally complete. With ~10 days before thesis submission, the project needs finalization: archive deprecated modules, remove dead code, enforce code quality (lint + format), generate comprehensive documentation for all modules, increase test coverage in under-tested modules, close obsolete issues/changes, and verify everything works end-to-end.

The system has 16 modules in the workspace. Two modules (rvsmart-tool, rv-agent-validation) are no longer needed and should be archived. The rvsmart OpenSpec spec (`openspec/specs/rvsmart/`) must also be archived, and rvsmart references removed from specs in aperv, platform, and tools domains. Nine modules lack architecture documentation. Code quality debt exists across all modules (formatting inconsistencies). Test coverage has critical gaps (rv-uiautomator has only 3 tests). Several GitHub issues and OpenSpec changes are obsolete.

## 2. Scope

**14 modules remaining** (after archiving rvsmart-tool and rv-agent-validation):

| Group | Modules | Work |
|-------|---------|------|
| **TG1: Archival** | rvsmart-tool, rv-agent-validation + OpenSpec rvsmart spec | Archive 2 modules, archive rvsmart spec, update references in code and specs |
| **TG2: Dead Code** | All 14 remaining modules | Remove dead imports, constants, stale comments |
| **TG3: Lint & Fix** | All 14 remaining modules | black + isort + flake8 |
| **TG4: Docstrings** | All 14 remaining modules (key files) | Code-level documentation |
| **TG5: Module Docs** | 8 modules missing arch docs, 3 missing CLAUDE.md, 2 missing README | CLAUDE.md, README.md, architecture.md |
| **TG6: Tests** | rv-uiautomator, rv-instrumentation, rv-monitor-generator, rv-tools | Add tests for public APIs |
| **TG7: Verification** | All 14 remaining modules + project level | Final checks, metrics, issue cleanup |

## 3. File Inventory

### TG1: Housekeeping & Module Archival

| File | Action | Detail |
|------|--------|--------|
| `modules/rvsmart-tool/` | Move | Move entire directory to `backup/rvsmart-tool` |
| `modules/rv-agent-validation/` | Move | Move entire directory to `backup/rv-agent-validation` |
| `pyproject.toml` | Edit | Remove `rvsmart-tool` and `rv-agent-validation` from workspace members |
| `modules/rv-platform/src/rv_platform/__init__.py` | Edit | Remove rvsmart-tool lazy import |
| `modules/aperv-tool/src/aperv_tool/tools/aperv/tool.py` | Edit | Remove rvsmart references |
| `openspec/specs/rvsmart/` | Move | Move entire spec directory to `backup/openspec-specs-rvsmart` |
| `openspec/specs/tools/spec.md` | Edit | Remove rvsmart-tool references |
| `openspec/specs/aperv/spec.md` | Edit | Remove rvsmart references |
| `openspec/specs/platform/spec.md` | Edit | Remove rvsmart references |
| `openspec/specs/agent/spec.md` | Edit | Remove rv-agent-validation references |
| `openspec/specs/analysis/spec.md` | Edit | Remove rv-agent-validation references |
| `docs/rv_android_architecture.md` | Edit | Remove rvsmart-tool and rv-agent-validation from diagrams/tables |
| `CLAUDE.md` | Edit | Update module list (14 modules), remove rvsmart and rv-agent-validation references |
| `.claude/AGENTS.md` | Edit | Update module references if present |

### TG2: Dead Code Removal

Per-module via `/rv-cleanup`. Key known targets:

| File | Action | Detail |
|------|--------|--------|
| `modules/rv-android-core/src/rv_android_core/constants.py` | Edit | Remove ~53 dead constants (77% dead) |
| `modules/rv-agent/src/rv_agent/agent/rv_agent.py` | Edit | Remove 6 unused imports |
| All modules `src/**/*.py` | Edit | Remove dead imports found by pyflakes |
| All modules `src/**/*.py` | Edit | Review 10 TODO/FIXME comments, remove stale ones |

### TG3: Lint & Fix

Per-module via `/rv-qa-lint-fix`. No specific file inventory — automated tool handles it.

### TG4: Docstrings

Key files per module (priority order):

| Module | Key Files |
|--------|-----------|
| rv-android-core | `domain/task.py`, `domain/coverage.py`, `error_handler.py`, `command.py`, `abstract_tool.py` |
| rv-agent | `agent/rv_agent.py`, `strategies/rvagent_strategy/rvagent_strategy.py`, `llm/llm_client.py`, `services/transition_manager.py`, `agent/nodes/*.py` |
| rv-platform | `platform.py`, `task_executor.py`, `storage/task_storage.py`, `config.py` |
| rv-experiment | `controller.py`, `execution_controller.py`, `config.py`, `__main__.py` |
| rv-tools | `registry.py`, `factory.py`, `builtin/*/tool.py` |
| rv-screen-parser | `parser/screen/visitor/abstract_visitor.py`, `parser/screen/visitor/enhanced_visitor.py` |
| rv-static-analysis | `analyzer.py`, `parser.py` |
| rv-coverage | `coverage_tracker.py`, `parser.py` |
| rv-uiautomator | `adapter.py`, `action_executor.py` |
| rv-instrumentation | `rvandroid.py` |
| rv-monitor-generator | `generator.py` |
| rvagent-tool | `tool.py` |
| aperv-tool | `tool.py` |
| aperv-llm-validation | `pipeline/*.py`, `constants.py` |

### TG5: Module Documentation

| Module | Missing | Skill |
|--------|---------|-------|
| rv-screen-parser | architecture.md | `/rv-doc-architecture rv-screen-parser` |
| rv-static-analysis | architecture.md | `/rv-doc-architecture rv-static-analysis` |
| rv-coverage | architecture.md | `/rv-doc-architecture rv-coverage` |
| rv-uiautomator | architecture.md | `/rv-doc-architecture rv-uiautomator` |
| rv-instrumentation | architecture.md | `/rv-doc-architecture rv-instrumentation` |
| rv-monitor-generator | architecture.md | `/rv-doc-architecture rv-monitor-generator` |
| rvagent-tool | CLAUDE.md, architecture.md | `/rv-doc-generate-claude-md rvagent-tool`, `/rv-doc-architecture rvagent-tool` |
| aperv-tool | README.md, CLAUDE.md, architecture.md | `/rv-doc-readme aperv-tool`, `/rv-doc-generate-claude-md aperv-tool`, `/rv-doc-architecture aperv-tool` |
| aperv-llm-validation | README.md, CLAUDE.md, architecture.md | `/rv-doc-readme aperv-llm-validation`, `/rv-doc-generate-claude-md aperv-llm-validation`, `/rv-doc-architecture aperv-llm-validation` |
| All 14 modules | Update existing docs | `/rv-docs-sync <module>` |
| Project root | CLAUDE.md update | Update module count, remove archived module references |

### TG6: Test Coverage

| Module | Current Tests | Target | Focus |
|--------|--------------|--------|-------|
| rv-uiautomator | 3 | >=20 | UIAdapter, ActionExecutor, StateConverter public APIs |
| rv-instrumentation | 12 | >=25 | Instrumentation pipeline, config validation |
| rv-monitor-generator | 17 | >=25 | Generator, spec parsing, output validation |
| rv-tools | 81 | >=100 | ToolRegistry edge cases, ToolFactory, builtin tool configs |

### TG7: Final Verification

| Action | Detail |
|--------|--------|
| Close issues | #34, #35, #36, #39 (rvsmart — archived), assess #20-#25, #41-#43 |
| Archive OpenSpec changes | gh34, gh35, gh36, gh43, gh9 (stale) |
| pyproject.toml audit | Verify version, description, authors, license in all 14 modules |
| CLI entry points | Test `rv-experiment --help`, `rv-platform --help`, `rv-agent --help` |
| Metrics report | Generate LOC, test count, complexity (radon), per module summary |
| OpenSpec specs sync | Sync any pending delta specs to main specs |
| `/rv-verify` | Run on all 14 modules |
| `/rv-code-reviewer` | Run on core, agent, platform, experiment |

## 4. Execution Order

```
TG1 (Archival) ──────────────────────────────────────────────┐
                                                              │
TG2 (Dead Code) ── depends on TG1 ───────────────────────────┤
                                                              │
TG3 (Lint & Fix) ── depends on TG2 ──────────────────────────┤
                                                              │
TG4 (Docstrings) ── depends on TG3 ──┐                       │
                                       ├── can run in parallel│
TG5 (Module Docs) ── depends on TG3 ──┘                      │
                                                              │
TG6 (Tests) ── depends on TG3, independent of TG4/TG5 ───────┤
                                                              │
TG7 (Verification) ── depends on ALL above ───────────────────┘
```

**Subagent dispatch** (WORKFLOW.md Section 5):
- TG2: 3-4 modules per subagent batch (independent modules in parallel)
- TG3: 3-4 modules per subagent batch
- TG4 + TG5: Can run in parallel, 2-3 modules per subagent
- TG6: Each module independently via subagent

## 5. Acceptance Criteria

- [ ] AC1: rvsmart-tool and rv-agent-validation archived in `backup/`; rvsmart spec archived; workspace builds cleanly with `uv sync`
- [ ] AC2: No dead imports across any module (pyflakes clean); dead constants removed from rv-android-core
- [ ] AC3: `black --check` and `isort --check` pass on all modules; flake8 errors reduced by >80%
- [ ] AC4: Key files in all modules have module-level and class/function docstrings
- [ ] AC5: All 14 modules have CLAUDE.md, README.md, and architecture.md
- [ ] AC6: rv-uiautomator >=20 tests, rv-instrumentation >=25, rv-monitor-generator >=25
- [ ] AC7: `/rv-verify` passes on all modules; CLI entry points functional
- [ ] AC8: Obsolete GitHub issues closed; stale OpenSpec changes archived
- [ ] AC9: pyproject.toml metadata consistent across all modules (version, authors, license)
- [ ] AC10: Project metrics report generated (LOC, tests, complexity per module)
