---
name: rv-doc-generate-claude-md
description: >-
  Generate CLAUDE.md documentation for a module. Use when documenting module architecture,
  creating onboarding docs, or updating module documentation.
  Do NOT use for: README.md (use /rv-doc-readme), architecture.md (use /rv-doc-architecture),
  ADRs (use /rv-doc-adr).
argument-hint: [module-name]
context: fork
agent: general-purpose
allowed-tools: Read, Grep, Glob, Write, Bash, Task, Skill
---

# Generate CLAUDE.md: $ARGUMENTS

## Documentation Guidelines

**CRITICAL**: Follow these guidelines:

1. **Language**: English only
2. **Tone**: Professional, objective, factual
3. **No bias terms**: Avoid "modern", "better", "elegant", "sophisticated"
4. **Current state only**: Do not reference migration, legacy, or what was changed
5. **Concise**: CLAUDE.md is part of prompt context - keep it focused

## MCP Integration

- **memory**: Check for existing module analysis
- **sequential-thinking**: Structure documentation systematically

## Workflow

```
STEP 1: AUTO-ANALYSIS ───────────────────────────────────────────►
    │  Use Skill tool: skill="rv-analyze-module" for deep understanding
    ▼
STEP 2: CHECK EXISTING ──────────────────────────────────────────►
    │  Preserve custom sections if CLAUDE.md exists
    ▼
STEP 3: GENERATE ────────────────────────────────────────────────►
    │  Create/update CLAUDE.md from template
    ▼
STEP 4: VALIDATE ────────────────────────────────────────────────►
    │  Ensure all sections are populated
```

## Steps

### 1. Auto-Analysis (NEW)

First, invoke `/rv-analyze-module $ARGUMENTS` to get:
- Module structure and architecture
- Key components and their roles
- Internal and external dependencies
- Test organization

If analysis was recently cached in memory, reuse it.

### 2. Check for Existing CLAUDE.md

```bash
CLAUDE_PATH="modules/$ARGUMENTS/CLAUDE.md"
if [ -f "$CLAUDE_PATH" ]; then
    # Extract custom sections to preserve:
    # - "Gotchas" section (user-added knowledge)
    # - "Current Work" section (active context)
    # - Any section marked with "<!-- CUSTOM -->"
fi
```

### 3. Analyze Module (supplement auto-analysis)

- Read pyproject.toml for metadata
- Map directory structure
- Identify key components
- Find entry points

### 4. Extract Documentation

- Read existing docstrings
- Find README if exists
- Merge with auto-analysis results

### 5. Generate CLAUDE.md

Following template below, with auto-analysis data filling sections.

### 6. Write to `modules/$MODULE/CLAUDE.md`

Preserve custom sections if they existed.

## CLAUDE.md Template

```markdown
# [Module Name] - CLAUDE.md

## Overview

[One paragraph describing module purpose and role in rv-android]

## Quick Start

```bash
# Install
cd modules && ./install.sh [module-name]

# Run tests
cd modules/[module-name]
PYTHONPATH=../rv-android-core/src:src poetry run pytest tests/unit/ -v
```

## Architecture

### Directory Structure
```
src/[package]/
├── domain/        # Domain models
├── services/      # Business logic
├── ...
```

### Key Components

| Component | Purpose |
|-----------|---------|
| component.py | Description |

### Dependencies

- **Internal**: rv-android-core, ...
- **External**: langchain, pydantic, ...

## Development

### Common Tasks

```bash
# Task 1
command

# Task 2
command
```

### Testing

| Category | Path | Purpose |
|----------|------|---------|
| unit | tests/unit/ | Isolated tests |

### Code Patterns

- Pattern 1: Description
- Pattern 2: Description

## Key Files

| File | Purpose |
|------|---------|
| main.py | Entry point |

## Gotchas

- Known issue 1
- Known issue 2
```

## Output Format

```
## Generated: CLAUDE.md for [module]

### File Created
- **Path**: modules/[module]/CLAUDE.md
- **Sections**: X
- **Lines**: Y

### Content Summary
- Overview: ✅
- Quick Start: ✅
- Architecture: ✅
- Development: ✅
- Key Files: ✅
- Gotchas: [if applicable]

### Next Steps
- Review and customize
- Add module-specific details
- Update as module evolves
```

## Guidelines

- Keep concise (CLAUDE.md is part of prompt)
- Focus on what helps Claude understand the module
- Include common commands and patterns
- Document gotchas and non-obvious behavior
- Update when architecture changes
