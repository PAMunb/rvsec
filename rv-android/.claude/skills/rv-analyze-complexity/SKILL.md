---
name: rv-analyze-complexity
description: >-
  Analyze code complexity and identify over-engineered code. Use when evaluating code quality,
  finding refactoring targets, or assessing technical debt.
  Do NOT use for: making changes (use /rv-refactor-simplify), full module analysis (use /rv-analyze-module).
argument-hint: [module-name or file-path]
context: fork
agent: general-purpose
allowed-tools: Read, Grep, Glob, Bash
---

# Analyze Code Complexity: $ARGUMENTS

## Supporting Files

Reference these files from this skill directory:
- **Templates**: `templates/report.md`

---

## MCP Integration (with fallback)

### Step 0: Check Memory for Cached Analysis

Before expensive analysis, check for recent cached data:

```
Use mcp__memory__search_nodes with query: "complexity-$ARGUMENTS"
```

**If found and recent** (< 7 days based on entity name date):
- Return cached findings
- Note: "Using cached analysis from [date]"

**If not found or stale**:
- Proceed with full analysis below

### Primary Path (MCP available)
1. Call `mcp__sequential-thinking__sequentialthinking` to reason through complexity metrics step-by-step
2. After analysis, use `mcp__memory__create_entities` to persist findings:
   - Entity name: `complexity-$ARGUMENTS-[YYYY-MM-DD]`
   - Type: `complexity-analysis`

### Fallback Path (MCP unavailable)
If MCP tools fail or timeout:
1. **Manual reasoning**: Break analysis into numbered steps in your response
2. **No persistence**: Output findings directly to user instead of memory
3. **Indicate fallback**: Note "MCP unavailable - using manual analysis"

### Error Detection
MCP is unavailable if:
- Tool call returns error/timeout
- Tool not found in available tools
- Connection refused

**Always complete the analysis** - MCP enhances but is not required.

## Complexity Thresholds

| Metric | Threshold | Action |
|--------|-----------|--------|
| Lines per file | > 500 | Split into focused components |
| Function length | > 50 lines | Extract helper functions |
| Classes per file | > 3 | Separate into modules |
| Imports | > 20 | Check for dependency issues |
| Nesting depth | > 4 levels | Refactor conditionals |

## Steps

1. **Parse scope** from $ARGUMENTS:
   - Empty: analyze rv-agent module (primary focus)
   - Module name (e.g., "rv-agent"): analyze that module
   - File path: analyze specific file

2. **Gather metrics** for each Python file:
   - Count total lines of code
   - Count function/method definitions and lengths
   - Count class definitions
   - Count imports
   - Identify deeply nested code

3. **Use sequential-thinking** to analyze patterns:
   - Which files have multiple threshold violations?
   - What are the root causes of complexity?
   - What's the refactoring priority?

4. **Generate report** with prioritized recommendations

5. **Persist to memory** (optional):
   - Save complexity hotspots for tracking over time

## Output Format

```
## Complexity Analysis Report

### Summary
- Total files analyzed: X
- Files exceeding thresholds: Y
- Priority refactoring targets: Z

### Files Over Threshold

| File | Lines | Functions | Classes | Issue | Priority |
|------|-------|-----------|---------|-------|----------|
| path/file.py | XXX | Y | Z | [Issue] | P1 |

### Recommendations

1. **file.py** (Priority 1)
   - Issue: [description]
   - Action: [recommended refactoring]

### Memory Reference
- Saved to memory as: [entity-name] (if persisted)
```

## Key Files to Check (rv-agent)

- `strategies/rvagent_strategy/rvagent_strategy.py` - Main strategy (largest)
- `agent/nodes/*.py` - Workflow nodes
- `llm/llm_client.py` - LLM integration
