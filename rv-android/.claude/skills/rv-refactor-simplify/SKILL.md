---
name: rv-refactor-simplify
description: >-
  Simplify over-engineered or complex code. Use when reducing complexity,
  removing unnecessary abstractions, or applying KISS principle.
  Do NOT use for: extracting components (use /rv-refactor-extract),
  full module refactoring (use /rv-refactor).
argument-hint: [file-path]
context: fork
agent: general-purpose
allowed-tools: Read, Grep, Glob, Edit, Write, Bash, Skill
---

# Simplify Code: $ARGUMENTS

## Principles

1. **No over-engineering**: Only necessary changes
2. **KISS**: Minimum complexity for current requirements
3. **No legacy wrappers**: Remove or overwrite, don't wrap
4. **Backup first**: Move old files to `backup/` before replacement

## Steps

1. **Analyze complexity** first - Use the **Skill tool**:
   ```
   Skill tool: skill="rv-analyze-complexity", args="$ARGUMENTS"
   ```
   This identifies the most complex areas that need simplification.

2. **Read and understand** the file at $ARGUMENTS

3. **Identify simplification opportunities**:
   - Unused parameters or variables
   - Over-abstracted code (unnecessary interfaces/base classes)
   - Duplicated code blocks
   - Complex conditionals
   - Unnecessary defensive code
   - Premature abstractions

4. **Plan simplifications**:
   - List specific changes
   - Ensure no functionality loss
   - Verify dependencies won't break

5. **Create backup** if major changes:
   ```bash
   cp path/to/file.py backup/file.py.bak
   ```

6. **Apply changes**:
   - Remove unused code
   - Inline trivial abstractions
   - Consolidate duplicated logic
   - Simplify conditionals

6. **Verify**:
   ```bash
   cd modules/$MODULE
   PYTHONPATH=../rv-android-core/src:src poetry run pytest tests/unit/ -v
   ```

## Common Simplifications

| Pattern | Before | After |
|---------|--------|-------|
| Nested ifs | `if x: if y:` | `if x and y:` |
| Boolean return | `if x: return True else: return False` | `return x` |
| Unnecessary else | `if x: return a else: return b` | `if x: return a; return b` |
| Single-use variable | `temp = f(); return temp` | `return f()` |
| Empty base class | `class X(Base): pass` | Remove if Base unused |

## Output Format

```
## Simplification Report: [filename]

### Before
- Lines: XXX
- Classes: Y
- Functions: Z
- Complexity issues: [list]

### Changes Made
1. **[Change 1]**: [reason]
   - Before: `code`
   - After: `code`

2. **[Change 2]**: [reason]

### After
- Lines: XXX (reduced by Y)
- Classes: Y
- Functions: Z

### Backup
- Created: backup/[filename].bak

### Verification
- Tests: [pass/fail]
- Imports: [ok/broken]
```

## Guidelines

- Three similar lines > premature abstraction
- Don't add helpers for one-time operations
- Don't design for hypothetical future
- If unused, delete completely
- Avoid backwards-compatibility hacks
