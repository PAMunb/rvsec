# Design: Skills Enrichment

## Context

This design supports the `gh13-skills-enrichment` change (GitHub Issue #13), addressing NFR01 (Maintainability) and NFR08 (Developer Experience).

An audit compared the 40 rv-android skills against the WORKFLOW.md workflow phases and against the reference skills from `agente-documentador` (49 skills, 20+ checklists, structured templates). The audit revealed that while most orchestrator and complex skills already have rich supporting files (e.g., `/rv-refactor` has 4 checklists + 3 templates + 2 examples, `/rv-feature` has 6 checklists + 3 templates), nine component skills produce structured analytical output but lack the guiding checklists that ensure consistency. Additionally, three defined skills are never referenced in WORKFLOW.md, and the five documentation skills lack explicit documentation quality principles.

**Constraints:**
- P1 (Simplicity): Only add checklists to skills that produce analytical output or make structured judgments. Mechanical skills (`/rv-qa-lint-fix`, `/rv-test-run`, `/rv-refactor-cleanup`) do not benefit from checklists — their behavior is deterministic.
- P2 (Human-readable): Checklists must be self-contained reference material. Each checklist tells the skill what to look for, what thresholds to apply, and how to categorize findings. An implementer reading a checklist should understand the analytical framework without consulting external sources.
- P4 (Current-state): No "inspired by agente-documentador" comments in the files. The checklists document techniques and criteria, not their origin.
- All content in English (project language rule).
- Checklist depth target: 80-200 lines each, matching the established pattern in `/rv-verify/checklists/` (128-305 lines).

**Current state of skills with supporting files:**

| Supporting Files | Skills |
|-----------------|--------|
| 4+ checklists + templates | rv-analyze-module, rv-feature, rv-refactor, rv-verify, rv-doc-architecture |
| 3 checklists | rv-risk, rv-retrospective, rv-tdd, rv-security, rv-planning, rv-release |
| 1 checklist + templates | rv-cleanup, rv-refactor-extract |
| Template only (no checklists) | rv-analyze-complexity, rv-analyze-dependencies, rv-analyze-dead-code, rv-analyze-file, rv-impact-analyzer, rv-debug-regression, rv-qa-lint, rv-doc-readme, rv-docs-sync |
| Nothing | rv-doc-adr, rv-doc-generate-claude-md, rv-test-add, rv-refactor-simplify, rv-refactor-constants, rv-refactor-cleanup, rv-qa-lint-fix, rv-test-run |

This change targets the "Template only" and "Nothing" groups, but only for skills where checklists add analytical value (8 skills, per proposal).

## Architecture

The change is purely additive — no existing files are deleted or restructured. The architecture is the skill file convention already established in the project:

```
.claude/skills/<skill-name>/
├── SKILL.md                    # Skill definition (frontmatter + prompt)
├── checklists/                 # Reference material (NEW for 8 skills)
│   ├── <topic-a>.md
│   └── <topic-b>.md
└── templates/                  # Output format templates (NEW for 4 skills)
    └── <output-name>.md
```

The SKILL.md references supporting files with a "Supporting Files" section that lists relative paths. When the skill is invoked, the LLM reads these files to guide its analysis. This pattern is already used by 15+ skills.

```
WORKFLOW.md ──references──> Skills (by slash command)
     │
     └─ Phases reference skills at decision points
            │
            └─ Skill reads its checklists/ and templates/ during execution
```

### Key Components

| Component | Responsibility | Files Affected |
|-----------|---------------|----------------|
| WORKFLOW.md | Skill references in phases | 1 file edited (3 new references + 3 retrospective paragraphs) |
| Checklist files | Analytical guidance for skills | 16 new files across 8 skill directories |
| Template files | Output format specification | 4 new files across 4 skill directories |
| SKILL.md edits (checklists) | Reference new supporting files | 8 files edited |
| SKILL.md edits (doc principles) | Embed documentation quality principles | 5 files edited |

## WORKFLOW.md Changes

Three skill references are added to existing phases, and a post-change retrospective paragraph is added at the end of each track.

### D1: Add `/rv-analyze-dependencies` to Full SDD Phase 1

In Section 6 (Full SDD), Phase 1 (Explore), after the existing bullet for `/rv-impact-analyzer`, add:

```markdown
- `/rv-analyze-dependencies <module>` — Map module dependency graph when the change affects cross-module interfaces
```

This skill is optional and conditional: it is useful when the change proposal mentions multiple modules or cross-module APIs. For single-module changes, `/rv-analyze-module` already covers dependencies as one of its 4 analysis perspectives.

### D2: Add `/rv-risk` to Full SDD Phase 3

In Section 6 (Full SDD), Phase 3 (Design), after the existing bullet for `/rv-doc-adr`, add:

```markdown
- `/rv-risk <change-name>` — Assess implementation risks when the design involves new dependencies, external APIs, or multi-module coordination
```

Risk assessment at design time prevents surprises during implementation. The skill produces a risk register with mitigation strategies that the implementer can consult during Phase 4.

### D3: Add `/rv-retrospective` post-Archive

Add a paragraph at the end of each track's final phase:

**Full SDD Phase 6 (Archive)** — after the archive bullet:
```markdown
**Optional**: Run `/rv-retrospective` to capture process learnings from this change cycle. Particularly valuable for changes that required deviation from the planned approach or encountered unexpected blockers.
```

**FF SDD Phase 4 (Close)** — after the archive bullet:
```markdown
**Optional**: Run `/rv-retrospective` to capture process learnings, especially if the fast-forward artifacts needed significant revision during implementation.
```

**Quick Path Phase 3 (Verify)** — after the verify bullet:
```markdown
**Optional**: Run `/rv-retrospective` for changes that revealed workflow improvements or recurring patterns worth documenting.
```

## Checklist Design

Each checklist follows the established pattern from `/rv-verify/checklists/`:
1. Title with `#` heading
2. One-line purpose statement
3. "How to Use" section (3-4 steps)
4. Content sections with tables and bullet lists
5. Target: 80-200 lines

### D4: `/rv-analyze-complexity` checklists

**`checklists/complexity-thresholds.md`** (~100 lines)

Reference table for complexity metrics and their acceptable ranges. The skill already computes these metrics but lacks documented thresholds for risk classification.

Content outline:
- Cyclomatic complexity scale: 1-10 (low), 11-20 (moderate), 21-50 (high), 50+ (very high, must refactor)
- Cognitive complexity thresholds (Sonar model): <15 OK, 15-25 warning, >25 must simplify
- Halstead metrics: volume, difficulty, effort — with interpretation guide
- Maintainability index: >85 (good), 65-85 (moderate), <65 (poor)
- Lines of code thresholds: function <50, class <500, file <1000
- Nesting depth: max 4 levels recommended
- Parameter count: max 5 for functions
- Coupling metrics: afferent (Ca) and efferent (Ce) coupling, instability ratio Ce/(Ca+Ce)
- Python-specific: comprehension complexity (nested comprehensions = red flag), decorator chains

**`checklists/refactoring-indicators.md`** (~120 lines)

Catalog of code patterns that indicate refactoring need, mapped to specific refactoring techniques. The skill identifies problems but currently lacks guidance on which refactoring to recommend.

Content outline:
- God Class indicators (>7 responsibilities, >20 methods, >15 fields) → Extract Class
- Long Method indicators (>30 lines, >3 indent levels, >4 params) → Extract Method, Introduce Parameter Object
- Feature Envy (method uses more data from another class) → Move Method
- Data Clumps (same group of data items appearing together) → Extract Class, Introduce Parameter Object
- Divergent Change (class changed for different reasons) → Extract Class by responsibility
- Shotgun Surgery (one change requires edits in many classes) → Move Method, Inline Class
- Primitive Obsession (using primitives instead of small objects) → Replace Primitive with Object
- Switch Statements (repeated type-checking) → Replace with Polymorphism
- Parallel Inheritance Hierarchies → Move Method, collapse hierarchy
- Speculative Generality (unused abstractions) → Collapse Hierarchy, Remove Middle Man
- Dead Code patterns specific to Python (unreachable after return, unused imports, `pass` in non-empty blocks)
- Mapping table: smell → refactoring technique → expected complexity reduction

### D5: `/rv-analyze-dependencies` checklists

**`checklists/dependency-health.md`** (~100 lines)

Health metrics for evaluating module dependency graphs. The skill maps dependencies but lacks criteria for classifying what constitutes a healthy vs. problematic graph.

Content outline:
- Dependency direction rules: core → platform → experiment (never reverse)
- Allowed dependency matrix for rv-android modules (which module may depend on which)
- Fan-in (how many modules depend on this one): high fan-in = stable abstraction needed
- Fan-out (how many modules this one depends on): high fan-out = fragile, consider facade
- Instability metric: I = Ce / (Ca + Ce), range 0 (stable) to 1 (unstable)
- Abstractness metric: A = abstract classes / total classes
- Distance from main sequence: D = |A + I - 1|, target < 0.3
- Dependency depth: max recommended 3-4 layers
- Package coupling principles: Acyclic Dependencies Principle (ADP), Stable Dependencies Principle (SDP), Stable Abstractions Principle (SAP)
- rv-android specific: module boundaries defined in `pyproject.toml` dependencies

**`checklists/circular-dependency-detection.md`** (~90 lines)

Patterns and resolution strategies for circular dependencies. The skill detects cycles but needs a catalog of resolution approaches.

Content outline:
- Detection method: build import graph, run Tarjan's algorithm (or DFS) for strongly connected components
- Common circular patterns in Python: A imports B, B imports A (direct); A→B→C→A (transitive)
- Type-only circles: often caused by type hints — resolve with `TYPE_CHECKING` guard
- Runtime circles: actual functional dependency — requires architectural intervention
- Resolution strategies:
  - Dependency Inversion: introduce interface/protocol in the lower module
  - Extract Common: move shared code to a new module both depend on
  - Merge Modules: if modules are too coupled, they may belong together
  - Event-based Decoupling: replace direct calls with event dispatch
  - Lazy Import: `import inside function` (Python workaround, not ideal)
- Decision matrix: circle type → recommended resolution strategy
- rv-android specific examples: rv-platform ↔ rv-tools potential cycles through ToolFactory

### D6: `/rv-analyze-dead-code` checklists

**`checklists/dead-code-categories.md`** (~100 lines)

Classification framework for dead code. The skill finds unused code but needs categories to prioritize removal and communicate findings.

Content outline:
- Category 1: Unreachable code (after return/raise/break, impossible conditions)
- Category 2: Unused imports (imported but never referenced)
- Category 3: Unused functions/methods (defined but never called)
- Category 4: Unused variables (assigned but never read)
- Category 5: Unused classes (defined but never instantiated or subclassed)
- Category 6: Commented-out code (code in comments, not documentation)
- Category 7: Redundant code (duplicate logic, unnecessary wrappers)
- Category 8: Obsolete feature flags (flags that are always on/off)
- Priority scale: P1 (remove immediately, no risk), P2 (remove after verification), P3 (investigate first)
- Removal guidelines per category
- Size impact estimation (lines removable per category)

**`checklists/false-positive-patterns.md`** (~80 lines)

Common patterns where code appears dead but is actually used through dynamic dispatch, reflection, or framework conventions. Prevents premature deletion.

Content outline:
- Dynamic imports: `importlib.import_module()`, `__import__()`
- Plugin/registry patterns: classes registered via decorator or metaclass, discovered at runtime
- String-based dispatch: `getattr(obj, method_name)()`, `globals()[name]()`
- Framework entry points: `pyproject.toml` `[tool.poetry.scripts]`, Click commands
- Test fixtures: `conftest.py` fixtures used by other test files
- Pydantic validators: `@field_validator` methods called by framework, not user code
- `__all__` exports: module-level symbol list for `from module import *`
- Abstract methods: defined for override, never called directly
- Signal handlers / event callbacks: registered dynamically
- rv-android specific: ErrorHandler decorators, TaskExecutor component lifecycle methods, ToolFactory registration

### D7: `/rv-analyze-file` checklists

**`checklists/file-analysis-dimensions.md`** (~110 lines)

Structured dimensions for single-file analysis. The skill analyzes files but currently follows an ad-hoc approach.

Content outline:
- Dimension 1 — Structure: classes, functions, module-level code, imports organization
- Dimension 2 — Responsibilities: Single Responsibility assessment, cohesion analysis
- Dimension 3 — Dependencies: imports (stdlib, third-party, internal), coupling assessment
- Dimension 4 — Complexity: per-function cyclomatic complexity, deepest nesting, longest function
- Dimension 5 — Error handling: try/except patterns, error propagation, cleanup
- Dimension 6 — API surface: public vs private, function signatures, return types
- Dimension 7 — Configuration: constants, environment variables, magic values
- Dimension 8 — Testing: testability assessment, mockable dependencies, side effects
- Analysis priority: Structure → Responsibilities → Dependencies → Complexity → Error Handling
- Output checklist: one finding per dimension minimum

**`checklists/code-smell-catalog.md`** (~120 lines)

Catalog of code smells detectable at the single-file level, with severity and fix suggestions. Complements the multi-file perspective of `/rv-analyze-complexity` refactoring indicators.

Content outline:
- Bloaters: Long Method, Large Class, Long Parameter List, Primitive Obsession, Data Clumps
- Object-Orientation Abusers: Switch Statements, Refused Bequest, Temporary Field, Alternative Classes
- Change Preventers: Divergent Change, Parallel Inheritance, Shotgun Surgery
- Dispensables: Comments (excessive), Dead Code, Duplicate Code, Speculative Generality, Data Class
- Couplers: Feature Envy, Inappropriate Intimacy, Message Chains, Middle Man
- Python-specific: mutable default args, bare except, global state mutation, string-based type checks (`isinstance` vs `type()`)
- Each smell: name, description, detection heuristic, severity (low/medium/high), suggested refactoring
- Table format for quick reference during analysis

### D8: `/rv-doc-adr` checklists

**`checklists/adr-quality.md`** (~90 lines)

Quality criteria for Architecture Decision Records. Ensures ADRs are complete, traceable, and useful for future readers.

Content outline:
- Completeness checklist: title, status, context, decision, consequences all present
- Context quality: describes forces/constraints/concerns, not just "we needed X"
- Decision statement: clear, unambiguous, starts with "We will..."
- Alternatives: at least 2 alternatives considered with pros/cons
- Consequences: both positive and negative consequences listed
- Traceability: links to issue number, affected specs, related ADRs
- Status lifecycle: proposed → accepted → deprecated → superseded (with link to successor)
- Anti-patterns: vague context, missing alternatives, no negative consequences, orphan ADRs
- Review criteria: would a new team member understand why this decision was made?

**`checklists/decision-drivers.md`** (~90 lines)

Framework for identifying and articulating the forces that drive architectural decisions. Helps the ADR author think through what matters before writing.

Content outline:
- Technical drivers: performance requirements, scalability needs, technology constraints
- Business drivers: time-to-market, cost, compliance, organizational structure
- Quality attribute drivers: maintainability, testability, security, reliability
- Constraint drivers: existing infrastructure, team expertise, third-party limitations
- Risk drivers: unknowns, dependencies on external systems, migration complexity
- Stakeholder drivers: who cares about this decision and why
- Driver prioritization: must-have vs nice-to-have, weighted scoring
- Common driver patterns in rv-android: P1 simplicity, academic context (thesis timeline), module boundaries
- Template: "This decision is driven by [driver] because [rationale]."

### D9: `/rv-doc-generate-claude-md` checklists

**`checklists/claude-md-sections.md`** (~100 lines)

Section completeness guide for module-level CLAUDE.md files. Ensures generated files contain all sections an LLM needs to work effectively with the module.

Content outline:
- Required sections: Module Overview, Architecture, Key Files, Development Commands, Dependencies, Configuration, Testing
- Module Overview: purpose, what it does, how it fits in rv-android, entry points
- Architecture: component diagram, key patterns, data flow
- Key Files: most important files with one-line descriptions, ordered by importance
- Development Commands: build, test, run commands specific to this module
- Dependencies: which modules it depends on and which depend on it
- Configuration: environment variables, config files, Pydantic models
- Testing: how to run tests, test categories, fixtures, test data locations
- Section depth: when to use tables vs prose, when to include code snippets
- Anti-patterns: copy-paste from README, outdated paths, missing entry points

**`checklists/audience-guidance.md`** (~80 lines)

Guidance on writing for the LLM audience vs human audience. CLAUDE.md is primarily consumed by LLMs, which have different needs than human readers.

Content outline:
- LLM audience priorities: precise file paths, exact command syntax, unambiguous naming
- Human audience priorities: conceptual understanding, motivation, context
- CLAUDE.md is LLM-first: favor precision over narrative
- File path conventions: always absolute from module root, include line numbers for key functions
- Command conventions: copy-pasteable, include working directory context
- Pattern description: name the pattern, show where it's implemented, not theory
- Avoid: relative paths, ambiguous references ("the config file"), assumptions about context
- Include: concrete examples, exact module names, version-specific details
- Length guidance: aim for 200-500 lines per module CLAUDE.md

### D10: `/rv-test-add` checklists

**`checklists/test-design-techniques.md`** (~120 lines)

Systematic test design techniques for creating effective tests. The skill adds tests but lacks guidance on how to design test cases systematically.

Content outline:
- Equivalence Partitioning: divide input domain into classes, one test per class
  - Valid partitions: normal inputs, boundary-adjacent, typical usage
  - Invalid partitions: empty, null/None, wrong type, out of range
- Boundary Value Analysis: test at exact boundaries of each partition
  - min, min+1, nominal, max-1, max for numeric ranges
  - Empty string, single char, max length for strings
  - Empty list, single element, max elements for collections
- Decision Table Testing: for functions with multiple conditions
  - Column per condition, row per combination, action columns
- State Transition Testing: for stateful components
  - Valid transitions, invalid transitions, state coverage
- Error Guessing: based on experience and common Python pitfalls
  - None arguments, empty collections, concurrent access, resource exhaustion
- Guidelines for test naming: `test_<unit>_<scenario>_<expected>`
- Guidelines for test structure: Arrange-Act-Assert, one assertion per test
- pytest-specific: parametrize for partitions, fixtures for setup, marks for categories

**`checklists/coverage-strategy.md`** (~90 lines)

Strategy for achieving meaningful test coverage without over-testing. Helps the skill decide what to test and what to skip.

Content outline:
- Coverage hierarchy: function > branch > line > path (diminishing returns)
- Must-test: public API, error handling paths, state transitions, boundary conditions
- Should-test: internal helper functions with complex logic, configuration parsing
- Skip: trivial getters/setters, framework-generated code, third-party wrappers
- Coverage targets by module type:
  - Core logic: 90%+ function coverage
  - Integration glue: 70%+ function coverage
  - CLI/UI: smoke tests for entry points, unit tests for argument parsing
- Test pyramid: many unit tests, fewer integration tests, minimal E2E tests
- rv-android specific test categories: `unit/`, `integration/`, `smoke/`, `online/`, `performance/`
- When to use mocks: external systems, file I/O, network calls, time-dependent code
- When NOT to mock: domain logic, pure functions, data transformations

### D11: `/rv-refactor-simplify` checklists

**`checklists/simplification-patterns.md`** (~110 lines)

Catalog of simplification patterns: common over-engineering patterns and their simpler replacements. The skill simplifies code but lacks a systematic catalog.

Content outline:
- Pattern 1: Unnecessary Abstraction → Inline. Class with one method → function. Interface with one implementor → delete interface
- Pattern 2: Over-Parameterized → Hardcode. Config option never changed → constant. Feature flag always on → remove flag
- Pattern 3: Premature Generalization → Specialize. Generic framework for one use case → direct implementation
- Pattern 4: Deep Inheritance → Composition. 3+ level hierarchy → flat composition with delegation
- Pattern 5: Callback Hell → Direct Call. Event bus with one subscriber → direct method call
- Pattern 6: Builder Pattern Overuse → Constructor. Builder for object with 2-3 fields → simple constructor
- Pattern 7: Strategy Pattern Overuse → If/Else. Strategy with 2 options → conditional
- Pattern 8: Wrapper/Adapter Over Nothing → Remove. Adapter that passes through without transformation → use wrapped object directly
- Pattern 9: Defensive Overvalidation → Trust Internal Code. Validation of internal parameters already validated upstream → remove
- Pattern 10: Unnecessary Indirection → Inline. Method that just calls another method → inline
- Each pattern: before/after code sketch, when to apply, when NOT to apply (false positive)
- P1 test: "three similar lines > premature abstraction"

**`checklists/complexity-reduction.md`** (~90 lines)

Measurable complexity reduction techniques with expected impact on metrics. Helps the skill set concrete improvement targets.

Content outline:
- Technique 1: Extract Method — reduces function cyclomatic complexity by isolating branches
- Technique 2: Replace Nested Conditionals with Guard Clauses — reduces nesting depth by 1-3 levels
- Technique 3: Replace Loop with Comprehension — reduces line count, may increase readability (or decrease if nested)
- Technique 4: Introduce Early Return — eliminates else branches, reduces indentation
- Technique 5: Replace Flag Arguments with Separate Methods — eliminates internal branching
- Technique 6: Decompose Conditional — name complex conditions as boolean variables/methods
- Technique 7: Consolidate Duplicate Conditional Fragments — DRY inside branches
- Technique 8: Replace Temp with Query — eliminate temporary variables that obscure flow
- Expected impact table: technique → cyclomatic reduction → cognitive reduction → line count change
- When NOT to simplify: performance-critical code, already-clear 3-line patterns, framework requirements

## Template Design

Each output template follows the established pattern from `/rv-verify/templates/verification-report.md`: Markdown structure with placeholder sections the skill fills in during execution.

### D12: `/rv-risk` template

**`templates/risk-register.md`** — Standardized risk register output. The skill already has 3 checklists (risk-categories, risk-indicators, mitigation-strategies) but no output template, meaning each invocation produces differently structured output.

```markdown
# Risk Register: $TARGET

## Summary
| Metric | Value |
|--------|-------|
| Total risks identified | N |
| Critical | N |
| High | N |
| Medium | N |
| Low | N |

## Risk Table
| ID | Risk | Probability | Impact | Score | Mitigation | Owner |
|----|------|------------|--------|-------|------------|-------|
| R1 | [description] | H/M/L | H/M/L | [PxI] | [strategy] | [who] |

## Risk Details
### R1: [Risk Name]
- **Category**: [from risk-categories.md]
- **Description**: [detailed explanation]
- **Trigger**: [what would cause this risk to materialize]
- **Indicators**: [from risk-indicators.md, early warning signs]
- **Mitigation**: [from mitigation-strategies.md]
- **Contingency**: [what to do if mitigation fails]
- **Status**: Open / Mitigated / Accepted / Closed

## RMMM Plan
[Mitigation-Monitoring-Management summary for top 3 risks]
```

### D13: `/rv-retrospective` template

**`templates/retrospective-report.md`** — Structured retrospective output. The skill has 3 checklists (process-analysis, improvement-cycle, gqm-framework) but no output format.

```markdown
# Retrospective: $TARGET

## Scope
- **Change**: [change name / issue number]
- **Track**: [Full SDD / FF SDD / Quick Path]
- **Duration**: [start date — end date]
- **Participants**: [who was involved]

## What Went Well
| Item | Impact | Keep Doing? |
|------|--------|-------------|
| [positive observation] | [how it helped] | Yes/No |

## What Could Improve
| Item | Impact | Action |
|------|--------|--------|
| [negative observation] | [how it hurt] | [improvement action] |

## Surprises / Deviations
[What was unexpected — blockers, scope changes, discoveries]

## Process Metrics (GQM)
| Goal | Question | Metric | Value |
|------|----------|--------|-------|
| [quality goal] | [how to measure] | [metric name] | [actual value] |

## Action Items
| ID | Action | Priority | Owner | Deadline |
|----|--------|----------|-------|----------|
| A1 | [specific action] | H/M/L | [who] | [when] |

## Lessons Learned
[Key takeaways for future changes of this type]
```

### D14: `/rv-doc-adr` template

**`templates/adr.md`** — ADR output format. This is the authoritative ADR template for the project (the previous `docs/templates/adr-template.md` was removed as redundant).

```markdown
# ADR-NNN: [Decision Title]

## Status
[Proposed | Accepted | Deprecated | Superseded by ADR-XXX]

## Context
[Describe the forces, constraints, and concerns that drive this decision.
Reference the issue number and affected specs. Explain what problem needs solving
and why the current state is insufficient.]

## Decision
We will [clear, unambiguous statement of the decision].

[Explain the decision in detail — what changes, what stays the same,
how it integrates with existing architecture.]

## Alternatives Considered

### Alternative 1: [Name]
- **Description**: [what this alternative entails]
- **Pros**: [advantages]
- **Cons**: [disadvantages]
- **Why rejected**: [specific reason]

### Alternative 2: [Name]
[same structure]

## Consequences

### Positive
- [benefit 1]
- [benefit 2]

### Negative
- [trade-off 1]
- [trade-off 2]

### Risks
- [risk and mitigation]

## References
- GitHub Issue: #N
- Affected specs: [list]
- Related ADRs: [list]
```

### D15: `/rv-doc-generate-claude-md` template

**`templates/claude-md.md`** — Module-level CLAUDE.md output format. Ensures every generated CLAUDE.md has the same section structure.

```markdown
# [Module Name]

## Overview
[1-2 paragraphs: what this module does, its role in rv-android, primary use cases]

## Architecture
[Component diagram or description, key patterns used, data flow]

## Key Files
| File | Purpose |
|------|---------|
| `path/to/file.py` | [one-line description] |

## Entry Points
[How to use this module: CLI commands, API calls, imports]

## Dependencies
### Depends On
- [module]: [what it uses from that module]

### Depended On By
- [module]: [what uses from this module]

## Configuration
| Variable / Setting | Purpose | Default |
|-------------------|---------|---------|
| `ENV_VAR` | [what it controls] | [default value] |

## Development
### Commands
[Build, test, run commands]

### Testing
[Test categories, how to run, fixtures]

## Key Patterns
[Patterns specific to this module: factories, strategies, decorators]
```

## Documentation Principles Integration

### D16: Principles block for `/rv-doc-*` skills

The following 7 documentation principles are added as a "Documentation Principles" section to the SKILL.md of 5 documentation skills. The block is inserted after the skill's workflow steps and before the output format section.

```markdown
## Documentation Principles

Apply these principles to all generated documentation:

1. **Reader perspective**: Write from the reader's viewpoint. What do they need to know? What will they look for first? Structure content for their workflow, not for comprehensiveness.
2. **No repetition**: State information once in the most logical location. Cross-reference instead of duplicating. If the same fact appears in two sections, one is wrong.
3. **No ambiguity**: Define terminology on first use. Use precise file paths. Prefer concrete examples over abstract descriptions. If a notation is used (diagram, table), explain how to read it.
4. **Standard organization**: Follow the established templates and section order. Consistency across documents reduces cognitive load. Deviations must be justified by content needs.
5. **Capture rationale**: Document WHY, not just WHAT. Every significant choice should have a brief explanation. Future readers need to understand the reasoning to make informed changes.
6. **Currency**: Only document current state (P4). Do not include migration history, version notes, or planned features. If something changed, describe the current behavior only.
7. **Stakeholder awareness**: Know the audience. CLAUDE.md is for LLMs (precise paths, exact commands). architecture.md is for developers (conceptual understanding). README.md is for newcomers (getting started).
```

**Affected skills and insertion point:**
- `/rv-doc-architecture/SKILL.md` — after "## Workflow" section, before "## Output Format"
- `/rv-doc-adr/SKILL.md` — after the main prompt instructions, before output section
- `/rv-doc-generate-claude-md/SKILL.md` — after the main prompt instructions, before output section
- `/rv-doc-readme/SKILL.md` — after the main prompt instructions, before output section
- `/rv-docs-sync/SKILL.md` — after "## Sync Process" section, before output section

## SKILL.md Checklist Reference Updates

### D17: Add supporting file references to 8 SKILL.md files

Each of the 8 skills receiving new checklists needs a "Supporting Files" section added (or updated) in its SKILL.md. The section follows this pattern:

```markdown
## Supporting Files

Read these reference files before starting analysis:

- `checklists/<name>.md` — [one-line description]
- `checklists/<name>.md` — [one-line description]
```

This is the same pattern already used by `/rv-analyze-module`, `/rv-verify`, `/rv-feature`, `/rv-refactor`, and others.

## AGENTS.md Synchronization

### D18: Sync `.claude/AGENTS.md` with enrichment changes

WORKFLOW.md references AGENTS.md as the authoritative skill/agent documentation (Section 4 table: `| .claude/AGENTS.md | Full skill and agent documentation |`). After this change, AGENTS.md is out of sync in three areas:

**A. File Structure section (line ~922)** — The directory tree shows skills without their new supporting directories. Update to reflect:

| Skill | Current in AGENTS.md | After Update |
|-------|---------------------|-------------|
| rv-analyze-complexity | `SKILL.md` only | + `checklists/` |
| rv-analyze-dependencies | `SKILL.md` only | + `checklists/` |
| rv-analyze-dead-code | `SKILL.md` only | + `checklists/` |
| rv-analyze-file | `SKILL.md` only | + `checklists/` |
| rv-doc-adr | `SKILL.md` only | + `checklists/` + `templates/` |
| rv-doc-generate-claude-md | `SKILL.md` only | + `checklists/` + `templates/` |
| rv-test-add | not listed individually | new entry with `checklists/` |
| rv-refactor-simplify | `SKILL.md` only | + `checklists/` |
| rv-risk | **missing entirely** | new entry with `SKILL.md` + `checklists/` + `templates/` |
| rv-retrospective | **missing entirely** | new entry with `SKILL.md` + `checklists/` + `templates/` |

**B. Component Skills tables** — `rv-risk` and `rv-retrospective` are not documented. Add a new "Risk & Process Skills" subsection with:

| Skill | Command | Purpose |
|-------|---------|---------|
| `rv-risk` | `/rv-risk [target]` | Technical risk assessment with RMMM plan |
| `rv-retrospective` | `/rv-retrospective [change]` | Post-change process retrospective |

**C. Quick Reference section (line ~1004)** — Add `/rv-risk` and `/rv-retrospective` under a new "Risk & Process" group.

## Mapping: Proposal → Implementation

| Proposal Item | Design Section | Files |
|---------------|---------------|-------|
| WORKFLOW.md integration (3 skills) | D1, D2, D3 | `docs/WORKFLOW.md` |
| rv-analyze-complexity checklists | D4 | 2 checklist files + SKILL.md edit |
| rv-analyze-dependencies checklists | D5 | 2 checklist files + SKILL.md edit |
| rv-analyze-dead-code checklists | D6 | 2 checklist files + SKILL.md edit |
| rv-analyze-file checklists | D7 | 2 checklist files + SKILL.md edit |
| rv-doc-adr checklists + template | D8, D14 | 2 checklist files + 1 template + SKILL.md edit |
| rv-doc-generate-claude-md checklists + template | D9, D15 | 2 checklist files + 1 template + SKILL.md edit |
| rv-test-add checklists | D10 | 2 checklist files + SKILL.md edit |
| rv-refactor-simplify checklists | D11 | 2 checklist files + SKILL.md edit |
| rv-risk template | D12 | 1 template file |
| rv-retrospective template | D13 | 1 template file |
| Doc principles integration | D16 | 5 SKILL.md edits |
| Checklist reference updates | D17 | 8 SKILL.md edits |
| AGENTS.md synchronization | D18 | `.claude/AGENTS.md` (File Structure + Component Skills + Quick Reference) |

## Testing Strategy

Since this change modifies development tooling (not application code), there are no automated tests. Verification is manual:

| Check | Method | Pass Criteria |
|-------|--------|---------------|
| WORKFLOW.md valid | Read file, verify new references are in correct phases | Each skill appears in the documented phase with correct syntax |
| Checklists readable | Read each checklist file | Valid Markdown, 80-200 lines, follows How to Use pattern |
| Templates usable | Read each template file | Valid Markdown, placeholder sections clear, matches skill output |
| SKILL.md references | Read each modified SKILL.md | Supporting Files section lists new checklists with correct relative paths |
| Doc principles present | Read each modified doc SKILL.md | Documentation Principles section present with all 7 principles |
| Skill invocation | Invoke 2-3 enriched skills on a real module | Skill reads checklists and produces structured output following them |
| No broken references | Grep all SKILL.md for checklist/template paths | Every referenced file exists on disk |

## Risks / Trade-offs

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Checklists too long → skill context window overhead | Medium | Low | Target 80-200 lines; skills read selectively, not in full |
| Checklists not consulted by LLM during skill execution | Low | Medium | Reference files in "Supporting Files" section with explicit "Read these before starting" instruction |
| Documentation principles section bloats SKILL.md | Low | Low | Section is 15 lines; SKILL.md files are already 100-500 lines |
| WORKFLOW.md changes create confusion about mandatory vs optional | Medium | Low | All new references use "optional" / "when" conditional language |
