---
name: rv-analyze-dependencies
description: >-
  Map module dependencies and identify issues. Use when understanding module relationships,
  finding circular dependencies, or planning refactoring.
  Do NOT use for: fixing dependencies (use /rv-refactor), full module analysis (use /rv-analyze-module).
argument-hint: [module-name or empty for all]
context: fork
agent: general-purpose
allowed-tools: Read, Grep, Glob, Bash
---

# Analyze Dependencies: $ARGUMENTS

## Supporting Files

Reference these files from this skill directory:
- **Templates**: `templates/report.md`

---

## MCP Integration (with fallback)

### Step 0: Check Memory for Cached Analysis

Before expensive analysis, check for recent cached data:

```
Use mcp__memory__search_nodes with query: "dependencies-$ARGUMENTS"
```

**If found and recent** (< 7 days based on entity name date):
- Return cached findings
- Note: "Using cached analysis from [date]"

**If not found or stale**:
- Proceed with full analysis below

### Primary Path (MCP available)
- **sequential-thinking**: Analyze dependency graph systematically
- **memory**: Persist dependency map:
  - Entity name: `dependencies-$ARGUMENTS-[YYYY-MM-DD]`
  - Type: `dependency-analysis`

### Fallback Path (MCP unavailable)
If MCP tools fail or timeout:
1. **Manual analysis**: Document reasoning steps in numbered format
2. **No persistence**: Output dependency map directly to user
3. **Indicate fallback**: Note "MCP unavailable - using manual analysis"

### Error Detection
MCP is unavailable if:
- Tool call returns error/timeout
- Tool not found in available tools
- Connection refused

**Always complete the analysis** - MCP enhances but is not required.

## Steps

1. **Determine scope**:
   - If $ARGUMENTS empty: analyze all modules
   - If module specified: focus on that module

2. **Map internal dependencies**:
   ```bash
   # For each module, check pyproject.toml
   for module in modules/rv-*/; do
     echo "=== $(basename $module) ==="
     grep -A 20 "\[tool.poetry.dependencies\]" $module/pyproject.toml | grep "rv-"
   done
   ```

3. **Check for circular dependencies**:
   - Build dependency graph
   - Detect cycles

4. **Analyze import patterns**:
   ```bash
   # Find cross-module imports
   grep -r "from rv_" modules/$MODULE/src/ | grep -v __pycache__
   ```

5. **Identify dependency issues**:
   - Circular dependencies
   - Over-coupling (too many deps)
   - Under-abstraction (direct imports of internals)

6. **Generate dependency graph** (ASCII)

## Output Format

```
## Dependency Analysis

### Module Dependency Graph

```
rv-experiment
    └── rv-platform
        ├── rv-android-core
        ├── rv-tools
        │   └── rv-android-core
        └── rv-agent
            ├── rv-android-core
            └── rv-screen-parser
```

### Dependency Matrix

| Module | Depends On | Depended By |
|--------|------------|-------------|
| rv-android-core | - | all |
| rv-agent | core, llm, screen-parser | platform |

### Issues Found

| Issue | Modules | Severity |
|-------|---------|----------|
| Circular dependency | A ↔ B | High |
| Over-coupling | X (10 deps) | Medium |

### Recommendations
1. [Prioritized actions]

### Memory Reference
- Saved as: rv-dependency-map
```

## Module Hierarchy (Expected)

```
Layer 1 (Foundation):
  rv-android-core

Layer 2 (Utilities):
  rv-tools, rv-uiautomator, rv-screen-parser

Layer 3 (Analysis):
  rv-static-analysis, rv-coverage, rv-monitor-generator

Layer 4 (Execution):
  rv-instrumentation, rv-agent

Layer 5 (Orchestration):
  rv-platform

Layer 6 (Experiment):
  rv-experiment, rv-agent-validation
```
