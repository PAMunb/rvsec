---
name: rv-analyze-complexity
description: Analyze code complexity of a module using radon and qualitative metrics.
argument-hint: "<module-name>"
context: fork
agent: general-purpose
allowed-tools: Read, Grep, Glob, Bash
---

# Analyze Module Complexity: $ARGUMENTS

> **Scope**: This skill analyzes an entire module. For single-file analysis, use `/rv-analyze-file-complexity`.
> Do NOT use for: making changes (use `/rv-refactor-simplify`), full module audit (use `/rv-analyze-module`).

## Steps

### Step 0: Check MCP Memory Cache

```
Use mcp__memory__search_nodes with query: "analysis:complexity:$ARGUMENTS"
```

If found, extract the `git_hash` observation. Compare with current hash:
```bash
git log -1 --format=%h -- modules/$ARGUMENTS/
```

- **Cache hit** (hashes match): Return the cached `summary` and `details` observations. Note "Using cached analysis. Module unchanged since [date]." and STOP.
- **Cache miss** (hashes differ or not found): Proceed to Step 1.

### Step 1: Read Reference

Read `reference.md` from this skill's directory. It contains complexity thresholds, refactoring indicators, and Python-specific signals. Use these thresholds for all classifications.

### Step 2: Run Static Analysis (radon)

Run radon across ALL module source files in a SINGLE Bash call:
```bash
echo "=== CC ===" && uv run radon cc modules/$ARGUMENTS/src/ -s -a -nc && echo "=== MI ===" && uv run radon mi modules/$ARGUMENTS/src/ -s && echo "=== RAW ===" && uv run radon raw modules/$ARGUMENTS/src/ -s
```

- `-nc` filters CC output to grade C or worse (≥11), reducing noise
- If no `src/` directory, use `modules/$ARGUMENTS/` instead
- Radon provides: CC per function (A-F), MI per file (A-C), raw LOC/SLOC/comments

### Step 3: Identify Hotspots

From radon output, identify files with ANY of:
- Function with CC grade C or worse (≥11)
- MI below 65 (grade B or C)
- SLOC > 500

For each hotspot file, Read it and assess what radon does NOT provide:
- Parameter count per function (exclude `self`/`cls`)
- Maximum nesting depth per function
- Code smell patterns from reference.md (God Class, Long Method, Feature Envy, etc.)

Skip this step if radon found no hotspots — report all-clear.

### Step 4: Persist to MCP Memory

```
Use mcp__memory__create_entities (or update existing via delete + create):
  Entity: "analysis:complexity:$ARGUMENTS"
  Type: "module-complexity-analysis"
  Observations:
    - "git_hash: <hash>"
    - "date: YYYY-MM-DD"
    - "summary: files=X, hotspots=Y, avg_MI=Z(grade), max_CC=W(grade), total_SLOC=N"
    - "details: <full report as single observation>"
```

If MCP fails, skip caching — still output the report.

## Output Format

```markdown
## Module Complexity: <module-name>

**Files**: X | **Hotspots**: Y | **Avg MI**: Z (grade) | **Max CC**: W (grade) | **Total SLOC**: N

### Hotspot Files

| File | SLOC | MI | Grade | Max CC | Grade | Status |
|------|------|----|-------|--------|-------|--------|
| path/file.py | X | Y | B | Z | C | Warning |

### Function-Level Detail (hotspots only)

| File | Function | CC | Grade | Lines | Params | Nesting | Status |
|------|----------|-----|-------|-------|--------|---------|--------|
| file.py | func | 15 | C | 80 | 6 | 4 | Must Refactor |

### Code Smells (if any)

| File | Smell | Evidence | Severity | Refactoring |
|------|-------|----------|----------|-------------|
| file.py | God Class | 25 methods | High | Extract Class |

### Recommendations

1. **file.py:func** — CC=15, 6 params: [specific action]
```
