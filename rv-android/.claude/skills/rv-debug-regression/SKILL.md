---
name: rv-debug-regression
description: >-
  Investigate regression bugs using git history. Use when tests fail after changes
  or when tracking down when something broke.
  Do NOT use for: new test failures (use /rv-tdd), flaky tests, or non-regression bugs.
argument-hint: [test-name or error-message]
context: fork
agent: general-purpose
allowed-tools: Bash, Read, Grep, Glob, Skill
---

# Debug Regression: $ARGUMENTS

Systematic investigation of regression bugs using git history to find when and why something broke.

## Supporting Files

- **Templates**: `templates/regression-report.md` - Analysis report format
- **Templates**: `templates/regression-test.py` - Regression test template

---

## Workflow

```
STEP 1: CONFIRM FAILURE ─────────────────────────────────────────►
    │  Reproduce the failing test
    ▼
STEP 2: FIND LAST GOOD ──────────────────────────────────────────►
    │  Binary search through git history
    ▼
STEP 3: ANALYZE BREAKING CHANGE ─────────────────────────────────►
    │  Understand what changed
    ▼
STEP 4: GENERATE FIX STRATEGY ───────────────────────────────────►
    │  Propose solution + regression test
    ▼
REPORT ──────────────────────────────────────────────────────────►
```

---

## Steps

### Step 1: Confirm Failure

First, reproduce the failure:

```bash
# Run the failing test
cd modules/[module]
PYTHONPATH=../rv-android-core/src:src poetry run pytest tests/[path]::$ARGUMENTS -v

# Capture error output
poetry run pytest tests/[path]::$ARGUMENTS -v 2>&1 | tee /tmp/test_failure.log
```

**Document**:
- Test name and location
- Error message
- Stack trace
- Expected vs actual behavior

### Step 2: Find Last Known Good Commit

Use git bisect guidance (manual, not automated):

```bash
# Start from recent history
git log --oneline -20

# Check if test passed N commits ago
git checkout HEAD~5
poetry run pytest tests/[path]::$ARGUMENTS -v

# Binary search to narrow down
# If PASS at HEAD~5, check HEAD~2
# If FAIL at HEAD~5, check HEAD~10
```

**Goal**: Find the commit where test started failing

### Step 3: Analyze Breaking Change

Once the breaking commit is found:

```bash
# See what changed
git show [breaking-commit] --stat
git show [breaking-commit] -- [relevant-files]

# Compare before and after
git diff [good-commit] [breaking-commit] -- src/
```

**Document**:
- Breaking commit hash and message
- Files changed
- Specific lines that caused the regression
- Reason for change (was it intentional or accidental?)

### Step 4: Generate Fix Strategy

Based on analysis, propose:

1. **Root cause**: Why the change broke the test
2. **Fix options**:
   - Revert the change?
   - Modify the change to preserve old behavior?
   - Update the test if behavior change was intentional?
3. **Regression test**: Template for test that prevents recurrence

### Step 5: Apply and Verify Fix

After implementing the chosen fix, use the **Skill tool**:

```
Skill tool: skill="rv-test-run", args="[module] [test-path]"
```

**Verify**:
- The originally failing test now passes
- No other tests were broken by the fix
- Run full test suite if fix touched shared code

---

## Output Format

```markdown
## Regression Analysis Report

### Test: [test-name]
**Location**: `tests/unit/test_file.py::test_name`
**Status**: FAILING

### Error
```
[Error message and relevant stack trace]
```

### Investigation Timeline

| Step | Commit | Result |
|------|--------|--------|
| HEAD | abc123 | FAIL |
| HEAD~5 | def456 | PASS |
| HEAD~3 | ghi789 | FAIL |
| HEAD~4 | jkl012 | PASS |

### Breaking Commit Found

**Commit**: `mno345` (HEAD~3)
**Author**: [author]
**Date**: [date]
**Message**: [commit message]

### What Changed

```diff
[Relevant diff showing the change]
```

### Root Cause Analysis

[Explanation of why this change broke the test]

### Fix Strategy

**Option 1: Revert** (if change was accidental)
```bash
git revert mno345
```

**Option 2: Fix forward** (if behavior should be preserved)
```python
# Suggested code change
```

**Option 3: Update test** (if new behavior is correct)
```python
# Updated test expectation
```

### Recommended: Option [X]
**Reason**: [Why this is the best approach]

### Regression Test Template

```python
def test_regression_[issue_name]():
    """
    Regression test for: [brief description]
    Breaking commit: mno345
    Root cause: [summary]
    """
    # Setup
    ...

    # Exercise
    result = function_under_test(...)

    # Verify - this should catch the regression
    assert result == expected_value, "Regression: [description]"
```

### Next Steps

1. [ ] Apply fix (Option X)
2. [ ] Add regression test
3. [ ] Run full test suite
4. [ ] Verify fix in CI
```

---

## Git Bisect Guidance

When manually bisecting:

```
                     GOOD              BAD
                      │                 │
    ─────────────────┼─────────────────┼─────
    HEAD~10         HEAD~5           HEAD~1

1. Start at HEAD~5
2. If PASS: breaking commit is between HEAD~5 and HEAD
3. If FAIL: breaking commit is between HEAD~10 and HEAD~5
4. Continue halving until found
```

**Commands**:
```bash
# Checkout specific commit
git checkout [commit-hash]

# Run test
poetry run pytest tests/[path] -v

# Return to original branch
git checkout -
```

---

## Special Cases

### Test Never Passed

If test was recently added and never passed:
- This is not a regression
- Use `/rv-test-add` debugging workflow instead

### Multiple Breaking Commits

If regression was introduced in stages:
- Document all contributing commits
- Fix may need to address multiple changes

### Flaky Test

If test sometimes passes, sometimes fails:
- Not a true regression
- Investigate test reliability first
- Check for timing, ordering, or resource issues

---

## Integration Notes

This skill is useful after:
- CI failure on previously-passing test
- Discovering a bug in production that used to work
- After merging code that breaks tests

---

## Rules

1. **REPRODUCE first** - Confirm failure before investigating
2. **BINARY SEARCH** - Don't check every commit
3. **DOCUMENT everything** - Keep track of what you tried
4. **FIND root cause** - Don't just fix symptoms
5. **ADD regression test** - Prevent recurrence
6. **DON'T automate bisect** - Keep user in control
