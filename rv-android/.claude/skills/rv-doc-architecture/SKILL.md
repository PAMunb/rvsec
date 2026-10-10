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
allowed-tools: Read, Grep, Glob, Write, Bash, Skill
---

# Generate Architecture Documentation: $ARGUMENTS

Creates standardized architecture documentation at `modules/$ARGUMENTS/docs/architecture.md`.

## Supporting Files

Reference these checklists from this skill directory:
- `checklists/architectural-views.md` - 4+1 view model (Logical, Process, Development, Physical)
- `checklists/design-decisions.md` - 9 key architectural questions to answer
- `checklists/nfr-architecture-mapping.md` - How NFRs influence architecture
- `checklists/pattern-documentation.md` - Format for documenting patterns
- `checklists/spec-traceability.md` - SDD alignment: FRs, NFRs, invariants, scenarios

And this template:
- `templates/architecture.md` - Section structure of the generated `architecture.md` (read at Step 3)

## SDD Integration — Domain Spec Mapping

This project follows Spec-Driven Development, and the architecture document MUST reference the
spec that covers the module. The module-to-spec mapping lives in `openspec/specs/README.md`;
read it there instead of relying on a copy, because specs are added over time.

1. When the module appears in the README's domain table, use that domain's `spec.md` and the
   FRs listed in the same row.
2. When the module appears only in the "Capabilities" table (for example `aperv-tool`), use that
   capability's `spec.md`; capabilities carry invariants but no FRs.
3. When the module appears in neither table (for example `rv-instrumentation-core`,
   `rv-instrumentation-ajc`, `rv-instrumentation-dexlib2` or `rvagent-tool`), search
   `openspec/specs/*/spec.md` for the module name. When several specs mention it, use the one
   whose requirements describe the module's own behavior as the primary spec and cite the others
   as cross-references. When no spec mentions it, say so in "Specification Alignment" instead
   of inventing a mapping.

The list of workspace modules is in the root `CLAUDE.md` ("Module map"). NFRs are defined in
`docs/PRD.md` Section 7 (NFR01-NFR08).

## Diagram Guidelines

**Use Mermaid diagrams** with the `neutral` theme for all architecture visualizations.

```
%%{init: {'theme': 'neutral'}}%%
```

**Mermaid Reserved Words** - Do NOT use as node IDs:
- `graph`, `subgraph`, `end`, `style`, `class`, `default`
- Use alternatives: `StateGraph`, `GraphManager`, `EndNode`, etc.

**Diagram Types to Use**:
- `flowchart TB/LR` - Component architecture, data flow
- `sequenceDiagram` - Execution flow between components
- `classDiagram` - Interface hierarchies
- `stateDiagram-v2` - State machines

## Workflow

```
STEP 0: READ DOMAIN SPEC ──────────────────────────────────────────►
    │  Identify and read the relevant domain spec for SDD traceability
    ▼
STEP 1: ANALYZE MODULE ──────────────────────────────────────────►
    │  Understand structure, components, patterns
    ▼
STEP 2: CREATE DOCS DIR ─────────────────────────────────────────►
    │  mkdir -p modules/$MODULE/docs
    ▼
STEP 3: GENERATE DOC ────────────────────────────────────────────►
    │  Write architecture.md from template (includes spec traceability)
    ▼
VERIFY ──────────────────────────────────────────────────────────►
```

## Steps

### 0. Read Domain Spec (SDD Alignment)

Before analyzing the module, identify and read the relevant specification following "SDD Integration" above.

1. Find the module in `openspec/specs/README.md` to determine its domain (or capability) and FRs
2. Read the domain spec file (first 200 lines minimum) to extract:
   - FRs this module satisfies and their descriptions
   - Key invariants (INV-XX-NN format) and what they enforce
   - Scenarios that exercise this module
3. Read `docs/PRD.md` Section 7 (NFR01-NFR08) for NFR definitions

This information feeds into the "Specification Alignment" and "NFR Support" sections of the generated document.

### 1. Analyze Module

First, use the **Skill tool** to invoke the module analysis skill:

```
Skill tool: skill="rv-analyze-module", args="$ARGUMENTS"
```

**IMPORTANT**: You MUST call the Skill tool before proceeding. Wait for results.

This provides:
- Module structure and components
- Key classes and their purposes
- Internal and external dependencies
- Design patterns used

Additionally, verify module exists:

```bash
ls modules/$ARGUMENTS/src/
```

### 2. Create Docs Directory

```bash
mkdir -p modules/$ARGUMENTS/docs
```

### 3. Generate Documentation

Read `templates/architecture.md` and write `modules/$ARGUMENTS/docs/architecture.md` from it.

## Template: architecture.md

The template lives in `templates/architecture.md`. Read it at Step 3, after the domain spec
(Step 0) and the module analysis (Step 1) are in hand, and fill every placeholder from them.
Reference `checklists/architectural-views.md` for the view definitions the template uses.

## Documentation Principles

Apply `.claude/documentation-principles.md` to the generated document.

## Output

Report what was generated:

```
## Generated: Architecture Documentation

### File Created
- **Path**: modules/[module]/docs/architecture.md
- **Sections**: X

### Architectural Views
- Logical View: ✅ (entities, component diagram)
- Development View: ✅ (module structure, packages)
- Process View: ✅/⏭️ (if concurrency relevant)
- Scenarios: ✅ (at least one)

### Content
- Overview: ✅
- Specification Alignment: ✅ (FRs, invariants, spec scenarios)
- Key Architectural Decisions: ✅
- Architectural Patterns: ✅
- Core Components: ✅
- NFR Support: ✅ (with PRD NFR IDs)
- Key Interfaces: ✅
- Dependencies: ✅

### SDD Traceability
- Domain spec read: ✅/❌
- FRs referenced: [list]
- Invariants documented: [count]
- NFR IDs from PRD: ✅/❌

### Next Steps
- Review diagrams in VS Code with Mermaid extension
- Test rendering on GitHub
- Create ADRs for significant decisions
- Link to related ADRs
```

## Rules

1. **Follow `.claude/documentation-principles.md`** - English, objective tone, current state only
2. **Use Mermaid diagrams** - With `%%{init: {'theme': 'neutral'}}%%`
3. **Avoid reserved words** - Don't use `graph`, `end`, `class`, `style` as node IDs
4. **Document decisions** - Not just structure, but why
5. **Include multiple views** - At minimum: Logical, Development, one Scenario
6. **Map NFRs to architecture** - Use PRD NFR IDs (NFR01-08), explain how architecture supports them
7. **Document patterns** - Name patterns used and their trade-offs
8. **Link to related docs** - Reference domain spec, PRD, CLAUDE.md, and ADRs
9. **Read domain spec first** - Step 0 is mandatory; extract FRs, invariants, and scenarios before writing
10. **Include Specification Alignment section** - FRs satisfied, key invariants, and spec scenarios traced through architecture
