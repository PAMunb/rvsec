---
name: rv-analyze-file-complexity
description: Analyze complexity metrics of a single Python file.
argument-hint: "<file-path>"
context: fork
agent: general-purpose
allowed-tools: Read, Grep, Glob, Bash
---

# Analyze File Complexity: $ARGUMENTS

> **Scope**: This skill analyzes ONE file. For module-wide complexity analysis, use `/rv-analyze-complexity`.
> Do NOT use for: making changes (use `/rv-refactor-simplify`), module analysis (use `/rv-analyze-complexity`).

## Thresholds

| Metric | OK | Warning | Must Refactor |
|--------|----|---------|---------------|
| Cyclomatic complexity | ≤10 (A-B) | 11-20 (C) | >20 (D-F) |
| Maintainability index | >65 (A) | 40-65 (B) | <40 (C) |
| Function length | ≤50 SLOC | 51-100 | >100 |
| Nesting depth | ≤3 | 4 | ≥5 |
| Parameter count | ≤3 | 4-5 | ≥6 |
| File SLOC | ≤500 | 501-1000 | >1000 |

Exclude `self`/`cls` from parameter count.

## Steps

### Step 0: Check MCP Memory Cache

```
Use mcp__memory__search_nodes with query: "analysis:file-complexity:$ARGUMENTS"
```

If found, extract the `git_hash` observation. Compare with current hash:
```bash
git log -1 --format=%h -- $ARGUMENTS
```

- **Cache hit** (hashes match): Return the cached `summary` and `details` observations. Note "Using cached analysis. File unchanged since [date]." and STOP.
- **Cache miss** (hashes differ or not found): Proceed to Step 1.

### Step 1: Run Static Analysis

Run ALL three radon commands in a SINGLE Bash call:
```bash
echo "=== CC ===" && uv run radon cc $ARGUMENTS -s -a && echo "=== MI ===" && uv run radon mi $ARGUMENTS -s && echo "=== RAW ===" && uv run radon raw $ARGUMENTS -s
```

This produces:
- **CC**: Cyclomatic complexity per function/class with grade (A-F) and average
- **MI**: Maintainability index with grade (A-C)
- **RAW**: LOC, LLOC, SLOC, comments, blank lines

### Step 2: Read File for Qualitative Analysis

Read the target file. Extract what radon does NOT provide:
- Parameter count per function (exclude `self`/`cls`)
- Max nesting depth per function
- Number of imports

### Step 3: Classify and Report

Combine radon metrics (Step 1) with qualitative metrics (Step 2). Classify each against thresholds. Only include Recommendations if at least one metric exceeds OK.

### Step 4: Persist to MCP Memory

```
Use mcp__memory__create_entities (or update existing via delete_observations + add_observations):
  Entity: "analysis:file-complexity:<file-path>"
  Type: "file-complexity-analysis"
  Observations:
    - "git_hash: <hash>"
    - "date: YYYY-MM-DD"
    - "summary: SLOC=X, MI=Y(grade), avg_CC=Z(grade), functions=N, max_CC=W"
    - "details: <full report as single observation>"
```

If MCP fails, skip caching — still output the report.

## Output Format

```markdown
## File Complexity: <filename>

**SLOC**: X | **MI**: Y (grade) | **Avg CC**: Z (grade) | **Functions**: N | **Classes**: M

### Static Analysis (radon)

| Function/Method | CC | Grade | Lines | Status |
|-----------------|-----|-------|-------|--------|
| func_name       | X   | A     | Y     | OK/Warning/Refactor |

### Qualitative Metrics

| Function/Method | Params | Nesting | Status |
|-----------------|--------|---------|--------|
| func_name       | X      | Y       | OK/Warning/Refactor |

### Recommendations

1. **func_name** — [issue]: [action]
```
