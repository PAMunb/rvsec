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

- **Template**: `templates/readme.md` - Base README template with placeholders

## Documentation Guidelines

**CRITICAL**: Follow these guidelines:

1. **Language**: English only
2. **Tone**: Professional, objective, no promotional language
3. **No bias terms**: Avoid "modern", "sophisticated", "elegant", "cutting-edge"
4. **Target audience**: Developers who want to USE the module
5. **Focus**: Installation, usage, configuration (not internal architecture)

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

Write to `modules/$ARGUMENTS/README.md` using template below.

## Template: README.md

````markdown
# [Module Name]

[One-line description from pyproject.toml or brief summary]

## Overview

[2-3 sentences explaining what the module does and its role in rv-android]

## Installation

```bash
# Install with all rv-android modules
cd modules && ./install.sh

# Or install just this module
cd modules && ./install.sh [module-name]
```

## Quick Start

```python
from [package] import [MainClass]

# Basic usage example
instance = MainClass(config)
result = instance.run()
```

Or via CLI (if available):

```bash
poetry run [cli-command] [options]
```

## Features

- **[Feature 1]**: Brief description
- **[Feature 2]**: Brief description
- **[Feature 3]**: Brief description

## Configuration

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `option_name` | str | `"default"` | What it does |

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `VAR_NAME` | What it does | Yes/No |

## Usage Examples

### Example 1: [Use Case]

```python
# Code example
```

### Example 2: [Use Case]

```bash
# CLI example
```

## Dependencies

### Internal (rv-android)
- `rv-android-core` - Foundation infrastructure

### External
- `package-name` - Purpose

## Documentation

- [CLAUDE.md](./CLAUDE.md) - Development reference
- [Architecture](./docs/architecture.md) - Detailed architecture documentation

## Testing

```bash
cd modules/[module-name]
PYTHONPATH=../rv-android-core/src:src poetry run pytest tests/ -v
```

## License

Part of the rv-android project.
````

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
2. **Working examples** - All code examples should be runnable
3. **Keep concise** - Link to CLAUDE.md/architecture.md for details
4. **No internal details** - Don't explain implementation
5. **Update links** - Reference existing docs if they exist
