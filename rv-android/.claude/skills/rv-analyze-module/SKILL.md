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
- **Checklists**:
  - `checklists/context-modeling.md` - System boundaries and environment
  - `checklists/interaction-modeling.md` - Use cases and sequences
  - `checklists/structural-modeling.md` - Classes and associations
  - `checklists/behavioral-modeling.md` - Data flow and state machines

---

## 4 Modeling Perspectives

Module analysis should cover these complementary perspectives:

| Perspective | What it Shows | Models |
|-------------|---------------|--------|
| **Context** | Module environment and boundaries | Context diagram, process context |
| **Interaction** | Communication with actors and systems | Use cases, sequence diagrams |
| **Structural** | Static organization and relationships | Class diagrams, hierarchies |
| **Behavioral** | Dynamic behavior during execution | Activity diagrams, state machines |

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

### Step 5: Context Modeling

Reference: `checklists/context-modeling.md`

Analyze the module's context and boundaries:

1. **System Boundaries**:
   - What functionality is inside this module?
   - What is delegated to other modules?

2. **Adjacent Modules**:
   - What rv-android modules does this depend on?
   - What modules depend on this one?
   - What data flows between them?

3. **External Systems**:
   - What external APIs/services does it use?
   - What hardware does it interact with?

4. **Process Context**:
   - What business processes use this module?
   - What triggers module execution?

### Step 6: Interaction Modeling

Reference: `checklists/interaction-modeling.md`

Identify how the module interacts with actors and systems:

1. **Actors**: Who/what initiates interactions?
   - Users (CLI, API)
   - Other modules (internal calls)
   - External systems (events, callbacks)

2. **Use Cases**: What discrete tasks does the module support?
   - Document: Actors, Description, Stimulus, Response

3. **Key Sequences** (for complex interactions):
   - Trace message flow between components
   - Identify alternative paths

### Step 7: Structural Modeling

Reference: `checklists/structural-modeling.md`

Analyze the static structure:

1. **Key Classes**: Identify main domain entities and services
2. **Associations**: Map relationships between classes
3. **Hierarchies**: Document inheritance structures
4. **Compositions**: Identify whole-part relationships
5. **Patterns**: Recognize design patterns used

### Step 8: Behavioral Modeling

Reference: `checklists/behavioral-modeling.md`

Analyze dynamic behavior:

1. **Behavior Type**: Is the module data-driven or event-driven?

2. **For Data-Driven**:
   - What is the input?
   - What processing steps occur?
   - What is the output?

3. **For Event-Driven**:
   - What states can the module be in?
   - What stimuli trigger state transitions?
   - What actions occur in each state?

4. **Key Scenarios**: Document happy path and error handling

### Step 9: Assess Test Coverage

- Count test files per category (unit, integration, etc.)
- Identify untested components
- Cross-reference with complexity hotspots

### Step 10: Synthesize Findings

Use **sequential-thinking** to combine all analysis results:
- What are the main architectural patterns?
- What issues were found by specialized skills?
- How do the 4 perspectives complement each other?
- What are the priority recommendations?

### Step 11: Persist to Memory
   ```
   Entity: rv-[module-name]-analysis
   Type: module-analysis
   Observations: key findings (context, interactions, structure, behavior)
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

---

### Context Model

#### System Boundaries
- **Scope**: [What the module is responsible for]
- **Exclusions**: [What is outside scope]

#### Adjacent Modules
| Module | Relationship | Data Exchanged |
|--------|--------------|----------------|
| rv-android-core | Depends-on | Domain models |

#### External Systems
| System | Type | Direction |
|--------|------|-----------|
| Android Device | Hardware | Both |

---

### Interaction Model

#### Actors
| Actor | Type | Description |
|-------|------|-------------|
| User | Human | CLI operator |

#### Use Cases
| Use Case | Actor(s) | Description |
|----------|----------|-------------|
| Execute Task | User | Run main operation |

---

### Structural Model

#### Key Classes
| Class | Responsibility |
|-------|----------------|
| MainClass | Primary orchestrator |

#### Hierarchies
```
BaseClass (abstract)
├── ConcreteA
└── ConcreteB
```

#### Patterns Identified
- [Pattern]: [Where and why]

---

### Behavioral Model

#### Behavior Type
- **Primary**: [Data-driven / Event-driven / Mixed]

#### States (if event-driven)
| State | Description |
|-------|-------------|
| Idle | Waiting for input |

#### Data Flow (if data-driven)
| Input | Processing | Output |
|-------|------------|--------|
| Request | Validate → Process | Result |

---

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
