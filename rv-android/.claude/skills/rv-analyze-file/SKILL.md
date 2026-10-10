---
name: rv-analyze-file
description: >-
  Qualitative analysis of one Python file: structure, responsibilities, dependencies,
  error handling, API surface, configuration, testability, and code smells (including
  co-change smells from git history), with thresholds from rv-analyze-complexity/reference.md.
  Use before extracting or refactoring code in a file, or to assess one file's health.
  Do NOT use for: radon metrics (use /rv-analyze-file-complexity), dead code
  (use /rv-analyze-file-dead-code), multiple files (use /rv-analyze-module),
  or making changes (use /rv-refactor-*).
argument-hint: "<file-path>"
context: fork
agent: general-purpose
allowed-tools: Read, Grep, Glob, Bash
---

# Analyze File: $ARGUMENTS

> **Scope**: Qualitative analysis of ONE file — structure, responsibilities, patterns, smells.
> For quantitative metrics, use `/rv-analyze-file-complexity` (radon) or `/rv-analyze-file-dead-code` (pyflakes/vulture).
> Do NOT use for: multiple files (use `/rv-analyze-module`), making changes (use `/rv-refactor-*`).

## Steps

### Step 0: Check MCP Memory Cache

```
Use mcp__memory__search_nodes with query: "analysis:file:$ARGUMENTS"
```

If found, extract the `git_hash` observation. Compare with current hash:
```bash
git log -1 --format=%h -- $ARGUMENTS
```

- **Cache hit** (hashes match): Return the cached `summary` and `details` observations. Note "Using cached analysis. File unchanged since [date]." and STOP.
- **Cache miss** (hashes differ or not found): Proceed to Step 1.

### Step 1: Read Reference

Read `reference.md` from this skill's directory. It contains the 8 analysis dimensions, code smell catalog, and health scoring. Read `.claude/skills/rv-analyze-complexity/reference.md` for every numeric threshold (size, CC, nesting, parameters) and for the `git log` commands that detect Divergent Change and Shotgun Surgery.

### Step 2: Read and Analyze File

Read the target file. Analyze through the 8 dimensions from reference.md (in priority order):

1. **Structure**: Imports, classes, functions, constants, file length
2. **Responsibilities**: SRP assessment — how many distinct responsibilities?
3. **Dependencies**: What it imports, what imports it (Grep reverse lookup)
4. **Complexity**: Nesting depth, function lengths, parameter counts
5. **Error Handling**: try/except quality, cleanup patterns
6. **API Surface**: Public symbols, docstrings, type annotations
7. **Configuration**: Magic values, environment reads
8. **Testing**: Testability assessment, mock requirements

Not every dimension needs deep analysis — focus depth where issues exist. For clean dimensions, a brief "OK" suffices.

### Step 3: Persist to MCP Memory

```
Use mcp__memory__create_entities (or update existing via delete + create):
  Entity: "analysis:file:$ARGUMENTS"
  Type: "file-analysis"
  Observations:
    - "git_hash: <hash>"
    - "date: YYYY-MM-DD"
    - "summary: LOC=X, classes=Y, functions=Z, health=GRADE, smells=W, responsibilities=R"
    - "details: <full report as single observation>"
```

If MCP fails, skip caching — still output the report.

## Output Format

```markdown
## File Analysis: <filename>

**LOC**: X | **Classes**: Y | **Functions**: Z | **Health**: GRADE

### Structure
(imports by category, classes/functions summary)

### Dependencies
| Direction | Module | What |
|-----------|--------|------|
| Uses | rv_android_core | ErrorHandler |
| Used by | rv_platform | TaskExecutor |

### Quality Assessment
| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Lines | X | (file size, complexity reference) | OK/Warning |
| Max function length | Y | (function size, complexity reference) | OK/Warning |
| Max nesting | Z | (nesting depth, complexity reference) | OK/Warning |

### Code Smells
| # | Smell | Location | Severity | Notes |
|---|-------|----------|----------|-------|
| 1 | Long Method | func:42 | High | 80 lines |

### Recommendations
1. **[issue]**: [specific action]
```
