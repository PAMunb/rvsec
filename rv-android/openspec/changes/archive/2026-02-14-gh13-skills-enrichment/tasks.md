# Tasks: Skills Enrichment

GitHub Issue: #13

## Execution Order

Tasks are grouped by type and numbered sequentially. Groups 1-3 are independent and can be parallelized via subagents. Group 4 (SKILL.md edits) depends on Groups 2-3 (checklists and templates must exist before being referenced). Group 8 (AGENTS.md sync) depends on Groups 2-5 (all new files and SKILL.md edits must exist before documenting them). Group 7 (verification) depends on all previous groups including Group 8.

---

## 1. WORKFLOW.md Integration

- [x] 1.1 In `docs/WORKFLOW.md`, Section 6 (Full SDD), Phase 1 (Explore): add `/rv-analyze-dependencies <module>` as optional skill after the existing `/rv-impact-analyzer` bullet. Use conditional language: "Map module dependency graph when the change affects cross-module interfaces." (Design ref: D1)
- [x] 1.2 In `docs/WORKFLOW.md`, Section 6 (Full SDD), Phase 3 (Design): add `/rv-risk <change-name>` as optional skill after the existing `/rv-doc-adr` bullet. Use conditional language: "Assess implementation risks when the design involves new dependencies, external APIs, or multi-module coordination." (Design ref: D2)
- [x] 1.3 In `docs/WORKFLOW.md`, Section 6 (Full SDD), Phase 6 (Archive): add optional `/rv-retrospective` paragraph after the archive bullet. Text: "**Optional**: Run `/rv-retrospective` to capture process learnings from this change cycle. Particularly valuable for changes that required deviation from the planned approach or encountered unexpected blockers." (Design ref: D3)
- [x] 1.4 In `docs/WORKFLOW.md`, Section 7 (FF SDD), Phase 4 (Close): add optional `/rv-retrospective` paragraph after the archive bullet. Text: "**Optional**: Run `/rv-retrospective` to capture process learnings, especially if the fast-forward artifacts needed significant revision during implementation." (Design ref: D3)
- [x] 1.5 In `docs/WORKFLOW.md`, Section 8 (Quick Path), Phase 3 (Verify): add optional `/rv-retrospective` paragraph after the verify bullet. Text: "**Optional**: Run `/rv-retrospective` for changes that revealed workflow improvements or recurring patterns worth documenting." (Design ref: D3)

## 2. Checklists — Analysis Skills

Each checklist follows the established pattern: `#` title, one-line purpose, "How to Use" section, content with tables/lists, 80-200 lines target. Content outlines are in design.md sections D4-D7.

- [x] 2.1 Create `.claude/skills/rv-analyze-complexity/checklists/complexity-thresholds.md` (~100 lines). Metric thresholds: cyclomatic (1-10/11-20/21-50/50+), cognitive (<15/15-25/>25), maintainability index (>85/65-85/<65), LOC (function <50, class <500, file <1000), nesting depth (max 4), parameter count (max 5), coupling (Ca, Ce, instability). Python-specific: comprehension complexity, decorator chains. (Design ref: D4)
- [x] 2.2 Create `.claude/skills/rv-analyze-complexity/checklists/refactoring-indicators.md` (~120 lines). Code smell → refactoring technique mapping table: God Class → Extract Class, Long Method → Extract Method, Feature Envy → Move Method, Data Clumps → Extract Class, Divergent Change → Extract Class, Shotgun Surgery → Move Method, Primitive Obsession → Replace with Object, Switch Statements → Polymorphism, Speculative Generality → Collapse Hierarchy. Each with detection heuristic and expected complexity reduction. (Design ref: D4)
- [x] 2.3 Create `.claude/skills/rv-analyze-dependencies/checklists/dependency-health.md` (~100 lines). rv-android dependency direction rules, allowed dependency matrix, fan-in/fan-out analysis, instability metric I=Ce/(Ca+Ce), abstractness metric, distance from main sequence D=|A+I-1|, Robert C. Martin package coupling principles (ADP, SDP, SAP). (Design ref: D5)
- [x] 2.4 Create `.claude/skills/rv-analyze-dependencies/checklists/circular-dependency-detection.md` (~90 lines). Detection via import graph + Tarjan's algorithm, common Python circular patterns (direct, transitive, type-only), resolution strategies: Dependency Inversion, Extract Common, Merge Modules, Event Decoupling, Lazy Import. Decision matrix: circle type → resolution. (Design ref: D5)
- [x] 2.5 Create `.claude/skills/rv-analyze-dead-code/checklists/dead-code-categories.md` (~100 lines). 8 categories: unreachable, unused imports, unused functions, unused variables, unused classes, commented-out code, redundant code, obsolete flags. Priority scale P1/P2/P3 with removal guidelines. (Design ref: D6)
- [x] 2.6 Create `.claude/skills/rv-analyze-dead-code/checklists/false-positive-patterns.md` (~80 lines). Patterns where code appears dead but is used: dynamic imports, plugin/registry patterns, string-based dispatch, framework entry points, test fixtures, Pydantic validators, `__all__` exports, abstract methods, signal handlers. rv-android specific: ErrorHandler decorators, TaskExecutor lifecycle, ToolFactory registration. (Design ref: D6)
- [x] 2.7 Create `.claude/skills/rv-analyze-file/checklists/file-analysis-dimensions.md` (~110 lines). 8 analysis dimensions: structure, responsibilities, dependencies, complexity, error handling, API surface, configuration, testing. Priority order for analysis. Output checklist: one finding per dimension minimum. (Design ref: D7)
- [x] 2.8 Create `.claude/skills/rv-analyze-file/checklists/code-smell-catalog.md` (~120 lines). Smell categories: Bloaters, OO Abusers, Change Preventers, Dispensables, Couplers. Each smell: name, description, detection heuristic, severity (low/medium/high), suggested refactoring. Python-specific smells. Table format for quick reference. (Design ref: D7)

## 3. Checklists — Documentation, Testing, and Refactoring Skills

- [x] 3.1 Create `.claude/skills/rv-doc-adr/checklists/adr-quality.md` (~90 lines). ADR completeness: title, status, context, decision, consequences. Context quality criteria. Decision statement format ("We will..."). Alternatives requirement (≥2). Consequences checklist (positive + negative). Traceability links. Status lifecycle. Anti-patterns. Review question: "Would a new team member understand why?" (Design ref: D8)
- [x] 3.2 Create `.claude/skills/rv-doc-adr/checklists/decision-drivers.md` (~90 lines). Driver categories: technical, business, quality attribute, constraint, risk, stakeholder. Prioritization framework. Common rv-android drivers: P1 simplicity, thesis timeline, module boundaries. Template: "This decision is driven by [driver] because [rationale]." (Design ref: D8)
- [x] 3.3 Create `.claude/skills/rv-doc-generate-claude-md/checklists/claude-md-sections.md` (~100 lines). Required sections: Overview, Architecture, Key Files, Dev Commands, Dependencies, Configuration, Testing. Depth guidance per section. Anti-patterns: copy-paste from README, outdated paths, missing entry points. (Design ref: D9)
- [x] 3.4 Create `.claude/skills/rv-doc-generate-claude-md/checklists/audience-guidance.md` (~80 lines). LLM audience vs human audience. CLAUDE.md is LLM-first: precise file paths, exact command syntax, unambiguous naming. Avoid relative paths, ambiguous references. Length guidance: 200-500 lines per module. (Design ref: D9)
- [x] 3.5 Create `.claude/skills/rv-test-add/checklists/test-design-techniques.md` (~120 lines). Techniques: Equivalence Partitioning, Boundary Value Analysis, Decision Table Testing, State Transition Testing, Error Guessing. Test naming: `test_<unit>_<scenario>_<expected>`. Structure: Arrange-Act-Assert. pytest-specific: parametrize, fixtures, marks. (Design ref: D10)
- [x] 3.6 Create `.claude/skills/rv-test-add/checklists/coverage-strategy.md` (~90 lines). Coverage hierarchy: function > branch > line > path. Must-test/should-test/skip criteria. Coverage targets by module type (core 90%, integration 70%, CLI smoke). Test pyramid. rv-android test categories. Mock guidelines. (Design ref: D10)
- [x] 3.7 Create `.claude/skills/rv-refactor-simplify/checklists/simplification-patterns.md` (~110 lines). 10 simplification patterns: Unnecessary Abstraction → Inline, Over-Parameterized → Hardcode, Premature Generalization → Specialize, Deep Inheritance → Composition, Callback Hell → Direct Call, Builder Overuse → Constructor, Strategy Overuse → If/Else, Wrapper Over Nothing → Remove, Defensive Overvalidation → Trust, Unnecessary Indirection → Inline. Each with before/after sketch and false-positive warnings. (Design ref: D11)
- [x] 3.8 Create `.claude/skills/rv-refactor-simplify/checklists/complexity-reduction.md` (~90 lines). 8 measurable techniques: Extract Method, Guard Clauses, Comprehension, Early Return, Separate Methods, Decompose Conditional, Consolidate Fragments, Replace Temp with Query. Impact table: technique → cyclomatic/cognitive reduction → line count change. (Design ref: D11)

## 4. Output Templates

- [x] 4.1 Create `.claude/skills/rv-risk/templates/risk-register.md`. Sections: Summary table (counts by severity), Risk Table (ID, risk, probability, impact, score, mitigation, owner), Risk Details (per-risk: category, description, trigger, indicators, mitigation, contingency, status), RMMM Plan (top 3 risks). (Design ref: D12)
- [x] 4.2 Create `.claude/skills/rv-retrospective/templates/retrospective-report.md`. Sections: Scope (change, track, duration, participants), What Went Well (table), What Could Improve (table), Surprises/Deviations, Process Metrics (GQM table), Action Items (table), Lessons Learned. (Design ref: D13)
- [x] 4.3 Create `.claude/skills/rv-doc-adr/templates/adr.md`. Sections: Status, Context, Decision, Alternatives Considered (name/description/pros/cons/why-rejected), Consequences (positive/negative/risks), References (issue, specs, related ADRs). (Design ref: D14)
- [x] 4.4 Create `.claude/skills/rv-doc-generate-claude-md/templates/claude-md.md`. Sections: Overview, Architecture, Key Files (table), Entry Points, Dependencies (depends-on/depended-on-by), Configuration (table), Development (commands + testing), Key Patterns. (Design ref: D15)

## 5. SKILL.md Modifications — Checklist References

Add "Supporting Files" section to each SKILL.md that received new checklists. The section follows the established pattern used by rv-analyze-module, rv-verify, rv-feature, etc. Insert after the workflow/instructions section and before the output section.

- [x] 5.1 Edit `.claude/skills/rv-analyze-complexity/SKILL.md`: add Supporting Files section referencing `checklists/complexity-thresholds.md` and `checklists/refactoring-indicators.md`. (Design ref: D17)
- [x] 5.2 Edit `.claude/skills/rv-analyze-dependencies/SKILL.md`: add Supporting Files section referencing `checklists/dependency-health.md` and `checklists/circular-dependency-detection.md`. (Design ref: D17)
- [x] 5.3 Edit `.claude/skills/rv-analyze-dead-code/SKILL.md`: add Supporting Files section referencing `checklists/dead-code-categories.md` and `checklists/false-positive-patterns.md`. (Design ref: D17)
- [x] 5.4 Edit `.claude/skills/rv-analyze-file/SKILL.md`: add Supporting Files section referencing `checklists/file-analysis-dimensions.md` and `checklists/code-smell-catalog.md`. (Design ref: D17)
- [x] 5.5 Edit `.claude/skills/rv-doc-adr/SKILL.md`: add Supporting Files section referencing `checklists/adr-quality.md`, `checklists/decision-drivers.md`, and `templates/adr.md`. (Design ref: D17)
- [x] 5.6 Edit `.claude/skills/rv-doc-generate-claude-md/SKILL.md`: add Supporting Files section referencing `checklists/claude-md-sections.md`, `checklists/audience-guidance.md`, and `templates/claude-md.md`. (Design ref: D17)
- [x] 5.7 Edit `.claude/skills/rv-test-add/SKILL.md`: add Supporting Files section referencing `checklists/test-design-techniques.md` and `checklists/coverage-strategy.md`. (Design ref: D17)
- [x] 5.8 Edit `.claude/skills/rv-refactor-simplify/SKILL.md`: add Supporting Files section referencing `checklists/simplification-patterns.md` and `checklists/complexity-reduction.md`. (Design ref: D17)

## 6. SKILL.md Modifications — Documentation Principles

Add the 7 documentation quality principles as a "Documentation Principles" section to 5 documentation skills. Insert after the workflow/instructions section and before the output format section. The exact text is in design.md section D16.

- [x] 6.1 Edit `.claude/skills/rv-doc-architecture/SKILL.md`: add Documentation Principles section after "## Workflow" section. (Design ref: D16)
- [x] 6.2 Edit `.claude/skills/rv-doc-adr/SKILL.md`: add Documentation Principles section after the main prompt instructions. (Design ref: D16)
- [x] 6.3 Edit `.claude/skills/rv-doc-generate-claude-md/SKILL.md`: add Documentation Principles section after the main prompt instructions. (Design ref: D16)
- [x] 6.4 Edit `.claude/skills/rv-doc-readme/SKILL.md`: add Documentation Principles section after the main prompt instructions. (Design ref: D16)
- [x] 6.5 Edit `.claude/skills/rv-docs-sync/SKILL.md`: add Documentation Principles section after "## Sync Process" section. (Design ref: D16)

## 8. AGENTS.md Synchronization

Depends on Groups 2-5 (all new files and SKILL.md edits must exist before documenting them in AGENTS.md). Design ref: D18.

- [x] 8.1 Edit `.claude/AGENTS.md` File Structure section: update the directory tree to show `checklists/` and `templates/` subdirectories for all 10 enriched skills. Add `rv-risk/` and `rv-retrospective/` as new entries with their full directory structure.
- [x] 8.2 Edit `.claude/AGENTS.md` Component Skills section: add a new "Risk & Process Skills" subsection (after Impact & Debugging Skills) documenting `rv-risk` and `rv-retrospective` with command, purpose, supporting files, and workflow integration notes.
- [x] 8.3 Edit `.claude/AGENTS.md` Quick Reference section: add `/rv-risk [target]` and `/rv-retrospective [change]` under a new "Risk & Process" group in the slash command list.

## 7. Verification

- [x] 7.1 Verify WORKFLOW.md: read `docs/WORKFLOW.md` and confirm all 3 new skill references appear in correct phases with conditional language. Confirm 3 retrospective paragraphs are in the right positions.
- [x] 7.2 Verify all 16 checklist files exist and are valid Markdown, 80-200 lines each, following the "How to Use" pattern.
- [x] 7.3 Verify all 4 template files exist and are valid Markdown with clear placeholder sections.
- [x] 7.4 Verify all 8 SKILL.md files have Supporting Files sections with correct relative paths pointing to existing files.
- [x] 7.5 Verify all 5 doc SKILL.md files have the Documentation Principles section with all 7 principles.
- [x] 7.6 Grep all modified SKILL.md files for checklist/template references and confirm every referenced path exists on disk.
- [x] 7.7 Run `openspec status --change gh13-skills-enrichment` to confirm all artifacts are done.
