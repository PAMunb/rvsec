<!-- Dependency hints (v2):
     - TG1-TG4, TG6: COMPLETE — do not re-execute.
     - Batch 1: TG5-R + TG5-shell + TG8-A (independent)
     - Batch 2: TG9-A + TG9-B + TG8-B (independent)
     - Batch 3: TG9-C + TG9-D + TG9-E + TG8-C + TG6-R (independent)
     - Batch 4: TG10 + TG7R.1-7R.2
     - Batch 5: TG7R.3-7R.6 (depends on everything above)
     - Subagent dispatch: batches 1-3 use 3-4 parallel subagents -->

## 1. Housekeeping & Module Archival — COMPLETE

- [x] 1.1-1.25 (25 tasks complete, see v1 history)

## 2. Dead Code Removal — COMPLETE

- [x] 2.1-2.6 (6 tasks complete)

## 3. Code Quality — Lint & Fix (modules/) — COMPLETE

- [x] 3.1-3.7 (7 tasks complete)

## 4. Code Documentation — Docstrings (modules/) — COMPLETE

- [x] 4.1-4.25 (25 tasks complete)

## 5R. Architecture Docs — Python Module Review (Batch 1)

Review depth and mermaid diagrams for all 14 modules. Use `/rv-doc-architecture`.
Criteria: >=3 mermaid diagrams, complete sections, WHY in decisions, data flow.

- [x] 5R.1 Create/improve `modules/rv-android-core/docs/architecture.md` (878->1050 lines, 9 mermaid, 8 ADs, data flow, 12 invariant refs)
- [x] 5R.2 Create/improve `modules/rv-agent/docs/architecture.md` (759->939 lines, 7 mermaid, 6 ADs, data flow)
- [x] 5R.3 Create/improve `modules/rv-platform/docs/architecture.md` (554->698 lines, 6 mermaid, 7 ADs, 10 invariant refs)
- [x] 5R.4 Review `modules/rv-experiment/docs/architecture.md` (636->785 lines, 6 mermaid, 7 ADs, 8 invariant refs)
- [x] 5R.5 Review `modules/rv-tools/docs/architecture.md` (593->726 lines, 8 mermaid, 4 ADs, data flow)
- [x] 5R.6 Review `modules/rv-coverage/docs/architecture.md` (514->644 lines, 5 mermaid, 6 ADs, data flow)
- [x] 5R.7 Review `modules/rv-screen-parser/docs/architecture.md` (596->728 lines, 6 mermaid, 6 ADs, data flow)
- [x] 5R.8 Review `modules/rv-static-analysis/docs/architecture.md` (501->623 lines, 5 mermaid, 6 ADs, data flow)
- [x] 5R.9 Review `modules/rv-uiautomator/docs/architecture.md` (539->670 lines, 6 mermaid, 6 ADs, data flow)
- [x] 5R.10 Review `modules/rv-instrumentation/docs/architecture.md` (533->689 lines, 8 mermaid, 6 ADs, data flow)
- [x] 5R.11 Review `modules/rv-monitor-generator/docs/architecture.md` (402->658 lines, 8 mermaid, 6 ADs, data flow)
- [x] 5R.12 Review `modules/rvagent-tool/docs/architecture.md` (401->491 lines, 5 mermaid, 4 ADs, data flow)
- [x] 5R.13 Review `modules/aperv-tool/docs/architecture.md` (444->565 lines, 5 mermaid, 5 ADs, data flow)
- [x] 5R.14 Create `modules/aperv-llm-validation/docs/architecture.md` (created 388 lines, 4 mermaid, 6 ADs)

## 5S. Shell Scripts Update (Batch 1)

- [x] 5S.1 Update MODULES array in `modules/clean.sh` (already correct — 14 modules)
- [x] 5S.2 Update MODULES array in `modules/lock.sh` (already correct)
- [x] 5S.3 Update MODULES array in `modules/test.sh` (already correct)
- [x] 5S.4 Update help text in all 3 scripts (already correct)

## 6. Test Coverage (v1) — COMPLETE

- [x] 6.1-6.5 (5 tasks complete: UV 66, INS 42, MG 41, TOOLS 195)

## 6R. Test Coverage Expansion (Batch 3)

Increase test count and coverage for modules with low ratios.
Run `uv run pytest --cov` per module and target gaps.

- [x] 6R.1 Measure coverage for 5 low-ratio modules: static-analysis 65%, coverage 86%, uiautomator 56%, aperv-tool 61%, rvagent-tool 75%
- [ ] 6R.2 Add tests for rv-static-analysis (5 test files / 9 src — target: cover analyzer.py, parser.py edge cases)
- [ ] 6R.3 Add tests for rv-coverage (5 test files / 8 src — target: cover tracker, analyzer)
- [ ] 6R.4 Add tests for rv-uiautomator (1 test file / 12 src — need more test files for adapter, executor, converter)
- [ ] 6R.5 Add tests for aperv-tool (2 test files / 4 src — cover tool.py variant logic, property mapping)
- [ ] 6R.6 Add tests for rvagent-tool (2 test files / 5 src — cover config mapping, variant resolution)
- [ ] 6R.7 Verify all modules pass after new tests: `modules/test.sh --continue-on-error`

## 8A. Scripts Lint & Fix (Batch 1)

- [x] 8A.1 Run `black scripts/*.py` (23 reformatted)
- [x] 8A.2 Run `isort scripts/*.py` (8 fixed)
- [x] 8A.3 Run `flake8 scripts/*.py`, fix errors (229->186, autoflake+f-string fixes)
- [x] 8A.4 Verify: `black --check` passes; flake8 186 remaining (E501 line-length, E741 acceptable)
- [x] 8A.5 Run tests on main modules to verify lint did not break anything (core 872, platform 211, experiment 163 passed)

## 8B. Scripts Docstrings (Batch 2)

Use `/rv-doc-code` on key scripts:
- [x] 8B.1 `scripts/calibration_orchestrator.py` — docstrings + inline WHY comments (main loop, TPE config, skip flags, stagger)
- [x] 8B.2 `scripts/aperv_objective.py` — module docstring, WHY on weights/trim
- [x] 8B.3 `scripts/aperv_parameter_space.py` — class/function docstrings, WHY on ordering/expansion
- [x] 8B.4 `scripts/analyze_calibration.py` — 7 functions documented, WHY on column mapping/trim
- [x] 8B.5 `scripts/analyze_comparacao.py` — 8 functions documented, WHY on tolerance/CV

## 8C. Scripts Tests — REMOVED

Scripts in `scripts/` are standalone utilities, many will move to `backup/`.
No tests for scripts — out of scope.

## 9A. Java Documentation — APE-RV (Batch 2)

175 Java files in `ape/`. README + architecture + javadoc.

- [x] 9A.1 Create/update `ape/README.md` (params, build, variants, architecture overview)
- [x] 9A.2 Create `ape/docs/architecture.md` (3 mermaid, 7 ADs, action selection pipeline, data flow, spec refs)
- [x] 9A.3 Javadoc on `Config.java` (class-level: parameter groups, loading, JIT inlining)
- [x] 9A.4 Javadoc on `SataAgent.java` (class-level: SATA strategy, epsilon-greedy, MOP boost)
- [x] 9A.5 Javadoc on `StatefulAgent.java` (class-level: graph mgmt, MOP/coverage/WTG boost, stagnation)
- [x] 9A.6 Javadoc on `MopScorer.java` (already has javadoc from gh9)
- [x] 9A.7 Javadoc on `State.java` (class-level: StateKey, actions, visit counts, refinement, saturation)
- [x] 9A.8 Javadoc on `ModelAction.java` (class-level: UI interaction, priority accumulation, MOP boost)
- [x] 9A.9 Javadoc on `Graph.java` (class-level: GSTG, state lookup, growth detection, shortest path)
- [x] 9A.10 MopScorer.java already had full javadoc from gh9

## 9B. Java Documentation — rvsec-gator/client (Batch 2)

GATOR client = all static analysis. 6 src + 2 commons.
Path: `rvsec/rvsec-android/rvsec-gator/`

- [x] 9B.1 Create `client/README.md` (pipeline, JSON format, consumers, build)
- [x] 9B.2 Create `client/docs/architecture.md` (4 mermaid, 6 ADs, data flow, spec refs)
- [x] 9B.3 Javadoc on `RvsecAnalysisClient.java` (already has class-level javadoc)
- [x] 9B.4 Javadoc on WTG model: Event, Window, Result, Transition (class + method docs)
- [x] 9B.5 Javadoc on Writer.java (class + 3 write overloads)
- [ ] 9B.6 Javadoc on commons: `Timer.java`, `Logger.java`

## 9C. Java Documentation — rvsec-agent (Batch 3)

Instrumentation agent. 28 Java files.
Path: `rvsec/rvsec-agent/`

- [x] 9C.1 Create/update `README.md` (purpose, architecture, integration pipeline)
- [ ] 9C.2 Create `docs/architecture.md` with >=3 mermaid
- [ ] 9C.3 Javadoc on key classes (agent, aspects, monitors)

## 9D. Java Documentation — mop-maven-plugin (Batch 3)

Maven plugin. 3 Java files.
Path: `rvsec/mop-maven-plugin/`

- [x] 9D.1 Create `README.md` (purpose, build, config, integration, known issues)
- [ ] 9D.2 Javadoc on all 3 classes

## 9E. Java Documentation — smaller modules (Batch 3)

For each: README.md with purpose and usage + minimal javadoc.

- [x] 9E.1 `rvsec/rvsec-core/README.md` (domain models, logger interfaces, constants)
- [x] 9E.2 `rvsec/rvsec-mop/README.md` (JCA 23 + Generic 118+27 specs, directory structure, build)
- [x] 9E.3 `rvsec/rvsec-mop-extractor/README.md` (JavamopFacade, signature extraction, integration)
- [x] 9E.4 `rvsec/rvsec-mop-defsuses/README.md` (defs-uses analysis)
- [x] 9E.5 `rvsec/rvsec-android/rvsec-apk/README.md` (APK metadata, manifest, components)
- [x] 9E.6 `rvsec/rvsec-logger-csv/README.md` (CSV logging for dev/testing)
- [x] 9E.7 `rvsec/rvsec-android/rvsec-logger-logcat/README.md` (logcat logging, RVSEC tags, format)
- [x] 9E.8 `rvsec/rvsec-android/README.md` (active vs deprecated submodules table)

## 10. CLAUDE.md & README.md Review — Python (Batch 4)

Review quality and accuracy:
- [x] 10.1 Review rv-android-core (removed fabricated circuit breaker section, fixed test dirs)
- [x] 10.2 Review rv-agent (fixed stochastic_probability default, prompt_version range, CLI options)
- [x] 10.3 Review rv-platform (fixed ToolConfig import/constructor, test structure)
- [x] 10.4 Review rv-experiment (added 5 missing test files to structure)
- [x] 10.5 Review rv-tools (removed non-existent PluginLoader, fixed ToolConfig field names x6)
- [x] 10.6 Review rv-coverage (removed 5 fabricated classes, fixed usage examples, corrected deps)
- [x] 10.7 Review rv-screen-parser (fixed ParserType->ScreenParserType, register_visitor method name)
- [x] 10.8 Review rv-static-analysis (fixed wrong method name in CLAUDE.md)
- [x] 10.9 Review rv-uiautomator (fixed 3 outdated constants, added 2 missing, removed speculative section)
- [x] 10.10 Review rv-instrumentation (fixed 4 non-existent classes, promotional language, wrong return type in README)
- [x] 10.11 Review rv-monitor-generator (removed false integration point, fixed output artifacts in README)
- [x] 10.12 Review rvagent-tool (accurate, no changes)
- [x] 10.13 Review aperv-tool (accurate, no changes)
- [x] 10.14 Review aperv-llm-validation (accurate, no changes)
- [x] 10.15 Update project-level CLAUDE.md (added 3 missing modules to list, updated Tools domain)

## 7R. Final Verification & Review (Batch 4-5)

### 7R.A Issues & Changes (Batch 4)
- [x] 7R.1 Assess issues #41, #42, #43 (#41 done, #42 done, #43 partial — recommend close all)
- [ ] 7R.2 Sync delta specs via `/opsx:sync`

### 7R.B Metadata Audit (Batch 4)
- [x] 7R.3 Audit pyproject.toml: all v0.1.0, all have descriptions/authors. Fix: add readme field to aperv-tool + aperv-llm-validation
- [x] 7R.4 CLI entry points: rv-experiment OK (4 subcmds), rv-platform OK (4 subcmds, 10 tools)

### 7R.C Quality Verification (Batch 5)
- [ ] 7R.5 Run `/rv-verify` on all 14 modules
- [ ] 7R.6 Full test suite: `uv run pytest` on all modules

### 7R.D Code Review (Batch 5)
- [ ] 7R.7 `/rv-code-reviewer` on rv-android-core
- [ ] 7R.8 `/rv-code-reviewer` on rv-agent
- [ ] 7R.9 `/rv-code-reviewer` on rv-platform
- [ ] 7R.10 `/rv-code-reviewer` on rv-experiment

### 7R.E Metrics & Reporting (Batch 5)
- [ ] 7R.11 Generate project metrics (LOC, test count, complexity, MI per module)
- [ ] 7R.12 Save to `docs/project_metrics.md`

### 7R.F Final Documentation (Batch 5)
- [ ] 7R.13 Review/update project-level `CLAUDE.md`
- [ ] 7R.14 Review `docs/WORKFLOW.md`
- [ ] 7R.15 Close GitHub issue #48
