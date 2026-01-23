---
name: rv-verify
description: >-
  Run all verification checks (tests, lint, type, security). Use before commits, after refactoring,
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
REPORT ──────────────────────────────────────────────────────────►
    │  Unified PASS/FAIL summary
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

### Overall: PASS / FAIL

### Issues Found (if any)
[List of issues with file:line references]

### Next Steps (if FAIL)
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
4. **Suggest fixes** - Help user resolve issues
5. **Exit code** - Return non-zero if ANY check fails

---

## Integration Notes

This skill is used by orchestrators:
- `rv-refactor` - After execution phase
- `rv-feature` - After implementation phase
- `rv-tdd` - After GREEN/REFACTOR phases
- `rv-cleanup` - After cleanup execution

Called as: "Use /rv-verify [module] to run full verification"
