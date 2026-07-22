# CLAUDE.md Section Guide

Section completeness guide for module-level CLAUDE.md files. Ensures generated files contain all sections an LLM needs to work effectively with the module.

## How to Use

1. When generating a CLAUDE.md, include every required section from the list below
2. Use the depth guidance to determine how much detail each section needs
3. Check against the anti-patterns list before finalizing
4. Validate all paths and commands are accurate and copy-pasteable

---

## Required Sections

Every module-level CLAUDE.md must contain these sections, in this order:

| # | Section | Purpose | Depth Guidance |
|---|---------|---------|----------------|
| 1 | Overview | What this module does, its role in rv-android | 1–2 paragraphs |
| 2 | Architecture | Components, patterns, data flow | Diagram + table of components |
| 3 | Key Files | Most important files with descriptions | Table, ordered by importance |
| 4 | Entry Points | How to use the module (CLI, API, imports) | Code snippets |
| 5 | Dependencies | What it depends on and what depends on it | Two lists with brief explanations |
| 6 | Configuration | Environment variables, config files, models | Table with defaults |
| 7 | Development Commands | Build, test, run commands | Copy-pasteable code blocks |
| 8 | Testing | Test categories, how to run, fixtures | Table of test dirs + commands |

### Section 1: Overview

**What to include**:
- Module's primary purpose in one sentence
- How it fits in the rv-android architecture (which layer: core, service, orchestration)
- Primary use cases (when would someone interact with this module)
- Entry point summary (CLI command, main class, or import)

**What to exclude**: Implementation details, history, comparison with alternatives.

### Section 2: Architecture

**What to include**:
- Directory structure (abbreviated, showing `src/` layout)
- Key components table: component name, file path, one-line purpose
- Design patterns in use (factory, strategy, observer, etc.)
- Data flow for the primary operation

**When to use diagrams**: If the module has 3+ interacting components, include an ASCII or Mermaid diagram showing their relationships.

### Section 3: Key Files

**What to include**:
- Top 10–15 most important files
- Ordered by importance (entry points first, then core logic, then utilities)
- One-line description that tells the reader what they'll find

**Format**:
```markdown
| File | Purpose |
|------|---------|
| `src/rv_agent/agent/rv_agent.py` | Main agent class, LangGraph workflow definition |
```

### Section 4: Entry Points

**What to include**:
- How to invoke the module from CLI (if applicable)
- How to import and use programmatically
- Configuration required before first use

**Format**: Working code snippets that can be copy-pasted.

### Section 5: Dependencies

**What to include**:
- Internal dependencies (other rv-android modules) with what is used from each
- External dependencies (third-party packages) with version constraints if critical
- Bidirectional: what depends ON this module too

### Section 6: Configuration

**What to include**:
- Environment variables with their purpose and defaults
- Configuration files with their location and format
- Pydantic model references if configuration is model-based

**Format**: Table with columns: Variable/Setting, Purpose, Default, Required.

### Section 7: Development Commands

**What to include**:
- Install command (module-specific if different from root)
- Run command (how to execute the module)
- Test command (full and filtered)
- Lint/format commands

**Rule**: Every command must work when copy-pasted from the CLAUDE.md. Include `cd` context or full paths.

### Section 8: Testing

**What to include**:
- Test directory structure and categories
- How to run each category
- Key fixtures and test data locations
- Environment requirements for tests (mocks, emulators, servers)

---

## Anti-Patterns

| Anti-Pattern | Problem | Fix |
|-------------|---------|-----|
| Copy from README | Different audiences need different content | Write CLAUDE.md from scratch for LLM audience |
| Outdated paths | Files moved/renamed but CLAUDE.md not updated | Verify every path exists before writing |
| Missing entry points | LLM can't figure out where to start | Always document main class/function/CLI command |
| Relative paths | `./src/` is ambiguous without context | Use paths relative to module root: `src/rv_agent/...` |
| Generic descriptions | "Handles configuration" tells nothing | Be specific: "Reads `config.yaml` and creates `PlatformConfig` Pydantic model" |
| Stale commands | Commands that no longer work | Test every command before including |

## Length Guidance

| Module Size | CLAUDE.md Target |
|-------------|-----------------|
| Small (< 10 files) | 100–200 lines |
| Medium (10–30 files) | 200–400 lines |
| Large (30+ files) | 400–600 lines |

Larger is not better. Every line should help the LLM understand or work with the module. Remove anything that doesn't serve that purpose.
