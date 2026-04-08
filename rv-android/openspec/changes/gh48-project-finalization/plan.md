# Change Plan: Project Finalization — Quality, Documentation, and Cleanup (v2)

**Date**: 2026-04-03 (revised 2026-04-08)
**Track**: Quick Path
**Priority**: High
**GitHub Issue**: [#48](https://github.com/PAMunb/rvsec/issues/48)
**PRD Reference**: NFR1 (Maintainability), NFR6 (Documentation), NFR8 (Reproducibility)
**Domains**: core, platform, experiment, agent, instrumentation, analysis, tools + Java/Maven

## 1. Context

RV-Android is functionally complete. The project needs finalization: archive
deprecated modules, remove dead code, enforce code quality (lint + format),
generate comprehensive documentation for ALL modules (Python and Java),
increase test coverage, and verify everything works end-to-end.

### 1.1 Completed work (v1, 99/118 tasks)

| TG | Status | Description |
|----|--------|-------------|
| TG1 | COMPLETE | Archival: rvsmart-tool, rv-agent-validation, rvsmart spec |
| TG2 | COMPLETE | Dead code removal: autoflake, f-strings, 3458 tests passing |
| TG3 | COMPLETE | Lint/fix on modules/: black, isort, flake8 3578->684 |
| TG4 | COMPLETE | Google-style docstrings on all 14 Python modules |
| TG6 | COMPLETE | Test coverage: UV 66, INS 42, MG 41, TOOLS 195 tests |

### 1.2 Remaining work (v2 scope)

1. **Python architecture docs**: 13/14 exist with mermaid and 400-878 lines.
   3 pending (core, agent, platform — failed due to rate limit in v1).
   Quality review needed on ALL.

2. **Full Java documentation**: Our Java modules lack docs entirely:
   - APE-RV (175 Java files) — testing engine
   - rvsec-gator/client (6 src + 8 test) — GATOR client (static analysis)
   - rvsec-agent (28 files) — instrumentation agent
   - mop-maven-plugin (3 files) — Maven MOP plugin
   - rvsec-core, rvsec-mop, rvsec-mop-extractor, rvsec-mop-defsuses (smaller)
   - rvsec-apk, rvsec-logger-csv, rvsec-logger-logcat (utilities)
   Level: README.md + docs/architecture.md + javadoc on key classes.

3. **Scripts quality**: 24 Python scripts in scripts/ need lint, tests, docstrings.

4. **Test coverage expansion**: Measure coverage for all modules, add tests where
   ratios are low (rv-static-analysis, rv-coverage, rv-uiautomator, aperv-tool, rvagent-tool).

5. **CLAUDE.md/README.md review**: Quality review across all 14 Python modules.

6. **Shell scripts**: clean.sh, lock.sh, test.sh MODULES arrays (already correct).

7. **TG7 verification**: Issues, metadata audit, code review, metrics.

### 1.3 Java modules — ours vs external

**OURS (document)**:
- `ape/` — APE-RV, testing engine (175 Java files)
- `rvsec/rvsec-android/rvsec-gator/client/` — GATOR client (6 src)
- `rvsec/rvsec-android/rvsec-gator/commons/` — Timer, Logger (2 files)
- `rvsec/rvsec-agent/` — instrumentation agent (28 files)
- `rvsec/mop-maven-plugin/` — Maven MOP plugin (3 files)
- `rvsec/rvsec-core/` — domain models (6 files)
- `rvsec/rvsec-mop/` — MOP specs (336 .mop)
- `rvsec/rvsec-mop-extractor/` — spec extractor (9 files)
- `rvsec/rvsec-mop-defsuses/` — defs-uses analysis (5 files)
- `rvsec/rvsec-android/rvsec-apk/` — APK utilities (6 files)
- `rvsec/rvsec-logger-csv/` — CSV logger (1 file)
- `rvsec/rvsec-android/rvsec-logger-logcat/` — logcat logger (1 file)

**EXTERNAL (do not modify)**:
- javamop, rv-monitor, crylogger (forked/copied)
- rvsec-gator/sootandroid (GATOR server, 178 files)
- rvsec-gesda, rvsec-reachability (deprecated, commented out in POM)
- rvsec-taint (deprecated), rvsec-methods-extractor (deprecated)

## 2. Execution Order

```
Batch 1: TG5-R (Python arch docs) + TG5-shell + TG8-A (scripts lint)
Batch 2: TG9-A (APE-RV) + TG9-B (gator client) + TG8-B (scripts docstrings)
Batch 3: TG9-C + TG9-D + TG9-E (Java docs) + TG8-C (script tests) + TG6-R (test coverage)
Batch 4: TG10 (CLAUDE.md/README review) + TG7R.1-7R.2 (issues, metadata)
Batch 5: TG7R.3-7R.6 (verification, code review, metrics, close)
```

Subagent dispatch: batches 1-3 use 3-4 parallel subagents per batch.

## 3. Acceptance Criteria

- [x] AC1: Modules archived, workspace builds (TG1)
- [x] AC2: Dead imports removed (TG2)
- [x] AC3: black/isort pass on modules/, flake8 reduced 81% (TG3)
- [x] AC4: Docstrings on key files across all Python modules (TG4)
- [ ] AC5: All 14 Python modules with architecture.md reviewed and >=3 mermaid
- [ ] AC6: All our Java modules with README.md + javadoc; APE-RV and gator client with architecture.md
- [ ] AC7: Scripts linted (black/flake8 pass) + docstrings + tests for 3 key scripts
- [x] AC8: Test coverage increased for 4 modules (TG6)
- [ ] AC9: Test coverage measured for all modules; gaps filled in low-ratio modules (TG6-R)
- [ ] AC10: CLAUDE.md and README.md reviewed for all 14 Python modules
- [ ] AC11: Shell scripts updated (MODULES arrays)
- [ ] AC12: `/rv-verify` passes on all modules; CLI entry points functional
- [ ] AC13: Obsolete issues closed; delta specs synced
- [ ] AC14: pyproject.toml metadata consistent
- [ ] AC15: Metrics report generated in `docs/project_metrics.md`
- [ ] AC16: Issue #48 closed
