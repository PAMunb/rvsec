---
name: rv-refactor-cleanup
description: >-
  Quick automated cleanup of unused imports and formatting. Use for fast cleanup without planning.
  Do NOT use for: large-scale dead code removal, cleanup requiring user approval, or when backups are critical.
  Use /rv-cleanup orchestrator for comprehensive cleanup with checkpoints and safety controls.
argument-hint: [module-name]
context: fork
agent: general-purpose
allowed-tools: Read, Grep, Glob, Edit, Write, Bash
---

# Cleanup Module: $ARGUMENTS

## Steps

1. **Run dead code analysis** first:
   ```
   Invoke /rv-analyze-dead-code $MODULE
   ```
   This will identify unused imports, functions, and dead code systematically.

2. **Identify cleanup targets**:
   - Unused imports
   - Unused functions/classes
   - Commented-out code
   - TODO/FIXME that are done
   - Empty files
   - Orphan test files

3. **Create backup**:
   ```bash
   mkdir -p backup/cleanup_$(date +%Y%m%d)
   ```

4. **Perform cleanup**:
   - Remove unused imports (autoflake)
   - Delete unused functions
   - Remove commented code blocks
   - Delete empty files

5. **Verify**:
   ```bash
   poetry run pytest tests/ -v
   ```

## Automated Cleanup

```bash
# Remove unused imports
poetry run autoflake --in-place --remove-all-unused-imports --recursive src/

# Sort imports
poetry run isort src/

# Format code
poetry run black src/

# Check for remaining issues
poetry run flake8 src/
```

## Manual Cleanup Checklist

- [ ] Remove files in backup/ that are confirmed unused
- [ ] Delete empty __init__.py with no exports
- [ ] Remove deprecated functions marked for removal
- [ ] Clean up old migration code
- [ ] Remove feature flags for shipped features

## Output Format

```
## Cleanup Report: [module]

### Summary
- Files cleaned: X
- Lines removed: Y
- Imports fixed: Z

### Changes Made

#### Removed Unused Imports
| File | Removed |
|------|---------|
| file.py | unused_module |

#### Deleted Dead Code
| File | Lines | What |
|------|-------|------|
| file.py | 50-75 | old_function |

#### Deleted Files
| File | Reason |
|------|--------|
| old_module.py | Unused |

### Backup Location
- backup/cleanup_YYYYMMDD/

### Verification
- Tests: [pass/fail]
- Linting: [pass/fail]
```

## Guidelines

- Always backup before cleanup
- Run tests after each major deletion
- Check git blame before removing old code
- Some "dead" code may be used dynamically
- When unsure, move to backup/ instead of deleting
