# Lint Report: {module}

## Summary

| Check | Status | Issues |
|-------|--------|--------|
| flake8 | {pass/fail} | {count} |
| mypy | {pass/fail} | {count} |
| black | {pass/fail} | {count} |
| isort | {pass/fail} | {count} |
| bandit | {pass/fail} | {count} |

## Overall: {PASS/FAIL}

---

## Security Issues (Bandit)

| Severity | File | Line | Issue ID | Description |
|----------|------|------|----------|-------------|
| HIGH | {file} | {line} | {B###} | {description} |
| MEDIUM | {file} | {line} | {B###} | {description} |

**Action Required**:
- HIGH severity: Must fix before commit
- MEDIUM severity: Review and document justification if acceptable

---

## Type Issues (MyPy)

| File | Line | Error |
|------|------|-------|
| {file} | {line} | {error_message} |

---

## Style Issues (Flake8)

### Errors (must fix)

| File | Line | Code | Message |
|------|------|------|---------|
| {file} | {line} | E### | {message} |

### Warnings (should fix)

| File | Line | Code | Message |
|------|------|------|---------|
| {file} | {line} | W### | {message} |

---

## Formatting Issues

### Black

| File | Status |
|------|--------|
| {file} | Would reformat |

### isort

| File | Status |
|------|--------|
| {file} | Imports would be sorted |

---

## Auto-Fix Commands

```bash
# Fix imports
poetry run autoflake --in-place --remove-all-unused-imports --recursive src/
poetry run isort src/

# Fix formatting
poetry run black src/

# Re-run verification
/rv-verify {module}
```

---

## Next Steps

1. [ ] Fix HIGH severity security issues
2. [ ] Review MEDIUM severity security issues
3. [ ] Fix type errors
4. [ ] Run auto-fixers for formatting
5. [ ] Manual fix for remaining issues
