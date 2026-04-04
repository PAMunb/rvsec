<!-- Dependency hints:
     - TG1 must complete first — TG2 depends on it (archived modules removed from workspace).
     - TG2 must complete before TG3 (dead code removed before formatting).
     - TG3 must complete before TG4, TG5, TG6 (clean code before documenting/testing).
     - TG4 and TG5 are independent and can run in parallel.
     - TG6 is independent of TG4/TG5 and can run in parallel with them.
     - TG7 (Verification) must run after all other groups. -->

## 1. Housekeeping & Module Archival

- [ ] 1.1 Move `modules/rvsmart-tool/` to `backup/rvsmart-tool`
- [ ] 1.2 Move `modules/rv-agent-validation/` to `backup/rv-agent-validation`
- [ ] 1.3 Move `openspec/specs/rvsmart/` to `backup/openspec-specs-rvsmart`
- [ ] 1.4 Edit `pyproject.toml`: remove `rvsmart-tool` and `rv-agent-validation` from workspace members and dependencies
- [ ] 1.5 Edit `modules/rv-platform/src/rv_platform/__init__.py`: remove rvsmart-tool lazy import block
- [ ] 1.6 Edit `modules/aperv-tool/src/aperv_tool/tools/aperv/tool.py`: remove rvsmart references
- [ ] 1.7 Grep all `modules/*/src/` for remaining rvsmart/rv-agent-validation references and remove them
- [ ] 1.8 Edit `openspec/specs/tools/spec.md`: remove rvsmart-tool references
- [ ] 1.9 Edit `openspec/specs/aperv/spec.md`: remove rvsmart references
- [ ] 1.10 Edit `openspec/specs/platform/spec.md`: remove rvsmart references
- [ ] 1.11 Edit `openspec/specs/agent/spec.md`: remove rv-agent-validation references
- [ ] 1.12 Edit `openspec/specs/analysis/spec.md`: remove rv-agent-validation references
- [ ] 1.13 Edit `docs/rv_android_architecture.md`: remove rvsmart-tool and rv-agent-validation from diagrams/tables
- [ ] 1.14 Edit `CLAUDE.md`: update module count (14), remove rvsmart and rv-agent-validation references
- [ ] 1.15 Edit `.claude/AGENTS.md`: update module references if present
- [ ] 1.16 Run `uv sync` and verify workspace builds cleanly
- [ ] 1.17 Run `/rv-test-run` on rv-platform, aperv-tool — verify no regressions
- [ ] 1.18 Close GitHub issues: #34, #35, #36 (rvsmart redesign/bugfixes/efficiency) as not_planned
- [ ] 1.19 Close GitHub issue #39 (rvsmart Track B improvements) as not_planned
- [ ] 1.20 Archive OpenSpec changes: `openspec archive gh34-rvsmart-redesign --skip-specs`
- [ ] 1.21 Archive OpenSpec changes: `openspec archive gh35-rvsmart-bugfixes --skip-specs`
- [ ] 1.22 Archive OpenSpec changes: `openspec archive gh36-rvsmart-efficiency --skip-specs`
- [ ] 1.23 Archive OpenSpec changes: `openspec archive gh43-aperv-llm-validation --skip-specs`
- [ ] 1.24 Archive OpenSpec changes: `openspec archive gh9-docker-calibration --skip-specs`

## 2. Dead Code Removal

Subagent dispatch: modules are independent, run 3-4 in parallel.

- [ ] 2.1 Run `/rv-cleanup rv-android-core` — focus on 53 dead constants in `constants.py`
- [ ] 2.2 Run `/rv-cleanup rv-agent` — focus on 6 unused imports in `rv_agent.py`
- [ ] 2.3 Run `/rv-cleanup rv-platform`
- [ ] 2.4 Run `/rv-cleanup rv-experiment`
- [ ] 2.5 Run `/rv-cleanup rv-tools`
- [ ] 2.6 Run `/rv-cleanup rv-screen-parser`
- [ ] 2.7 Run `/rv-cleanup rv-static-analysis`
- [ ] 2.8 Run `/rv-cleanup rv-coverage`
- [ ] 2.9 Run `/rv-cleanup rv-uiautomator`
- [ ] 2.10 Run `/rv-cleanup rv-instrumentation`
- [ ] 2.11 Run `/rv-cleanup rv-monitor-generator`
- [ ] 2.12 Run `/rv-cleanup rvagent-tool`
- [ ] 2.13 Run `/rv-cleanup aperv-tool`
- [ ] 2.14 Run `/rv-cleanup aperv-llm-validation`
- [ ] 2.15 Review 10 TODO/FIXME comments across codebase — remove stale ones, convert actionable ones to GitHub issues

## 3. Code Quality — Lint & Fix

Subagent dispatch: modules are independent, run 3-4 in parallel.

- [ ] 3.1 Run `/rv-qa-lint-fix rv-android-core`
- [ ] 3.2 Run `/rv-qa-lint-fix rv-agent`
- [ ] 3.3 Run `/rv-qa-lint-fix rv-platform`
- [ ] 3.4 Run `/rv-qa-lint-fix rv-experiment`
- [ ] 3.5 Run `/rv-qa-lint-fix rv-tools`
- [ ] 3.6 Run `/rv-qa-lint-fix rv-screen-parser`
- [ ] 3.7 Run `/rv-qa-lint-fix rv-static-analysis`
- [ ] 3.8 Run `/rv-qa-lint-fix rv-coverage`
- [ ] 3.9 Run `/rv-qa-lint-fix rv-uiautomator`
- [ ] 3.10 Run `/rv-qa-lint-fix rv-instrumentation`
- [ ] 3.11 Run `/rv-qa-lint-fix rv-monitor-generator`
- [ ] 3.12 Run `/rv-qa-lint-fix rvagent-tool`
- [ ] 3.13 Run `/rv-qa-lint-fix aperv-tool`
- [ ] 3.14 Run `/rv-qa-lint-fix aperv-llm-validation`

## 4. Code Documentation — Docstrings

Subagent dispatch: modules are independent, run 2-3 in parallel.

- [ ] 4.1 Run `/rv-doc-code rv-android-core` — key files: `domain/task.py`, `domain/coverage.py`, `error_handler.py`, `command.py`, `abstract_tool.py`
- [ ] 4.2 Run `/rv-doc-code rv-agent` — key files: `agent/rv_agent.py`, `strategies/rvagent_strategy/rvagent_strategy.py`, `llm/llm_client.py`, `services/transition_manager.py`, main nodes
- [ ] 4.3 Run `/rv-doc-code rv-platform` — key files: `platform.py`, `task_executor.py`, `storage/task_storage.py`, `config.py`
- [ ] 4.4 Run `/rv-doc-code rv-experiment` — key files: `controller.py`, `execution_controller.py`, `config.py`
- [ ] 4.5 Run `/rv-doc-code rv-tools` — key files: `registry.py`, `factory.py`
- [ ] 4.6 Run `/rv-doc-code rv-screen-parser` — key files: `abstract_visitor.py`, `enhanced_visitor.py`
- [ ] 4.7 Run `/rv-doc-code rv-static-analysis` — key files: `analyzer.py`, `parser.py`
- [ ] 4.8 Run `/rv-doc-code rv-coverage` — key files: `coverage_tracker.py`, `parser.py`
- [ ] 4.9 Run `/rv-doc-code rv-uiautomator` — key files: `adapter.py`, `action_executor.py`
- [ ] 4.10 Run `/rv-doc-code rv-instrumentation` — key file: `rvandroid.py`
- [ ] 4.11 Run `/rv-doc-code rv-monitor-generator` — key file: `generator.py`
- [ ] 4.12 Run `/rv-doc-code rvagent-tool` — key file: `tool.py`
- [ ] 4.13 Run `/rv-doc-code aperv-tool` — key file: `tool.py`
- [ ] 4.14 Run `/rv-doc-code aperv-llm-validation` — key files: `pipeline/*.py`, `constants.py`

## 5. Module Documentation — CLAUDE.md, README, Architecture

Subagent dispatch: modules are independent, run 2-3 in parallel.

### 5A. Missing documentation (create)

- [ ] 5.1 Run `/rv-doc-readme aperv-tool`
- [ ] 5.2 Run `/rv-doc-readme aperv-llm-validation`
- [ ] 5.3 Run `/rv-doc-generate-claude-md rvagent-tool`
- [ ] 5.4 Run `/rv-doc-generate-claude-md aperv-tool`
- [ ] 5.5 Run `/rv-doc-generate-claude-md aperv-llm-validation`
- [ ] 5.6 Run `/rv-doc-architecture rv-screen-parser`
- [ ] 5.7 Run `/rv-doc-architecture rv-static-analysis`
- [ ] 5.8 Run `/rv-doc-architecture rv-coverage`
- [ ] 5.9 Run `/rv-doc-architecture rv-uiautomator`
- [ ] 5.10 Run `/rv-doc-architecture rv-instrumentation`
- [ ] 5.11 Run `/rv-doc-architecture rv-monitor-generator`
- [ ] 5.12 Run `/rv-doc-architecture rvagent-tool`
- [ ] 5.13 Run `/rv-doc-architecture aperv-tool`
- [ ] 5.14 Run `/rv-doc-architecture aperv-llm-validation`

### 5B. Existing documentation (sync/update)

- [ ] 5.15 Run `/rv-docs-sync rv-android-core`
- [ ] 5.16 Run `/rv-docs-sync rv-agent`
- [ ] 5.17 Run `/rv-docs-sync rv-platform`
- [ ] 5.18 Run `/rv-docs-sync rv-experiment`
- [ ] 5.19 Run `/rv-docs-sync rv-tools`
- [ ] 5.20 Update project-level `CLAUDE.md` with final module count (14), remove archived references
- [ ] 5.21 Update project-level `docs/rv_android_architecture.md` with final state (14 modules)

## 6. Test Coverage

Subagent dispatch: each module independently.

- [ ] 6.1 Run `/rv-test-add rv-uiautomator` — target: UIAdapter, UIAutomator2Adapter, ActionExecutor, StateConverter public APIs (goal: >=20 tests)
- [ ] 6.2 Run `/rv-test-add rv-instrumentation` — target: instrumentation pipeline, config validation, error handling (goal: >=25 tests)
- [ ] 6.3 Run `/rv-test-add rv-monitor-generator` — target: generator, spec parsing, output validation (goal: >=25 tests)
- [ ] 6.4 Run `/rv-test-add rv-tools` — target: ToolRegistry edge cases, ToolFactory variant resolution, builtin tool specs (goal: >=100 tests)
- [ ] 6.5 Run `/rv-test-run` on each module after adding tests to verify all pass

## 7. Final Verification & Review

Must run after all other groups complete.

### 7A. Issue & change housekeeping

- [ ] 7.1 Assess and close/keep GitHub issues #20, #21, #22, #23, #25 (enhancement/refactoring — assess if still relevant post-finalization)
- [ ] 7.2 Assess and close/keep GitHub issues #41, #42, #43 (aperv enhancements — assess relevance)
- [ ] 7.3 Sync any pending delta specs to main specs via `/opsx:sync`

### 7B. Metadata & configuration audit

- [ ] 7.4 Audit `pyproject.toml` in all 14 modules: verify version, description, authors, license are consistent
- [ ] 7.5 Verify CLI entry points: `uv run rv-experiment --help`, `uv run rv-platform --help`, `uv run rv-agent --help`

### 7C. Quality verification

- [ ] 7.6 Run `/rv-verify rv-android-core`
- [ ] 7.7 Run `/rv-verify rv-agent`
- [ ] 7.8 Run `/rv-verify rv-platform`
- [ ] 7.9 Run `/rv-verify rv-experiment`
- [ ] 7.10 Run `/rv-verify rv-tools`
- [ ] 7.11 Run `/rv-verify rv-screen-parser`
- [ ] 7.12 Run `/rv-verify rv-static-analysis`
- [ ] 7.13 Run `/rv-verify rv-coverage`
- [ ] 7.14 Run `/rv-verify rv-uiautomator`
- [ ] 7.15 Run `/rv-verify rv-instrumentation`
- [ ] 7.16 Run `/rv-verify rv-monitor-generator`
- [ ] 7.17 Run `/rv-verify rvagent-tool`
- [ ] 7.18 Run `/rv-verify aperv-tool`
- [ ] 7.19 Run `/rv-verify aperv-llm-validation`

### 7D. Code review (key modules)

- [ ] 7.20 Run `/rv-code-reviewer rv-android-core`
- [ ] 7.21 Run `/rv-code-reviewer rv-agent`
- [ ] 7.22 Run `/rv-code-reviewer rv-platform`
- [ ] 7.23 Run `/rv-code-reviewer rv-experiment`

### 7E. Metrics & reporting

- [ ] 7.24 Generate project metrics report: LOC per module (radon raw), test count per module, average CC per module, MI per module
- [ ] 7.25 Save metrics report to `docs/project_metrics.md`

### 7F. Final documentation review

- [ ] 7.26 Review and update project-level `CLAUDE.md` — ensure it reflects final state
- [ ] 7.27 Review `docs/WORKFLOW.md` — ensure it reflects current skills and process
- [ ] 7.28 Close GitHub issue #48 (this issue)
