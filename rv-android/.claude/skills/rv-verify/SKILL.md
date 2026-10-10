---
name: rv-verify
description: >-
  Run all verification checks (tests, lint, type, security, metrics). Use before commits, after refactoring,
  or to validate code changes.
  Do NOT use for: only running tests (use /rv-test-run), only linting (use /rv-qa-lint).
argument-hint: [module-name]
context: fork
agent: general-purpose
allowed-tools: Bash, Read, Glob
---

# Verify Module: $ARGUMENTS

Unified verification that runs all quality checks in sequence.

## Supporting Files

- **Templates**: `templates/verification-report.md` - Report output format
- **Checklists**:
  - `checklists/quality-attributes.md` - 15 quality attributes and tool mappings
  - `checklists/inspection-checklist.md` - Manual code inspection categories
  - `checklists/product-metrics.md` - Metrics thresholds and interpretation
  - `checklists/dependability-analysis.md` - 4 dimensions of dependability (Availability, Reliability, Safety, Security)

---

## Quality Context

Software quality is multidimensional. Our verification targets these attributes:

| Check | Primary Attributes |
|-------|-------------------|
| Tests | Reliability, Robustness |
| Security | Security |
| Lint | Understandability, Complexity |
| Type | Maintainability |
| Metrics | Complexity, Maintainability |

Reference `checklists/quality-attributes.md` for the full attribute list.

### Dependability Dimensions

Dependability is the degree to which a system can be trusted. Four complementary dimensions:

| Dimension | Definition | How We Verify |
|-----------|------------|---------------|
| **Availability** | System ready when needed | Health checks, smoke tests |
| **Reliability** | Correct behavior over time | Unit/integration tests |
| **Safety** | No harmful states | Input validation, fail-safe defaults |
| **Security** | Protected from unauthorized access | bandit, pip-audit, /rv-security |

Reference `checklists/dependability-analysis.md` for systematic analysis framework.

---

## Workflow

```
STEP 1: UNIT TESTS ──────────────────────────────────────────────►
    │  Fast feedback on logic errors
    ▼
STEP 2: INTEGRATION TESTS ───────────────────────────────────────►
    │  Component interaction verification
    ▼
STEP 3: DEPENDENCY SECURITY ─────────────────────────────────────►
    │  Check for known vulnerabilities (pip-audit)
    ▼
STEP 4: FORMAT CHECK ────────────────────────────────────────────►
    │  black --check, isort --check
    ▼
STEP 5: LINT ────────────────────────────────────────────────────►
    │  flake8
    ▼
STEP 6: TYPE CHECK (if configured) ──────────────────────────────►
    │  mypy
    ▼
STEP 7: METRICS ANALYSIS ────────────────────────────────────────►
    │  Cyclomatic complexity, maintainability index
    ▼
STEP 8: ANOMALY DETECTION ───────────────────────────────────────►
    │  Flag components exceeding thresholds
    ▼
REPORT ──────────────────────────────────────────────────────────►
    │  Unified PASS/FAIL summary with metrics
```

---

## Steps

### 1. Determine Module Path

```bash
MODULE_PATH="modules/$ARGUMENTS"

# Verify module exists
if [ ! -d "$MODULE_PATH" ]; then
    echo "ERROR: Module not found at $MODULE_PATH"
    exit 1
fi
```

### 2. Run Unit Tests

Every pytest call carries `--import-mode=importlib -o "addopts="` (the CI contract: without
them, conftest isolation breaks across modules) and excludes the markers CI excludes. Most
modules have no `tests/unit/` directory; for those, this step runs the whole `tests/` directory
and step 3 is skipped.

```bash
# From project root
CI_MARKERS="not (slow or online or sglang or performance or dataset)"
UNIT_DIR="modules/$ARGUMENTS/tests/unit"
[ -d "$UNIT_DIR" ] || UNIT_DIR="modules/$ARGUMENTS/tests"
uv run pytest "$UNIT_DIR" -m "$CI_MARKERS" --import-mode=importlib -o "addopts=" --tb=short -q -rs
```

**Expected**: All tests pass (exit code 0)

### 3. Run Integration Tests (if exist)

```bash
if [ -d "modules/$ARGUMENTS/tests/unit" ] && [ -d "modules/$ARGUMENTS/tests/integration" ]; then
    uv run pytest "modules/$ARGUMENTS/tests/integration" \
        -m "not (slow or online or sglang or performance or dataset)" \
        --import-mode=importlib -o "addopts=" --tb=short -q -rs
fi
```

**Expected**: All tests pass (exit code 0)

### 4. Check Dependency Security

```bash
# Known vulnerabilities in the installed environment. Workspace packages are editable
# and not on PyPI, hence --skip-editable. Needs network access; no account.
uv run pip-audit --skip-editable

# JSON output, written outside modules/
mkdir -p out/verify && uv run pip-audit --skip-editable -f json -o out/verify/pip-audit.json
```

The audit covers the whole shared `.venv`, not only this module, and is not part of CI.

**Expected**: No known vulnerabilities (exit code 0; pip-audit exits 1 when it finds any)

**If vulnerabilities found**:
- CRITICAL/HIGH: Stop and report. Do not proceed until resolved or explicitly accepted.
- MEDIUM/LOW: Document and continue, but flag for review.

### 5. Check Formatting

```bash
# Black
uv run black --check modules/$ARGUMENTS/src/

# isort
uv run isort --check modules/$ARGUMENTS/src/
```

**Expected**: No formatting issues (exit code 0)

### 6. Run Linter

```bash
uv run flake8 modules/$ARGUMENTS/src/
```

**Expected**: No lint errors (exit code 0)

### 7. Run Type Checker (if configured)

```bash
# Check if mypy is configured
if [ -f "modules/$ARGUMENTS/mypy.ini" ] || grep -q "\[tool.mypy\]" "modules/$ARGUMENTS/pyproject.toml"; then
    uv run mypy modules/$ARGUMENTS/src/
fi
```

**Expected**: No type errors (exit code 0)

### 8. Run Metrics Analysis

```bash
# Cyclomatic Complexity (CC)
# Grades: A (1-5), B (6-10), C (11-20), D (21-30), E (31-40), F (41+)
uv run radon cc modules/$ARGUMENTS/src/ -a -s --total-average

# Maintainability Index (MI): compare the printed number, not radon's letter grade
uv run radon mi modules/$ARGUMENTS/src/ -s
```

**Thresholds**:
| Metric | Good | Acceptable | Review Needed |
|--------|------|------------|---------------|
| CC (avg) | ≤ 5 (A) | 6-10 (B) | > 10 (C+) |
| MI (min) | > 50 | 38-50 | < 38 |

### 9. Anomaly Detection

After collecting metrics, identify components that deviate significantly:

```bash
# List files with complexity > 10 (grade C or worse)
uv run radon cc modules/$ARGUMENTS/src/ -a -nc

# List files with poor maintainability (MI < 38, see rv-analyze-complexity/reference.md)
uv run radon mi modules/$ARGUMENTS/src/ -s | awk -F'[()]' '$(NF-1)+0 < 38'
```

**Anomaly Criteria**:
- Cyclomatic complexity > 10 for any function
- Maintainability index < 40 for any file
- File length > 500 lines
- Function length > 50 lines

**Action for Anomalies**: Flag for review, consider refactoring.

---

## Output Format

```markdown
## Verification Report: [module-name]

### Summary
| Check | Status | Details |
|-------|--------|---------|
| Unit Tests | PASS/FAIL | X passed, Y failed |
| Integration Tests | PASS/FAIL/SKIP | X passed, Y failed |
| Dependency Security | PASS/FAIL | X vulnerabilities |
| Format (black) | PASS/FAIL | X files checked |
| Format (isort) | PASS/FAIL | X files checked |
| Lint (flake8) | PASS/FAIL | X issues found |
| Type (mypy) | PASS/FAIL/SKIP | X errors found |
| Complexity (CC) | PASS/WARN | Avg: X, Max: Y |
| Maintainability (MI) | PASS/WARN | Min: X |

### Overall: PASS / FAIL / WARN

### Metrics Summary
| Metric | Value | Grade | Status |
|--------|-------|-------|--------|
| Avg Cyclomatic Complexity | 5.2 | A | OK |
| Max Cyclomatic Complexity | 12 | C | REVIEW |
| Min Maintainability Index | 55 | B | OK |

### Anomalies Detected
| File | Metric | Value | Threshold |
|------|--------|-------|-----------|
| executor.py | CC | 25 | > 10 |
| parser.py | MI | 35 | < 38 |

### Issues Found (if any)
[List of issues with file:line references]

### Quality Attributes Verified
- [x] Reliability (tests)
- [x] Security (pip-audit, bandit)
- [x] Maintainability (complexity, MI)
- [x] Understandability (lint)

### Next Steps (if FAIL/WARN)
1. [Suggested fix 1]
2. [Suggested fix 2]
```

---

## Quick Fix Commands

If verification fails, use these to auto-fix:

```bash
# Fix formatting
uv run black modules/$ARGUMENTS/src/ && uv run isort modules/$ARGUMENTS/src/

# Then re-run verification
/rv-verify [module-name]
```

---

## Rules

1. **Run ALL checks** - Don't skip any step
2. **Report ALL issues** - Collect before reporting
3. **Stop on critical failure** - Test failures are blocking
4. **WARN on metrics issues** - Metrics violations are warnings, not failures
5. **Flag anomalies** - Components exceeding thresholds need attention
6. **Suggest fixes** - Help user resolve issues
7. **Exit code** - Return non-zero if ANY check fails (WARN = exit 0 with warnings)

---

## Integration Notes

This skill is used by orchestrators:
- `rv-refactor` - After execution phase
- `rv-feature` - After implementation phase
- `rv-tdd` - After GREEN/REFACTOR phases
- `rv-cleanup` - After cleanup execution

Called as: "Use /rv-verify [module] to run full verification"
