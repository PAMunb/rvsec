# RV-Android Specifications

## Organization

Specs are organized by 7 domains, each covering one or more Python modules. Together they provide full traceability for all 37 functional requirements (FR01-FR37) and 8 non-functional requirements (NFR01-NFR08) from the [PRD](../../docs/PRD.md).

| Domain | Modules | FRs | NFRs | Invariants | Scenarios | Spec |
|--------|---------|-----|------|------------|-----------|------|
| **core** | rv-android-core | FR33-FR37 | NFR01-NFR06 | 26 | 37 | [core/spec.md](core/spec.md) |
| **platform** | rv-platform | FR07-FR11, FR14 | NFR02, NFR04, NFR07, NFR08 | 14 | 30 | [platform/spec.md](platform/spec.md) |
| **experiment** | rv-experiment | FR15-FR17 | NFR05, NFR08 | 12 | 18 | [experiment/spec.md](experiment/spec.md) |
| **agent** | rv-agent | FR21-FR32 | NFR02, NFR04, NFR07, NFR08 | 18 | 54 | [agent/spec.md](agent/spec.md) |
| **instrumentation** | rv-monitor-generator, rv-instrumentation | FR01-FR03 | NFR07 | 12 | 19 | [instrumentation/spec.md](instrumentation/spec.md) |
| **analysis** | rv-static-analysis, rv-coverage, rv-screen-parser | FR04-FR06, FR12-FR13 | NFR06 | 15 | 32 | [analysis/spec.md](analysis/spec.md) |
| **tools** | rv-tools, rv-uiautomator | FR18-FR20 | NFR02 | 14 | 24 | [tools/spec.md](tools/spec.md) |
| **Total** | 14 modules | **37 FRs** | **8 NFRs** | **111** | **214** | |

## Spec Structure

Each spec follows the template at [docs/templates/spec-template.md](../../docs/templates/spec-template.md) with four sections:

1. **Purpose** — Narrative description with data models, diagrams, and cross-domain relationships
2. **Data Contracts** — Input, Output, Side-Effects, Error types
3. **Invariants** — Testable assertions using RFC 2119 keywords (INV-XX-NN)
4. **Requirements** — One per FR/NFR with WHEN/THEN/AND scenarios

## Conventions

- **Language**: English throughout
- **Keywords**: RFC 2119 (MUST, MUST NOT, SHALL, SHOULD, MAY)
- **Invariant IDs**: `INV-XX-NN` where XX is the domain abbreviation
  - CORE, PLT, EXP, AGT, INS, ANA, TOOL
- **Requirement format**: `### Requirement: Name (FR/NFR ID)`
- **Scenario format**: `#### Scenario: Descriptive Name` with WHEN/THEN/AND

## Brownfield Rule

These specs document the **current implemented behavior** of the system.
They are NOT aspirational — they describe what exists today.

Future changes follow the OpenSpec workflow:
1. Create a change proposal in `openspec/changes/`
2. Generate artifacts: proposal.md, specs/ (delta), design.md, tasks.md
3. Implement, verify, and archive
4. Sync delta specs to main specs via `/opsx:sync`

## Change Workflow

Not every change requires the same ceremony. Three tracks match scope to formality:

| Track | When | How to Start |
|-------|------|-------------|
| **Full SDD** | Multi-module, architectural, new features | `/opsx:explore` → `/opsx:new` → `/opsx:continue` (x4) → `/opsx:apply` → `/opsx:verify` → `/opsx:archive` |
| **Fast-Forward SDD** | Single module, clear requirements | `/opsx:ff` → `/opsx:apply` → `/rv-verify` → `/opsx:archive` |
| **Quick Path** | Bug fixes, refactoring, test additions | `/rv-analyze-*` → fix → `/rv-verify` |

Full workflow details: [docs/WORKFLOW.md](../../docs/WORKFLOW.md)

## Templates

| Template | Path | When to Use |
|----------|------|-------------|
| **Spec** | [docs/templates/spec-template.md](../../docs/templates/spec-template.md) | Domain specs and delta specs |
| **Design** | [docs/templates/design-template.md](../../docs/templates/design-template.md) | Design documents for changes |
| **ADR** | [.claude/skills/rv-doc-adr/templates/adr.md](../../.claude/skills/rv-doc-adr/templates/adr.md) | Architectural Decision Records (via `/rv-doc-adr` skill) |

## OpenSpec Skills and Commands

The OpenSpec workflow tools are committed as part of the project (not installed separately):

- **Skills** (`.claude/skills/openspec-*/`): 10 skill definitions for SDD workflow phases
- **Commands** (`.claude/commands/opsx/`): 10 shorthand commands (`/opsx:new`, `/opsx:ff`, etc.)

These are committed alongside the `rv-*` skills for consistency — all Claude Code workflow tools live in `.claude/` and are version-controlled with the project.

## Related Documents

- **PRD**: [docs/PRD.md](../../docs/PRD.md) — 37 FRs, 8 NFRs, system overview
- **Workflow**: [docs/WORKFLOW.md](../../docs/WORKFLOW.md) — Authoritative workflow reference
- **Architecture**: [docs/rv_android_architecture.md](../../docs/rv_android_architecture.md) — System architecture
- **Plan**: [docs/20260209_plano_spec_driven.md](../../docs/20260209_plano_spec_driven.md) — SDD adoption plan (complete)
- **Config**: [openspec/config.yaml](../config.yaml) — OpenSpec rules and conventions
- **CLAUDE.md**: [CLAUDE.md](../../CLAUDE.md) — Development guide with SDD artifacts section
