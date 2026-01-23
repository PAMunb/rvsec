---
name: rv-analyze-module
description: >-
  Analyze module architecture and dependencies. Use when understanding a module's structure,
  mapping dependencies, or onboarding to a new module.
  Do NOT use for: single file analysis (use /rv-analyze-file), making changes (use /rv-refactor).
argument-hint: [module-name]
context: fork
agent: general-purpose
allowed-tools: Read, Grep, Glob, Bash
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

1. **Parse module name** from $ARGUMENTS (e.g., "rv-agent", "rv-platform")

2. **Gather metadata**:
   ```bash
   # Read pyproject.toml
   cat modules/$MODULE/pyproject.toml

   # Count source files
   find modules/$MODULE/src -name "*.py" | wc -l

   # Count test files
   find modules/$MODULE/tests -name "*.py" | wc -l
   ```

3. **Map directory structure**:
   - Identify architectural patterns (domain/, services/, etc.)
   - List key components and their purposes

4. **Analyze dependencies**:
   - Internal: other rv-* modules
   - External: third-party packages
   - Check for circular dependencies

5. **Assess test coverage**:
   - Count test files per category (unit, integration, etc.)
   - Identify untested components

6. **Use sequential-thinking** for architectural assessment:
   - Is the module well-structured?
   - Are responsibilities clearly separated?
   - What improvements are needed?

7. **Persist to memory**:
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
