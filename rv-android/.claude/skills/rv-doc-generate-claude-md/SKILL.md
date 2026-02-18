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
allowed-tools: Read, Grep, Glob, Write, Bash, Skill
---

# Generate CLAUDE.md: $ARGUMENTS

## Supporting Files

Read these reference files before generating CLAUDE.md:

- `checklists/claude-md-sections.md` — Required sections, depth guidance, anti-patterns, length targets
- `checklists/audience-guidance.md` — LLM-first writing conventions, path/command formatting rules
- `templates/claude-md.md` — CLAUDE.md output template with section structure

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
# Install (from project root)
uv sync

# Run tests (from project root)
uv run pytest modules/[module-name]/tests/ -v
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

## Documentation Principles

Apply these principles to all generated documentation:

1. **Reader perspective**: Write from the reader's viewpoint. What do they need to know? What will they look for first? Structure content for their workflow, not for comprehensiveness.
2. **No repetition**: State information once in the most logical location. Cross-reference instead of duplicating. If the same fact appears in two sections, one is wrong.
3. **No ambiguity**: Define terminology on first use. Use precise file paths. Prefer concrete examples over abstract descriptions. If a notation is used (diagram, table), explain how to read it.
4. **Standard organization**: Follow the established templates and section order. Consistency across documents reduces cognitive load. Deviations must be justified by content needs.
5. **Capture rationale**: Document WHY, not just WHAT. Every significant choice should have a brief explanation. Future readers need to understand the reasoning to make informed changes.
6. **Currency**: Only document current state (P4). Do not include migration history, version notes, or planned features. If something changed, describe the current behavior only.
7. **Stakeholder awareness**: Know the audience. CLAUDE.md is for LLMs (precise paths, exact commands). architecture.md is for developers (conceptual understanding). README.md is for newcomers (getting started).

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
