---
name: rv-analyze-dependencies
description: Map module dependencies and detect violations, cycles, and coupling issues.
argument-hint: "<module-name or empty for all>"
context: fork
agent: general-purpose
allowed-tools: Read, Grep, Glob, Bash
---

# Analyze Dependencies: $ARGUMENTS

> **Scope**: Analyzes declared (pyproject.toml) and actual (import) dependencies. Defaults to all modules if $ARGUMENTS is empty.
> Do NOT use for: fixing dependencies (use `/rv-refactor`), full module analysis (use `/rv-analyze-module`).

## Steps

### Step 0: Check MCP Memory Cache

```
Use mcp__memory__search_nodes with query: "analysis:dependencies:$ARGUMENTS"
```

If $ARGUMENTS is empty, search for `"analysis:dependencies:workspace"`.

Compare `git_hash` with current:
```bash
git log -1 --format=%h -- modules/$ARGUMENTS/
```
For workspace-wide: `git log -1 --format=%h -- modules/`

- **Cache hit** (hashes match): Return cached results and STOP.
- **Cache miss**: Proceed to Step 1.

### Step 1: Read Reference

Read `reference.md` from this skill's directory. It contains the allowed dependency matrix, health metrics (fan-in/fan-out, instability, depth), and circular dependency resolution strategies.

### Step 2: Extract Declared Dependencies

Parse `pyproject.toml` for each module in scope in a SINGLE Bash call:
```bash
for module in modules/rv-*/; do
  name=$(basename $module)
  echo "=== $name ==="
  grep -A 30 '^\[project\]' $module/pyproject.toml 2>/dev/null | grep -E '^\s+"rv-' | sed 's/[",]//g' | xargs
done
```

### Step 3: Extract Actual Import Dependencies

Scan source files for cross-module imports in a SINGLE Bash call:
```bash
for module in modules/rv-*/; do
  name=$(basename $module)
  echo "=== $name ==="
  grep -rh --include='*.py' 'from rv_\|import rv_' $module/src/ 2>/dev/null | grep -v __pycache__ | sort -u
done
```

If $ARGUMENTS specifies a single module, limit both steps to that module.

### Step 4: Analyze

Compare declared vs actual dependencies:
- **Undeclared imports**: Module imports `rv_X` but `rv-X` not in its `pyproject.toml` — potential hidden dependency
- **Unused declarations**: `rv-X` declared in `pyproject.toml` but never imported — unnecessary coupling
- **Matrix violations**: Dependencies not in the allowed matrix from reference.md — architectural issue
- **Circular dependencies**: A depends on B and B depends on A (check transitively)

Compute for each module:
- Fan-in (Ca), Fan-out (Ce), Instability I = Ce / (Ca + Ce)
- Max dependency depth

### Step 5: Persist to MCP Memory

```
Use mcp__memory__create_entities (or update existing via delete + create):
  Entity: "analysis:dependencies:$ARGUMENTS" (or "analysis:dependencies:workspace")
  Type: "module-dependency-analysis"
  Observations:
    - "git_hash: <hash>"
    - "date: YYYY-MM-DD"
    - "summary: modules=X, violations=Y, cycles=Z, max_depth=W, undeclared=U"
    - "details: <full report as single observation>"
```

If MCP fails, skip caching — still output the report.

## Output Format

```markdown
## Dependency Analysis: <scope>

**Modules**: X | **Violations**: Y | **Cycles**: Z | **Max Depth**: W

### Dependency Matrix

| Module | Layer | Declared Deps | Actual Imports | Fan-In | Fan-Out | I |
|--------|-------|---------------|----------------|--------|---------|---|
| rv-android-core | 1 | 0 | 0 | 11 | 0 | 0.0 |

### Issues

| # | Type | Modules | Severity | Notes |
|---|------|---------|----------|-------|
| 1 | Violation | A → B | High | Not in allowed matrix |
| 2 | Cycle | A ↔ B | Medium | Type-only, use TYPE_CHECKING |
| 3 | Undeclared | A imports B | Low | Missing from pyproject.toml |

### Dependency Graph (ASCII)

(tree showing module hierarchy and dependencies)

### Recommendations

1. **[issue]**: [specific action]
```
