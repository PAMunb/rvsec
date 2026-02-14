# Claude Code Configuration - RV-Android

Complete documentation for agents, skills, workflows, and MCP integrations.

---

## Table of Contents

1. [Development Principles](#development-principles)
2. [Architecture Overview](#architecture-overview)
3. [Frontmatter Reference](#frontmatter-reference)
4. [Agents](#agents)
5. [Orchestrator Skills](#orchestrator-skills)
6. [Component Skills](#component-skills)
7. [MCP Servers](#mcp-servers)
8. [Plugins](#plugins)
9. [Agent Chains](#agent-chains)
10. [Usage Guide](#usage-guide)
11. [Decision Framework](#decision-framework)
12. [Examples](#examples)

---

## Development Principles

### Core Principles

| Principle | Description |
|-----------|-------------|
| **YAGNI** | You Aren't Gonna Need It - Don't implement until necessary |
| **KISS** | Keep It Simple, Stupid - Prefer simple solutions |
| **Single Responsibility** | One thing, done well |
| **Fail Fast** | Surface errors early, don't hide them |

### RV-Android Specific

| Principle | Description |
|-----------|-------------|
| **MOP Terminology** | "Monitored operations", NOT "security" - MOP is generic |
| **Code Evolution** | Remove legacy code, don't wrap it with adapters |
| **Backup Before Replace** | Move old files to `backup/` before replacement |
| **Specification Sets** | JCA (crypto) and Generic - used separately in experiments |

### Code Quality Standards

- **Comments**: English only, reflect current state, no promotional language
- **Error Handling**: Use ErrorHandler decorators, meaningful messages
- **Configuration**: Unified objects, validate at boundaries
- **Testing**: Unit → Integration → Smoke → System hierarchy

---

## Architecture Overview

### Design Philosophy

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER REQUEST                                │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR SKILLS                              │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │
│  │/rv-refactor │ │/rv-feature  │ │  /rv-tdd    │ │/rv-cleanup  │   │
│  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘   │
│         │               │               │               │           │
│         └───────────────┴───────┬───────┴───────────────┘           │
│                                 │                                   │
│                    Supporting files (templates, checklists)         │
│                    Multi-phase workflows                            │
│                    User checkpoints                                 │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      rv-code-reviewer                               │
│                   (Agent - Final quality gate)                      │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     COMPONENT SKILLS                                │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │ rv-analyze-*     │  │ rv-refactor-*    │  │ rv-test-*        │  │
│  │ (6 skills)       │  │ (4 skills)       │  │ (2 skills)       │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │ rv-qa-*, verify  │  │ rv-doc-*, sync   │  │ rv-debug-*       │  │
│  │ (3 skills)       │  │ (5 skills)       │  │ (1 skill)        │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        MCP SERVERS                                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │ sequential-      │  │ memory           │  │ context7         │  │
│  │ thinking         │  │                  │  │                  │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### Component Types

| Type | Location | Invocation | Context | Best For |
|------|----------|------------|---------|----------|
| **Agents** | `.claude/agents/` | Claude delegates or explicit | Isolated | Single-file autonomous tasks |
| **Skills** | `.claude/skills/` | `/skill-name` or auto-trigger | Main or forked | Workflows with supporting files |
| **MCP Servers** | `claude mcp list` | Tool calls | Persistent | External capabilities |
| **Plugins** | External | Various | Various | Shared configurations |

**Key Distinction**:
- **Agents**: Single `.md` file only, NO supporting directories
- **Skills**: `SKILL.md` file + optional supporting files (templates, checklists, scripts)

---

## Frontmatter Reference

Official Claude Code frontmatter fields. Reference: https://code.claude.com/docs/en/skills and https://code.claude.com/docs/en/sub-agents

### Skills Frontmatter (SKILL.md)

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `name` | No | string | Display name, becomes `/slash-command`. Max 64 chars, lowercase, hyphens |
| `description` | Recommended | string | When to use. Claude uses this for auto-triggering. Include WHEN + WHEN NOT |
| `argument-hint` | No | string | Hint for expected arguments. E.g., `[module-name]`, `[file-path]` |
| `context` | No | `fork` | Execution context. `fork` = isolated subagent context |
| `agent` | No | string | Subagent type when `context: fork`. Values: `Explore`, `Plan`, `general-purpose`, custom |
| `allowed-tools` | No | string | Comma-separated tools. E.g., `Read, Grep, Glob, Bash`. **Include `Skill` if invoking other skills** |
| `model` | No | string | Model to use. E.g., `claude-opus-4-1` |
| `disable-model-invocation` | No | boolean | If `true`, Claude won't auto-trigger. Manual `/name` only |
| `user-invocable` | No | boolean | If `false`, hidden from `/` menu. Only Claude can invoke |
| `hooks` | No | object | Hooks scoped to skill lifecycle |

**Example:**
```yaml
---
name: rv-refactor
description: >-
  Senior refactoring architect. Use when restructuring modules or reducing complexity.
  Do NOT use for: simple bug fixes, adding new features.
argument-hint: [module-name or file-path]
context: fork
agent: general-purpose
allowed-tools: Read, Grep, Glob, Edit, Write, Bash, Task, AskUserQuestion, Skill
---
```

**Note**: `Skill` is included because this orchestrator invokes other skills like `/rv-analyze-complexity`.

### Agents Frontmatter (.md in .claude/agents/)

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `name` | Yes | string | Unique identifier. Lowercase, hyphens only |
| `description` | Yes | string | When Claude should delegate. Include "use proactively" for auto-delegation |
| `tools` | No | string/array | Tools the agent can use. Omit to inherit all |
| `disallowedTools` | No | string/array | Tools to explicitly deny |
| `model` | No | string | `sonnet`, `opus`, `haiku`, `inherit` (default: `inherit`) |
| `permissionMode` | No | string | `default`, `acceptEdits`, `dontAsk`, `bypassPermissions`, `plan` |
| `skills` | No | array | Skills to preload at startup |
| `hooks` | No | object | Hooks scoped to agent lifecycle |

**Example:**
```yaml
---
name: rv-code-reviewer
description: >-
  Expert code reviewer. Use after writing or modifying code to review for quality.
  Do NOT use for: implementing fixes, writing code.
tools: Read, Grep, Glob, Bash
model: inherit
skills:
  - rv-analyze-complexity
  - rv-analyze-dependencies
---
```

### Description Best Practices

From official docs: **"Generic descriptions fail. Use WHEN + WHEN NOT pattern."**

| Pattern | Example |
|---------|---------|
| **WHEN** | "Use when restructuring modules, reducing complexity..." |
| **WHEN NOT** | "Do NOT use for: simple bug fixes, adding features..." |
| **ALTERNATIVES** | "Use /rv-feature for new functionality, /rv-tdd for test-driven fixes" |

### Skill Invocation Pattern

When a skill needs to invoke another skill, use the explicit **Skill tool** syntax:

```markdown
Use the **Skill tool** to invoke [skill-name]:
```
Skill tool: skill="rv-analyze-module", args="$ARGUMENTS"
```
```

**Important Notes**:
- Skills that invoke other skills MUST have `Skill` in their `allowed-tools`
- The syntax `Invoke /rv-skill-name` is ambiguous - always use explicit Skill tool syntax
- Wait for results before proceeding to the next step

**Example from rv-analyze-module**:
```markdown
### Step 3: Invoke Specialized Analysis Skills

**IMPORTANT**: You MUST use the Skill tool to invoke each analysis skill below.

1. **Dependency Analysis** - Use the **Skill tool**:
   ```
   Skill tool: skill="rv-analyze-dependencies", args="$ARGUMENTS"
   ```

2. **Complexity Analysis** - Use the **Skill tool**:
   ```
   Skill tool: skill="rv-analyze-complexity", args="$ARGUMENTS"
   ```
```

---

## Agents

Located in `.claude/agents/`. Single `.md` file only (no supporting directories).

### rv-code-reviewer

**Purpose**: Expert code review, final quality gate in agent chain.

**When to Use**:
- After any code changes
- As chain endpoint from orchestrators
- Proactively on `git diff`

**Preloaded Skills**:
- `rv-analyze-complexity` - For deep analysis
- `rv-analyze-dependencies` - For dependency issues

**Chain Integration**:
- Called by: `rv-refactor`, `rv-feature`, `rv-tdd`, `rv-cleanup`
- Position: Final gate before user approval

**Review Checklist**:
- Code quality (readability, naming, duplication)
- Architecture (boundaries, patterns, separation)
- Security (secrets, validation, data handling)
- Testing (coverage, edge cases, mocks)
- rv-android specific (MOP terminology, evolution guidelines)

**Feedback Format**:
- 🔴 Critical (must fix)
- 🟡 Warnings (should fix)
- 🟢 Suggestions (consider)

---

## Orchestrator Skills

Located in `.claude/skills/`. Invoke with `/skill-name`. These are complex multi-phase workflows with supporting files (templates, checklists).

### /rv-refactor

**Purpose**: Complete refactoring workflow with analysis, planning, execution, and review.

**When to Use**:
- Restructuring modules or large files
- Reducing code complexity
- Breaking circular dependencies
- Improving code architecture

**Workflow**:
```
ANALYSIS → PLANNING → [CHECKPOINT #1] → EXECUTION → VERIFICATION → CODE REVIEW → [CHECKPOINT #2] → AUDIT
```

**Chains To**: `rv-code-reviewer` agent

**Supporting Files**: `.claude/skills/rv-refactor/`
- Templates: `analysis-report.md`, `refactoring-plan.md`, `final-report.md`
- Checklists: `pre-refactor.md`, `verification.md`

---

### /rv-feature

**Purpose**: Complete feature implementation with discovery, design options, and TDD.

**When to Use**:
- Implementing new features
- Adding new capabilities
- Creating new modules or components

**Workflow**:
```
DISCOVERY → DESIGN → [CHECKPOINT #1: Choose Approach] → PLANNING → [CHECKPOINT #2] → IMPLEMENTATION (TDD) → CODE REVIEW → [CHECKPOINT #3] → AUDIT
```

**Chains To**: `rv-code-reviewer` agent

**Key Feature**: User CHOOSES approach (not just approves) at first checkpoint.

**Dependency Management**: Phase 2.5 handles adding dependencies with `/rv-analyze-dependencies` verification.

**Supporting Files**: `.claude/skills/rv-feature/`
- Templates: `discovery-report.md`, `design-options.md`, `implementation-plan.md`
- Checklists: `acceptance-checklist.md`

---

### /rv-tdd

**Purpose**: Strict Test-Driven Development with RED-GREEN-REFACTOR cycles.

**When to Use**:
- Implementing features with TDD methodology
- Bug fixes that need regression tests
- When test coverage is critical

**Workflow**:
```
ANALYSIS → TEST PLANNING → [CHECKPOINT #1] → RED (failing tests) → GREEN (minimal impl) → REFACTOR → CODE REVIEW → [CHECKPOINT #2] → AUDIT
```

**Chains To**: `rv-code-reviewer` agent

**Key Rules**:
- NEVER write implementation before tests
- Tests MUST fail first (RED phase)
- Implement MINIMAL code to pass (GREEN phase)
- Refactor only when GREEN

**Supporting Files**: `.claude/skills/rv-tdd/`
- Templates:
  - `unit/test_component.py` - Standard unit tests
  - `integration/test_component_integration.py` - Component tests
  - `smoke/test_smoke.py` - Quick sanity checks
  - `property/test_component_pbt.py` - Property-based tests (Hypothesis)
  - `regression/test_component_regression.py` - Bug prevention tests
  - `snapshot/test_component_snapshot.py` - Baseline comparison tests
  - `conftest/conftest.py` - Shared fixtures
- Checklists: `tdd-rules.md`

**Dependency Management**: Phase 1.5 handles adding test dependencies (e.g., `hypothesis`, `pytest-snapshot`) with `/rv-analyze-dependencies` verification.

---

### /rv-cleanup

**Purpose**: Safe codebase cleanup with dead code removal and verification.

**When to Use**:
- Removing technical debt
- Cleaning unused code
- Preparing for major refactoring
- Reducing codebase size

**Workflow**:
```
ANALYSIS → PLANNING → [CHECKPOINT #1] → EXECUTION (per group with rollback) → CODE REVIEW → [CHECKPOINT #2] → AUDIT
```

**Chains To**: `rv-code-reviewer` agent

**Safety Features**:
- Backup before any removal
- Rollback on test failure
- Confidence levels (HIGH/MEDIUM/LOW)
- User approval required

**Supporting Files**: `.claude/skills/rv-cleanup/`
- Templates: `analysis-report.md`, `cleanup-plan.md`
- Checklists: `safety-checklist.md`

---

## Component Skills

Located in `.claude/skills/`. Invoke with `/skill-name` or let Claude auto-trigger.

### Analysis Skills

| Skill | Command | Purpose | MCP Integration |
|-------|---------|---------|-----------------|
| `rv-analyze-complexity` | `/rv-analyze-complexity [module]` | Code complexity metrics | sequential-thinking, memory |
| `rv-analyze-dependencies` | `/rv-analyze-dependencies [module]` | Module dependency mapping | sequential-thinking, memory |
| `rv-analyze-dead-code` | `/rv-analyze-dead-code [module]` | Unused code detection | memory |
| `rv-analyze-file` | `/rv-analyze-file [path]` | Single file analysis | - |
| `rv-analyze-module` | `/rv-analyze-module [module]` | Module architecture | sequential-thinking, memory, context7 |

**Complexity Thresholds**:
| Metric | Threshold | Action |
|--------|-----------|--------|
| Lines per file | > 500 | Split into components |
| Function length | > 50 lines | Extract helpers |
| Classes per file | > 3 | Separate modules |
| Imports | > 20 | Check dependencies |
| Nesting depth | > 4 levels | Refactor conditionals |

---

### Refactoring Skills

| Skill | Command | Purpose |
|-------|---------|---------|
| `rv-refactor-simplify` | `/rv-refactor-simplify [path]` | Simplify complex code |
| `rv-refactor-extract` | `/rv-refactor-extract [path] [target]` | Extract function/class/module |
| `rv-refactor-cleanup` | `/rv-refactor-cleanup [module]` | Quick automated cleanup (imports, formatting) |
| `rv-refactor-constants` | `/rv-refactor-constants [path]` | Extract magic values |

**Note**: `/rv-refactor-cleanup` is for quick fixes. Use `/rv-cleanup` orchestrator for comprehensive dead code removal with safety controls.

---

### Testing Skills

| Skill | Command | Purpose |
|-------|---------|---------|
| `rv-test-add` | `/rv-test-add [path] [function]` | Add single test file for existing code |
| `rv-test-run` | `/rv-test-run [module]` | Run tests |

**Note**: `/rv-test-add` includes a decision tree for test type selection. Use `/rv-tdd` orchestrator for full RED-GREEN-REFACTOR workflow.

**Test Categories**:
| Category | Path | Purpose | Marker |
|----------|------|---------|--------|
| unit | tests/unit/ | Isolated tests | - |
| integration | tests/integration/ | Component tests | - |
| smoke | tests/smoke/ | Sanity checks | smoke |
| online | tests/online/ | Device/LLM required | online |
| performance | tests/performance/ | Latency tests | performance |
| regression | tests/regression/ | Bug prevention | regression |
| property | tests/property/ | Hypothesis PBT | hypothesis |
| snapshot | tests/snapshot/ | Baseline comparison | snapshot |

**Test Commands**:
```bash
# Run module tests
cd modules/$MODULE
PYTHONPATH=../rv-android-core/src:src poetry run pytest tests/ -v

# Run with coverage
poetry run pytest --cov=src --cov-report=html

# Run single test
poetry run pytest tests/unit/test_file.py::TestClass::test_name -v
```

---

### QA Skills

| Skill | Command | Purpose |
|-------|---------|---------|
| `rv-qa-lint` | `/rv-qa-lint [module]` | Run linters + security analysis |
| `rv-qa-lint-fix` | `/rv-qa-lint-fix [module]` | Auto-fix lint issues + verify |

**Checks Performed by rv-qa-lint**:
| Tool | Purpose |
|------|---------|
| flake8 | Style + errors |
| mypy | Type checking |
| black | Formatting |
| isort | Import ordering |
| bandit | Security vulnerabilities |

**Lint Commands**:
```bash
# Format
poetry run black src/ && poetry run isort src/

# Check
poetry run flake8 src/
poetry run mypy src/

# Security
poetry run bandit -r src/ --severity-level medium
```

---

### Documentation Skills

| Skill | Command | Purpose |
|-------|---------|---------|
| `rv-doc-readme` | `/rv-doc-readme [module]` | Generate README.md for GitHub/GitLab |
| `rv-doc-generate-claude-md` | `/rv-doc-generate-claude-md [module]` | Generate CLAUDE.md (with auto-analysis) |
| `rv-doc-architecture` | `/rv-doc-architecture [module]` | Generate architecture.md (Mermaid diagrams) |
| `rv-doc-adr` | `/rv-doc-adr [decision-title]` | Create Architecture Decision Record |
| `rv-docs-sync` | `/rv-docs-sync [module or 'all']` | Sync docs with code changes |

**Documentation Guidelines**:
- Language: English only (code, comments, documentation)
- Tone: Professional, objective, no promotional language
- No bias terms: Avoid "modern", "sophisticated", "elegant", "cutting-edge"
- Current state only: Do not reference migration, legacy, or what was changed

**Documentation Locations**:
- `modules/<module>/README.md` - User-facing documentation (GitHub/GitLab)
- `modules/<module>/CLAUDE.md` - Quick reference for Claude Code
- `modules/<module>/docs/architecture.md` - Detailed architecture (Mermaid diagrams)
- `modules/<module>/docs/adr/ADR-XXX-*.md` - Architecture Decision Records

---

### Verification Skills

| Skill | Command | Purpose |
|-------|---------|---------|
| `rv-verify` | `/rv-verify [module]` | Run all checks (tests, lint, type, security) |

**Checks Performed by rv-verify**:
1. Unit tests
2. Integration tests (if exist)
3. Dependency security (`safety check`)
4. Formatting (black, isort)
5. Linting (flake8)
6. Type checking (mypy)

---

### Impact & Debugging Skills

| Skill | Command | Purpose |
|-------|---------|---------|
| `rv-impact-analyzer` | `/rv-impact-analyzer [file or module]` | Analyze change impact before refactoring |
| `rv-debug-regression` | `/rv-debug-regression [test-name]` | Investigate regression bugs via git history |

---

### Risk & Process Skills

| Skill | Command | Purpose |
|-------|---------|---------|
| `rv-risk` | `/rv-risk [target]` | Technical risk assessment with RMMM plan |
| `rv-retrospective` | `/rv-retrospective [scope]` | Post-change process retrospective |

**rv-risk** — Proactive risk identification and mitigation planning. Produces a risk register with probability/impact scoring and RMMM (Risk Mitigation, Monitoring, Management) plan.

**Supporting Files**: `.claude/skills/rv-risk/`
- Checklists: `risk-categories.md`, `risk-indicators.md`, `mitigation-strategies.md`
- Templates: `risk-register.md`

**Workflow Integration**: Optional in Full SDD Phase 3 (Design) — assess implementation risks when the design involves new dependencies, external APIs, or multi-module coordination.

**rv-retrospective** — Post-change process analysis using GQM (Goal-Question-Metric) framework. Identifies what went well, what could improve, and produces actionable improvement items.

**Supporting Files**: `.claude/skills/rv-retrospective/`
- Checklists: `process-analysis.md`, `improvement-cycle.md`, `gqm-framework.md`
- Templates: `retrospective-report.md`

**Workflow Integration**: Optional post-Archive step in all three tracks (Full SDD, FF SDD, Quick Path) — captures process learnings after each change cycle.

---

## Dependency Management

When adding new dependencies to a module, follow this workflow:

### Process

```
1. Identify needed dependency
       │
       ▼
2. poetry add [--group dev] [package]
       │
       ▼
3. Invoke /rv-analyze-dependencies [module]
       │  Checks for:
       │  - Circular dependencies
       │  - Version conflicts
       │  - Security vulnerabilities
       │
       ▼
4. poetry lock
       │
       ▼
5. Continue implementation
```

### Commands

```bash
cd modules/$MODULE

# Production dependency
poetry add [package-name]

# Development-only dependency (tests, linting)
poetry add --group dev [package-name]

# Lock dependencies
poetry lock

# Verify
poetry run safety check
```

### Common Dependencies by Purpose

| Purpose | Package | Group |
|---------|---------|-------|
| Property testing | `hypothesis` | dev |
| Snapshot testing | `pytest-snapshot` or `syrupy` | dev |
| Coverage | `pytest-cov` | dev |
| Parallel tests | `pytest-xdist` | dev |
| HTTP client | `httpx` | prod |
| Data validation | `pydantic` | prod |
| Security scan | `bandit`, `safety` | dev |

### Integration with Skills

- `/rv-feature` - Phase 2.5 handles dependency addition
- `/rv-tdd` - Phase 1.5 handles test dependency addition
- `/rv-analyze-dependencies` - Verifies dependency health

---

## MCP Servers

Configured via `claude mcp add --scope user`. Check with `claude mcp list`.

### sequential-thinking

**Purpose**: Structured, step-by-step reasoning for complex analysis.

**When to Use**:
- Complex code analysis requiring multiple steps
- Debugging with hypothesis testing
- Architectural decision-making

**Tool**: `mcp__sequential-thinking__sequentialthinking`

**Example Usage**:
```
Analyzing complexity of rv-agent module:

Thought 1: First, gather metrics for all Python files...
Thought 2: Files over threshold: rvagent_strategy.py (847 lines)...
Thought 3: Root cause analysis...
```

**Fallback**: If unavailable, use numbered reasoning steps in response.

---

### memory

**Purpose**: Persistent knowledge graph across sessions for caching and audit trails.

**When to Use**:
- Caching analysis results to avoid redundant work
- Tracking operation history (audits)
- Building knowledge about codebase

**Tools**:
- `mcp__memory__search_nodes` - **Check FIRST** before expensive analysis
- `mcp__memory__create_entities` - Store findings after analysis
- `mcp__memory__read_graph` - Read all entities

**Cache Pattern** (used by analysis skills):
```
1. Search memory for cached data: "complexity-rv-agent"
2. If found and recent (< 7 days) → return cached
3. If not found or stale → do analysis
4. Save results to memory with date in entity name
```

**Entity Types Used**:
| Entity Pattern | Type | When Created | Cache TTL |
|----------------|------|--------------|-----------|
| `complexity-[module]-[date]` | complexity-analysis | After rv-analyze-complexity | 7 days |
| `dependencies-[module]-[date]` | dependency-analysis | After rv-analyze-dependencies | 7 days |
| `dead-code-[module]-[date]` | dead-code-analysis | After rv-analyze-dead-code | 7 days |
| `rv-[module]-analysis` | module-analysis | After rv-analyze-module | 7 days |
| `refactor-[date]-[target]` | refactoring-operation | After rv-refactor | permanent |
| `feature-[date]-[name]` | feature-implementation | After rv-feature | permanent |
| `tdd-[date]-[feature]` | tdd-implementation | After rv-tdd | permanent |
| `cleanup-[date]-[module]` | cleanup-operation | After rv-cleanup | permanent |
| `review-[date]-[module]` | code-review | After rv-code-reviewer | permanent |

**Fallback**: If unavailable, output audit summary directly to user.

---

### context7

**Purpose**: Up-to-date documentation for libraries.

**When to Use**:
- Looking up library APIs (LangGraph, pytest, pydantic)
- Checking framework patterns
- Verifying best practices

**Tools**:
- `mcp__context7__resolve-library-id` - Find library ID
- `mcp__context7__query-docs` - Query documentation

**Example**:
```
# First resolve library ID
resolve-library-id: "pytest fixtures"

# Then query docs
query-docs: libraryId="/pytest-dev/pytest", query="fixture scope and parametrize"
```

---

## Plugins

### superpowers

Provides additional skills and patterns:

| Skill | Purpose |
|-------|---------|
| `brainstorming` | Creative exploration before implementation |
| `systematic-debugging` | 4-phase debugging process |
| `test-driven-development` | TDD workflow guidance |
| `writing-plans` | Implementation planning |
| `verification-before-completion` | Pre-commit verification |
| `code-reviewer` | Code review patterns |

### claude-md-management

| Skill | Purpose |
|-------|---------|
| `revise-claude-md` | Update CLAUDE.md with learnings |
| `claude-md-improver` | Audit and improve CLAUDE.md files |

---

## Agent Chains

### Standard Chain Flow

```
┌──────────────────────────────────────────────────────────────────┐
│                        ORCHESTRATOR                              │
│  (rv-refactor / rv-feature / rv-tdd / rv-cleanup)               │
│                                                                  │
│  1. Analysis phase (uses preloaded skills)                      │
│  2. Planning phase                                               │
│  3. User checkpoint (AskUserQuestion)                           │
│  4. Execution phase                                              │
│  5. Verification phase                                           │
└──────────────────────────────────┬───────────────────────────────┘
                                   │
                                   │ Task tool with
                                   │ subagent_type: rv-code-reviewer
                                   ▼
┌──────────────────────────────────────────────────────────────────┐
│                      rv-code-reviewer                            │
│                                                                  │
│  - Reviews all changes                                           │
│  - Can invoke analysis skills for deep dive                     │
│  - Returns findings to orchestrator                              │
└──────────────────────────────────┬───────────────────────────────┘
                                   │
                                   │ Findings incorporated
                                   ▼
┌──────────────────────────────────────────────────────────────────┐
│                        ORCHESTRATOR                              │
│                                                                  │
│  6. Final user checkpoint (with review findings)                │
│  7. Audit phase (persist to memory)                             │
│  8. Complete                                                     │
└──────────────────────────────────────────────────────────────────┘
```

### Chain Configuration

Orchestrators invoke code review via Task tool:
```
Task tool:
  subagent_type: rv-code-reviewer
  prompt: "Review the [operation] changes for [target]. Focus on: [specific areas]"
```

---

## Usage Guide

### When to Use Each Component

| Task | Use | Why |
|------|-----|-----|
| "Refactor this module" | `/rv-refactor` orchestrator skill | Full workflow with checkpoints |
| "Implement login feature" | `/rv-feature` orchestrator skill | Discovery + design + TDD |
| "Add tests for X" | `/rv-tdd` orchestrator skill | Strict RED-GREEN-REFACTOR |
| "Clean up dead code" | `/rv-cleanup` orchestrator skill | Safe removal with rollback |
| "Review my changes" | `rv-code-reviewer` agent | Expert code review |
| "Check complexity of file" | `/rv-analyze-complexity` skill | Quick analysis |
| "Run the tests" | `/rv-test-run` skill | Simple test execution |
| "Fix lint issues" | `/rv-qa-lint-fix` skill | Auto-fix formatting |

### Explicit Invocation

**Orchestrator Skills** - Use slash command:
```
/rv-refactor rv-agent
/rv-feature add caching to LLM client
/rv-tdd new_function_name
/rv-cleanup rv-platform
```

**Component Skills** - Use slash command:
```
/rv-analyze-complexity rv-agent
/rv-test-run rv-platform
/rv-qa-lint-fix rv-android-core
```

**Agent** - Ask Claude to use:
```
Have rv-code-reviewer review my changes
```

### Automatic Invocation

Claude automatically:
- **Invokes orchestrator skills** based on task description and complexity
- **Triggers component skills** based on context and description
- **Chains to code review agent** after orchestrator skill completes

---

## Decision Framework

### Orchestrator Skill vs Component Skill?

```
Is it a complex, multi-phase workflow with checkpoints?
    │
    ├── YES → Use ORCHESTRATOR SKILL
    │         • /rv-refactor, /rv-feature, /rv-tdd, /rv-cleanup
    │
    └── NO → Is it a focused, single-purpose task?
              │
              ├── YES → Use COMPONENT SKILL
              │         • /rv-analyze-*, /rv-test-*, /rv-qa-*
              │
              └── NO → Let Claude decide based on context
```

### Which Orchestrator Skill?

```
What are you trying to do?
    │
    ├── Improve existing code structure → /rv-refactor
    │
    ├── Add new functionality → /rv-feature
    │
    ├── Fix bug with tests → /rv-tdd
    │
    ├── Remove technical debt → /rv-cleanup
    │
    └── Review changes → rv-code-reviewer (agent)
```

### MCP Usage

```
Do you need...
    │
    ├── Step-by-step reasoning? → sequential-thinking
    │
    ├── Persistent knowledge? → memory
    │
    └── Library documentation? → context7
```

---

## Examples

### Example 1: Refactoring a Module

**User**: "The rv-agent strategy module is too complex, refactor it" or `/rv-refactor rv-agent`

**Claude**: Invokes `/rv-refactor` skill

**Flow**:
1. Analysis using `rv-analyze-complexity` patterns
2. Creates refactoring plan
3. **Checkpoint #1**: User approves plan
4. Executes with backup
5. Runs tests via `/rv-verify`
6. Chains to `rv-code-reviewer` agent
7. **Checkpoint #2**: User approves result
8. Persists audit to memory

---

### Example 2: Implementing a Feature

**User**: "Add caching to the LLM client" or `/rv-feature caching for LLM client`

**Claude**: Invokes `/rv-feature` skill

**Flow**:
1. Discovery: requirements, location, patterns
2. Design: 2-3 approaches with pros/cons
3. **Checkpoint #1**: User CHOOSES approach
4. Planning: detailed steps
5. **Checkpoint #2**: User approves plan
6. Implementation with TDD
7. Chains to `rv-code-reviewer` agent
8. **Checkpoint #3**: User approves feature
9. Persists audit to memory

---

### Example 3: Quick Analysis

**User**: "Check if there's dead code in rv-platform"

**Claude**: Uses `/rv-analyze-dead-code` skill directly (no orchestrator needed)

**Output**: Analysis report with unused imports, functions, variables

---

### Example 4: Running Tests

**User**: "Run the rv-agent tests"

**Claude**: Uses `/rv-test-run` skill directly

**Commands**:
```bash
cd modules/rv-agent
PYTHONPATH=../rv-android-core/src:src poetry run pytest tests/ -v
```

---

## File Structure

```
.claude/
├── AGENTS.md                          # This file - full documentation
├── project-info.md                    # Quick reference (paths, env vars, commands)
│
├── agents/                            # Autonomous agents (single .md file only)
│   └── rv-code-reviewer.md            # Code review quality gate
│
└── skills/                            # Invocable skills (via /skill-name)
    │
    │   # Orchestrator Skills (with supporting files)
    ├── rv-refactor/
    │   ├── SKILL.md
    │   ├── templates/
    │   └── checklists/
    ├── rv-feature/
    │   ├── SKILL.md
    │   ├── templates/
    │   └── checklists/
    ├── rv-tdd/
    │   ├── SKILL.md
    │   ├── templates/
    │   │   ├── unit/test_component.py
    │   │   ├── integration/test_component_integration.py
    │   │   ├── smoke/test_smoke.py
    │   │   ├── property/test_component_pbt.py      # Hypothesis PBT
    │   │   ├── regression/test_component_regression.py
    │   │   ├── snapshot/test_component_snapshot.py
    │   │   └── conftest/conftest.py
    │   └── checklists/
    ├── rv-cleanup/
    │   ├── SKILL.md
    │   ├── templates/
    │   └── checklists/
    │
    │   # Analysis Skills
    ├── rv-analyze-complexity/
    │   ├── SKILL.md
    │   ├── checklists/
    │   └── templates/
    ├── rv-analyze-dependencies/
    │   ├── SKILL.md
    │   └── checklists/
    ├── rv-analyze-dead-code/
    │   ├── SKILL.md
    │   └── checklists/
    ├── rv-analyze-file/
    │   ├── SKILL.md
    │   └── checklists/
    ├── rv-analyze-module/SKILL.md
    ├── rv-impact-analyzer/
    │   ├── SKILL.md
    │   └── templates/
    │
    │   # Refactoring Skills
    ├── rv-refactor-simplify/
    │   ├── SKILL.md
    │   └── checklists/
    ├── rv-refactor-extract/SKILL.md
    ├── rv-refactor-cleanup/SKILL.md
    ├── rv-refactor-constants/SKILL.md
    │
    │   # Testing & Debugging Skills
    ├── rv-test-add/
    │   ├── SKILL.md
    │   └── checklists/
    ├── rv-test-run/SKILL.md
    ├── rv-debug-regression/
    │   ├── SKILL.md
    │   └── templates/
    │
    │   # QA & Verification Skills
    ├── rv-qa-lint/
    │   ├── SKILL.md
    │   └── templates/lint-report.md
    ├── rv-qa-lint-fix/SKILL.md
    ├── rv-verify/
    │   ├── SKILL.md
    │   └── templates/
    │
    │   # Documentation Skills
    ├── rv-doc-readme/
    │   ├── SKILL.md
    │   └── templates/readme.md
    ├── rv-doc-generate-claude-md/
    │   ├── SKILL.md
    │   ├── checklists/
    │   └── templates/
    ├── rv-doc-architecture/SKILL.md
    ├── rv-doc-adr/
    │   ├── SKILL.md
    │   ├── checklists/
    │   └── templates/
    ├── rv-docs-sync/
    │   ├── SKILL.md
    │   └── templates/
    │
    │   # Risk & Process Skills
    ├── rv-risk/
    │   ├── SKILL.md
    │   ├── checklists/
    │   └── templates/
    └── rv-retrospective/
        ├── SKILL.md
        ├── checklists/
        └── templates/
```

---

## Quick Reference

### Agent
- `rv-code-reviewer` - Quality gate (delegated by Claude or orchestrators)

### Orchestrator Skills (invoke via /skill-name)
- `/rv-refactor` - Restructure code
- `/rv-feature` - New features
- `/rv-tdd` - Test-driven development
- `/rv-cleanup` - Remove dead code

### Skills (Slash commands)

**Analysis**:
- `/rv-analyze-complexity [target]`
- `/rv-analyze-dependencies [module]`
- `/rv-analyze-dead-code [module]`
- `/rv-analyze-file [path]`
- `/rv-analyze-module [module]`
- `/rv-impact-analyzer [file or module]`

**Refactoring**:
- `/rv-refactor-simplify [path]`
- `/rv-refactor-extract [path] [target]`
- `/rv-refactor-cleanup [module]`
- `/rv-refactor-constants [path]`

**Testing & Debugging**:
- `/rv-test-add [path] [function]`
- `/rv-test-run [module]`
- `/rv-debug-regression [test-name]`

**Quality & Verification**:
- `/rv-qa-lint [module]`
- `/rv-qa-lint-fix [module]`
- `/rv-verify [module]`

**Documentation**:
- `/rv-doc-readme [module]`
- `/rv-doc-generate-claude-md [module]`
- `/rv-doc-architecture [module]`
- `/rv-doc-adr [decision-title]`
- `/rv-docs-sync [module or 'all']`

**Risk & Process**:
- `/rv-risk [target]`
- `/rv-retrospective [scope]`

### MCP Tools
- `mcp__sequential-thinking__sequentialthinking`
- `mcp__memory__create_entities`
- `mcp__memory__search_nodes`
- `mcp__context7__query-docs`
