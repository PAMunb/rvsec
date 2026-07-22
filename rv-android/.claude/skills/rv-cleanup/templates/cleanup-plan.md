# Cleanup Plan Template

---

## Cleanup Plan

### Target: `[module-name]`
### Date: `[YYYY-MM-DD]`
### Based on Analysis: `[analysis-report reference]`

---

## 1. Scope

### Approved for Cleanup

- [x] Unused imports (X items)
- [x] Unused private functions (X items)
- [ ] Unused public functions (needs review)
- [ ] Unused classes (needs review)

### Out of Scope

- [ ] `file.py` - Too risky, needs manual review
- [ ] External API code - May be used by clients

---

## 2. Cleanup Groups

### Group 1: Unused Imports (P1 - Very Low Risk)

| File | Import | Line |
|------|--------|------|
| `file1.py` | `os` | 5 |
| `file2.py` | `sys` | 3 |

**Verification**: Unit tests only

---

### Group 2: Unused Private Functions (P2 - Low Risk)

| File | Function | Lines |
|------|----------|-------|
| `file1.py` | `_old_helper()` | 50-65 |

**Verification**: Unit + Integration tests

---

### Group 3: Unused Classes (P3 - Medium Risk)

| File | Class | Lines |
|------|-------|-------|
| `file2.py` | `LegacyHandler` | 100-150 |

**Verification**: Full test suite

---

## 3. Execution Order

```
Group 1 (imports) ──► Group 2 (functions) ──► Group 3 (classes)
     │                      │                      │
     ▼                      ▼                      ▼
   Test                   Test                   Test
```

---

## 4. Rollback Strategy

### Backup Commands

```bash
# Before starting
mkdir -p backup/cleanup_$(date +%Y%m%d)
cp file1.py backup/cleanup_$(date +%Y%m%d)/
cp file2.py backup/cleanup_$(date +%Y%m%d)/
```

### Rollback Commands

```bash
# If needed
cp backup/cleanup_YYYYMMDD/file1.py file1.py
cp backup/cleanup_YYYYMMDD/file2.py file2.py
```

---

## 5. Success Criteria

- [ ] All tests pass after each group
- [ ] No new linting errors
- [ ] Estimated lines removed: X
- [ ] No functionality regression

---

## 6. Approval

**Plan Status**: PENDING / APPROVED / PARTIAL

**User Decision**: [awaiting]

**Notes**: [any modifications requested]
