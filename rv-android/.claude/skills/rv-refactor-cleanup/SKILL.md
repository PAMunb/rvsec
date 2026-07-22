---
name: rv-refactor-cleanup
description: >-
  Quick automated cleanup of unused imports and formatting. Use for fast cleanup without planning.
  Do NOT use for: large-scale dead code removal, cleanup requiring user approval, or when backups are critical.
  Use /rv-cleanup orchestrator for comprehensive cleanup with checkpoints and safety controls.
argument-hint: [module-name]
context: fork
agent: general-purpose
allowed-tools: Read, Grep, Glob, Edit, Write, Bash, Skill
---

# Cleanup Module: $ARGUMENTS

## Steps

1. **Run dead code analysis** (MANDATORY — DO NOT SKIP). You MUST invoke this sub-skill BEFORE any cleanup. Do NOT search for dead code yourself via Grep/Read — delegate to rv-analyze-dead-code:
   ```
   Skill tool: skill="rv-analyze-dead-code", args="$MODULE"
   ```

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

5. **Verify via rv-verify** (MANDATORY — DO NOT SKIP). You MUST invoke rv-verify using the **Skill tool**. Do NOT run pytest, flake8, or any other tool directly via Bash — delegate to rv-verify:
   ```
   Skill tool: skill="rv-verify", args="$MODULE"
   ```

## Automated Cleanup

```bash
# Remove unused imports
uv run autoflake --in-place --remove-all-unused-imports --recursive src/

# Sort imports
uv run isort src/

# Format code
uv run black src/

# Check for remaining issues
uv run flake8 src/
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
