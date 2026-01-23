---
name: rv-doc-architecture
description: >-
  Generate architecture documentation for a module. Use when creating or updating
  module architecture docs in modules/<module>/docs/architecture.md.
  Do NOT use for: CLAUDE.md generation, ADRs, or general documentation.
  Use /rv-doc-generate-claude-md for CLAUDE.md, /rv-doc-adr for ADRs.
argument-hint: [module-name]
context: fork
agent: general-purpose
allowed-tools: Read, Grep, Glob, Write, Bash
---

# Generate Architecture Documentation: $ARGUMENTS

Creates standardized architecture documentation at `modules/$ARGUMENTS/docs/architecture.md`.

## Documentation Guidelines

**CRITICAL**: Follow these guidelines for all documentation:

1. **Language**: English only (code, comments, documentation)
2. **Tone**: Professional, objective, no promotional language
3. **No bias terms**: Avoid "modern", "sophisticated", "elegant", "cutting-edge"
4. **Current state only**: Do not reference migration, legacy, or what was changed
5. **Target audience**: Developers and researchers

## Workflow

```
STEP 1: ANALYZE MODULE ──────────────────────────────────────────►
    │  Understand structure, components, patterns
    ▼
STEP 2: CREATE DOCS DIR ─────────────────────────────────────────►
    │  mkdir -p modules/$MODULE/docs
    ▼
STEP 3: GENERATE DOC ────────────────────────────────────────────►
    │  Write architecture.md from template
    ▼
VERIFY ──────────────────────────────────────────────────────────►
```

## Steps

### 1. Analyze Module

```bash
# Check module exists
ls modules/$ARGUMENTS/src/

# Get structure
find modules/$ARGUMENTS/src -type f -name "*.py" | head -30

# Find key classes
grep -r "^class " modules/$ARGUMENTS/src --include="*.py" | head -20
```

### 2. Create Docs Directory

```bash
mkdir -p modules/$ARGUMENTS/docs
```

### 3. Generate Documentation

Write to `modules/$ARGUMENTS/docs/architecture.md` using template below.

## Template: architecture.md

```markdown
# [Module Name] Architecture

## Overview

[One paragraph describing the module's purpose and role in rv-android]

## Design Principles

- [Principle 1]: [Brief explanation]
- [Principle 2]: [Brief explanation]

## Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      [Module Name]                          │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Component1  │  │  Component2  │  │  Component3  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### [Component Name]

**Purpose**: [What it does]

**Location**: `src/[package]/[component].py`

**Key Classes**:
- `ClassName`: [Purpose]

**Dependencies**:
- Internal: [list]
- External: [list]

### [Next Component]
...

## Data Flow

```
[Input] → [Component1] → [Component2] → [Output]
```

## Key Interfaces

### [Interface/Protocol Name]

```python
class IComponentName(Protocol):
    """Description of interface contract."""

    def method_name(self, param: Type) -> ReturnType:
        """What this method does."""
        ...
```

## Extension Points

- **[Extension Point]**: How to extend this module
- **[Configuration]**: How to configure behavior

## Dependencies

### Internal (rv-android modules)
- `rv-android-core`: [What for]
- `rv-[module]`: [What for]

### External
- `package-name`: [What for]

## Testing Strategy

| Type | Location | Purpose |
|------|----------|---------|
| Unit | tests/unit/ | Isolated component tests |
| Integration | tests/integration/ | Component interaction tests |

## Related Documentation

- [CLAUDE.md](../CLAUDE.md) - Quick reference for Claude
- [ADR-001](./adr/ADR-001.md) - Relevant architectural decision
```

## Output

Report what was generated:

```
## Generated: Architecture Documentation

### File Created
- **Path**: modules/[module]/docs/architecture.md
- **Sections**: X

### Content
- Overview: ✅
- Design Principles: ✅
- Component Architecture: ✅
- Core Components: ✅
- Data Flow: ✅
- Dependencies: ✅

### Next Steps
- Review and refine diagrams
- Add specific implementation details
- Link to related ADRs
```

## Rules

1. **Follow documentation guidelines** - English, no bias, current state only
2. **Use ASCII diagrams** - Compatible with markdown rendering
3. **Keep concise** - Focus on architecture, not implementation details
4. **Link to related docs** - Reference CLAUDE.md and ADRs
