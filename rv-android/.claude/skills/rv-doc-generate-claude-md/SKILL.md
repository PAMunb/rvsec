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
- `templates/claude-md.md` — CLAUDE.md output template with section structure (read at Step 5)

## Documentation Principles

Apply `.claude/documentation-principles.md` to the generated CLAUDE.md. Specific to this
document: CLAUDE.md is loaded into the prompt context, so keep it concise.

## MCP Integration

- **memory**: Check for existing module analysis
- **sequential-thinking**: Structure documentation systematically

## Workflow

```
STEP 1: ANALYZE MODULE ──────────────────────────────────────────►
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

### 1. Analyze the Module with rv-analyze-module

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
    # - Any content between <!-- CUSTOM:START --> and <!-- CUSTOM:END -->
fi
```

### 3. Supplement the Analysis

- Read pyproject.toml for metadata
- Map directory structure
- Identify key components
- Find entry points

### 4. Extract Documentation

- Read existing docstrings
- Find README if exists
- Merge with the Step 1 analysis results

### 5. Generate CLAUDE.md

Read `templates/claude-md.md` and fill its sections with the analysis results. The section
order and depth come from `checklists/claude-md-sections.md`.

### 6. Write to `modules/$MODULE/CLAUDE.md`

Preserve custom sections if they existed.

## Output Format

```
## Generated: CLAUDE.md for [module]

### File Created
- **Path**: modules/[module]/CLAUDE.md
- **Sections**: X
- **Lines**: Y

### Content Summary
- Overview: ✅
- Architecture: ✅
- Key Files: ✅
- Entry Points: ✅
- Dependencies: ✅
- Configuration: ✅
- Development (commands, testing): ✅
- Key Patterns: ✅
- Gotchas: [if applicable]
- Custom content preserved: [list or none]

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
