---
name: rv-analyze-file-dead-code
description: Find unused imports, functions, and dead code in a single file.
argument-hint: "<file-path>"
context: fork
agent: general-purpose
allowed-tools: Read, Grep, Glob, Bash
---

# Find Dead Code in File: $ARGUMENTS

> **Scope**: This skill analyzes ONE file. For module-wide dead code analysis, use `/rv-analyze-dead-code`.
> Do NOT use for: removing code (use `/rv-cleanup`), quick auto-fix (use `/rv-refactor-cleanup`).

## False Positive Awareness

Before classifying code as dead, check these patterns — code may be alive through:
- **Dynamic dispatch**: `getattr()`, `globals()[]`, dictionary dispatch, `importlib`
- **Framework entry points**: `@click.command`, `@pytest.fixture`, `@abstractmethod`, `@field_validator`
- **Registries**: `@register`, `@error_handler`, decorator-based registration
- **Exports**: listed in `__all__`, referenced in `pyproject.toml` scripts
- **LangGraph nodes**: registered in graph builder, called by runtime (rv-agent specific)
- **ToolFactory**: tools registered by name string (rv-tools specific)

If uncertain, mark as "investigate" — false removal is worse than false retention.

## Steps

### Step 0: Check MCP Memory Cache

```
Use mcp__memory__search_nodes with query: "analysis:file-dead-code:$ARGUMENTS"
```

If found, extract the `git_hash` observation. Compare with current hash:
```bash
git log -1 --format=%h -- $ARGUMENTS
```

- **Cache hit** (hashes match): Return the cached `summary` and `details` observations. Note "Using cached analysis. File unchanged since [date]." and STOP.
- **Cache miss** (hashes differ or not found): Proceed to Step 1.

### Step 1: Run Static Analysis

Run pyflakes AND vulture in a SINGLE Bash call:
```bash
echo "=== PYFLAKES ===" && uv run python -m pyflakes $ARGUMENTS 2>&1; echo "=== VULTURE ===" && uv run vulture $ARGUMENTS --min-confidence 80 2>&1
```

This produces:
- **pyflakes**: Unused imports with file:line:message format
- **vulture**: Unused code (imports, functions, classes, variables) with confidence %

### Step 2: Cross-Reference Vulture Findings

For symbols flagged by vulture (functions, classes, methods), verify with a SINGLE batched Bash call to check if they're used elsewhere in the project:
```bash
for name in SYM1 SYM2 SYM3; do
  count=$(grep -rl --include='*.py' "\b${name}\b" modules/ 2>/dev/null | grep -v __pycache__ | grep -v "$ARGUMENTS" | wc -l)
  echo "${name}:${count}"
done
```

Skip this step if vulture found no functions/classes/methods (only imports — pyflakes already confirmed those).

### Step 3: Read File and Apply False-Positive Checks

Read the target file. For each dead candidate:
- Check false-positive patterns from the list above
- Check for dead code patterns: unreachable code after `return`/`raise`, empty `except` blocks, `pass`-only functions, commented-out code blocks (3+ consecutive lines)

Assign confidence: HIGH (tool-confirmed + no false-positive pattern), MEDIUM (tool-flagged but possible false positive), LOW (uncertain).

### Step 4: Persist to MCP Memory

```
Use mcp__memory__create_entities (or update existing via delete_observations + add_observations):
  Entity: "analysis:file-dead-code:<file-path>"
  Type: "file-dead-code-analysis"
  Observations:
    - "git_hash: <hash>"
    - "date: YYYY-MM-DD"
    - "summary: unused_imports=X, unused_functions=Y, unused_vars=Z, dead_patterns=W"
    - "details: <full report as single observation>"
```

If MCP fails, skip caching — still output the report.

## Output Format

```markdown
## Dead Code Analysis: <filename>

**Unused imports**: X | **Unused functions**: Y | **Unused vars**: Z | **Dead patterns**: W

### Tool Results

| Tool | Findings |
|------|----------|
| pyflakes | X unused imports |
| vulture | Y unused symbols (≥80% confidence) |

### Findings

| # | Type | Name | Line | Confidence | Source | Notes |
|---|------|------|------|------------|--------|-------|
| 1 | Import | unused_mod | 5 | HIGH | pyflakes+vulture | Not used in file |
| 2 | Function | old_func | 42 | MEDIUM | vulture(60%) | No external callers; check dynamic dispatch |

### Recommendations
1. [Prioritized actions]
```
