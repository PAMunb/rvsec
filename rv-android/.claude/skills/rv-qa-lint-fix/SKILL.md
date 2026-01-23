---
name: rv-qa-lint-fix
description: >-
  Auto-fix linting issues. Use after running rv-qa-lint to automatically fix formatting and import issues.
  Do NOT use for: analysis only (use /rv-qa-lint), manual fixes requiring review.
argument-hint: [module-name or file-path]
context: fork
agent: general-purpose
allowed-tools: Read, Bash
---

# Auto-Fix Lint Issues: $ARGUMENTS

## Steps

1. **Parse scope** from $ARGUMENTS

2. **Run auto-fixers**:
   ```bash
   cd modules/$MODULE

   # Fix imports (remove unused, sort)
   poetry run autoflake --in-place --remove-all-unused-imports --recursive src/
   poetry run isort src/

   # Fix formatting
   poetry run black src/
   ```

3. **Verify fixes**:
   ```bash
   poetry run flake8 src/ --max-line-length=120
   poetry run mypy src/ --ignore-missing-imports
   ```

4. **Run tests** to ensure no breakage:
   ```bash
   poetry run pytest tests/unit/ -v
   ```

5. **Run full verification**:
   ```
   Invoke /rv-verify $MODULE
   ```
   This ensures all checks pass after auto-fixes (tests, lint, types, formatting).

6. **Report changes**

## Fix Order

1. **autoflake** - Remove unused imports
2. **isort** - Sort imports
3. **black** - Format code

This order prevents conflicts between tools.

## Output Format

```
## Lint Fix Report: [scope]

### Fixes Applied

#### autoflake (unused imports)
| File | Removed |
|------|---------|
| file.py | unused_module, another |

#### isort (import sorting)
| File | Status |
|------|--------|
| file.py | ✅ Fixed |

#### black (formatting)
| File | Status |
|------|--------|
| file.py | ✅ Reformatted |

### Remaining Issues (manual fix needed)
| File | Line | Code | Message |
|------|------|------|---------|
| file.py | 50 | F841 | unused variable 'x' |

### Verification
- Linting: [pass/issues remaining]
- Tests: [pass/fail]

### Git Diff
```bash
git diff --stat
```
```

## Manual Fixes Required

Some issues can't be auto-fixed:
- F841: Unused variables (may be intentional)
- E501: Some long strings (URLs, docstrings)
- Type errors from mypy

## Rollback

If fixes break something:
```bash
git checkout -- src/
```
