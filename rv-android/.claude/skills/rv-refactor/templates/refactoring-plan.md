# Refactoring Plan Template

Use this template to document Phase 2 (Planning) output.

---

## Refactoring Plan

### Target: `[module or file path]`
### Date: `[YYYY-MM-DD]`
### Based on Analysis: `[reference to analysis report]`

---

## 1. Scope

### In Scope

- [x] File/component 1
- [x] File/component 2

### Out of Scope

- [ ] File/component 3 (reason: too risky)
- [ ] File/component 4 (reason: separate effort)

---

## 2. Refactoring Steps

### Step 1: [Name]

**Target**: `path/to/file.py`

**What**:
- [specific change 1]
- [specific change 2]

**How**:
```
Before: [describe current state]
After:  [describe target state]
```

**Dependencies**: None / Step X must complete first

**Verification**:
- [ ] Unit tests pass
- [ ] No new linting errors

---

### Step 2: [Name]

**Target**: `path/to/file.py`

**What**:
- [specific change]

**How**:
```
Before: Class A contains methods X, Y, Z
After:  Method Z extracted to new class B
```

**Dependencies**: Step 1

**Verification**:
- [ ] Unit tests pass
- [ ] Integration tests pass

---

### Step 3: [Name]

[Continue pattern...]

---

## 3. Execution Order

```
Step 1 ──► Step 2 ──► Step 3
              │
              └──► Step 4 (parallel)
```

| Step | Depends On | Can Parallelize |
|------|------------|-----------------|
| 1 | - | No |
| 2 | 1 | No |
| 3 | 2 | Yes (with 4) |
| 4 | 2 | Yes (with 3) |

---

## 4. Impact Assessment

### Files Modified

| File | Changes | Risk |
|------|---------|------|
| `file1.py` | Extract class | LOW |
| `file2.py` | Update imports | LOW |
| `file3.py` | Major restructure | MEDIUM |

### Breaking Changes

| Change | Affected Code | Migration |
|--------|---------------|-----------|
| Rename function X | callers in Y, Z | Update all callers |
| None | - | - |

---

## 5. Rollback Strategy

### Backup Locations

```
backup/
├── file1_YYYYMMDD.py
├── file2_YYYYMMDD.py
└── file3_YYYYMMDD.py
```

### Rollback Commands

```bash
# Full rollback
cp backup/file1_YYYYMMDD.py path/to/file1.py
cp backup/file2_YYYYMMDD.py path/to/file2.py

# Partial rollback (Step 2 only)
git checkout HEAD -- path/to/file2.py
```

---

## 6. Success Criteria

- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] No new linting errors
- [ ] Code review approved
- [ ] Complexity metrics improved

### Metrics Goals

| Metric | Before | Target | Actual |
|--------|--------|--------|--------|
| Lines in file.py | 800 | < 500 | TBD |
| Cyclomatic complexity | 25 | < 15 | TBD |

---

## 7. Approval

**Plan Status**: PENDING / APPROVED / REJECTED

**User Decision**: [awaiting / approved / rejected with feedback]

**Notes**: [any user feedback or modifications]
