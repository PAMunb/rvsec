---
name: rv-analyze-module
description: Analyze module architecture using sub-skills and 4 modeling perspectives.
argument-hint: "<module-name>"
context: fork
agent: general-purpose
allowed-tools: Read, Grep, Glob, Bash, Skill
---

# Analyze Module: $ARGUMENTS

> **Scope**: Comprehensive module analysis — chains to sub-skills and applies 4 modeling perspectives.
> Do NOT use for: single file analysis (use `/rv-analyze-file`), making changes (use `/rv-refactor`).

## Steps

### Step 0: Check MCP Memory Cache

```
Use mcp__memory__search_nodes with query: "analysis:module:$ARGUMENTS"
```

Compare `git_hash` with current:
```bash
git log -1 --format=%h -- modules/$ARGUMENTS/
```

- **Cache hit** (hashes match): Return cached results and STOP.
- **Cache miss**: Proceed to Step 1.

### Step 1: Read Reference and Gather Metadata

Read `reference.md` from this skill's directory. It contains the 4 modeling perspectives (context, interaction, structural, behavioral) and the rv-android module directory.

Gather module metadata in a SINGLE Bash call:
```bash
echo "=== PYPROJECT ===" && cat modules/$ARGUMENTS/pyproject.toml && echo "=== SRC FILES ===" && find modules/$ARGUMENTS/src -name '*.py' ! -path '*__pycache__*' | wc -l && echo "=== TEST FILES ===" && find modules/$ARGUMENTS/tests -name '*.py' ! -path '*__pycache__*' 2>/dev/null | wc -l && echo "=== SLOC ===" && find modules/$ARGUMENTS/src -name '*.py' ! -path '*__pycache__*' -exec cat {} + | wc -l
```

### Step 2: Invoke Sub-Skills

Use the Skill tool to invoke each analysis. These sub-skills have MCP cache — if the module hasn't changed, they return cached results in ~2 tool calls each.

1. **Dependency Analysis**:
   ```
   Skill tool: skill="rv-analyze-dependencies", args="$ARGUMENTS"
   ```

2. **Complexity Analysis**:
   ```
   Skill tool: skill="rv-analyze-complexity", args="$ARGUMENTS"
   ```

3. **Dead Code Analysis**:
   ```
   Skill tool: skill="rv-analyze-dead-code", args="$ARGUMENTS"
   ```

### Step 3: Map Directory Structure

Read the module's source directory structure (Glob `modules/$ARGUMENTS/src/**/*.py`). Identify:
- Architectural patterns (domain/, services/, cli/, etc.)
- Key components and their purposes
- Correlate with sub-skill findings (complexity hotspots, dead code)

### Step 4: Apply 4 Modeling Perspectives

Using the reference.md checklists, analyze each perspective:

1. **Context**: System boundaries, adjacent modules, external systems, process triggers
2. **Interaction**: Actors, use cases, key sequences (for non-trivial modules)
3. **Structural**: Key classes, associations, hierarchies, design patterns
4. **Behavioral**: Data-driven vs event-driven, states/flows, key scenarios

Focus depth on what matters for the specific module. Not every module needs all 4 perspectives in equal depth.

### Step 5: Persist to MCP Memory

```
Use mcp__memory__create_entities (or update existing via delete + create):
  Entity: "analysis:module:$ARGUMENTS"
  Type: "module-analysis"
  Observations:
    - "git_hash: <hash>"
    - "date: YYYY-MM-DD"
    - "summary: files=X, SLOC=Y, classes=Z, patterns=[list], hotspots=W, issues=V"
    - "details: <full report as single observation>"
```

If MCP fails, skip caching — still output the report.

## Output Format

```markdown
## Module Analysis: <module-name>

**Files**: X | **SLOC**: Y | **Tests**: Z | **Dependencies**: W

### Purpose
[One paragraph description]

### Directory Structure
(source tree with architectural patterns noted)

### Key Components
| Component | Purpose | Lines | Complexity |
|-----------|---------|-------|------------|
| component.py | Description | X | CC=Y |

### Sub-Skill Results
- **Dependencies**: [summary from rv-analyze-dependencies]
- **Complexity**: [summary from rv-analyze-complexity]
- **Dead Code**: [summary from rv-analyze-dead-code]

### Context Model
(boundaries, adjacent modules, external systems)

### Interaction Model
(actors, use cases, key sequences)

### Structural Model
(classes, hierarchies, patterns)

### Behavioral Model
(behavior type, states/flows, key scenarios)

### Recommendations
1. **[priority]**: [specific action]
```
