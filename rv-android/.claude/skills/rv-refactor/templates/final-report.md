# Final Report Template

Use this template to document the completed refactoring.

---

## Refactoring Final Report

### Target: `[module or file path]`
### Date: `[YYYY-MM-DD]`
### Duration: `[start] to [end]`

---

## 1. Executive Summary

[2-3 sentences summarizing what was accomplished]

**Status**: SUCCESS / PARTIAL / FAILED

---

## 2. Changes Made

### Files Created

| File | Purpose | Lines |
|------|---------|-------|
| `new_file.py` | Extracted from X | 150 |

### Files Modified

| File | Changes | Lines Changed |
|------|---------|---------------|
| `file1.py` | Extracted class Y | -200 |
| `file2.py` | Updated imports | +5, -3 |

### Files Deleted

| File | Reason |
|------|--------|
| `old_file.py` | Merged into X |
| None | - |

---

## 3. Metrics Comparison

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Total lines | 1500 | 1200 | -20% |
| Files | 5 | 6 | +1 |
| Avg file size | 300 | 200 | -33% |
| Max complexity | 25 | 12 | -52% |
| Test coverage | 75% | 80% | +5% |

---

## 4. Test Results

### Unit Tests

```
========================= test session starts ==========================
collected X items

tests/unit/test_file1.py ....                                     [100%]
tests/unit/test_file2.py ....                                     [100%]

========================= X passed in Y.YYs ===========================
```

### Integration Tests

```
[paste test output]
```

### Linting

```
flake8: PASS (0 errors)
mypy: PASS (0 errors)
black: PASS (formatted)
```

---

## 5. Code Review Summary

**Reviewer**: rv-code-reviewer

### Critical Issues: 0

### Warnings: X

| Issue | File | Resolution |
|-------|------|------------|
| [warning] | file.py | Fixed in commit Y |

### Suggestions: X

| Suggestion | Status |
|------------|--------|
| [suggestion] | Accepted / Deferred |

---

## 6. Backup Locations

All original files backed up to:

```
backup/
├── file1_YYYYMMDD.py
├── file2_YYYYMMDD.py
└── file3_YYYYMMDD.py
```

**Retention**: Keep for 30 days, then safe to delete.

---

## 7. Known Issues

| Issue | Severity | Workaround | Future Fix |
|-------|----------|------------|------------|
| None | - | - | - |

---

## 8. Lessons Learned

1. [What went well]
2. [What could be improved]
3. [Recommendations for future refactoring]

---

## 9. Sign-off

**Refactoring Status**: COMPLETE / PARTIAL

**User Approval**: APPROVED / PENDING

**Notes**: [any final notes]
