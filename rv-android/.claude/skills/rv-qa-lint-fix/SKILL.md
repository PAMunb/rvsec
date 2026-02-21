---
name: rv-qa-lint-fix
description: >-
  Auto-fix linting issues. Use after running rv-qa-lint to automatically fix formatting and import issues.
  Do NOT use for: analysis only (use /rv-qa-lint), manual fixes requiring review.
argument-hint: [module-name or file-path]
context: fork
agent: general-purpose
allowed-tools: Read, Bash, Skill
---

# Auto-Fix Lint Issues: $ARGUMENTS

## Step 1: Parse Scope

Parse module name from `$ARGUMENTS`.

## Step 2: Run Auto-Fixers (ONLY these 3 commands)

Run ONLY these 3 commands. Do NOT add any verification, checking, or analysis steps. Do NOT run flake8, mypy, or any other tool. Do NOT read or manually edit source files.

```bash
cd modules/$MODULE
uv run autoflake --in-place --remove-all-unused-imports --recursive src/
uv run isort src/
uv run black src/
```

After these 3 commands complete, go DIRECTLY to Step 3. Do NOT perform any intermediate verification.

## Step 3: Verify via rv-verify (MANDATORY — DO NOT SKIP)

You MUST invoke rv-verify using the **Skill tool**. This is the ONLY verification step — do NOT run flake8, mypy, pytest, or any other tool directly via Bash:

```
Skill tool: skill="rv-verify", args="$MODULE"
```

rv-verify handles ALL verification (tests, lint, types, formatting). You MUST invoke this skill even if the auto-fixers reported no changes.

## Step 4: Report Changes

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
