<!-- Dependency hints:
     - TG1 must complete first — TG2 depends on it (archived modules removed from workspace).
     - TG2 must complete before TG3 (dead code removed before formatting).
     - TG3 must complete before TG4, TG5, TG6 (clean code before documenting/testing).
     - TG4 and TG5 are independent and can run in parallel.
     - TG6 is independent of TG4/TG5 and can run in parallel with them.
     - TG7 (Verification) must run after all other groups. -->

## 1. Housekeeping & Module Archival

- [x] 1.1 Move `modules/rvsmart-tool/` to `backup/rvsmart-tool`
- [x] 1.2 Move `modules/rv-agent-validation/` to `backup/rv-agent-validation`
- [x] 1.3 Move `openspec/specs/rvsmart/` to `backup/openspec-specs-rvsmart`
- [x] 1.4 Edit `pyproject.toml`: remove `rvsmart-tool` and `rv-agent-validation` from workspace members and dependencies
- [x] 1.5 Edit `modules/rv-platform/src/rv_platform/__init__.py`: remove rvsmart-tool lazy import block
- [x] 1.6 Edit `modules/aperv-tool/src/aperv_tool/tools/aperv/tool.py`: remove rvsmart references
- [x] 1.7 Grep all `modules/*/src/` for remaining rvsmart/rv-agent-validation references and remove them
- [x] 1.8 Edit `openspec/specs/tools/spec.md`: remove rvsmart-tool references (INV-RSM-*, RVSmartTool sections)
- [x] 1.9 Edit `openspec/specs/aperv/spec.md`: remove rvsmart references
- [x] 1.10 Edit `openspec/specs/platform/spec.md`: remove rvsmart references (rvsmart integration section)
- [x] 1.11 Edit `openspec/specs/agent/spec.md`: remove rv-agent-validation references
- [x] 1.12 Edit `openspec/specs/analysis/spec.md`: remove rv-agent-validation references
- [x] 1.13 Edit `docs/rv_android_architecture.md`: remove rvsmart-tool and rv-agent-validation from diagrams/tables
- [x] 1.14 Edit `CLAUDE.md`: update module count (14), remove rvsmart and rv-agent-validation references
- [x] 1.15 Edit `.claude/AGENTS.md`: update module references
- [x] 1.16 Edit `.claude/project-info.md`: remove rv-agent-validation from module table and dependency order
- [x] 1.17 Edit `.claude/skills/rv-release/SKILL.md`, `checklists/release-checklist.md`, `checklists/version-management.md`: remove rv-agent-validation, add rvagent-tool and aperv-tool
- [x] 1.18 Edit `.claude/skills/rv-analyze-dependencies/reference.md`: update layer 5 and dependency matrix
- [x] 1.19 Edit `.claude/skills/rv-analyze-module/reference.md`: remove rv-agent-validation, add aperv-tool
- [x] 1.20 Run `uv sync` and verify workspace builds cleanly
- [x] 1.21 Run tests on rv-platform (149 pass), aperv-tool (43 pass) — no regressions
- [x] 1.22 Close GitHub issues: #9, #20, #21, #22, #23, #25, #34, #35, #36, #39 as not_planned
- [x] 1.23 Move issues to Done on Kanban; move #48 to In Progress
- [x] 1.24 Archive OpenSpec changes: gh34, gh35, gh36, gh43, gh9 (all --skip-specs)
- [x] 1.25 Add `autoflake` and `isort` to dev dependencies in `pyproject.toml`

## 2. Dead Code Removal

- [x] 2.1 Run autoflake on all 13 modules src/ (remove unused imports and variables)
- [x] 2.2 Run autoflake on all 13 modules tests/
- [x] 2.3 Fix 20 f-strings without placeholders across 6 modules
- [x] 2.4 Revert false positive: `import logging` in `rv_android_core/util/logging/constants.py` (re-exported)
- [x] 2.5 Remove `TestCalibrationParamForwarding` tests from rvagent-tool (depended on archived rv-agent-validation)
- [x] 2.6 Verify all 13 modules pass tests (3,458 total)

## 3. Code Quality — Lint & Fix

- [x] 3.1 Run `black` (88 chars) on all 13 modules src/ and tests/
- [x] 3.2 Run `isort` (black profile) on all 13 modules src/ and tests/
- [x] 3.3 Run `autoflake` on all 13 modules tests/ (missed in TG2)
- [x] 3.4 Add `.flake8` config: max-line-length=88, extend-ignore E203/W503, exclude qtesting/droidmate/backup
- [x] 3.5 Add `[tool.black]`, `[tool.isort]`, `[tool.flake8]` sections to `pyproject.toml`
- [x] 3.6 Verify flake8 errors reduced from 3,578 to 684 (81% reduction)
- [x] 3.7 Verify all 13 modules pass tests (3,458 total)

## 4. Code Documentation — Docstrings & Inline Comments

### 4A. Docstrings (Google-style, following rv-doc-code templates)

- [x] 4.1 rv-android-core: `domain/task.py`, `domain/coverage.py`, `error_handler.py`, `command.py`, `abstract_tool.py`
- [x] 4.2 rv-agent: `rv_agent.py`, `rvagent_strategy.py`, `llm_client.py`, `transition_manager.py`, nodes (parse, decision, execute)
- [x] 4.3 rv-platform: `platform.py`, `executor.py`, `task_storage.py`, `platform_config.py`
- [x] 4.4 rv-experiment: `experiment_controller.py`, `execution_controller.py`, `config.py`, `__main__.py`
- [x] 4.5 rv-tools: `registry.py`, `factory.py`, `monkey/tool.py`, `droidbot/tool.py`, `ape/tool.py`, `fastbot/tool.py`
- [x] 4.6 rv-screen-parser: `abstract_visitor.py`, `enhanced_visitor.py`, `default_visitor.py`
- [x] 4.7 rv-static-analysis: all 4 src files
- [x] 4.8 rv-coverage: all 3 src files
- [x] 4.9 rv-uiautomator: all 7 src files
- [x] 4.10 rv-instrumentation: `rvandroid.py`, `config.py`
- [x] 4.11 rv-monitor-generator: `runtime_verification_generator.py`, `config.py`
- [x] 4.12 rvagent-tool: `tool.py`, `config.py`
- [x] 4.13 aperv-tool: `tool.py` (already well documented, minor updates)
- [x] 4.14 Verify all 13 modules pass tests

### 4B. Inline Comments (WHY blocks, phase/step markers, section dividers)

- [x] 4.15 rv-android-core: `task.py`, `coverage.py`, `error_handler.py`, `command.py`, `abstract_tool.py`, `package_detector.py`
- [x] 4.16 rv-agent: `rv_agent.py`, `rvagent_strategy.py`, `llm_client.py`, `transition_manager.py`, `routing_manager.py`
- [x] 4.17 rv-platform (deep): all 12 src files — resume logic, atomic writes, component lifecycle, port allocation
- [x] 4.18 rv-experiment (deep): all 8 src files — three-phase workflow, resume logic, pre-processing pipeline
- [x] 4.19 rv-tools: `registry.py`, `factory.py`, `monkey/tool.py`, `droidbot/tool.py`, `ape/tool.py`, `fastbot/tool.py`
- [x] 4.20 rv-coverage: `tracker.py`, `logcat_parser.py`
- [x] 4.21 rv-static-analysis: `static_analysis_parser.py`, `static_analysis.py`
- [x] 4.22 rv-screen-parser: `abstract_visitor.py`, `enhanced_visitor.py`
- [x] 4.23 rv-instrumentation: `rvandroid.py` (6-phase pipeline with step markers)
- [x] 4.24 aperv-tool: `tool.py`
- [x] 4.25 Verify all 13 modules pass tests

## 5. Module Documentation — Architecture, Specs, Scripts

### 5A. Architecture docs (`/rv-doc-architecture` per module)

- [x] 5.1 rv-screen-parser — architecture.md created
- [x] 5.2 rv-static-analysis — architecture.md created
- [x] 5.3 rv-coverage — architecture.md created
- [x] 5.4 rv-uiautomator — architecture.md created
- [x] 5.5 rv-instrumentation — architecture.md created
- [x] 5.6 rv-monitor-generator — architecture.md created
- [x] 5.7 rvagent-tool — architecture.md created
- [x] 5.8 aperv-tool — architecture.md created
- [x] 5.9 rv-experiment — architecture.md updated
- [ ] 5.10 rv-android-core — architecture.md update (retry after rate limit)
- [ ] 5.11 rv-agent — architecture.md update (retry after rate limit)
- [ ] 5.12 rv-platform — architecture.md update (retry after rate limit)
- [x] 5.13 rv-tools — architecture.md created

### 5B. Aperv spec update

- [x] 5.14 Rewrite `openspec/specs/aperv/spec.md` from APE-RV PRD + specs + implementation (7→12 invariants, 5→13+ variants, LLM/MOP/component triggering)

### 5C. Shell scripts update

- [ ] 5.15 Update `modules/clean.sh`: remove rv-agent-validation from MODULES array, add aperv-tool and aperv-llm-validation
- [ ] 5.16 Update `modules/lock.sh`: same MODULES array update
- [ ] 5.17 Update `modules/test.sh`: same MODULES array update
- [ ] 5.18 Update help text in all 3 scripts to match new module list

### 5D. Existing documentation sync

- [ ] 5.19 Run `/rv-docs-sync rv-android-core`
- [ ] 5.20 Run `/rv-docs-sync rv-agent`
- [ ] 5.21 Run `/rv-docs-sync rv-platform`
- [ ] 5.22 Run `/rv-docs-sync rv-experiment`
- [ ] 5.23 Run `/rv-docs-sync rv-tools`
- [ ] 5.24 Update project-level `CLAUDE.md` with final state
- [ ] 5.25 Update project-level `docs/rv_android_architecture.md` with final state

### 5E. Missing README/CLAUDE.md

- [ ] 5.26 Run `/rv-doc-readme aperv-tool`
- [ ] 5.27 Run `/rv-doc-readme aperv-llm-validation`
- [ ] 5.28 Run `/rv-doc-generate-claude-md rvagent-tool`
- [ ] 5.29 Run `/rv-doc-generate-claude-md aperv-tool`
- [ ] 5.30 Run `/rv-doc-generate-claude-md aperv-llm-validation`

## 6. Test Coverage

Subagent dispatch: each module independently.

- [ ] 6.1 Run `/rv-test-add rv-uiautomator` — target: UIAdapter, ActionExecutor, StateConverter (goal: >=20 tests)
- [ ] 6.2 Run `/rv-test-add rv-instrumentation` — target: pipeline, config validation (goal: >=25 tests)
- [ ] 6.3 Run `/rv-test-add rv-monitor-generator` — target: generator, spec parsing (goal: >=25 tests)
- [ ] 6.4 Run `/rv-test-add rv-tools` — target: ToolRegistry, ToolFactory (goal: >=100 tests)
- [ ] 6.5 Run full test suite on all modules to verify

## 7. Final Verification & Review

Must run after all other groups complete.

### 7A. Issue & change housekeeping

- [x] 7.1 Close/assess GitHub issues #20, #21, #22, #23, #25 — closed as not_planned
- [ ] 7.2 Assess and close/keep GitHub issues #41, #42, #43 (aperv enhancements)
- [ ] 7.3 Sync any pending delta specs to main specs via `/opsx:sync`

### 7B. Metadata & configuration audit

- [ ] 7.4 Audit `pyproject.toml` in all 14 modules: verify version, description, authors, license are consistent
- [ ] 7.5 Verify CLI entry points: `uv run rv-experiment --help`, `uv run rv-platform --help`, `uv run rv-agent --help`

### 7C. Quality verification

- [ ] 7.6 Run `/rv-verify` on all 14 modules
- [ ] 7.7 Run full test suite via `modules/test.sh --continue-on-error`

### 7D. Code review (key modules)

- [ ] 7.8 Run `/rv-code-reviewer rv-android-core`
- [ ] 7.9 Run `/rv-code-reviewer rv-agent`
- [ ] 7.10 Run `/rv-code-reviewer rv-platform`
- [ ] 7.11 Run `/rv-code-reviewer rv-experiment`

### 7E. Metrics & reporting

- [ ] 7.12 Generate project metrics report: LOC per module, test count, CC, MI
- [ ] 7.13 Save metrics report to `docs/project_metrics.md`

### 7F. Final documentation review

- [ ] 7.14 Review and update project-level `CLAUDE.md` — ensure it reflects final state
- [ ] 7.15 Review `docs/WORKFLOW.md` — ensure it reflects current skills and process
- [ ] 7.16 Close GitHub issue #48
