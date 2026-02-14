# Verification Checklist

Complete this checklist AFTER each refactoring step and at the end.

---

## Per-Step Verification

After EACH step in the plan:

### Tests

- [ ] Unit tests pass
- [ ] Integration tests pass (if applicable)
- [ ] No new test failures

### Linting

- [ ] `black` formatting applied
- [ ] `isort` imports sorted
- [ ] `flake8` no errors
- [ ] `mypy` no type errors (if enabled)

### Functionality

- [ ] Feature still works as expected
- [ ] No regressions introduced
- [ ] Error handling intact

---

## Final Verification

After ALL steps complete:

### Full Test Suite

```bash
cd modules/$MODULE
PYTHONPATH=../rv-android-core/src:src uv run pytest tests/ -v --tb=short
```

- [ ] All tests pass
- [ ] Test count same or higher than before
- [ ] No skipped tests that weren't skipped before

### Full Lint Suite

```bash
uv run black src/ --check
uv run isort src/ --check-only
uv run flake8 src/
uv run mypy src/ --ignore-missing-imports
```

- [ ] All linters pass

### Code Review

- [ ] Code review requested (rv-code-reviewer)
- [ ] Critical issues: 0
- [ ] Warnings addressed or documented
- [ ] Suggestions considered

### Metrics Improvement

| Metric | Before | After | Improved? |
|--------|--------|-------|-----------|
| Lines of code | | | [ ] |
| Max file size | | | [ ] |
| Complexity | | | [ ] |
| Test coverage | | | [ ] |

### Documentation

- [ ] Code comments updated
- [ ] Docstrings updated
- [ ] CLAUDE.md updated (if architectural change)

---

## Sign-off

- [ ] All verifications passed
- [ ] User approved final result
- [ ] Backups can be retained/deleted per policy

---

## If Verification Fails

1. **Identify** which check failed
2. **Analyze** the root cause
3. **Fix** if possible (max 3 attempts)
4. **Rollback** if cannot fix
5. **Report** to user with details
