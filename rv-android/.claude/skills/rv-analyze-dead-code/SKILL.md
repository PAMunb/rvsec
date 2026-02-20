---
name: rv-analyze-dead-code
description: Find dead code across a module using pyflakes, vulture, and cross-references.
argument-hint: "<module-name>"
context: fork
agent: general-purpose
allowed-tools: Read, Grep, Glob, Bash
---

# Find Dead Code in Module: $ARGUMENTS

> **Scope**: This skill analyzes an entire module. For single-file analysis, use `/rv-analyze-file-dead-code`.
> Do NOT use for: removing code (use `/rv-cleanup`), quick auto-fix (use `/rv-refactor-cleanup`).

## Steps

### Step 0: Check MCP Memory Cache

```
Use mcp__memory__search_nodes with query: "analysis:dead-code:$ARGUMENTS"
```

If found, extract the `git_hash` observation. Compare with current hash:
```bash
git log -1 --format=%h -- modules/$ARGUMENTS/
```

- **Cache hit** (hashes match): Return the cached `summary` and `details` observations. Note "Using cached analysis. Module unchanged since [date]." and STOP.
- **Cache miss** (hashes differ or not found): Proceed to Step 1.

### Step 1: Read Reference

Read `reference.md` from this skill's directory. It contains dead code categories, false-positive patterns (especially rv-android-specific ones), and removal guidelines.

### Step 2: Run Static Analysis

Run pyflakes AND vulture across ALL module source files in a SINGLE Bash call:
```bash
echo "=== PYFLAKES ===" && uv run python -m pyflakes modules/$ARGUMENTS/src/ 2>&1; echo "=== VULTURE ===" && uv run vulture modules/$ARGUMENTS/src/ --min-confidence 80 2>&1
```

- **pyflakes**: Unused imports with file:line:message format
- **vulture**: Unused code (imports, functions, classes, variables) with confidence %

### Step 3: Cross-Reference Vulture Findings

For functions, classes, and methods flagged by vulture, verify with a SINGLE batched Bash call:
```bash
for name in SYM1 SYM2 SYM3; do
  count=$(grep -rl --include='*.py' "\b${name}\b" modules/ 2>/dev/null | grep -v __pycache__ | grep -v "modules/$ARGUMENTS/src/" | wc -l)
  echo "${name}:${count}"
done
```

Symbols with external callers (count > 0) are alive — remove from findings. Skip this step if vulture found no functions/classes (only imports).

### Step 4: Apply False-Positive Checks

For remaining dead candidates, check against false-positive patterns from reference.md:
- Dynamic dispatch, framework entry points, registries, rv-android-specific patterns
- Assign confidence: HIGH (tool-confirmed + no FP pattern), MEDIUM (tool-flagged but possible FP), LOW (uncertain)

Also scan for dead code patterns tools miss:
- Commented-out code blocks (3+ consecutive lines of commented Python)
- Unreachable code after `return`/`raise`
- Pass-only functions, empty `except` blocks

### Step 5: Persist to MCP Memory

```
Use mcp__memory__create_entities (or update existing via delete + create):
  Entity: "analysis:dead-code:$ARGUMENTS"
  Type: "module-dead-code-analysis"
  Observations:
    - "git_hash: <hash>"
    - "date: YYYY-MM-DD"
    - "summary: files=X, unused_imports=Y, unused_functions=Z, unused_vars=W, dead_patterns=V"
    - "details: <full report as single observation>"
```

If MCP fails, skip caching — still output the report.

## Output Format

```markdown
## Dead Code Analysis: <module-name>

**Files**: X | **Unused imports**: Y | **Unused functions**: Z | **Unused vars**: W | **Dead patterns**: V

### Tool Results

| Tool | Findings |
|------|----------|
| pyflakes | X unused imports, Y unused vars |
| vulture | Z unused symbols (≥80% confidence) |

### Findings by Priority

| # | Priority | Type | File | Name | Line | Confidence | Source | Notes |
|---|----------|------|------|------|------|------------|--------|-------|
| 1 | P1 | Import | file.py | unused_mod | 5 | HIGH | pyflakes+vulture | No references |
| 2 | P2 | Function | file.py | old_func | 42 | MEDIUM | vulture | Check dynamic dispatch |

### Recommendations

1. **P1 (auto-removable)**: [count] unused imports — safe for `autoflake --remove-all-unused-imports`
2. **P2 (review needed)**: [count] unused functions — verify no dynamic callers
3. **P3 (investigate)**: [count] patterns needing manual review
```
