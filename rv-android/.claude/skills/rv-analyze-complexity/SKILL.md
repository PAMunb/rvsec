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

## Guiding Principles

Your complexity analysis must be guided by fundamental software measurement principles. The goal is not just to collect numbers, but to gain insight into the quality of the software design and identify areas for improvement.

1.  **Use Goal-Oriented Measurement (GQM)**: Start with a clear goal. Don't just measure for the sake of measuring. Define what you want to understand, what metrics will provide that information, and how you will interpret the results.
    *   **Justification**: "My goal is to 'identify modules that are difficult to test'. Therefore, I will focus on the **Cyclomatic Complexity** metric, as it directly measures testability."

2.  **Analyze Key Complexity Indicators**: Focus on metrics that are proven indicators of internal quality attributes like maintainability and reliability.
    *   **Cyclomatic Complexity**: Measures the amount of decision logic in a function. A high value (typically > 10) indicates complex branching that is difficult to test and understand.
    *   **Coupling**: Measures the degree of interdependence between modules. High coupling is a primary driver of system-level complexity and makes the code harder to change without causing ripple effects.
    *   **Cohesion**: Measures how focused a module's responsibilities are. Low cohesion (a module doing many unrelated things) is a sign of poor design and high complexity.
    *   **Size (Lines of Code)**: While not a perfect metric for complexity on its own, very large modules or functions are often a symptom of other design problems, such as low cohesion.

3.  **Interpret Metrics in Context**: Raw numbers are not enough. A high complexity score isn't automatically "bad." You must interpret the metrics in the context of the code's purpose. A complex algorithm might have an inherently high cyclomatic complexity, but the goal is to ensure it is not *unnecessarily* complex.
    *   **Justification**: "Although the cyclomatic complexity of this function is 15, this is acceptable because it implements a complex state machine. The complexity is therefore essential, not accidental."

## Requirement for Principle-Based Justification

When you present your findings, you **must** justify your analysis using the principles above.

- "This function is a high-priority refactoring target because its **High Cyclomatic Complexity (25)** and **Low Cohesion** indicate it is likely difficult to maintain and test."
- "My analysis follows the **GQM** principle. The goal is to find unstable components, so I am focusing on **Coupling** metrics to identify modules with excessive external dependencies."

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
