---
name: rv-analyze-module
description: >-
  Analyze module architecture and dependencies. Use when understanding a module's structure,
  mapping dependencies, or onboarding to a new module.
  Do NOT use for: single file analysis (use /rv-analyze-file), making changes (use /rv-refactor).
argument-hint: [module-name]
context: fork
agent: general-purpose
allowed-tools: Read, Grep, Glob, Bash, Skill
---

# Analyze Module: $ARGUMENTS

## Supporting Files

Reference these files from this skill directory:
- **Templates**: `templates/report.md`

---

## MCP Integration (with fallback)

### Primary Path (MCP available)
1. **sequential-thinking**: Structure the analysis in clear phases
2. **memory**: Persist module analysis for future reference
3. **context7**: Fetch docs for external dependencies if needed

### Fallback Path (MCP unavailable)
If MCP tools fail or timeout:
1. **Manual analysis**: Document reasoning steps in numbered format
2. **No persistence**: Output analysis directly to user
3. **Skip context7**: Use existing knowledge for external deps
4. **Indicate fallback**: Note "MCP unavailable - using manual analysis"

### Error Detection
MCP is unavailable if:
- Tool call returns error/timeout
- Tool not found in available tools
- Connection refused

**Always complete the analysis** - MCP enhances but is not required.

## Steps

### Step 1: Check Memory for Cached Analysis

Before doing expensive analysis, check if we have recent data:

```
Use mcp__memory__search_nodes with query: "rv-$ARGUMENTS-analysis"
```

If found and recent (< 7 days):
- Use cached data as baseline
- Only re-analyze if specifically requested

If not found or stale:
- Proceed with full analysis below

### Step 2: Parse Module and Gather Metadata

Parse module name from $ARGUMENTS (e.g., "rv-agent", "rv-platform")

```bash
# Read pyproject.toml
cat modules/$ARGUMENTS/pyproject.toml

# Count source files
find modules/$ARGUMENTS/src -name "*.py" | wc -l

# Count test files
find modules/$ARGUMENTS/tests -name "*.py" | wc -l
```

### Step 3: Invoke Specialized Analysis Skills

**IMPORTANT**: You MUST use the Skill tool to invoke each analysis skill below. Do NOT skip this step.

1. **Dependency Analysis** - Use Skill tool:
   ```
   Skill tool: skill="rv-analyze-dependencies", args="$ARGUMENTS"
   ```
   Provides: internal/external deps, circular dependencies, coupling issues

2. **Complexity Analysis** - Use Skill tool:
   ```
   Skill tool: skill="rv-analyze-complexity", args="$ARGUMENTS"
   ```
   Provides: large files, complex functions, nesting issues

3. **Dead Code Analysis** (optional) - Use Skill tool:
   ```
   Skill tool: skill="rv-analyze-dead-code", args="$ARGUMENTS"
   ```
   Provides: unused imports, functions, variables

### Step 4: Map Directory Structure

- Identify architectural patterns (domain/, services/, etc.)
- List key components and their purposes
- Correlate with findings from specialized analyses

### Step 5: Assess Test Coverage

- Count test files per category (unit, integration, etc.)
- Identify untested components
- Cross-reference with complexity hotspots

### Step 6: Synthesize Findings

Use **sequential-thinking** to combine all analysis results:
- What are the main architectural patterns?
- What issues were found by specialized skills?
- What are the priority recommendations?

### Step 7: Persist to Memory
   ```
   Entity: rv-[module-name]-analysis
   Type: module-analysis
   Observations: key findings
   ```

## Output Format

```
## Module Analysis: [module-name]

### Overview
- **Location**: modules/[module-name]/
- **Package**: [package_name]
- **Source Files**: X
- **Test Files**: Y
- **Total Lines**: Z

### Purpose
[One paragraph description]

### Directory Structure
```
src/[package]/
├── domain/        # Domain models
├── services/      # Business logic
└── ...
```

### Key Components
| Component | Purpose | Lines |
|-----------|---------|-------|
| component.py | Description | XXX |

### Dependencies

#### Internal (rv-android)
| Module | Purpose |
|--------|---------|
| rv-android-core | Foundation services |

#### External
| Package | Purpose |
|---------|---------|
| langchain | LLM orchestration |

### Test Coverage
| Category | Files | Tests |
|----------|-------|-------|
| unit/ | X | Y |

### Recommendations
1. [Recommendation]

### Memory Reference
- Persisted as: rv-[module-name]-analysis
```

## Available Modules

- rv-android-core, rv-platform, rv-tools, rv-uiautomator
- rv-monitor-generator, rv-instrumentation, rv-static-analysis
- rv-coverage, rv-screen-parser
- rv-agent, rv-llm
- rv-experiment, rv-agent-validation
