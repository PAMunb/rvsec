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
| **Security** | Protected from unauthorized access | bandit, safety, auth tests |

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
    │  Check for known vulnerabilities (safety)
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

```bash
cd modules/$ARGUMENTS
PYTHONPATH=../rv-android-core/src:src poetry run pytest tests/unit/ -v --tb=short
```

**Expected**: All tests pass (exit code 0)

### 3. Run Integration Tests (if exist)

```bash
if [ -d "tests/integration" ]; then
    PYTHONPATH=../rv-android-core/src:src poetry run pytest tests/integration/ -v --tb=short
fi
```

**Expected**: All tests pass (exit code 0)

### 4. Check Dependency Security

```bash
# Check for known vulnerabilities in dependencies
poetry run safety check

# For JSON output (CI integration)
poetry run safety check --json
```

**Expected**: No known vulnerabilities (exit code 0)

**If vulnerabilities found**:
- CRITICAL/HIGH: Stop and report. Do not proceed until resolved or explicitly accepted.
- MEDIUM/LOW: Document and continue, but flag for review.

### 5. Check Formatting

```bash
# Black
poetry run black --check src/

# isort
poetry run isort --check src/
```

**Expected**: No formatting issues (exit code 0)

### 6. Run Linter

```bash
poetry run flake8 src/
```

**Expected**: No lint errors (exit code 0)

### 7. Run Type Checker (if configured)

```bash
# Check if mypy is configured
if [ -f "mypy.ini" ] || grep -q "\[tool.mypy\]" pyproject.toml; then
    poetry run mypy src/
fi
```

**Expected**: No type errors (exit code 0)

### 8. Run Metrics Analysis

```bash
# Cyclomatic Complexity (CC)
# Grades: A (1-5), B (6-10), C (11-20), D (21-30), E (31-40), F (41+)
poetry run radon cc src/ -a -s --total-average

# Maintainability Index (MI)
# Grades: A (100-20), B (19-10), C (9-0)
poetry run radon mi src/ -s
```

**Thresholds**:
| Metric | Good | Acceptable | Review Needed |
|--------|------|------------|---------------|
| CC (avg) | ≤ 5 (A) | 6-10 (B) | > 10 (C+) |
| MI (min) | ≥ 65 (A) | 40-64 (B) | < 40 (C) |

### 9. Anomaly Detection

After collecting metrics, identify components that deviate significantly:

```bash
# List files with complexity > 10 (grade C or worse)
poetry run radon cc src/ -a -nc

# List files with poor maintainability (MI < 40)
poetry run radon mi src/ -s | grep -E "^[CF]"
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
| parser.py | MI | 35 | < 40 |

### Issues Found (if any)
[List of issues with file:line references]

### Quality Attributes Verified
- [x] Reliability (tests)
- [x] Security (safety, bandit)
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
poetry run black src/ && poetry run isort src/

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
