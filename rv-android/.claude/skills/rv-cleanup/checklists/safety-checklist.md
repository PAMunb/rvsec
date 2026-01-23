# Cleanup Safety Checklist

Complete before and after each cleanup group.

---

## Pre-Cleanup Verification

- [ ] Analysis report reviewed
- [ ] Cleanup plan approved by user
- [ ] All tests currently passing
- [ ] Backups created for all target files
- [ ] No uncommitted changes in target files

### Backup Verification

```bash
# List backups
ls -la backup/cleanup_*/

# Verify backup content
diff file.py backup/cleanup_YYYYMMDD/file.py
```

---

## Per-Group Verification

After EACH cleanup group:

### Immediate Checks

- [ ] Files saved successfully
- [ ] No syntax errors (file loads)
- [ ] Linters pass:
  ```bash
  poetry run flake8 path/to/file.py
  poetry run black path/to/file.py --check
  ```

### Test Verification

- [ ] Unit tests pass
- [ ] Integration tests pass (if applicable)
- [ ] No new test failures
- [ ] Test count unchanged (no tests removed)

### Rollback Decision

If tests fail:
- [ ] Attempted fix (max 2 attempts)
- [ ] If cannot fix: ROLLBACK from backup
- [ ] Mark group as SKIPPED
- [ ] Document reason

---

## Confidence Level Guide

| Level | Criteria | Action |
|-------|----------|--------|
| HIGH | No references, private, isolated | Auto-approve removal |
| MEDIUM | Few refs, might be dynamic | Ask user |
| LOW | Unclear, public API | Manual review only |

---

## Do NOT Remove If

- [ ] Referenced via reflection (`getattr`, `__getattribute__`)
- [ ] Used in dynamic imports (`importlib`)
- [ ] Part of public API (used externally)
- [ ] Has TODO/FIXME indicating future use
- [ ] Tests reference it directly
- [ ] Confidence is LOW

---

## Final Verification

After ALL groups complete:

- [ ] Full test suite passes
- [ ] All linters pass
- [ ] Code review completed
- [ ] Metrics documented (lines removed)
- [ ] Backups retained for 30 days
- [ ] User approved final result
