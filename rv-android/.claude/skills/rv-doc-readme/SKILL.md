---
name: rv-doc-readme
description: >-
  Generate README.md for a module. Use when creating module documentation for GitHub/GitLab.
  Do NOT use for: CLAUDE.md (use /rv-doc-generate-claude-md), architecture docs (use /rv-doc-architecture).
argument-hint: [module-name]
context: fork
agent: general-purpose
allowed-tools: Read, Grep, Glob, Write, Bash
---

# Generate README: $ARGUMENTS

Creates standardized README.md at `modules/$ARGUMENTS/README.md`.

## Supporting Files

- **Template**: `templates/readme.md` - The README section structure with `{PLACEHOLDER}` fields (read at Step 3)

## Documentation Principles

Apply `.claude/documentation-principles.md` to the generated README. Specific to this document:

- **Target audience**: developers who want to USE the module.
- **Focus**: installation, usage, configuration (not internal architecture).

## Diagram Guidelines

**Use Mermaid diagrams** with the `neutral` theme when helpful.

```
%%{init: {'theme': 'neutral'}}%%
```

Only include diagrams if they clarify usage (e.g., workflow overview). Keep README focused on practical usage.

## Workflow

```
STEP 1: ANALYZE MODULE ──────────────────────────────────────────►
    │  Understand purpose, entry points, configuration
    ▼
STEP 2: CHECK PYPROJECT.TOML ────────────────────────────────────►
    │  Get name, version, description, dependencies
    ▼
STEP 3: GENERATE README ─────────────────────────────────────────►
    │  Write README.md from template
    ▼
VERIFY ──────────────────────────────────────────────────────────►
```

## Steps

### 1. Analyze Module

```bash
# Check module exists
ls modules/$ARGUMENTS/

# Get pyproject.toml info
cat modules/$ARGUMENTS/pyproject.toml

# Find entry points / CLI commands
grep -A5 "scripts" modules/$ARGUMENTS/pyproject.toml

# Find main classes
grep -r "^class " modules/$ARGUMENTS/src --include="*.py" | head -10
```

### 2. Check for Existing Docs

```bash
# Check if CLAUDE.md exists
ls modules/$ARGUMENTS/CLAUDE.md

# Check if architecture.md exists
ls modules/$ARGUMENTS/docs/architecture.md
```

### 3. Generate README

Read `templates/readme.md` and write `modules/$ARGUMENTS/README.md` from it, replacing every
`{PLACEHOLDER}`. When the module has no CLI entry point in `pyproject.toml`, omit the CLI
subsections; when it has no environment variables, omit that table.

## Output

Report what was generated:

```
## Generated: README.md

### File Created
- **Path**: modules/[module]/README.md
- **Sections**: X

### Content
- Overview: ✅
- Installation: ✅
- Quick Start: ✅
- Features: ✅
- Configuration: ✅
- Usage Examples: ✅
- Dependencies: ✅
- Documentation Links: ✅

### Next Steps
- Review and customize examples
- Add module-specific configuration details
- Test code examples
```

## Rules

1. **Focus on USAGE** - README is for users, not developers
2. **Working examples** - Every code example must run as written
3. **Keep concise** - Link to CLAUDE.md/architecture.md for details
4. **No internal details** - Don't explain implementation
5. **Update links** - Reference existing docs if they exist
