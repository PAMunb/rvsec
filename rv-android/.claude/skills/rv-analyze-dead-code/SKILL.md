---
name: rv-analyze-dead-code
description: >-
  Find unused imports, functions, and dead code. Use when cleaning up codebase,
  reducing technical debt, or before major refactoring.
  Do NOT use for: removing code (use /rv-cleanup), quick auto-fix (use /rv-refactor-cleanup).
argument-hint: [module-name]
context: fork
agent: general-purpose
allowed-tools: Read, Grep, Glob, Bash
---

# Find Dead Code: $ARGUMENTS

## Supporting Files

Read these reference files before starting analysis:

- `checklists/dead-code-categories.md` — 8 dead code categories with priority-based removal guidelines
- `checklists/false-positive-patterns.md` — Patterns where code appears dead but is actually used (dynamic dispatch, frameworks, registries)
- `templates/report.md` — Output report format

---

## MCP Integration (with fallback)

### Step 0: Check Memory for Cached Analysis

Before expensive analysis, check for recent cached data:

```
Use mcp__memory__search_nodes with query: "dead-code-$ARGUMENTS"
```

**If found and recent** (< 7 days based on entity name date):
- Return cached findings
- Note: "Using cached analysis from [date]"

**If not found or stale**:
- Proceed with full analysis below

### Primary Path (MCP available)
- **memory**: Persist dead code findings:
  - Entity name: `dead-code-$ARGUMENTS-[YYYY-MM-DD]`
  - Type: `dead-code-analysis`

### Fallback Path (MCP unavailable)
If MCP tools fail:
1. Output findings directly to user
2. Note "MCP unavailable - findings not persisted"

**Always complete the analysis** - MCP enhances but is not required.

---

## Steps

1. **Parse module** from $ARGUMENTS (default: rv-agent)

2. **Find unused imports**:
   ```bash
   cd modules/$MODULE
   uv run python -m pyflakes src/ 2>&1 | grep "imported but unused"
   ```

3. **Find unused functions**:
   - Search for function definitions
   - Check if they're called anywhere
   - Look for `# TODO: remove` or `# deprecated` comments

4. **Find unused variables**:
   ```bash
   uv run python -m pyflakes src/ 2>&1 | grep "assigned to but never used"
   ```

5. **Check for dead code patterns**:
   - Unreachable code after return/raise
   - Empty except blocks
   - Pass-only functions
   - Commented-out code blocks

6. **Generate cleanup report**

## Output Format

```
## Dead Code Analysis: [module]

### Summary
- Unused imports: X
- Unused functions: Y
- Unused variables: Z
- Dead code blocks: W

### Unused Imports

| File | Import | Line |
|------|--------|------|
| file.py | unused_module | 10 |

### Unused Functions

| File | Function | Line | Reason |
|------|----------|------|--------|
| file.py | old_function | 50 | No callers found |

### Dead Code Blocks

| File | Lines | Type |
|------|-------|------|
| file.py | 100-110 | Commented code |

### Cleanup Commands

```bash
# Remove unused imports automatically
uv run autoflake --in-place --remove-all-unused-imports src/
```

### Recommendations
1. [Prioritized cleanup actions]
```

## Guidelines

- Move removed code to `backup/` if unsure
- Run tests after cleanup
- Check git blame before removing old code
- Some "unused" code may be used via reflection/dynamic imports
