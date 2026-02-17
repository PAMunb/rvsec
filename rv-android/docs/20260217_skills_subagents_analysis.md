# Skills vs Subagents: Analysis and Validation Plan

**Date**: 2026-02-17 (v3 — reframed as validation-first plan)
**Scope**: Architectural audit + empirical validation plan for Claude Code skill/subagent nesting
**Status**: PHASE 2 (Optimization) in progress — Phase 1 validated all hypotheses
**Comparative**: `agente-documentador` (Claude Code, 50 skills) and `hello-opencode` (OpenCode, nested subagents)

---

## Executive Summary

This document serves as both analysis and plan. The analysis (Sections 2-8) identified confirmed and uncertain gaps in how rv-android uses Claude Code skills and agents. The key finding: **we cannot resolve the uncertainties from documentation alone — empirical validation is required.**

**Plan structure:**

| Phase | Status | Gate |
|-------|--------|------|
| **Phase 1: Empirical Validation** | **COMPLETE** (T1-T11 all pass) | Results validated — Phase 2 proceeds |
| **Phase 2: Optimization** | **IN PROGRESS** | Implementing R1B, R2, R3, R4, R5 |
| Phase 3: WORKFLOW.md update (conditional) | BLOCKED by Phase 2 | Only after validated solution is stable |

**Decision matrix** (after Phase 1):

| Validation Result | Action |
|-------------------|--------|
| **✓ SELECTED** — Skill tool works in forks AND Task nesting silently ignored | Fix only the 4 orchestrators' Task→rv-code-reviewer. Keep "bombarded" skills as-is. |
| Skill tool works in forks BUT Task nesting causes errors | Same fix, but more urgent (errors vs silent failure). |
| Skill tool does NOT work in forks | Larger restructuring needed — de-fork orchestrators (agente-documentador pattern), evaluate which skills truly benefit from fork. |
| Hooks reveal unexpected patterns (e.g., session_id reuse, tool availability varies by agent type) | Re-analyze based on empirical data before any changes. |

---

## Phase 1: Empirical Validation Project

### 1.1 Objective

Create a standalone Claude Code project (`hello-claude-code`) that exhaustively tests skill/subagent nesting behavior using hooks to trace execution. The project uses a **bibliographic review agent** as its domain — adapted from the existing `hello-opencode` project (which uses OpenCode, a different framework where subagents CAN call subagents).

**Why a separate project?** Testing nesting behavior in rv-android itself risks polluting 42 skills and 1 agent with diagnostic code. A clean, minimal project isolates the experiment.

**Reference projects:**
- `hello-opencode` (`/home/pedro/.../workspace-rv/hello-opencode`): OpenCode project with OrchestratorAgent → SearchAgent/FilterAgent/AnalysisAgent/SynthesisAgent hierarchy. Demonstrates subagent→subagent nesting that OpenCode supports. Must be adapted for Claude Code constraints.
- `agente-documentador` (`/home/pedro/.../workspace-rv/agente-documentador`): Claude Code project with 50 skills, 1 agent, comprehensive hook tracing. Proves the inline-orchestrator + forked-leaf pattern works. Source of `trace_logger.py`.

### 1.2 Test Cases

Each test case validates a specific nesting pattern. The hook trace log provides evidence.

| # | Pattern | What to Test | Expected (from docs) | Needs Validation? |
|---|---------|-------------|---------------------|:-----------------:|
| T1 | Main → Skill (inline) | Invoke a skill WITHOUT `context: fork` | Works (inline loading) | Baseline |
| T2 | Main → Skill (fork) | Invoke a skill WITH `context: fork` | Works (spawns subagent) | Baseline |
| T3 | Main → Task(agent) | Spawn a true subagent from `.claude/agents/` | Works (one level) | Baseline |
| T4 | **Forked skill → Skill tool** | From within a `context: fork` skill, call Skill tool to invoke another skill | **UNCERTAIN** | **YES** |
| T5 | **Forked skill → Task tool** | From within a `context: fork` skill, call Task tool to spawn a subagent | Fails silently (Task absent) | **YES — confirm** |
| T6 | **Agent → Skill tool** | From a true subagent, call Skill tool to invoke a skill | **UNCERTAIN** (agente-documentador includes Skill in agent tools) | **YES** |
| T7 | **Agent → Task tool** | From a true subagent, call Task tool to spawn another subagent | Fails (confirmed by docs) | **YES — confirm** |
| T8 | **Agent with `skills:` preload** | Subagent with `skills:` field — does the preloaded content appear in its context? | Works (confirmed by docs) | Verify |
| T9 | **Fork depth** | Main → forked skill A → Skill tool → skill B (which also has `context: fork`) — what happens? | Unknown — does the inner fork create a nested subagent? | **YES** |
| T10 | **Context window identification** | Do forked skills / subagents get different `session_id` in hook events? If not, is temporal bracketing (SubagentStart→PreToolUse→SubagentStop) the only way to attribute tool calls to subagent contexts? Also: does `agent_id` appear in PreToolUse data? | Unknown | **YES** |

### 1.3 Project Structure: `hello-claude-code`

```
hello-claude-code/                          # New Claude Code project
├── CLAUDE.md                               # Minimal project instructions
├── .claude/
│   ├── settings.json                       # Hook configuration (from agente-documentador)
│   ├── hooks/
│   │   └── trace_logger.py                 # Adapted from agente-documentador
│   ├── agents/
│   │   ├── reviewer.md                     # True subagent: has Skill tool, tests T6/T7
│   │   └── analyzer.md                     # True subagent: has skills: preload, tests T8
│   └── skills/
│       ├── search-papers/
│       │   └── SKILL.md                    # Inline skill (NO fork) — T1 baseline
│       ├── filter-papers/
│       │   └── SKILL.md                    # Forked skill — tries Skill tool (T4)
│       ├── analyze-paper/
│       │   └── SKILL.md                    # Forked skill — tries Task tool (T5)
│       ├── synthesize-review/
│       │   └── SKILL.md                    # Inline skill — T1 variant
│       ├── semantic-filter/
│       │   └── SKILL.md                    # Forked skill — target for T4 nesting
│       └── orchestrate-review/
│           └── SKILL.md                    # Inline orchestrator — spawns Task agents (T3)
├── papers/                                 # Sample data (1-2 paper abstracts)
│   └── sample_papers.json
└── output/                                 # Generated review output
    └── .gitkeep
```

### 1.4 Hook Configuration

Adapted from `agente-documentador/.claude/settings.json`. Key addition: capture `session_id` in every event to correlate context windows.

```json
{
  "hooks": {
    "SessionStart": [{"hooks": [{"type": "command", "command": "python3 .claude/hooks/trace_logger.py", "timeout": 5}]}],
    "SessionEnd": [{"hooks": [{"type": "command", "command": "python3 .claude/hooks/trace_logger.py", "timeout": 5}]}],
    "PreToolUse": [{"matcher": "Read|Write|Edit|Bash|Task|Skill|Glob|Grep|mcp__.*", "hooks": [{"type": "command", "command": "python3 .claude/hooks/trace_logger.py", "timeout": 5}]}],
    "PostToolUse": [{"matcher": "Write|Edit|Bash|Task|Skill|mcp__.*", "hooks": [{"type": "command", "command": "python3 .claude/hooks/trace_logger.py", "timeout": 5}]}],
    "SubagentStart": [{"hooks": [{"type": "command", "command": "python3 .claude/hooks/trace_logger.py", "timeout": 5}]}],
    "SubagentStop": [{"hooks": [{"type": "command", "command": "python3 .claude/hooks/trace_logger.py", "timeout": 5}]}]
  }
}
```

**trace_logger.py adaptation**: Same structure as agente-documentador's version. Change log path from `.docgen/logs/trace.log` to `output/trace.log`.

**Context window identification — what the trace actually provides**:

The agente-documentador's `trace_logger.py` captures `session_id` from `data.get('session_id')` in ALL 7 event handlers. However, `agent_id` is ONLY available in two events: `SubagentStart` and `SubagentStop`. PreToolUse/PostToolUse events do NOT carry `agent_id`.

This means: to determine "was this tool call made from within a subagent?", we depend on one of these strategies:

| Strategy | Works if... | How |
|----------|-------------|-----|
| **session_id differs per context** | Claude Code assigns different session_ids to subagents | Compare PreToolUse.session_id against main session_id from SessionStart |
| **Temporal bracketing** | session_id is the same everywhere | Match PreToolUse timestamps between SubagentStart and SubagentStop for the same agent_id |

**T10 resolves this**: by running a test and inspecting the trace, we learn which strategy to use. The `hello-claude-code` trace_logger should log `data.get('agent_id')` in PreToolUse as well (it may be null — that's informative), so we capture maximum data.

### 1.5 Validation Protocol

Run these tests IN ORDER. Each test builds on the previous baseline.

**Step 1 — Baselines (T1, T2, T3)**:
1. Invoke `/search-papers` (inline skill) — verify trace shows tool calls in main session_id
2. Invoke `/filter-papers` (forked skill, but don't test nesting yet) — verify SubagentStart/Stop events with different session_id
3. Invoke `/orchestrate-review` (inline skill that spawns Task agents) — verify SubagentStart/Stop for each Task

**Step 2 — Critical Tests (T4, T5)**:
4. Invoke `/filter-papers` with instructions to call Skill tool for `semantic-filter` — check trace: does PreToolUse(Skill) appear? Does semantic-filter content load?
5. Invoke `/analyze-paper` with instructions to call Task tool for `reviewer` agent — check trace: does PreToolUse(Task) appear? Does SubagentStart fire?

**Step 3 — Agent Tests (T6, T7, T8)**:
6. Spawn `reviewer` agent (has `tools: ..., Skill`) — instruct it to call Skill tool — check trace
7. Spawn `analyzer` agent (has `skills: [semantic-filter]`) — verify preloaded skill content is available
8. Spawn either agent and instruct it to use Task tool — confirm it cannot

**Step 4 — Depth and Identity Tests (T9, T10)**:
9. Invoke a forked skill that calls Skill tool for another forked skill — does the inner skill fork or run inline within the outer fork's context?
10. Correlate all `session_id` and `agent_id` values from the trace to build a context window map

### 1.6 Interpreting Results

After running all tests, the trace log provides a complete execution map. Key questions to answer:

| Question | Where to Look in Trace | Depends on T10 |
|----------|----------------------|:-:|
| Does a forked skill get a new session_id? | Compare SubagentStart.session_id against SESSION_START.session_id from the main session | **T10 primary** |
| How to attribute tool calls to subagent contexts? | If session_id differs: match PreToolUse.session_id. If session_id is shared: use temporal bracketing between SubagentStart and SubagentStop timestamps. | **T10 secondary** |
| Is `agent_id` present in PreToolUse data? | Log `data.get('agent_id')` in PreToolUse handler — check if it's non-null for subagent tool calls | **T10 tertiary** |
| Is the Skill tool available in forks? | Look for PreToolUse events with tool_name="Skill" within a forked context (identified per T10 strategy) | No |
| Is the Task tool available in forks? | Look for PreToolUse events with tool_name="Task" within a forked context | No |
| Does `skills:` preloading work? | The subagent should reference preloaded skill content without a Skill tool call | No |
| What does "fork within a fork" look like? | Count SubagentStart events — one for the outer fork, another for the inner? Or does the inner skill load inline? | No |

### 1.7 Decision Gate

After Phase 1, present results and decide:

**If Skill tool WORKS in forks (T4=pass, T6=pass)**:
- rv-android's "bombarded" skills (31 forked skills with rich instructions, templates, checklists) are **valid and should be kept**
- Only fix: the 4 orchestrators' Task→rv-code-reviewer nesting (T5 will confirm it fails)
- Minimal change to rv-android: replace Task invocation in 4 SKILL.md files with chain message, OR de-fork just those 4 orchestrators
- **Phase 2 scope: small** (~4-7 files)
- WORKFLOW.md update: minor (document the chain pattern)

**If Skill tool DOES NOT work in forks (T4=fail, T6=fail)**:
- rv-android's 35+ Skill→Skill invocations from forked contexts are ALL broken
- Need to decide per-skill: which skills truly benefit from fork (isolation, clean context) vs which should be inline?
- The agente-documentador pattern (inline orchestrators, forked leaves) becomes the model
- **Phase 2 scope: large** (~20+ SKILL.md files + AGENTS.md + WORKFLOW.md)
- May need to consolidate skills or use `skills:` preloading instead of runtime Skill invocation

**If results are mixed or surprising**:
- Re-analyze before committing to any restructuring
- The trace data may reveal patterns not anticipated by documentation or issues
- Example: Skill tool might work for `general-purpose` agent type but not `Plan`

### 1.8 Phase 1 Results

Validation performed in `hello-claude-code` project (11 test cases, all PASS). Full results: `hello-claude-code/docs/validation-results.md`.

| Test | Pattern | Result | Key Finding |
|------|---------|:------:|-------------|
| T1 | Main → Skill (inline) | PASS | Inline skills work as expected |
| T2 | Main → Skill (fork) | PASS | Forked skills spawn subagent correctly |
| T3 | Main → Task(agent) | PASS | One level of nesting works |
| T4 | **Forked skill → Skill tool** | **PASS** | Skill tool IS available in forks — 35+ Skill→Skill chains are valid |
| T5 | **Forked skill → Task tool** | **PASS** | Task tool is ABSENT in forks — confirmed silent failure |
| T6 | Agent → Skill tool | PASS | Skill tool works in true subagents |
| T7 | Agent → Task tool | PASS | Task tool absent in true subagents — confirmed |
| T8 | Agent with `skills:` preload | PASS | Preloaded skill content appears in context |
| T9 | Fork depth (fork → Skill → fork) | PASS | Inner fork creates nested subagent correctly |
| T10 | Context window identification | PASS | session_id same across contexts; agent_id available in PreToolUse |
| T11 | Deep nesting (5 levels) | PASS | Fork depth unlimited, ~3-4s latency per level |

**Decision**: Best-case scenario materialized (row 1 of decision matrix). Fix only the 4 orchestrators (de-fork per R1B), keep everything else as-is. Additional optimizations (R2-R5) applied opportunistically.

---

## Analysis Context (Sections 2-8)

The following sections provide the analytical foundation for the validation plan above. They document what is confirmed, what is uncertain, and what evidence exists from documentation, GitHub issues, and comparative projects.

**Concern raised**: The original analysis (v1) stated that ALL skill→skill chaining was broken due to the nesting constraint. The user challenged this: *"acho que skill pode chamar skill sim, em profundidade"* — skills CAN call skills in depth. This led to a corrected analysis (v2) distinguishing the Skill tool (inline content loading) from the Task tool (subprocess spawning).

**Sources consulted**:
- Official Claude Code docs: [sub-agents](https://code.claude.com/docs/en/sub-agents), [skills](https://code.claude.com/docs/en/skills), [hooks](https://code.claude.com/docs/en/hooks)
- GitHub issues: [#4182](https://github.com/anthropics/claude-code/issues/4182) (Task tool absent from subagents), [#24072](https://github.com/anthropics/claude-code/issues/24072) (Skill tool absent in Plan mode), [#4850](https://github.com/anthropics/claude-code/issues/4850) (infinite nesting bug)
- `agente-documentador` project: Working Claude Code project with 50 skills, 1 agent, comprehensive hook-based tracing — used as empirical reference
- 8+ community blog/articles on skill vs subagent patterns

---

## 2. Key Distinction: Skill Tool vs Task Tool

The original v1 report conflated these two mechanisms. They are fundamentally different.

### 2.1 The Skill Tool (Inline Content Loading)

The **Skill tool** loads a skill's SKILL.md content into the **current context**. It is NOT subprocess spawning — it is text injection.

```
Main conversation → Skill tool("rv-analyze-module") → content loaded INLINE → same context
```

The Skill tool's own description says: *"Execute a skill within the main conversation."* This is instruction loading, not process creation. Using the Skill tool from within a forked skill would load the second skill's instructions into the forked context — effectively enriching the subagent's task, not creating a nested subprocess.

### 2.2 The Task Tool (Subprocess Spawning)

The **Task tool** spawns a new subprocess — a subagent with its own isolated context window, conversation history, and tool set.

```
Main conversation → Task(rv-code-reviewer) → NEW subprocess → isolated context
```

This IS the mechanism that the nesting constraint applies to. Subagents do NOT have the Task tool in their tool array.

### 2.3 The `skills:` Frontmatter Field (Startup Preloading)

A subagent definition (`.claude/agents/*.md`) can preload skill content at startup:

```yaml
skills:
  - rv-analyze-complexity
  - rv-analyze-dependencies
```

This injects the full skill text into the subagent's initial context. From the docs: *"The full content of each skill is injected into the subagent's context, not just made available for invocation."*

### 2.4 Summary

| Mechanism | What It Does | Creates Subprocess? | Nesting Applies? |
|-----------|-------------|:-------------------:|:----------------:|
| **Skill tool** | Loads SKILL.md content inline | No | No |
| **Task tool** | Spawns isolated subprocess | Yes | **Yes** |
| **`skills:` field** | Preloads skill text at startup | No | No |

---

## 3. The Nesting Constraint (CONFIRMED)

From the official docs ([sub-agents page](https://code.claude.com/docs/en/sub-agents)):

> **"Subagents cannot spawn other subagents."**
>
> *"If your workflow requires nested delegation, use Skills or chain subagents from the main conversation."*
>
> *"Subagents cannot spawn other subagents, so `Task(agent_type)` has no effect in subagent definitions."*

### 3.1 Enforcement Mechanism

This is a **hard constraint**, not a guideline. The Task tool is simply absent from a subagent's tool array. GitHub issue [#4182](https://github.com/anthropics/claude-code/issues/4182) confirms: when a subagent attempts to use the Task tool, it reports *"I don't have access to a 'Task' tool"*.

### 3.2 What Counts as a Subagent?

Both mechanisms create subagents:
- A `.claude/agents/*.md` definition → true subagent
- A skill with `context: fork` → also a subagent

From the docs: *"With `skills` in a subagent, the subagent controls the system prompt and loads skill content. With `context: fork` in a skill, the skill content is injected into the agent you specify. **Both use the same underlying system.**"*

### 3.3 Skill Tool Availability in Subagents

**Status: UNCERTAIN** — evidence suggests it may NOT be available, but this is NOT definitively confirmed.

Evidence suggesting unavailability:
- Issue [#4182](https://github.com/anthropics/claude-code/issues/4182) lists subagent tools: `Bash, Glob, Grep, LS, ExitPlanMode, Read, Edit, MultiEdit, Write, NotebookRead, NotebookEdit, WebFetch, TodoWrite, WebSearch`. **Neither Task nor Skill appears.**
- Issue [#24072](https://github.com/anthropics/claude-code/issues/24072) reports Skill tool absent in Plan mode subagent.

Counter-evidence:
- The `agente-documentador` project's `docgen` agent lists `Skill` in its tools: `tools: Read, Write, Glob, Grep, Bash, Skill`. This is a working, validated project.
- The official docs say subagents *"inherit all tools if omitted"* from the `tools:` field.

**Conclusion**: The Skill tool's availability in subagents is undocumented. The `agente-documentador` explicitly requests it. Whether Claude Code actually provides it is something that can only be validated empirically — which is why hooks/tracing are essential (see Section 7).

---

## 4. Comparative Analysis: agente-documentador

The `agente-documentador` project (`/home/pedro/.../workspace-rv/agente-documentador`) is a working documentation generation system with 50 skills, 1 agent, and comprehensive hook-based tracing. It provides empirical evidence of correct architecture patterns.

### 4.1 Architecture Pattern

```
┌──────────────────────────────────────────────────┐
│              MAIN CONVERSATION                    │
│                                                   │
│  ┌────────────────────────────────────────────┐  │
│  │  Orchestrator skills (INLINE, no fork):     │  │
│  │  - docgen-generate                          │  │
│  │  - docgen-analyze                           │  │
│  │  - docgen-synthesize                        │  │
│  │  → Run in main conversation context          │  │
│  │  → HAVE access to Task and Skill tools       │  │
│  └─────────────┬──────────────────────────────┘  │
│                │                                  │
│        Task tool (spawns subagents)               │
│                │                                  │
│  ┌─────────────┼──────────────────────────────┐  │
│  │     ┌───────┼───────┐                       │  │
│  │     ▼       ▼       ▼                       │  │
│  │  arch-    arch-    arch-     ...  (15+)      │  │
│  │  generate generate generate                  │  │
│  │  -overview -roadmap -components              │  │
│  │  (fork)    (fork)   (fork)                   │  │
│  │  → Isolated subagent contexts                │  │
│  │  → NO Task tool, NO Skill tool               │  │
│  └──────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────┘
```

### 4.2 Key Design Decisions

| Decision | Implementation | Rationale |
|----------|---------------|-----------|
| Orchestrators are **inline** (no fork) | `docgen-generate` has NO `context: fork` | Needs Task tool to spawn parallel subagents |
| Leaf skills are **forked** | `arch-generate-*` have `context: fork` | Benefit from isolation: focused task, clean context |
| Agent explicitly lacks Task | `docgen` agent: `tools: Read, Write, Glob, Grep, Bash, Skill` — **no Task** | Acknowledges: *"Não pode chamar subagentes"* |
| External scripts for parallelism | `docgen-analyze` uses `orchestrate.py` with `opencode run` | Avoids need for Task tool altogether |
| **Single level of nesting** | Main → forked leaf skill | **LEGAL**: main conversation has Task tool |

### 4.3 The Docgen Agent

```yaml
# .claude/agents/docgen.md (frontmatter)
name: docgen
tools: Read, Write, Glob, Grep, Bash, Skill  # NO Task!
skills:
  - docgen-init
  - docgen-core
  - docgen-analyze
  - docgen-synthesize
  - docgen-generate
  - docgen-adr
```

Line 230 of the agent's body explicitly states: *"Não pode chamar subagentes: Skills rodam isoladamente"* — "Cannot call subagents: Skills run in isolation."

This is a correct understanding of the constraint. The agent preloads 6 skills via the `skills:` field and does NOT attempt Task-based nesting.

### 4.4 Hook-Based Tracing

The `agente-documentador` has a comprehensive hook system (`.claude/settings.json`) that traces ALL tool calls, skill invocations, and subagent lifecycle:

| Event | Handler | Data Captured |
|-------|---------|--------------|
| SessionStart | trace_logger.py | session_id, model, cwd |
| SessionEnd | trace_logger.py | session_id, reason |
| UserPromptSubmit | trace_logger.py | prompt preview, skill detection |
| PreToolUse | trace_logger.py | tool name, inputs (Task: subagent_type, Skill: skill name) |
| PostToolUse | trace_logger.py | tool name, exit codes, success |
| SubagentStart | trace_logger.py | agent_id, agent_type |
| SubagentStop | trace_logger.py | agent_id, transcript_path |

Output: JSONL at `.docgen/logs/trace.log`.

**This tracing system can empirically validate whether Skill/Task tool calls actually execute from within forked contexts.** RV-Android has NO equivalent — making behavioral claims about the nesting constraint impossible to verify.

---

## 5. RV-Android Architecture Assessment

### 5.1 Current Inventory

| Category | Count | Items |
|----------|-------|-------|
| True subagent | 1 | `rv-code-reviewer` (`.claude/agents/rv-code-reviewer.md`) |
| Orchestrator skills (`fork` + Task) | 4 | rv-refactor, rv-feature, rv-tdd, rv-cleanup |
| Component skills (`fork`) | 27 | ALL other rv-* skills |
| Process skills (inline) | 10 | openspec-* skills (no fork) |
| **Total** | **42** | 31 rv-* skills + 10 openspec-* skills + 1 agent |

### 5.2 The Confirmed Problem: Task Tool in Forked Orchestrators

All 4 orchestrator skills have `context: fork` (making them subagents) AND instruct calling `Task(rv-code-reviewer)`:

| Orchestrator | Line | Instruction |
|-------------|------|-------------|
| rv-refactor | 226 | `Task tool: subagent_type: rv-code-reviewer` |
| rv-feature | 473 | `Task tool: subagent_type: rv-code-reviewer` |
| rv-tdd | 356 | `Task tool: subagent_type: rv-code-reviewer` |
| rv-cleanup | 266 | `Task tool: subagent_type: rv-code-reviewer` |

**Since forked skills ARE subagents, and subagents do NOT have the Task tool, these calls silently fail.** The code review quality gate — which all 4 orchestrators depend on — is not executing.

### 5.3 The Uncertain Problem: Skill Tool in Forked Skills

35+ instances across rv-* skills instruct calling other skills via the Skill tool from within forked contexts. Examples:

```markdown
# From rv-feature/SKILL.md:
Skill tool: skill="rv-analyze-module", args="$TARGET_MODULE"
Skill tool: skill="rv-analyze-dependencies", args="$TARGET_MODULE"
Skill tool: skill="rv-verify", args="[module-name]"
```

If the Skill tool IS available in forked contexts, these work correctly (inline loading, not nesting).
If the Skill tool is NOT available, these ALL silently fail — a much broader impact than just the Task tool issue.

**Status: UNVERIFIABLE without tracing hooks.** This is why R7 (adopt hooks) is critical.

### 5.4 Contrast: rv-android vs agente-documentador

| Aspect | agente-documentador | rv-android | Issue |
|--------|-------------------|------------|-------|
| Orchestrator skills | **Inline** (no fork) | **Forked** | Forked orchestrators lack Task tool |
| Leaf skills | **Forked** | **Forked** | Correct in both |
| Agent has Task tool? | No (explicit) | N/A (no agent orchestrates) | — |
| Hook tracing | **Yes** (comprehensive) | **No** | Cannot validate behavioral claims |
| Nesting levels | 1 (main → leaf) | 2 (main → orch → reviewer) | Violation |
| Skill→Skill chains | Minimal | 35+ instances | Uncertain if working |

---

## 6. Gap Analysis (Corrected)

### 6.1 Gaps Ordered by Severity

| # | Gap | Severity | Scope | Confidence |
|---|-----|----------|-------|------------|
| G1 | **Task tool unavailable in forked orchestrators** | CRITICAL | 4 orchestrator skills → rv-code-reviewer | CONFIRMED |
| G2 | **Skill tool status in forked skills unknown** | HIGH | 35+ Skill→Skill invocations across all rv-* skills | UNCERTAIN |
| G3 | **No tracing/hook system** | HIGH | Cannot validate ANY behavioral claims about tool availability | CONFIRMED |
| G4 | **Unnecessary fork on simple skills** | MEDIUM | ~12 skills fork without benefiting from isolation | CONFIRMED |
| G5 | **No `disable-model-invocation`** | MEDIUM | 7+ rarely-used skills compete for auto-trigger | CONFIRMED |
| G6 | **No `permissionMode` on reviewer** | MEDIUM | rv-code-reviewer should be read-only | CONFIRMED |
| G7 | **No persistent memory on reviewer** | LOW | No cross-session pattern learning | CONFIRMED |

### 6.2 Correction from v1

The v1 report characterized G1 as "ALL chaining is broken." This was **wrong**. The corrected understanding:

| Pattern | Works? | Why |
|---------|:------:|-----|
| Skill → Skill (via Skill tool, inline) | **Probably yes** | Inline content loading, not subprocess spawning |
| Main conversation → Subagent (via Task tool) | **Yes** | One level of nesting, legal |
| Subagent → Subagent (via Task tool) | **No** | Task tool absent from subagents |
| Forked skill → Task(rv-code-reviewer) | **No** | Forked skill IS a subagent |

**The user's challenge was correct**: *"skill pode chamar skill sim, em profundidade"* — the Skill tool loads content inline, which is fundamentally different from Task tool subprocess spawning. The v1 analysis was imprecise about this distinction.

---

## 7. Recommendations (Prioritized)

### R1. Fix Task Nesting in Orchestrators (CRITICAL)

**Problem**: 4 forked orchestrator skills attempt `Task(rv-code-reviewer)` — this silently fails.

**Solution A — Fix nesting (minimum change)**: Replace the Task invocation with a post-completion chain message. When the orchestrator finishes, it outputs:

```
CHAIN: rv-code-reviewer — Review [target]. Focus on: [areas].
```

The main conversation (which HAS the Task tool) then spawns rv-code-reviewer.

Also remove `Task` from the 4 orchestrators' `allowed-tools` (plus 3 other skills that list it without using it: rv-security, rv-docs-sync, rv-doc-generate-claude-md).

**Solution B — Adopt agente-documentador pattern (structural fix)**: Remove `context: fork` from the 4 orchestrator skills so they run inline. They keep full access to Task and Skill tools. This is the pattern used by the validated agente-documentador.

**Recommended**: Solution B. It's more honest architecturally — orchestrators NEED Task/Skill access, which inline execution provides.

**Files**: rv-refactor/SKILL.md, rv-feature/SKILL.md, rv-tdd/SKILL.md, rv-cleanup/SKILL.md (+ 3 others for Task removal)
**Effort**: ~1-2h | **Risk**: Low | **ROI**: HIGH

### R2. Adopt Hook-Based Tracing (HIGH)

**Problem**: RV-Android has NO hooks. We cannot empirically verify whether Skill tool calls work in forked contexts, whether Task calls silently fail, or what the actual subagent lifecycle looks like.

**Solution**: Adopt the `agente-documentador`'s `trace_logger.py` pattern:

1. Create `.claude/hooks/trace_logger.py` — adapted from the agente-documentador version (193 lines, handles 7 event types)
2. Create `.claude/settings.json` with hook configuration for all events
3. Log to `.rvagent/logs/trace.log` (JSONL format)

This enables:
- **Validating G2**: Run a forked skill that uses the Skill tool, check trace log for tool availability
- **Confirming G1**: Run an orchestrator, verify Task tool call doesn't appear in trace
- **General observability**: Understand skill/subagent execution patterns

**Source**: `agente-documentador/.claude/hooks/trace_logger.py` + `.claude/settings.json`
**Effort**: ~1h | **Risk**: Zero (hooks are non-blocking, exit 0) | **ROI**: HIGH

### R3. Remove `context: fork` from Simple Skills (MEDIUM)

**Problem**: ALL 31 rv-* skills use `context: fork`, including trivially simple ones that gain nothing from context isolation.

**Skills to de-fork** (12 — simple, single-purpose, mechanical):

| Skill | Reason |
|-------|--------|
| rv-test-run | Just runs pytest |
| rv-qa-lint | Just runs linters |
| rv-qa-lint-fix | Runs linters + auto-fix |
| rv-refactor-cleanup | Runs black + isort |
| rv-refactor-constants | Mechanical extraction |
| rv-doc-readme | Template-driven generation |
| rv-doc-adr | Template-driven generation |
| rv-doc-generate-claude-md | Template + analysis |
| rv-docs-sync | Diff + update |
| rv-debug-regression | Git history analysis |
| rv-doc-architecture | Analysis + Mermaid generation |
| rv-release | Multi-step but mechanical |

**Skills to keep forked** (19 — benefit from isolation):

| Category | Skills |
|----------|--------|
| Analysis (5) | rv-analyze-module, -complexity, -file, -dead-code, -dependencies |
| Refactoring (2) | rv-refactor-simplify, rv-refactor-extract |
| Testing (1) | rv-test-add |
| Verification (1) | rv-verify |
| Documentation (1) | rv-doc-code |
| Other (5) | rv-impact-analyzer, rv-planning, rv-risk, rv-security, rv-retrospective |
| *Orchestrators (4)* | *rv-refactor, -feature, -tdd, -cleanup* — **de-fork per R1B** |

Note: If R1B is adopted (de-fork orchestrators), they move from "keep forked" to "de-forked". Total de-forked: 16 skills.

**Effort**: ~1h | **Risk**: Low | **ROI**: MEDIUM

### R4. Add `disable-model-invocation: true` to Rarely-Used Skills (MEDIUM)

**Problem**: 42 skill descriptions load at session start. 7+ rarely-used skills compete for auto-trigger attention, creating confusion with overlapping descriptions (rv-refactor vs rv-refactor-simplify vs rv-refactor-extract).

**Skills to disable auto-trigger** (7):

| Skill | Reason |
|-------|--------|
| rv-risk | Optional, rarely invoked |
| rv-retrospective | Optional post-Archive |
| rv-release | Only for actual releases |
| rv-planning | Overlaps with orchestrator planning phases |
| rv-security | Only for specific security reviews |
| rv-refactor-simplify | Easily confused with rv-refactor |
| rv-refactor-extract | Easily confused with rv-refactor |

They remain invocable via `/skill-name`.

**Effort**: ~30min | **Risk**: Zero | **ROI**: MEDIUM

### R5. Add `permissionMode: plan` to rv-code-reviewer (MEDIUM)

**Problem**: rv-code-reviewer should be read-only. Currently has `tools: Read, Grep, Glob, Bash, Skill`.

**Solution**: Add `permissionMode: plan` to frontmatter. Enforces read-only at system level.

**Effort**: 5min | **Risk**: Zero | **ROI**: MEDIUM

### R6. Add `memory: project` to rv-code-reviewer (LOW)

**Problem**: No cross-session pattern learning for recurring review findings.

**Solution**: Add `memory: project` to frontmatter + instructions for reading/writing memory about recurring patterns.

**Effort**: ~30min | **Risk**: Low | **ROI**: LOW (grows over time)

### R7. Verify Skill Tool Availability Empirically — **RESOLVED**

**Status**: RESOLVED by Phase 1 validation (T4, T6). The Skill tool IS available in forked skills and true subagents. All 35+ Skill→Skill chains in rv-android are valid. No action needed.

---

## 8. Honest Assessment

### What was wrong in v1?

The v1 report correctly identified the Task tool nesting constraint but incorrectly extended it to ALL skill chaining. The Skill tool is not subprocess spawning — it's inline content loading. The user's challenge was valid.

### What's actually broken?

**CONFIRMED broken**: The 4 orchestrators' `Task(rv-code-reviewer)` calls. The code review quality gate is not executing.

**POSSIBLY broken**: 35+ Skill→Skill invocations from forked contexts. Evidence is mixed — the `agente-documentador` includes Skill in its agent's tools, but research suggests it may not be available in all subagent types. **Only hooks/tracing can resolve this.**

**Working fine**: OpenSpec skills (10 inline skills), direct conversation interactions, `skills:` preloading in rv-code-reviewer agent.

### What is the agente-documentador teaching us?

1. **Orchestrators should be inline** — they need Task/Skill access
2. **Only leaf skills should fork** — they benefit from isolation
3. **Hooks/tracing are essential** — you can't validate architecture without observability
4. **The agent definition should NOT include Task** — if it can't spawn subagents, don't pretend it can

### Recommended implementation order

```
Phase 1 (resolve critical issues):
  R1B (de-fork orchestrators)     — fixes broken code review chain
  R2  (adopt hooks/tracing)       — enables empirical validation

Phase 2 (validate and optimize):
  R7  (verify Skill tool in forks) — resolves G2 uncertainty
  R3  (de-fork simple skills)      — reduces overhead
  R4  (disable auto-trigger)       — cleaner UX

Phase 3 (enhance):
  R5  (permissionMode: plan)       — enforces read-only reviewer
  R6  (memory: project)            — cross-session learning
```

---

## 9. Verification Plan

| After | Test | Pass Criteria |
|-------|------|---------------|
| R1B | Invoke `/rv-feature` → verify it runs inline (no "launching agent" message) → verify it can call Task(rv-code-reviewer) from main conversation | Code review phase executes |
| R2 | Check `.rvagent/logs/trace.log` exists after any session | JSONL entries for all event types |
| R3 | Invoke `/rv-test-run rv-agent` → verify no forking | Faster response, no subprocess |
| R4 | Type a generic message → check if disabled skills trigger | Only enabled skills auto-trigger |
| R5 | Invoke rv-code-reviewer → try Write tool | Permission denied |
| R7 | Invoke a forked skill that uses Skill tool → check trace log | PRE_TOOL_USE with tool_name: "Skill" present or absent |

---

## Appendix A: Architecture Diagrams

### Current (Problematic)

```
┌─────────────────────────────────────────────────────────┐
│                    USER MESSAGE                          │
└───────────────────────────┬─────────────────────────────┘
                            │
           ┌────────────────┼────────────────┐
           │                │                │
           ▼                ▼                ▼
     ┌──────────┐    ┌──────────┐    ┌──────────────┐
     │ rv-*     │    │ openspec │    │ Direct       │
     │ skills   │    │ skills   │    │ conversation │
     │ (31)     │    │ (10)     │    │              │
     └─────┬────┘    └──────────┘    └──────────────┘
           │         (inline, OK)
   ALL use context: fork
           │
   ┌───────┼───────────────┐
   │       │               │
   ▼       ▼               ▼
Orchestrators  Component    Simple
(4 skills)    w/ Skill     w/o Skill
   │         calls (?)     (no issue)
   │
   │  ✖ Task(rv-code-reviewer)
   │  Task tool ABSENT in subagent
   │  → SILENTLY FAILS
   ▼
rv-code-reviewer
(never reached)
```

### Proposed (After R1B + R2 + R3)

```
┌─────────────────────────────────────────────────────────┐
│                    USER MESSAGE                          │
└───────────────────────────┬─────────────────────────────┘
                            │
           ┌────────────────┼────────────────┐
           │                │                │
           ▼                ▼                ▼
     ┌──────────┐    ┌──────────┐    ┌──────────────┐
     │ Inline   │    │ openspec │    │ Direct       │
     │ skills   │    │ skills   │    │ conversation │
     │ (16)     │    │ (10)     │    │              │
     └─────┬────┘    └──────────┘    └──────────────┘
           │
   ┌───────┼───────────────┐
   │       │               │
   ▼       ▼               ▼
Orchestrators  Simple     De-forked
(4 inline)    (12 inline)  simple
   │                       skills
   │
   │  ✓ Task(rv-code-reviewer)
   │  Main conversation HAS Task tool
   │  → WORKS
   ▼
rv-code-reviewer         Forked skills
(agent, reached)         (15 remaining)
+ permissionMode: plan   Analysis, complex
+ memory: project        refactoring, etc.
```

### Agente-documentador (Reference Pattern)

```
┌─────────────────────────────────────────────────────────┐
│              MAIN CONVERSATION (or docgen agent)         │
│                                                          │
│  Orchestrators (INLINE, no fork):                        │
│    docgen-generate, docgen-analyze, docgen-synthesize    │
│    → HAVE Task + Skill tools                             │
│                                                          │
│  ┌───── Task tool (spawns subagents) ─────────────┐     │
│  │                                                  │     │
│  ▼                                                  ▼     │
│  arch-generate-*  (15+ forked skills)    arch-analyze-*  │
│  → Isolated contexts                                      │
│  → NO Task, NO Skill                                      │
│  → Single level of nesting ✓                              │
│                                                          │
│  Hook tracing: trace_logger.py → .docgen/logs/trace.log  │
│  → SessionStart/End, PreToolUse, SubagentStart/Stop      │
└──────────────────────────────────────────────────────────┘
```

---

## Appendix B: trace_logger.py Reference

The agente-documentador's tracing hook at `.claude/hooks/trace_logger.py` (193 lines) handles 7 events:

```python
handlers = {
    'SessionStart':    handle_session_start,    # session_id, model, cwd
    'SessionEnd':      handle_session_end,      # session_id, reason
    'UserPromptSubmit': handle_user_prompt,      # prompt preview, skill detection
    'PreToolUse':      handle_pre_tool_use,     # tool_name, inputs
    'PostToolUse':     handle_post_tool_use,    # tool_name, exit codes
    'SubagentStart':   handle_subagent_start,   # agent_id, agent_type
    'SubagentStop':    handle_subagent_stop,    # agent_id, transcript_path
}
```

For Task tool calls, captures `subagent_type` and `description`.
For Skill calls, captures `skill` and `args`.

Settings configuration (`.claude/settings.json`):
```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Read|Write|Edit|Bash|Task|Skill|Glob|Grep|mcp__.*",
      "hooks": [{"type": "command", "command": "python3 .claude/hooks/trace_logger.py", "timeout": 5}]
    }],
    "SubagentStart": [...],
    "SubagentStop": [...]
  }
}
```

**Adaptation for rv-android**: Change log path from `.docgen/logs/` to `.rvagent/logs/`, adjust tool matchers, add to `.gitignore`.
