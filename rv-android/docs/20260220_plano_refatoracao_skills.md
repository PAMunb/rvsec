# Plan: Redesign Analysis Skill Tree — Scope Correction

**Date**: 2026-02-20
**Author**: Pedro Henrique Teixeira Costa
**Status**: PLANNED
**Origin**: Findings F1/F2 during skills verification (Batch 1 of `docs/20260218_skills.md`)

---

## 1. Context

During skills verification (Batch 1), we discovered that three "leaf" skills (rv-analyze-complexity, rv-analyze-dead-code, rv-analyze-dependencies) operate at **module scope** despite being classified as Level 0 leaves. A leaf node analyzing an entire module (46 files, 49 tool calls) is architecturally wrong — leaves should be file-scoped, fast, and focused. Module-level orchestration belongs to higher-level skills.

Root cause: skills were designed as standalone tools, not as composable building blocks for the skill chain hierarchy.

Secondary root cause: mandatory supporting file reads (3 checklists per skill) add ~9-12 tool calls before any analysis begins. This is the primary driver behind F1 (30 tool calls for a single 128-line file).

### Evidence

| Skill | Classification | Actual Scope | Tool Calls | Problem |
|-------|---------------|--------------|------------|---------|
| rv-analyze-file | L0 leaf | Single file | 30 | Correct scope, but exhaustive (8-dimension checklist + 3 supporting file reads) |
| rv-analyze-complexity | L0 leaf | Entire module | 49 | Module-wide scan for a "leaf" + 3 supporting file reads + sequential-thinking overhead |
| rv-analyze-dead-code | L0 leaf | Entire module | (untested) | Module-wide scan for a "leaf" + 3 supporting file reads |
| rv-analyze-dependencies | L0 leaf | Module or all | (untested) | Module-wide scan for a "leaf" + 3 supporting file reads + sequential-thinking overhead |
| rv-analyze-module | L1 mid-level | Module | (untested) | Calls three module-scoped "leaves" — redundant orchestration + 4 modeling checklists |

---

## 2. Design Principles

1. **Leaf = file scope, fast, cheap**. Module scope = orchestrator with internal iteration.
2. **Naming convention**: `rv-analyze-file-*` for file-scoped variants. `rv-analyze-*` (without `file`) for module-scoped.
3. **Always fork** (`context: fork`): every skill gets its own context window.
4. **Minimize tokens**: lean SKILL.md (~50-80 lines), no checklists/supporting files unless essential, no MCP cache/memory overhead.
5. **No fork-per-file iteration**: module-scoped skills iterate internally (Glob+Read), not by forking to file-level skills (too expensive: 46 forks × ~30s each).
6. **Seamless workflow integration**: naming and scope must align with WORKFLOW.md usage patterns (Phase 0, Explore, Quick Path Analyze).
7. **Compact supporting files**: the knowledge in checklists/templates is valuable and must be preserved — not deleted. Approach: merge 3 separate files into 1 consolidated `reference.md` per skill (preserving all content), inline only the essential thresholds (~5 lines) in SKILL.md, and change instruction from "Read before starting" to "Consult reference.md for detailed patterns if needed during analysis". This reduces mandatory reads from 3 to 0 (1 optional) while keeping all accumulated knowledge accessible. Supporting files that prove genuinely unused after verification can be removed later. This addresses the primary root cause of F1.
8. **No sequential-thinking MCP in L0 skills**: the `sequential-thinking` MCP server adds ~2-3 tool calls overhead without clear value for leaf skills. Numbered steps in the output suffice. Reserve sequential-thinking for complex orchestrators (L1+) where multi-step reasoning adds value.
9. **Compact frontmatter descriptions**: skill descriptions are loaded into the main context window permanently (not just when invoked) and consume a shared budget of ~16,000 chars (2% of context window). With 32 skills at avg 260 chars/description = 8,334 chars = **52% of the budget**. With 2 new skills (34 total), this pressure increases. Shorten descriptions to <100 chars, moving routing info ("Do NOT use for...") to the SKILL.md body. **Critical**: `context: fork` MUST stay — without it skills run inline in the main window, defeating all context isolation. `agent: general-purpose` is technically the default for forked skills, but keeping it explicit is low-risk.

---

## 2.1. MCP Memory Integration Design

The analysis skills already have MCP memory integration (rv-analyze-complexity, rv-analyze-dead-code, rv-analyze-dependencies), but the current implementation uses date-based entity names (e.g., `complexity-rv-android-core-[2026-02-20]`) which proliferate entities and use fragile 7-day staleness checks.

### Redesigned Schema

**Entity naming**: `analysis:{type}:{scope}`
- Example: `analysis:complexity:rv-android-core`
- One entity per analysis type per scope — no date suffixes
- Update existing entity via `add_observations` / `delete_observations`

**Git hash-based cache invalidation** (replaces 7-day staleness check):
- Store `git_hash: <short-sha>` in observations
- Before analysis: compare stored hash with `git rev-parse --short HEAD`
- If equal → reuse cached results (skip analysis)
- If different → delete old observations, re-analyze, persist new results

**Observations structure**:
```
git_hash: abc1234                          — cache invalidation key
date: 2026-02-20                           — reference timestamp
summary: 5 files, avg complexity 3.2       — quick lookups (parent skills)
details: <full structured findings>        — complete reuse
```

**Workflow**: check cache → (cache hit: return summary) | (cache miss: analyze → persist → return)

### Inspiration

The agente-documentador project uses Neo4j as externalized state between atomic skill invocations — each skill reads/writes graph nodes, avoiding recalculation across calls. MCP memory serves the same role for rv-android in a lightweight form: persistent analysis results keyed by git hash, shared across skill invocations within and across sessions.

---

## 2.2. Frontmatter Compaction Plan

### Problem

Claude Code loads all skill **descriptions** into the main context window permanently (not on invocation — always). The budget is 2% of the context window (~16,000 chars). Current state across 32 rv-* skills:

| Metric | Value |
|--------|-------|
| Total frontmatter chars | 14,278 |
| Total description chars | 8,334 (52% of budget) |
| Average description | 260 chars |
| Longest description (rv-tdd) | 382 chars |
| Top 5 longest | rv-tdd (382), rv-doc-code (353), rv-cleanup (341), rv-code-reviewer (327), rv-doc-adr (313) |

Every description follows a verbose template: `[Role]. Use when [scenario]. Do NOT use for: [anti-scenarios]. Use /other-skill for [redirect].` The "Do NOT use for" routing sections alone consume ~3,277 chars.

### What Gets Loaded Where

Understanding this distinction is critical for deciding what to compact:

| Content | Where Loaded | When | Impact |
|---------|-------------|------|--------|
| `description` field | **Main context window** | Always (all sessions) | Permanent budget consumption |
| `context`, `agent`, `allowed-tools`, etc. | Nowhere until invocation | On skill invocation | Only in the fork's context |
| SKILL.md body | Fork's context window | On skill invocation | Only in the fork's context |
| Supporting files | Fork's context window | When Read is called | Only in the fork's context |

**Key insight**: only `description` affects the main context. The rest of the frontmatter and the SKILL.md body live in the fork's context window (thanks to `context: fork`). Compacting descriptions has the highest ROI.

### Fields Analysis

| Field | Present In | Redundant? | Action |
|-------|-----------|------------|--------|
| `context: fork` | 32/32 | **NO** — without it skills run inline in main context, defeating all isolation | **KEEP** — non-negotiable |
| `agent: general-purpose` | 32/32 | Partially — it's the default for forked skills | **KEEP** — explicit is safer, low savings (~768 chars in fork, not in main context) |
| `description` | 32/32 | No, but too verbose | **SHORTEN** to <100 chars — high impact on main context budget |
| `allowed-tools` | 32/32 | No — varies per skill | **KEEP** — only 7 distinct combinations, but tool restrictions are essential |
| `argument-hint` | 32/32 | No | **FIX** 4 skills with unquoted YAML brackets |
| `disable-model-invocation` | 7/32 | No | **KEEP** — controls routing |

### Compaction Strategy

**Phase 1 (this refactoring — analysis skills only)**: Shorten descriptions of the 7 analysis skills being modified. Move "Do NOT use for" routing info to the SKILL.md body (first section after frontmatter). Target: <100 chars per description.

**Phase 2 (future — all 32 skills)**: Apply the same pattern to all remaining skills. Fix 4 YAML parse issues (unquoted brackets in `argument-hint`). Estimated savings: ~5,100 chars from descriptions = budget usage drops from 52% to ~20%.

### Example: Before/After

**Before** (rv-analyze-complexity, 257 chars):
```
Analyze code complexity and identify over-engineered code. Use when evaluating
code quality, finding refactoring targets, or assessing technical debt. Do NOT
use for: making changes (use /rv-refactor-simplify), full module analysis
(use /rv-analyze-module).
```

**After** (<100 chars):
```
Analyze code complexity and find refactoring targets in a module.
```

The "Do NOT use for" routing moves to the SKILL.md body, where it's only loaded into the fork's context when invoked — not permanently in the main window.

---

## 3. Naming Convention

```
rv-analyze-file-*         → file-scoped (L0 leaf)
rv-analyze-*              → module-scoped (L0 leaf or L1 orchestrator)
rv-analyze-module         → comprehensive module orchestrator (L1)
```

Alphabetical listing shows the hierarchy naturally:
```
rv-analyze-complexity           (module — iterates internally)
rv-analyze-dead-code            (module — iterates internally)
rv-analyze-dependencies         (module — inherently cross-file)
rv-analyze-file                 (file — comprehensive)
rv-analyze-file-complexity      (file — complexity only)
rv-analyze-file-dead-code       (file — dead code only)
rv-analyze-module               (module — orchestrator, calls above via Skill)
rv-impact-analyzer              (file/class — change impact, keep name as-is)
```

---

## 4. Redesigned Analysis Skill Tree

### Level 0 — Leaves (18 total, was 16)

No skill chains. Either file-scoped or module-scoped.

| Skill | Scope | Change | Target Tool Calls |
|-------|-------|--------|-------------------|
| rv-analyze-file | File | SLIM DOWN: compact 3 supporting files → 1 reference.md (optional read), inline essentials | ~15 |
| **rv-analyze-file-complexity** | File | **NEW**: complexity of ONE file (LOC, functions, nesting) | ~5 |
| **rv-analyze-file-dead-code** | File | **NEW**: dead code in ONE file (unused imports, functions, unreachable) | ~5 |
| rv-analyze-complexity | Module | REDESIGN: remove supporting files + sequential-thinking, internal iteration, MCP memory with git hash cache, aggregate report | ~20 |
| rv-analyze-dead-code | Module | REDESIGN: remove supporting files, internal iteration, MCP memory with git hash cache, aggregate report | ~15 |
| rv-analyze-dependencies | Module | REDESIGN: remove supporting files + sequential-thinking, MCP memory with git hash cache | ~15 |
| rv-impact-analyzer | File/class | KEEP as-is | ~15 |
| *(12 other leaves unchanged)* | Various | No change | — |

### Level 1 — Mid-level (10 total, was 9)

| Skill | Change | Chains To |
|-------|--------|-----------|
| rv-analyze-module | REDESIGN: calls 3 L0 skills via Skill | rv-analyze-{complexity, dead-code, dependencies} |
| rv-code-reviewer | UPDATE refs (file-scoped analysis) | rv-analyze-file-{complexity, dead-code}, rv-analyze-dependencies |
| rv-refactor-simplify | UPDATE ref (file-scoped analysis) | rv-analyze-file-complexity |
| rv-refactor-cleanup | No change — already uses module-scoped rv-analyze-dead-code | rv-analyze-dead-code |
| rv-refactor-extract | No change | rv-analyze-file, rv-analyze-dependencies |
| rv-security | No change | rv-analyze-file |
| rv-test-add | No change | rv-analyze-file, rv-test-run |
| rv-debug-regression | No change | rv-test-run |
| rv-qa-lint-fix | No change | rv-verify |

### Levels 2-4 — Unchanged

Doc generators, doc sync, and orchestrators remain the same. No orchestrator ref updates needed:

| Skill | Change |
|-------|--------|
| rv-refactor (L4) | No change — already uses module-scoped rv-analyze-complexity (refactoring is module-scoped) |
| rv-cleanup (L4) | No change — already calls module-scoped rv-analyze-{dead-code, complexity} |

### Consumer Update Corrections (vs. original plan)

| Skill | Original Plan | Correction | Reason |
|-------|--------------|------------|--------|
| rv-refactor-cleanup (L1) | UPDATE ref → file-dead-code | **KEEP** ref to rv-analyze-dead-code (module) | Cleanup operates on module scope; needs module-scoped dead-code analysis |
| rv-refactor (L4) | UPDATE ref → file-complexity | **KEEP** ref to rv-analyze-complexity (module) | Refactoring analysis is module-scoped |
| rv-code-reviewer (L1) | UPDATE refs | CORRECT — change to file-complexity and file-dead-code | Code review focuses on specific files |
| rv-refactor-simplify (L1) | UPDATE ref → file-complexity | CORRECT | Simplification is file-scoped |

### Maximum Fork Depth — Unchanged (5 levels)

```
Orchestrator (L4, fork 1)
  → rv-docs-sync (L3, fork 2)
    → rv-doc-generate-claude-md (L2, fork 3)
      → rv-analyze-module (L1, fork 4)
        → rv-analyze-complexity (L0, fork 5) — iterates internally, no further forks
```

---

## 5. Workflow Integration Check

| WORKFLOW.md Reference | Skill Used | After Redesign | Status |
|-----------------------|-----------|----------------|--------|
| Phase 0: Ideation | `/rv-analyze-module` | Orchestrates 3 forks instead of 3 redundant module scans | IMPROVED |
| Full SDD Phase 1 | `/rv-analyze-module`, `/rv-impact-analyzer`, `/rv-analyze-dependencies` | All work as before | OK |
| FF SDD Phase 1 | `/rv-analyze-file` | No change | OK |
| Quick Path Analyze | `/rv-analyze-dead-code` | Module-scoped, internal iteration | OK |
| Section 10: "Optimize performance" | `/rv-analyze-complexity` | Module-scoped, internal iteration | OK |
| Section 10: "Remove dead code" | `/rv-analyze-dead-code` | Module-scoped, internal iteration | OK |
| MCP memory cache pattern | All module-scoped L0 skills | NEW: skills check git hash cache before analysis, skip if unchanged | NEW |
| Section 9: Skill inventory | 5 analysis components | 7 analysis components (5 existing + 2 new) | UPDATE NEEDED |
| Section 9: Total count | 42 skills | 44 skills (42 + 2 new) | UPDATE NEEDED |

---

## 5.1. Insights from agente-documentador

The agente-documentador project (runtime documentation generation with Neo4j knowledge graph) uses patterns that validate and inform the rv-android skill redesign:

| Pattern in agente-documentador | Analog in rv-android |
|-------------------------------|---------------------|
| Atomic skills (~5-10k tokens, designed for 8B models with 64k context) | Target of ~50-80 lines for SKILL.md (Principle 4) |
| Externalized state in Neo4j between calls (avoids recalculation via hash-based checks) | MCP memory between skills with git hash cache (Section 2.1) |
| Entry points → workflow phases | Skills → WORKFLOW.md phases (Principle 6) |
| Internal iteration in analyze-* skills | Principle 5: no fork-per-file iteration |
| Task queue in SQLite (resumable after failures) | TodoWrite (no change needed) |
| OpenSpec manages workflow | Process layer (OpenSpec) → Execution layer (rv-*) |

---

## 5.2. Future: OpenSpec Schema Customization

**Not part of this refactoring** — noted as a future opportunity.

The OpenSpec schemas (`rv-sdd` and `quick-path`) have `instruction` fields for each artifact (proposal, specs, design, tasks, plan). These instructions could reference the new skills explicitly:

- Artifact `tasks` (rv-sdd): annotate implementation items with the appropriate skill (e.g., `/rv-analyze-file-complexity` for file-scoped analysis tasks)
- Artifact `design` (rv-sdd): instruct use of `/rv-analyze-module` for architectural understanding
- Artifact `plan` (quick-path): instruct use of the correct analysis skills by scope (file vs. module)

This would formalize the OpenSpec ↔ rv-* skill integration at the schema level (not just in WORKFLOW.md documentation).

**Track**: FF SDD (single-module: openspec schemas, design decision on which skills to reference)

---

## 6. Files to Create

| # | File | Description |
|---|------|-------------|
| 1 | `.claude/skills/rv-analyze-file-complexity/SKILL.md` | New file-scoped complexity skill (~50 lines) |
| 2 | `.claude/skills/rv-analyze-file-dead-code/SKILL.md` | New file-scoped dead code skill (~50 lines) |

## 7. Files to Modify

| # | File | Change |
|---|------|--------|
| 1 | `.claude/skills/rv-analyze-complexity/SKILL.md` | Redesign: merge 3 supporting files → 1 reference.md, remove Guiding Principles (9 paragraphs → 3 lines inline), remove sequential-thinking, redesign MCP memory schema (entity naming + git hash cache), module-scoped internal iteration, **compact description to <100 chars**, move routing to body, slim to ~60 lines |
| 2 | `.claude/skills/rv-analyze-dead-code/SKILL.md` | Redesign: merge 3 supporting files → 1 reference.md, redesign MCP memory schema (entity naming + git hash cache), module-scoped internal iteration, **compact description to <100 chars**, move routing to body, slim to ~60 lines |
| 3 | `.claude/skills/rv-analyze-dependencies/SKILL.md` | Redesign: merge 3 supporting files → 1 reference.md, remove sequential-thinking, redesign MCP memory schema (entity naming + git hash cache), **compact description to <100 chars**, move routing to body, slim to ~60 lines |
| 4 | `.claude/skills/rv-analyze-module/SKILL.md` | Redesign: remove 4 Modeling Perspectives (Steps 5-8), simplify to: check cache → call 3 L0 via Skill → own analysis (directory + components + tests) → synthesize → persist, **compact description to <100 chars**, move routing to body |
| 5 | `.claude/skills/rv-analyze-file/SKILL.md` | Slim: compact 3 supporting files → 1 reference.md (optional read), change "Read before starting" to "Consult reference.md for detailed patterns if needed", **compact description to <100 chars**, move routing to body |
| 6 | `.claude/skills/rv-code-reviewer/SKILL.md` | Update refs: line 66 rv-analyze-complexity → rv-analyze-file-complexity, line 68 rv-analyze-dead-code → rv-analyze-file-dead-code, **compact description to <100 chars** |
| 7 | `.claude/skills/rv-refactor-simplify/SKILL.md` | Update ref: line 52 rv-analyze-complexity → rv-analyze-file-complexity, **compact description to <100 chars** |
| 8 | `docs/WORKFLOW.md` | Update Section 9 inventory (add 2 new skills, update count 42→44) |
| 9 | `CLAUDE.md` | Update skill count (42→44) |
| 10 | `docs/20260218_skills.md` | Update dependency graph, add new skills to verification plan |
| 11 | `docs/RELATORIO_SKILLS.md` | Record findings F2 + F3 (frontmatter analysis) |

**Total: 2 files to create + 11 files to modify = 13 files**

**Note**: frontmatter compaction (Phase 1) applies to the 7 analysis skills already being modified (rows 1-7). Phase 2 (remaining 25+ skills) is a separate future task — see Section 2.2.

---

## 8. Verification

After all changes:

1. `/rv-analyze-file-complexity modules/rv-android-core/src/rv_android_core/constants.py` → ONE file, <7 tool calls
2. `/rv-analyze-file-dead-code modules/rv-android-core/src/rv_android_core/constants.py` → ONE file, <7 tool calls
3. `/rv-analyze-complexity rv-android-core` → module, internal iteration, ~20 tool calls (down from 49)
4. `/rv-analyze-dead-code rv-android-core` → module, internal iteration, ~15 tool calls
5. `/rv-analyze-module rv-android-core` → 3 Skill forks + own modeling, ~10 own tool calls + 3 forks
6. MCP memory cache: re-run `/rv-analyze-complexity rv-android-core` immediately after — should hit cache and return in <5 tool calls
7. Frontmatter check: run `/context` and verify no "excluded skills" warnings — description budget should be well under 16,000 chars
8. Resume Batch 1 from L0.2 with corrected skills

---

## 9. Execution Order

1. Create rv-analyze-file-complexity (new skill, compact description from start)
2. Create rv-analyze-file-dead-code (new skill, compact description from start)
3. Redesign rv-analyze-complexity (module scope, internal iteration, MCP memory, remove supporting files + sequential-thinking, compact description)
4. Redesign rv-analyze-dead-code (module scope, internal iteration, MCP memory, remove supporting files, compact description)
5. Redesign rv-analyze-dependencies (remove supporting files + sequential-thinking, MCP memory, compact description)
6. Redesign rv-analyze-module (Skill-based orchestration, remove modeling perspectives, compact description)
7. Slim rv-analyze-file (compact supporting files → 1 reference.md, compact description)
8. Update 2 consumer skills (code-reviewer, refactor-simplify — update refs + compact descriptions)
9. Update docs (WORKFLOW.md, CLAUDE.md, verification plan, report)
10. Verify with test invocations (including MCP memory cache hit test + `/context` budget check)
11. Resume Batch 1
12. (Future) Phase 2: compact descriptions of remaining 25+ skills, fix 4 YAML parse issues
