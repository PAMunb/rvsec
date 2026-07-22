## Why

GitHub Issue: #13

An audit of the 40 skills and 1 agent against WORKFLOW.md and the reference skills from `agente-documentador` revealed integration gaps and enrichment opportunities. The audit compared skill invocations in each workflow phase, checked for supporting files (checklists, templates), and evaluated whether the depth of guidance matches the `agente-documentador` standard (20+ checklists with 80-300 lines each, structured output templates, Mermaid diagram templates).

The audit found three categories of issues:

1. **Workflow integration gaps**: Three skills (`/rv-analyze-dependencies`, `/rv-risk`, `/rv-retrospective`) are defined and functional but never referenced in any WORKFLOW.md phase, making them invisible during guided workflow execution. The workflow also lacks a post-archive retrospective step.

2. **Skills without supporting files**: Nine component skills have no checklists or templates, while peer skills of similar complexity already have 3-6 supporting files each. The gap is most impactful in documentation skills (`/rv-doc-adr`, `/rv-doc-generate-claude-md`) and analysis skills (`/rv-analyze-complexity`, `/rv-analyze-dependencies`, `/rv-analyze-dead-code`, `/rv-analyze-file`) that produce structured output but lack the guiding checklists that make output consistent.

3. **Documentation quality principles**: The `agente-documentador` embeds 7 documentation principles (reader perspective, no repetition, no ambiguity, standard organization, rationale capture, currency, stakeholder review) in every generation skill. Our `/rv-doc-*` skills lack these explicit principles, relying on implicit knowledge instead.

The enrichment scope is deliberately bounded by P1 (Simplicity): only skills that produce structured output or make analytical judgments benefit from checklists. Skills that perform mechanical operations (`/rv-qa-lint-fix`, `/rv-test-run`, `/rv-refactor-cleanup`) are excluded — adding checklists to them would be over-engineering.

## What Changes

### WORKFLOW.md Integration (3 additions + 1 new section)

- Add `/rv-analyze-dependencies` as optional skill in Full SDD Phase 1 (Explore) — useful for multi-module changes where dependency mapping informs the proposal
- Add `/rv-risk` as optional skill in Full SDD Phase 3 (Design) — risk assessment before implementation prevents surprises
- Add `/rv-retrospective` as optional post-Archive step in all tracks — captures process learnings after each change cycle
- Add brief "Post-Change Retrospective" paragraph at end of each track section

### Checklist Creation (8 skills, 16 new files)

Add external checklist files to skills that currently lack them but produce analytical output requiring structured guidance:

| Skill | New Checklists | Rationale |
|-------|---------------|-----------|
| `/rv-analyze-complexity` | `complexity-thresholds.md`, `refactoring-indicators.md` | Needs threshold tables and refactoring trigger criteria |
| `/rv-analyze-dependencies` | `dependency-health.md`, `circular-dependency-detection.md` | Needs health metrics and cycle detection guidance |
| `/rv-analyze-dead-code` | `dead-code-categories.md`, `false-positive-patterns.md` | Needs categorization framework and false positive awareness |
| `/rv-analyze-file` | `file-analysis-dimensions.md`, `code-smell-catalog.md` | Needs structured analysis dimensions |
| `/rv-doc-adr` | `adr-quality.md`, `decision-drivers.md` | Needs quality criteria for well-formed ADRs |
| `/rv-doc-generate-claude-md` | `claude-md-sections.md`, `audience-guidance.md` | Needs section completeness guidance |
| `/rv-test-add` | `test-design-techniques.md`, `coverage-strategy.md` | Needs systematic test design (equivalence partitioning, boundary analysis) |
| `/rv-refactor-simplify` | `simplification-patterns.md`, `complexity-reduction.md` | Needs pattern catalog for common simplifications |

### Template Creation (4 skills, 4 new files)

Add structured output templates to skills that produce reports but lack format guidance:

| Skill | New Template | Purpose |
|-------|-------------|---------|
| `/rv-risk` | `templates/risk-register.md` | Standardized risk register output format |
| `/rv-retrospective` | `templates/retrospective-report.md` | Standardized retrospective output format |
| `/rv-doc-adr` | `templates/adr.md` | ADR output template (authoritative ADR template for the project) |
| `/rv-doc-generate-claude-md` | `templates/claude-md.md` | CLAUDE.md output template for modules |

### Documentation Principles Integration (5 skills)

Embed the 7 documentation quality principles into `/rv-doc-architecture`, `/rv-doc-adr`, `/rv-doc-generate-claude-md`, `/rv-doc-readme`, and `/rv-docs-sync` SKILL.md files. The principles are added as a reference section that the skill consults during generation, not as checklist files — they are universal constraints, not analytical guidance.

### AGENTS.md Synchronization

Update `.claude/AGENTS.md` to reflect the enrichment changes. WORKFLOW.md references AGENTS.md as the authoritative skill documentation (Section 4, line 905), so it must stay in sync:

- **File Structure section**: Update the directory tree to show new `checklists/` and `templates/` directories for all 10 enriched skills (8 existing + 2 newly listed)
- **Component Skills tables**: Add `rv-risk` and `rv-retrospective` to the component skills documentation (both already had SKILL.md + checklists before this change, but were never added to AGENTS.md)
- **Quick Reference section**: Add `/rv-risk` and `/rv-retrospective` to the slash command reference

### Frontmatter Review (all 40 skills)

Audit and standardize frontmatter across all skills. The audit confirmed current frontmatter is adequate and does not need compaction. The review ensures consistency in the WHEN/WHEN NOT description pattern and correct `allowed-tools` lists.

## Capabilities

### New Capabilities

_None_ — This change enriches existing development tooling (skills and workflow docs). Skills are not part of the application specification domains.

### Modified Capabilities

_None_ — No spec-level behavior changes. Skills and WORKFLOW.md are development infrastructure outside the spec domain model.

## Impact

### Affected Files

**WORKFLOW.md** (1 file):
- `docs/WORKFLOW.md` — Add 3 skill references in appropriate phases + post-change retrospective paragraphs

**Checklist files** (16 new files):
- `.claude/skills/rv-analyze-complexity/checklists/complexity-thresholds.md`
- `.claude/skills/rv-analyze-complexity/checklists/refactoring-indicators.md`
- `.claude/skills/rv-analyze-dependencies/checklists/dependency-health.md`
- `.claude/skills/rv-analyze-dependencies/checklists/circular-dependency-detection.md`
- `.claude/skills/rv-analyze-dead-code/checklists/dead-code-categories.md`
- `.claude/skills/rv-analyze-dead-code/checklists/false-positive-patterns.md`
- `.claude/skills/rv-analyze-file/checklists/file-analysis-dimensions.md`
- `.claude/skills/rv-analyze-file/checklists/code-smell-catalog.md`
- `.claude/skills/rv-doc-adr/checklists/adr-quality.md`
- `.claude/skills/rv-doc-adr/checklists/decision-drivers.md`
- `.claude/skills/rv-doc-generate-claude-md/checklists/claude-md-sections.md`
- `.claude/skills/rv-doc-generate-claude-md/checklists/audience-guidance.md`
- `.claude/skills/rv-test-add/checklists/test-design-techniques.md`
- `.claude/skills/rv-test-add/checklists/coverage-strategy.md`
- `.claude/skills/rv-refactor-simplify/checklists/simplification-patterns.md`
- `.claude/skills/rv-refactor-simplify/checklists/complexity-reduction.md`

**Template files** (4 new files):
- `.claude/skills/rv-risk/templates/risk-register.md`
- `.claude/skills/rv-retrospective/templates/retrospective-report.md`
- `.claude/skills/rv-doc-adr/templates/adr.md`
- `.claude/skills/rv-doc-generate-claude-md/templates/claude-md.md`

**SKILL.md modifications** (5 files — doc principles):
- `.claude/skills/rv-doc-architecture/SKILL.md`
- `.claude/skills/rv-doc-adr/SKILL.md`
- `.claude/skills/rv-doc-generate-claude-md/SKILL.md`
- `.claude/skills/rv-doc-readme/SKILL.md`
- `.claude/skills/rv-docs-sync/SKILL.md`

**AGENTS.md** (1 file):
- `.claude/AGENTS.md` — Sync File Structure, Component Skills tables, and Quick Reference with enrichment changes

**SKILL.md modifications** (8 files — checklist references):
- `.claude/skills/rv-analyze-complexity/SKILL.md`
- `.claude/skills/rv-analyze-dependencies/SKILL.md`
- `.claude/skills/rv-analyze-dead-code/SKILL.md`
- `.claude/skills/rv-analyze-file/SKILL.md`
- `.claude/skills/rv-doc-adr/SKILL.md`
- `.claude/skills/rv-doc-generate-claude-md/SKILL.md`
- `.claude/skills/rv-test-add/SKILL.md`
- `.claude/skills/rv-refactor-simplify/SKILL.md`

### Dependencies

- No code dependencies — all changes are to development tooling files
- No module dependencies — skills are independent of application modules
- WORKFLOW.md changes are additive (new references, not restructuring)
- Checklist content draws from Sommerville (Software Engineering, 10th ed.) and Clements et al. (Documenting Software Architectures, 2nd ed.) — same sources used by `agente-documentador`

### Related FRs/NFRs (from PRD)

- **NFR01** (Maintainability) — Better tooling documentation improves maintainability of the development process itself
- **NFR08** (Developer Experience) — Richer skill guidance reduces cognitive load during development workflows
