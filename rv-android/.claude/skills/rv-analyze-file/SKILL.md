---
name: rv-analyze-file
description: >-
  Analyze single Python file structure and dependencies. Use when understanding a specific file,
  preparing to modify it, or reviewing code.
  Do NOT use for: multiple files (use /rv-analyze-module), making changes (use /rv-refactor-*).
argument-hint: [file-path]
context: fork
agent: general-purpose
allowed-tools: Read, Grep, Glob
---

# Analyze File: $ARGUMENTS

## Supporting Files

Read these reference files before starting analysis:

- `checklists/file-analysis-dimensions.md` — 8 analysis dimensions (structure, responsibilities, dependencies, complexity, error handling, API, config, testing)
- `checklists/code-smell-catalog.md` — Code smell catalog by category with severity and suggested refactoring
- `templates/report.md` — Output report format

---

## Steps

1. **Read the file** at $ARGUMENTS

2. **Extract structure**:
   - Imports (stdlib, third-party, internal)
   - Classes and their methods
   - Standalone functions
   - Constants and globals

3. **Analyze dependencies**:
   - What does this file import?
   - What imports this file? (reverse lookup)

4. **Assess complexity**:
   - Lines of code
   - Number of classes/functions
   - Cyclomatic complexity indicators
   - Nesting depth

5. **Identify patterns**:
   - Design patterns used
   - Code smells
   - Documentation quality

## Output Format

```
## File Analysis: [filename]

### Overview
- **Path**: [full path]
- **Lines**: X
- **Classes**: Y
- **Functions**: Z

### Imports

#### Standard Library
- os, sys, ...

#### Third-Party
- langchain, pydantic, ...

#### Internal (rv-android)
- rv_android_core.models
- rv_agent.domain

### Structure

#### Classes
| Class | Methods | Lines | Purpose |
|-------|---------|-------|---------|
| ClassName | X | Y | Description |

#### Functions
| Function | Lines | Purpose |
|----------|-------|---------|
| func_name | X | Description |

### Dependencies

#### Used By (importers)
| File | Import |
|------|--------|
| other.py | from this import X |

#### Uses (imports)
| Module | What |
|--------|------|
| module | Class, function |

### Quality Assessment

| Metric | Value | Status |
|--------|-------|--------|
| Lines | X | ✅/⚠️ |
| Max function length | Y | ✅/⚠️ |
| Max nesting | Z | ✅/⚠️ |

### Recommendations
1. [Improvement suggestions]
```
