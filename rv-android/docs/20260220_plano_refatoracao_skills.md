# Plan: Redesign Analysis Skill Tree — Scope Correction + Verification

**Date**: 2026-02-20
**Author**: Pedro Henrique Teixeira Costa
**Status**: PLANNED
**Origin**: Findings F1/F2 during skills verification (Batch 1)
**Results**: `docs/RELATORIO_SKILLS.md`

---

## 1. Context

During skills verification (Batch 1), we discovered that three "leaf" skills (rv-analyze-complexity, rv-analyze-dead-code, rv-analyze-dependencies) operate at **module scope** despite being classified as Level 0 leaves. A leaf node analyzing an entire module (46 files, 49 tool calls) is architecturally wrong — leaves should be file-scoped, fast, and focused. Module-level orchestration belongs to higher-level skills.

Root cause: skills were designed as standalone tools, not as composable building blocks for the skill chain hierarchy.

Secondary root cause: mandatory supporting file reads (3 checklists per skill) add ~9-12 tool calls before any analysis begins. This is the primary driver behind F1 (30 tool calls for a single 128-line file).

This document unifies the analysis skill tree redesign with the bottom-up verification plan (originally `docs/20260218_skills.md`). The verification is Phase 3 of the broader skills/subagents work (Phase 1: empirical validation in `hello-claude-code`, T1-T11; Phase 2: Solution C — `docs/20260217_skills_subagents_analysis.md`). The redesign batches (1R-10R) are intercalated with the verification batches to validate each skill immediately after modification.

### Evidence

| Skill | Classification | Actual Scope | Tool Calls | Problem |
|-------|---------------|--------------|------------|---------|
| rv-analyze-file | L0 leaf | Single file | 30 | Correct scope, but exhaustive (8-dimension checklist + 3 supporting file reads) |
| rv-analyze-complexity | L0 leaf | Entire module | 49 | Module-wide scan for a "leaf" + 3 supporting file reads + sequential-thinking overhead |
| rv-analyze-dead-code | L0 leaf | Entire module | (untested) | Module-wide scan for a "leaf" + 3 supporting file reads |
| rv-analyze-dependencies | L0 leaf | Module or all | (untested) | Module-wide scan for a "leaf" + 3 supporting file reads + sequential-thinking overhead |
| rv-analyze-module | L1 mid-level | Module | (untested) | Calls three module-scoped "leaves" — redundant orchestration + 4 modeling checklists (Steps 5-8, 73 lines + 4 external checklist files) |

**Pre-existing mismatch**: rv-code-reviewer already passes file-scoped args (`args="<file-path>"`) to module-scoped skills (rv-analyze-complexity, rv-analyze-dead-code). This latent scope mismatch is additional evidence for the redesign — the new file-scoped variants (`rv-analyze-file-complexity`, `rv-analyze-file-dead-code`) resolve it.

---

## 2. Design Principles

1. **Leaf = file scope, fast, cheap**. Module scope = orchestrator with internal iteration.
2. **Naming convention**: `rv-analyze-file-*` for file-scoped variants. `rv-analyze-*` (without `file`) for module-scoped.
3. **Always fork** (`context: fork`): every skill gets its own context window.
4. **Minimize tokens**: lean SKILL.md (~50-80 lines), no checklists/supporting files unless essential, no MCP cache/memory overhead.
5. **No fork-per-file iteration in module-scoped skills**: iterate internally (Glob+Read), not by forking to file-level skills for every file (too expensive: 46 forks × ~30s each). File-scoped skills may be invoked individually by consumers for targeted analysis (e.g., rv-code-reviewer calling rv-analyze-file-complexity for 1-3 specific files).
6. **Seamless workflow integration**: naming and scope must align with WORKFLOW.md usage patterns (Phase 0, Explore, Quick Path Analyze).
7. **Consolidate supporting files**: the knowledge in checklists/templates is valuable and must be preserved — not deleted. Approach: merge 3 separate files into 1 consolidated `reference.md` per skill (preserving all content), inline only the essential thresholds (~5 lines) in SKILL.md, and change instruction to "Read reference.md before starting analysis". This reduces mandatory reads from 3 to **1** while keeping all accumulated knowledge accessible — the consolidated file contains checklists that **standardize** analyses, so reading it is mandatory (without it, each analysis would be inconsistent). Supporting files that prove genuinely unused after verification can be removed later. This addresses the primary root cause of F1.
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
- Before analysis: compare stored hash with scope-specific git command:
  - Module-scoped skills: `git log -1 --format=%h -- modules/<module>/`
  - File-scoped skills: `git log -1 --format=%h -- <file-path>`
- This ensures the cache is only invalidated when the analyzed scope actually changes (not on every unrelated commit, as `git rev-parse --short HEAD` would)
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

**Clarification**: `rv-analyze-module` is the sole L1 orchestrator in this group. All other `rv-analyze-*` (without `file`) — `rv-analyze-complexity`, `rv-analyze-dead-code`, `rv-analyze-dependencies` — are L0 leaves with internal iteration. The naming convention does not encode the L0/L1 distinction; the list above is the authoritative reference.

---

## 4. Redesigned Analysis Skill Tree

### Level 0 — Leaves (18 total, was 16)

No skill chains. Either file-scoped or module-scoped.

| Skill | Scope | Change | Target Tool Calls |
|-------|-------|--------|-------------------|
| rv-analyze-file | File | SLIM DOWN: consolidate 3 supporting files → 1 reference.md (mandatory read), inline essentials | ~15 |
| **rv-analyze-file-complexity** | File | **NEW**: complexity of ONE file (LOC, functions, nesting) | ~5 |
| **rv-analyze-file-dead-code** | File | **NEW**: dead code in ONE file (unused imports, functions, unreachable) | ~5 |
| rv-analyze-complexity | Module | REDESIGN: remove supporting files + sequential-thinking, internal iteration, MCP memory with git hash cache, aggregate report | ~20 |
| rv-analyze-dead-code | Module | REDESIGN: remove supporting files, internal iteration, MCP memory with git hash cache, aggregate report | ~15 |
| rv-analyze-dependencies | Module | REDESIGN: remove supporting files + sequential-thinking, MCP memory with git hash cache | ~15 |
| rv-impact-analyzer | File/class | KEEP as-is | ~15 |
| *(12 other leaves unchanged)* | Various | No change | — |

### Level 1 — Mid-level (9 total, unchanged)

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
| 1 | `.claude/skills/rv-analyze-file-complexity/SKILL.md` | New file-scoped complexity skill (~50 lines), no supporting files (lightweight, ~5 tool calls) |
| 2 | `.claude/skills/rv-analyze-file-dead-code/SKILL.md` | New file-scoped dead code skill (~50 lines), no supporting files (lightweight, ~5 tool calls) |
| 3 | `.claude/skills/rv-analyze-complexity/reference.md` | Consolidated from 3 supporting files (checklists + templates). Original files deleted after consolidation |
| 4 | `.claude/skills/rv-analyze-dead-code/reference.md` | Consolidated from 3 supporting files. Original files deleted after consolidation |
| 5 | `.claude/skills/rv-analyze-dependencies/reference.md` | Consolidated from 3 supporting files. Original files deleted after consolidation |
| 6 | `.claude/skills/rv-analyze-file/reference.md` | Consolidated from 3 supporting files. Original files deleted after consolidation |
| 7 | `.claude/skills/rv-analyze-module/reference.md` | Consolidated from 4 modeling checklist files. Original files deleted after consolidation |

## 7. Files to Modify

| # | File | Change |
|---|------|--------|
| 1 | `.claude/skills/rv-analyze-complexity/SKILL.md` | Redesign: merge 3 supporting files → 1 reference.md, remove Guiding Principles (9 paragraphs → 3 lines inline), remove sequential-thinking, redesign MCP memory schema (entity naming + git hash cache), module-scoped internal iteration, **compact description to <100 chars**, move routing to body, slim to ~60 lines |
| 2 | `.claude/skills/rv-analyze-dead-code/SKILL.md` | Redesign: merge 3 supporting files → 1 reference.md, redesign MCP memory schema (entity naming + git hash cache), module-scoped internal iteration, **compact description to <100 chars**, move routing to body, slim to ~60 lines |
| 3 | `.claude/skills/rv-analyze-dependencies/SKILL.md` | Redesign: merge 3 supporting files → 1 reference.md, remove sequential-thinking, redesign MCP memory schema (entity naming + git hash cache), **compact description to <100 chars**, move routing to body, slim to ~60 lines |
| 4 | `.claude/skills/rv-analyze-module/SKILL.md` | Redesign: remove Steps 5-8 (73 lines of in-SKILL.md modeling instructions) + delete 4 checklist files (context-modeling.md, interaction-modeling.md, structural-modeling.md, behavioral-modeling.md), simplify to: check cache → call 3 L0 via Skill → own analysis (directory + components + tests) → synthesize → persist, **compact description to <100 chars**, move routing to body |
| 5 | `.claude/skills/rv-analyze-file/SKILL.md` | Slim: consolidate 3 supporting files → 1 reference.md (mandatory read), change to "Read reference.md before starting analysis", **compact description to <100 chars**, move routing to body |
| 6 | `.claude/skills/rv-code-reviewer/SKILL.md` | Update refs: line 66 rv-analyze-complexity → rv-analyze-file-complexity, line 68 rv-analyze-dead-code → rv-analyze-file-dead-code, **compact description to <100 chars** |
| 7 | `.claude/skills/rv-refactor-simplify/SKILL.md` | Update ref: line 52 rv-analyze-complexity → rv-analyze-file-complexity, **compact description to <100 chars** |
| 8 | `docs/WORKFLOW.md` | Update Section 9 inventory (add 2 new skills, update count 42→44) |
| 9 | `CLAUDE.md` | Update skill count (42→44) |
| 10 | `docs/20260218_skills.md` | Add redirect note (content merged into this document) |
| 11 | `docs/RELATORIO_SKILLS.md` | Record findings F2 + F3 (frontmatter analysis) |

**Total: 7 files to create + 11 files to modify + ~16 files to delete (original supporting files) = ~34 file operations**

**Note**: frontmatter compaction (Phase 1) applies to the 7 analysis skills already being modified (rows 1-7). Phase 2 (remaining 25+ skills) is a separate future task — see Section 2.2. File-scoped variants (`rv-analyze-file-complexity`, `rv-analyze-file-dead-code`) operate WITHOUT supporting files — they are lightweight (~5 tool calls) and don't need reference material.

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
7. Slim rv-analyze-file (consolidate supporting files → 1 reference.md, compact description)
8. Update 2 consumer skills (code-reviewer, refactor-simplify — update refs + compact descriptions)
9. Update docs (WORKFLOW.md, CLAUDE.md, verification plan, report)
10. Verify with test invocations (including MCP memory cache hit test + `/context` budget check)
11. Resume Batch 1
12. (Future) Phase 2: compact descriptions of remaining 25+ skills, fix 4 YAML parse issues

---

# PART 2: VERIFICATION

---

## 10. Skill Inventory

### 10.1 Counts

| Category | Count | Description |
|----------|------:|-------------|
| rv-* leaf skills | 18 | No Skill tool in allowed-tools; cannot invoke other skills |
| rv-* mid-level skills | 9 | Invoke only leaf skills (Level 0) |
| rv-* doc generators | 2 | Invoke mid-level skills (Level 1) |
| rv-* doc sync | 1 | Invokes doc generators (Level 2) |
| rv-* orchestrators | 4 | Invoke across all levels + rv-code-reviewer |
| **rv-* subtotal** | **34** | **(was 32 — added rv-analyze-file-complexity, rv-analyze-file-dead-code)** |
| OpenSpec skills | 10 | External tooling, inline context (not forked) |
| **Total** | **44** | |

### 10.2 Common Properties

All 34 rv-* skills share:
- `context: fork` — runs as isolated subagent (separate context window)
- `agent: general-purpose` — uses the general-purpose agent type
- SKILL.md in `.claude/skills/<name>/SKILL.md`

Seven skills additionally have `disable-model-invocation: true` (can only be invoked explicitly via `/name`, not auto-triggered): rv-planning, rv-risk, rv-retrospective, rv-release, rv-security, rv-refactor-simplify, rv-refactor-extract.

---

## 11. Dependency Graph

The graph shows which skills invoke other skills via the Skill tool. A skill at Level N only invokes skills at Level N-1 or below. The verification order follows this graph bottom-up.

```
Level 0 — Leaf skills (18)
│
│  rv-analyze-file               Read, Grep, Glob
│  rv-analyze-file-complexity    Read, Grep, Glob                          (NEW)
│  rv-analyze-file-dead-code     Read, Grep, Glob                          (NEW)
│  rv-analyze-complexity         Read, Grep, Glob, Bash
│  rv-analyze-dependencies       Read, Grep, Glob, Bash
│  rv-analyze-dead-code          Read, Grep, Glob, Bash
│  rv-impact-analyzer            Grep, Glob, Read, Bash
│  rv-refactor-constants         Read, Grep, Glob, Edit, Write
│  rv-qa-lint                    Read, Bash
│  rv-test-run                   Read, Bash
│  rv-verify                     Bash, Read, Glob
│  rv-doc-code                   Read, Grep, Glob, Edit, Write, Bash
│  rv-doc-readme                 Read, Grep, Glob, Write, Bash
│  rv-doc-adr                    Read, Grep, Glob, Write, Bash, AskUserQuestion
│  rv-planning*                  Read, Grep, Glob, Bash, AskUserQuestion
│  rv-risk*                      Read, Grep, Glob, Bash, AskUserQuestion
│  rv-retrospective*             Read, Grep, Glob, Bash
│  rv-release*                   Read, Bash, Glob, Edit, Write, AskUserQuestion
│
│  (* = disable-model-invocation: true)
│
├─── Level 1 — Mid-level skills (9)
│    │
│    │  rv-analyze-module        → rv-analyze-dependencies
│    │                           → rv-analyze-complexity
│    │                           → rv-analyze-dead-code
│    │
│    │  rv-code-reviewer         → rv-analyze-file-complexity    (conditional, updated)
│    │                           → rv-analyze-dependencies       (conditional)
│    │                           → rv-analyze-file-dead-code     (conditional, updated)
│    │
│    │  rv-debug-regression      → rv-test-run
│    │
│    │  rv-qa-lint-fix           → rv-verify
│    │
│    │  rv-refactor-cleanup      → rv-analyze-dead-code
│    │
│    │  rv-refactor-simplify*    → rv-analyze-file-complexity    (updated)
│    │
│    │  rv-refactor-extract*     → rv-analyze-file
│    │                           → rv-analyze-dependencies
│    │
│    │  rv-security*             → rv-analyze-file
│    │
│    │  rv-test-add              → rv-analyze-file
│    │                           → rv-test-run
│    │
│    ├─── Level 2 — Documentation generators (2)
│    │    │
│    │    │  rv-doc-architecture      → rv-analyze-module (Level 1)
│    │    │  rv-doc-generate-claude-md → rv-analyze-module (Level 1)
│    │    │
│    │    ├─── Level 3 — Documentation sync (1)
│    │    │    │
│    │    │    │  rv-docs-sync → rv-doc-generate-claude-md (Level 2)
│    │    │    │               → rv-doc-architecture       (Level 2)
│    │    │    │
│    │    │    ├─── Level 4 — Orchestrators (4)
│    │    │    │
│    │    │    │  rv-refactor  → rv-impact-analyzer      (L0)
│    │    │    │               → rv-analyze-complexity    (L0)
│    │    │    │               → rv-analyze-dependencies  (L0)
│    │    │    │               → rv-verify                (L0)
│    │    │    │               → rv-docs-sync             (L3)
│    │    │    │               → rv-code-reviewer         (L1)
│    │    │    │
│    │    │    │  rv-feature   → rv-analyze-module        (L1)
│    │    │    │               → rv-analyze-dependencies  (L0)
│    │    │    │               → rv-analyze-file          (L0)
│    │    │    │               → rv-verify                (L0)
│    │    │    │               → rv-docs-sync             (L3)
│    │    │    │               → rv-code-reviewer         (L1)
│    │    │    │
│    │    │    │  rv-tdd       → rv-analyze-file          (L0)
│    │    │    │               → rv-analyze-dependencies  (L0)
│    │    │    │               → rv-test-run              (L0)
│    │    │    │               → rv-verify                (L0)
│    │    │    │               → rv-code-reviewer         (L1)
│    │    │    │
│    │    │    │  rv-cleanup   → rv-analyze-dead-code     (L0)
│    │    │    │               → rv-analyze-dependencies  (L0)
│    │    │    │               → rv-analyze-complexity    (L0)
│    │    │    │               → rv-docs-sync             (L3)
│    │    │    │               → rv-code-reviewer         (L1)
```

### 11.1 Maximum Nesting Depth

The deepest chain in practice:

```
Orchestrator (L4, fork level 1)
  → rv-docs-sync (L3, fork level 2)
    → rv-doc-generate-claude-md (L2, fork level 3)
      → rv-analyze-module (L1, fork level 4)
        → rv-analyze-dependencies (L0, fork level 5)
```

This is 5 levels of fork nesting. Empirically validated in hello-claude-code (T11: 5 levels, ~3-4s per level). Total latency overhead for the deepest chain: ~15-20s.

However, the typical orchestrator path is shallower:

```
Orchestrator (L4, fork level 1)
  → rv-code-reviewer (L1, fork level 2)
    → rv-analyze-file-complexity (L0, fork level 3)
```

This is 3 levels — the most common case.

---

## 12. Verification Procedure

### 12.1 Test Targets

**Levels 0-3**: Use **rv-android-core** as the primary target:
- Smallest module, simplest structure
- Has tests (`modules/rv-android-core/tests/`)
- Source at `modules/rv-android-core/src/rv_android_core/`
- Target file for single-file skills: `src/rv_android_core/constants.py`

**Level 4 (Orchestrators)**: Use **rv-agent** as the target:
- Most substantial module (~50+ files), exercises full analysis/planning phases
- Orchestrators like rv-refactor and rv-feature are designed for complex modules and may not exercise their full workflow on a trivial target like rv-android-core
- Source at `modules/rv-agent/src/rv_agent/`

### 12.2 Tracing Infrastructure

Every skill invocation produces events in `output/trace.log` (JSONL format):
- `SUBAGENT_START` — confirms the skill was forked
- `PRE_TOOL_USE` — confirms tool calls within the skill
- `SUBAGENT_STOP` — confirms clean exit
- `POST_TOOL_USE_FAILURE` — indicates errors

For chained skills, nested `SUBAGENT_START`/`SUBAGENT_STOP` pairs appear inside the parent's span.

### 12.3 Pass Criteria

A skill **passes** if:
1. It launches (SUBAGENT_START in trace.log)
2. It performs meaningful work (PRE_TOOL_USE events for expected tools)
3. It exits cleanly (SUBAGENT_STOP in trace.log)
4. Its output is coherent and relevant to the target
5. For chained skills: nested SUBAGENT events appear for child skills

A skill **fails** if:
- It does not launch (no SUBAGENT_START)
- It crashes or hangs
- It references missing templates/checklists (file not found errors)
- It attempts to invoke a non-existent skill
- Its output is empty or incoherent

### 12.4 Test Procedure Per Skill

```
1. Note the current line count of output/trace.log
2. Invoke: /skill-name <args>
3. Wait for completion
4. Examine new trace.log entries
5. Evaluate output quality
6. Record result in docs/RELATORIO_SKILLS.md
```

### 12.5 Infrastructure Verification (Level 0 Prerequisites)

Before testing any skills, verify the tracing infrastructure is operational:

| ID | Test | Action | Pass Criteria |
|----|------|--------|---------------|
| V0.0 | Hook files exist | `ls .claude/settings.json .claude/hooks/trace_logger.py` | Both files exist |
| V0.1 | trace.log created on session start | Check `output/trace.log` exists after session start | File exists with SESSION_START event |
| V0.2 | SUBAGENT events captured | Invoke any leaf skill; check trace.log | SUBAGENT_START and SUBAGENT_STOP appear |
| V0.3 | PRE_TOOL_USE events captured | Same invocation as V0.2 | PRE_TOOL_USE entries for tools used by skill |
| V0.4 | Context budget | Run `/context` after session start | No "skills excluded due to budget" warnings |
| V0.5 | MCP memory server | Invoke `mcp__memory__search_nodes` with a test query | Server responds (success or empty results — not connection error) |
| V0.6 | MCP sequential-thinking server | Invoke `mcp__sequential-thinking__sequentialthinking` with a trivial thought | Server responds (not connection error) |

**Pre-condition**: Hooks must be re-enabled from `hooks_locked/` before any testing (see Section 16). MCP servers (memory, sequential-thinking) must be running for skills that depend on them — V0.5/V0.6 verify this.

### 12.6 Static Checks (Level 1 Prerequisites)

Static checks that don't require skill invocation:

| ID | Test | Action | Pass Criteria |
|----|------|--------|---------------|
| V1.1 | All 34 SKILL.md files exist | `ls .claude/skills/rv-*/SKILL.md \| wc -l` | Count = 34 |
| V1.2 | All have `context: fork` | `grep -l "context: fork" .claude/skills/rv-*/SKILL.md \| wc -l` | Count = 34 |
| V1.3 | 7 have `disable-model-invocation` | `grep -l "disable-model-invocation: true" .claude/skills/rv-*/SKILL.md \| wc -l` | Count = 7 |
| V1.4 | No stale agent files | `ls .claude/agents/ 2>/dev/null` | Empty or not found |
| V1.5 | No `Task` tool in allowed-tools | `grep -l "Task" .claude/skills/rv-*/SKILL.md` (check frontmatter only) | Zero matches in `allowed-tools` |
| V1.6 | All chain targets exist | Cross-ref Section 11 graph targets with actual SKILL.md files | All targets present |
| V1.7 | SKILL.md size audit | `wc -l .claude/skills/rv-*/SKILL.md` | Note files >500 lines (finding, not blocker) |

### 12.7 Incremental Report

Results from each batch are recorded incrementally in `docs/RELATORIO_SKILLS.md`. This report is the final verification artifact — consolidating results, observations, and conclusions as each batch is executed.

**Protocol**: After each batch, Claude updates the report with that batch's results before proceeding to the next.

---

## 13. Execution Plan per Level

### 13.1 Level 0 — Leaf Skills (18 skills)

These have no dependencies on other skills. They can be tested in any order.

| # | Skill | Invocation | What to Verify |
|---|-------|-----------|----------------|
| L0.1 | rv-analyze-file | `/rv-analyze-file modules/rv-android-core/src/rv_android_core/constants.py` | Produces file structure analysis |
| L0.2 | rv-analyze-complexity | `/rv-analyze-complexity rv-android-core` | Produces complexity metrics |
| L0.3 | rv-analyze-dependencies | `/rv-analyze-dependencies rv-android-core` | Maps module dependencies |
| L0.4 | rv-analyze-dead-code | `/rv-analyze-dead-code rv-android-core` | Identifies unused code |
| L0.5 | rv-impact-analyzer | `/rv-impact-analyzer rv-android-core` | Analyzes change impact |
| L0.6 | rv-refactor-constants | `/rv-refactor-constants modules/rv-android-core/src/rv_android_core/constants.py` | Identifies magic values |
| L0.7 | rv-qa-lint | `/rv-qa-lint rv-android-core` | Runs linter, reports issues |
| L0.8 | rv-test-run | `/rv-test-run rv-android-core` | Runs pytest, reports results |
| L0.9 | rv-verify | `/rv-verify rv-android-core` | Runs tests + lint + type checks |
| L0.10 | rv-doc-code | `/rv-doc-code modules/rv-android-core/src/rv_android_core/constants.py` | Generates code documentation |
| L0.11 | rv-doc-readme | `/rv-doc-readme rv-android-core` | Generates README.md |
| L0.12 | rv-doc-adr | `/rv-doc-adr "test decision for verification"` | Creates ADR document |
| L0.13 | rv-planning | `/rv-planning rv-android-core` | Generates planning analysis |
| L0.14 | rv-risk | `/rv-risk rv-android-core` | Generates risk assessment |
| L0.15 | rv-retrospective | `/rv-retrospective rv-android-core` | Generates retrospective |
| L0.16 | rv-release | `/rv-release rv-android-core` | Checks release readiness |
| L0.17 | rv-analyze-file-complexity | `/rv-analyze-file-complexity modules/rv-android-core/src/rv_android_core/constants.py` | Produces file complexity metrics **(NEW)** |
| L0.18 | rv-analyze-file-dead-code | `/rv-analyze-file-dead-code modules/rv-android-core/src/rv_android_core/constants.py` | Identifies dead code in file **(NEW)** |

**Special notes:**
- L0.12 (rv-doc-adr): Will prompt for decision details via AskUserQuestion — answer with test data
- L0.13-L0.16: Have `disable-model-invocation: true` — must invoke explicitly, will not auto-trigger
- L0.16 (rv-release): May need context about what release means for rv-android-core; observe if it handles gracefully
- L0.17-L0.18: **New skills** — tested as part of Batches 1R-2R (refactoring batches)

### 13.2 Level 1 — Mid-Level Skills (9 skills)

These invoke Level 0 skills. Test only after Level 0 is confirmed working.

| # | Skill | Invocation | Chains To | What to Verify |
|---|-------|-----------|-----------|----------------|
| L1.1 | rv-analyze-module | `/rv-analyze-module rv-android-core` | rv-analyze-{dependencies, complexity, dead-code} | Produces comprehensive module analysis; trace.log shows 3 nested SUBAGENT pairs |
| L1.2 | rv-code-reviewer | `/rv-code-reviewer rv-android-core` | rv-analyze-file-{complexity, dead-code}, rv-analyze-dependencies (conditional, **updated**) | Produces code review; may or may not chain depending on findings |
| L1.3 | rv-debug-regression | `/rv-debug-regression b652652a` | rv-test-run | Investigates commit; trace.log shows nested SUBAGENT for test run |
| L1.4 | rv-qa-lint-fix | `/rv-qa-lint-fix rv-android-core` | rv-verify | Auto-fixes lint issues then verifies; trace.log shows nested SUBAGENT |
| L1.5 | rv-refactor-cleanup | `/rv-refactor-cleanup rv-android-core` | rv-analyze-dead-code | Identifies cleanup targets; trace.log shows nested SUBAGENT |
| L1.6 | rv-refactor-simplify | `/rv-refactor-simplify rv-android-core` | rv-analyze-file-complexity (**updated**) | Identifies simplification targets |
| L1.7 | rv-refactor-extract | `/rv-refactor-extract modules/rv-android-core/src/rv_android_core/constants.py` | rv-analyze-{file, dependencies} | Identifies extraction targets |
| L1.8 | rv-security | `/rv-security modules/rv-android-core/src/rv_android_core/constants.py` | rv-analyze-file | Security analysis of file |
| L1.9 | rv-test-add | `/rv-test-add modules/rv-android-core/src/rv_android_core/constants.py` | rv-analyze-file, rv-test-run | Suggests/creates tests |

**Special notes:**
- L1.2 (rv-code-reviewer): This is the key skill changed in Solution C. Verify it works both standalone and when chained from orchestrators (Level 4).
- L1.3 (rv-debug-regression): Uses commit SHA `b652652a` (recent fix for DynamicWTG type mismatch).
- L1.4 (rv-qa-lint-fix): May make changes — review before accepting.
- L1.5-L1.7: May propose changes — verify they just analyze, don't apply without confirmation.

### 13.3 Level 2 — Documentation Generators (2 skills)

These invoke rv-analyze-module (Level 1), which itself invokes 3 Level 0 skills. Test depth: up to 3 fork levels.

| # | Skill | Invocation | Chains To | What to Verify |
|---|-------|-----------|-----------|----------------|
| L2.1 | rv-doc-architecture | `/rv-doc-architecture rv-android-core` | rv-analyze-module → rv-analyze-{deps, complexity, dead-code} | Generates architecture.md; trace.log shows 2 levels of nesting |
| L2.2 | rv-doc-generate-claude-md | `/rv-doc-generate-claude-md rv-android-core` | rv-analyze-module → rv-analyze-{deps, complexity, dead-code} | Generates CLAUDE.md; trace.log shows 2 levels of nesting |

**Special notes:**
- Both skills write files (architecture.md and CLAUDE.md respectively). Review generated content before committing.
- These validate that 3-level nesting works: skill → rv-analyze-module → rv-analyze-*.

### 13.4 Level 3 — Documentation Sync (1 skill)

Invokes both Level 2 skills. Test depth: up to 4 fork levels.

| # | Skill | Invocation | Chains To | What to Verify |
|---|-------|-----------|-----------|----------------|
| L3.1 | rv-docs-sync | `/rv-docs-sync rv-android-core` | rv-doc-generate-claude-md, rv-doc-architecture (each → rv-analyze-module → rv-analyze-*) | Syncs all docs; trace.log shows 3+ levels of nesting |

**Special notes:**
- This is the deepest non-orchestrator chain. Validates 4-level nesting in practice.
- May take significant time due to cascading skill invocations.

### 13.5 Level 4 — Orchestrators (4 skills)

These are the full workflow skills. Each invokes multiple skills across all levels, including rv-code-reviewer (the Solution C target). These are the most important tests.

| # | Skill | Invocation | Key Chains | What to Verify |
|---|-------|-----------|------------|----------------|
| L4.1 | rv-refactor | `/rv-refactor rv-agent` | impact-analyzer, analyze-{complexity, dependencies}, verify, docs-sync, code-reviewer | Full refactoring workflow; code review via Skill tool (Solution C) |
| L4.2 | rv-feature | `/rv-feature rv-agent` | analyze-{module, dependencies, file}, verify, docs-sync, code-reviewer | Full feature workflow |
| L4.3 | rv-tdd | `/rv-tdd rv-agent` | analyze-{file, dependencies}, test-run, verify, code-reviewer | Full TDD workflow |
| L4.4 | rv-cleanup | `/rv-cleanup rv-agent` | analyze-{dead-code, dependencies, complexity}, docs-sync, code-reviewer | Full cleanup workflow |

**Special notes:**
- **Target: rv-agent** (not rv-android-core) — orchestrators need a substantial module to exercise their full analysis/planning phases.
- Orchestrators will make real changes. `git checkout .` after each batch to discard (artifacts policy, Section 16).
- The critical verification point: does rv-code-reviewer get invoked successfully via `Skill tool: skill="rv-code-reviewer"`? Before Solution C, this chain was broken (Task tool absent in forks).
- Each orchestrator has AskUserQuestion in allowed-tools — they may ask for confirmation before proceeding.
- These tests are time-intensive (10-15 min each). Testing one orchestrator thoroughly may be sufficient if the pattern is the same for all four.

---

## 14. Known Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Hooks disabled | All tests fail (no trace.log generated) | Re-enable from `.claude/hooks_locked/` before testing; verify with V0.0 |
| Orchestrators make unintended changes | Modified source files | `git checkout .` after each batch to discard changes; review before accepting |
| Deep nesting timeout | Skills at Level 3-4 take too long | Set timeout expectations (~15-20s for deepest chain); accept latency |
| Skills reference missing templates | Skill fails with file-not-found | Identify missing files, create stubs or fix references |
| rv-doc-adr / rv-release prompt for interactive input | Skill blocks waiting for user | Provide test answers via AskUserQuestion responses |
| AskUserQuestion visibility | Interactive skills may appear to "hang" waiting for input | AskUserQuestion added to PreToolUse/PostToolUse matchers in settings.json; trace.log now captures these calls |
| trace.log grows large | Hard to parse | Use `grep` with timestamp ranges to isolate test windows |

---

## 15. Success Criteria

The verification is successful when:

1. **All 34 rv-* skills invoked** — every row in the RELATORIO has a status
2. **Zero unexpected failures** — all FAIL entries have a known cause and a fix plan
3. **Skill chaining works** — Level 1+ skills show nested SUBAGENT events in trace.log
4. **Solution C confirmed** — at least one orchestrator (Level 4) successfully chains to rv-code-reviewer via Skill tool
5. **Maximum nesting depth confirmed** — rv-docs-sync or an orchestrator shows 4+ fork levels in trace.log
6. **Trace infrastructure validated** — output/trace.log correctly captures all 8 configured event types (of 15 available in Claude Code)

---

## 16. Pre-conditions (do once, before first batch)

1. **Re-enable hooks** (from `.claude/hooks_locked/`):
   ```bash
   cp .claude/hooks_locked/settings.json .claude/settings.json
   mkdir -p .claude/hooks
   cp .claude/hooks_locked/trace_logger.py .claude/hooks/trace_logger.py
   ```
   Then **restart the Claude Code session** (hooks load at startup).

2. **Verify hooks active**: Run V0.0 check (`ls .claude/settings.json .claude/hooks/trace_logger.py`).

3. **Artifacts policy**: This is purely functional validation — code created/altered by skills will NOT be committed. After each batch, `git checkout .` to discard any file changes made by skills.

---

# PART 3: EXECUTION

---

## 17. Execution Batches

**Estimated total time**: ~3-4 hours across multiple sessions.

**Critical chain** (if time is limited, batches 0, 1, 1R-2R, 5, 8 are sufficient to validate Solution C end-to-end + new skills):

The batches intercalate **refactoring** (creating/modifying skills) with **verification** (testing them). Batches marked "R" (refactoring) substitute/absorb the tests of the analysis skills that were in the original verification-only batches.

| Batch | Scope | Skills | Target | Type |
|-------|-------|--------|--------|------|
| 0 | Infrastructure + Static Checks | V0, V1 | N/A | Verification (DONE) |
| 1 | L0.1 rv-analyze-file (original) | 1 skill | rv-android-core | Verification (L0.1 PASS) |
| **1R** | **Create** rv-analyze-file-complexity + **validate** (no supporting files — lightweight) | 1 skill | rv-android-core | Refactoring + Verification |
| **2R** | **Create** rv-analyze-file-dead-code + **validate** (no supporting files — lightweight) | 1 skill | rv-android-core | Refactoring + Verification |
| **3R** | **Redesign** rv-analyze-complexity + **validate** (absorbs L0.2) | 1 skill | rv-android-core | Refactoring + Verification |
| **4R** | **Redesign** rv-analyze-dead-code + **validate** (absorbs L0.4) | 1 skill | rv-android-core | Refactoring + Verification |
| **5R** | **Redesign** rv-analyze-dependencies + **validate** (absorbs L0.3) | 1 skill | rv-android-core | Refactoring + Verification |
| **6R** | **Redesign** rv-analyze-module + **validate** (absorbs L1.1) | 1 skill | rv-android-core | Refactoring + Verification |
| **7R** | **Slim** rv-analyze-file (consolidate supporting files) + **re-validate** L0.1 | 1 skill | rv-android-core | Refactoring + Verification |
| **8R** | **Update** rv-code-reviewer + rv-refactor-simplify (refs + descriptions) | 2 skills | — | Refactoring |
| **9R** | **Update** docs (WORKFLOW.md, CLAUDE.md) + static re-checks | — | — | Documentation |
| **10R** | MCP memory cache hit test + `/context` budget check | — | — | Verification |
| 2 | L0.5-L0.9 (non-analysis leaves) | 5 skills | rv-android-core | Verification |
| 3 | L0.10-L0.12 (doc leaves) | 3 skills | rv-android-core | Verification |
| 4 | L0.13-L0.16 (planning/risk leaves) | 4 skills | rv-android-core | Verification |
| 5 | L1.2-L1.4 (code-reviewer, debug-regression, qa-lint-fix) | 3 skills | rv-android-core | Verification |
| 6 | L1.5-L1.9 (remaining mid-level) | 5 skills | rv-android-core | Verification |
| 7 | L2.1-L2.2 + L3.1 (deep nesting) | 3 skills | rv-android-core | Verification |
| 8 | L4.1 + L4.4 (orchestrators, critical) | 2 skills | **rv-agent** | Verification |
| 9 | L4.2 + L4.3 (remaining orchestrators) | 2 skills | **rv-agent** | Verification |

**Note**: The "R" (refactoring) batches replace/absorb the tests of analysis skills from the original verification batches 1-5. Batches 2-9 (verification-only) test skills that were NOT refactored.

---

## 18. Interaction Protocol

This verification has two actors: **User** (Pedro) and **Claude** (the AI agent in each session). This section defines who does what.

### 18.1 Roles

| Action | Who | Notes |
|--------|-----|-------|
| Start/stop Claude Code sessions | User | `exit` to end, `claude` to start fresh |
| Re-enable hooks (once) | User | Commands in Section 16, before first batch |
| Delete `output/trace.log` between batches | User | `rm -f output/trace.log` before starting new session |
| Discard file changes between batches | User | `git checkout .` before starting new session |
| Give batch kickoff prompt | User | Copy template from Section 18.2 |
| Invoke skills via Skill tool | Claude | One at a time, in order listed for the batch |
| Approve tool permissions | User | Approve all — these are read/analysis operations on our own code |
| Answer AskUserQuestion prompts | User | Use standard responses from Section 18.4 |
| Check trace.log after each skill | Claude | Verify SUBAGENT_START/STOP, PRE_TOOL_USE events |
| Record results in RELATORIO_SKILLS.md | Claude | Edit docs/RELATORIO_SKILLS.md directly with PASS/FAIL/notes |
| Final review of results | User | After all batches, review RELATORIO for completeness |

### 18.2 Session Lifecycle (per batch)

```
USER (terminal, outside Claude Code):
  1. rm -f output/trace.log        # clean trace for this batch
  2. git checkout .                 # discard previous batch's file changes
  3. claude                         # start fresh session

USER (inside Claude Code):
  4. Paste the batch prompt (Section 18.3)
  5. Approve permission prompts as they appear
  6. Answer AskUserQuestion prompts with test data (Section 18.4)
  7. Review Claude's results summary at the end
  8. exit                           # end session
```

Steps 1-2 are skipped for Batch 0 (first session). Step 1 ensures trace.log only contains events from the current batch, making verification unambiguous.

### 18.3 Prompt Templates

**Batch 0 (Infrastructure + Static Checks):**
```
Execute Batch 0 from docs/20260220_plano_refatoracao_skills.md.
Run all V0 infrastructure checks (V0.0-V0.4) and V1 static checks (V1.1-V1.7).
Record results in docs/RELATORIO_SKILLS.md.
Do NOT invoke any skills — this batch is checks only.
```

**Batches 1R-10R (Refactoring + Validation):**
```
Execute Batch NR from docs/20260220_plano_refatoracao_skills.md.
Follow the execution steps in Section 9 for the corresponding skill(s).
After modification, validate the skill as specified in Section 13.
Record results in docs/RELATORIO_SKILLS.md.
```
(Replace `N` with the batch number: 1, 2, ..., 10.)

**Batches 2-7 (Leaf and Mid-Level Skills — verification only):**
```
Execute Batch N from docs/20260220_plano_refatoracao_skills.md.
For each skill listed in the batch:
  1. Note the current line count of output/trace.log
  2. Invoke the skill using the Skill tool with the args from Section 13
  3. After completion, check trace.log for SUBAGENT_START/STOP and PRE_TOOL_USE
  4. Record PASS/FAIL in docs/RELATORIO_SKILLS.md with notes
After all skills in the batch, give me a summary.
```

**Batches 8-9 (Orchestrators):**
```
Execute Batch N from docs/20260220_plano_refatoracao_skills.md.
Target module: rv-agent.
For each orchestrator listed in the batch:
  1. Note the current line count of output/trace.log
  2. Invoke the skill using the Skill tool
  3. When the orchestrator asks for confirmation via AskUserQuestion, I will respond
  4. After completion, check trace.log for:
     - SUBAGENT_START/STOP for the orchestrator itself
     - Nested SUBAGENT events for chained skills (especially rv-code-reviewer)
  5. Record PASS/FAIL in docs/RELATORIO_SKILLS.md
  6. Do NOT commit any code changes
After all skills in the batch, give me a summary.
```

### 18.4 Standard AskUserQuestion Responses

When a skill prompts via AskUserQuestion during testing, use these responses:

| Skill | Expected Question | Response |
|-------|------------------|----------|
| rv-doc-adr (L0.12) | Decision details, context | "Test ADR: choosing Python over Java for new module. Context: verification testing only." |
| rv-planning (L0.13) | Planning scope, goals | "Scope: rv-android-core module. Goal: improve test coverage. This is a verification test." |
| rv-risk (L0.14) | Risk assessment context | "Context: routine maintenance of rv-android-core. This is a verification test." |
| rv-release (L0.16) | Release scope, version | "Version: test-0.0.0. Scope: rv-android-core only. This is a verification test." |
| Orchestrators (L4.*) | Confirmation to proceed with changes | "Yes, proceed. This is a verification test — changes will be discarded." |
| Any skill | Unexpected question | "Accept the default / first option. This is a verification test." |

### 18.5 Permission Handling

Forked skills trigger tool permission prompts (Read, Bash, Edit, Glob, Grep, etc.). During verification:

- **Approve all tool permissions** — skills are operating on our own codebase with test data
- Changes will be discarded via `git checkout .` after each batch
- If a skill requests a destructive action (e.g., `rm`, `git push`), **deny** and record as anomaly

### 18.6 Abort Criteria

Stop the current batch and record FAIL if:

- A skill hangs for more than 5 minutes with no progress
- A skill enters an infinite loop (repeated identical tool calls)
- Claude Code crashes or loses connection
- A skill attempts to modify files outside the rv-android project directory

Resume from the next skill in the batch after recording the failure.
