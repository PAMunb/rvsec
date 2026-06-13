# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Architecture Overview

RV-Android is a modular framework for runtime verification of Android applications with LLM-driven testing capabilities. The system uses a uv workspace architecture with modules in the `modules` directory.

### Core Architecture Principles

- **Modular Design**: uv workspace modules in editable mode with clear dependencies and interfaces
- **Component-Based Execution**: TaskExecutor uses pluggable components for different execution phases
- **Configuration Management**: Unified configuration across all modules using Pydantic models
- **Error Handling**: Error handling with proper context and recovery strategies

### System Modules

The system consists of the following modules:

**Core Infrastructure:**
1. **rv-android-core**: Foundation infrastructure with domain models, error handling, and logging
2. **rv-platform**: Central execution platform coordinating task execution and result processing
3. **rv-tools**: Testing tool plugin system with registry and factory patterns
4. **rv-uiautomator**: Shared UIAutomator components for direct device interaction

**Analysis and Processing:**
5. **rv-monitor-generator**: JavaMOP/RV-Monitor integration for generating runtime verification monitors
6. **rv-instrumentation-core**: Pure abstractions — `Instrumenter` ABC + shared Pydantic result types
7. **rv-instrumentation**: Parent canonical — `get_instrumenter()` factory + shared keystore asset; re-exports the public API from `rv-instrumentation-core`
8. **rv-instrumentation-ajc**: AspectJ-based instrumentation variant (legacy dex2jar+ajc+d8 pipeline)
9. **rv-instrumentation-dexlib2**: DEX-native instrumentation variant (gh52)
10. **rv-static-analysis**: Unified GATOR-based static analysis for Android applications
11. **rv-coverage**: Coverage analysis and tracking for monitored operations
12. **rv-screen-parser**: Android UI parsing with visitor patterns for state analysis

**LLM Testing:**
13. **rv-agent**: Main LLM-driven testing tool using LangGraph for workflow orchestration

**Tool Plugins (rv-platform):**
14. **rvagent-tool**: rv-platform plugin wrapping rv-agent as an AbstractTool
15. **aperv-tool**: rv-platform plugin wrapping the APE-RV binary (ape-rv.jar) for model-based UI exploration

**Experiment Orchestration:**
16. **rv-experiment**: Experiment orchestration and coordination system

**Temporary/Validation:**
- **aperv-llm-validation**: Offline validation for APE-RV LLM coordinate mapping pipeline (temporary module — excluded from the canonical 16 production modules)

## Development Commands

### Environment and Installation
```bash
export RV_PYDANTIC=true  # Enable validation during development
export RVSEC_HOME="/path/to/rvsec"  # Required for monitors and static analysis
export ANDROID_HOME="/path/to/android-sdk"

# Install all modules (uv workspace, editable mode, shared .venv)
uv sync  # or: cd modules && ./install.sh
```

uv workspace: single `uv sync` at root installs ALL modules in editable mode. Source changes are immediate — no reinstall needed unless `pyproject.toml` changes.

### Testing and Quality
```bash
# Run all tests per-module (matches CI pipeline — .github/workflows/ci.yml):
for module in modules/*/; do
  [ -d "$module/tests" ] && uv run pytest "$module/tests" \
    -m "not (slow or online or sglang or performance or dataset)" \
    --import-mode=importlib --tb=short -q -o "addopts="
done

# Single module:
uv run pytest modules/MODULE_NAME/tests/ \
  --import-mode=importlib -o "addopts=" -v

# Lint:
uv run black modules/ && uv run flake8 modules/
```

**Important**: Always use `--import-mode=importlib` and `-o "addopts="` to match CI behavior. Without these flags, conftest isolation breaks across modules causing collection errors. The CI runs each module's tests in isolation with these flags.

### Experiment Execution
```bash
uv run rv-experiment run --tools monkey,droidbot:dfs_greedy --specification-set jca
uv run rv-experiment run --tools monkey --name my_experiment  # Auto-resume on re-run
uv run rv-platform run --tools monkey --apks-dir ./apks_examples  # Direct platform
```

### RV-Agent
Two modes: **standalone CLI** (`rv-agent` — user manages emulator/APK) or **via rv-experiment** (`rvagent` tool — platform manages everything). Without `RVSEC_HOME`, static analysis and instrumentation are skipped.

```bash
# Via rv-experiment (recommended)
uv run rv-experiment run --tools rvagent:pure_algorithm --apks-dir ./apks_examples --timeout 60
# Standalone (requires emulator running + APK installed)
cd modules/rv-agent && uv run rv-agent run --package br.unb.cic.cryptoapp --mode pure_algorithm --timeout 60
```

See `.claude/project-info.md` for Docker commands, monitor generation, and full command reference.

## Execution Flow

### Entry Points
- **rv-experiment** (`rv_experiment/__main__.py`): Experiment orchestration — pre-processing (instrumentation, static analysis) -> execution -> post-processing
- **rv-platform** (`rv_platform/__main__.py`): Direct task execution without experiment wrapper
- **rv-agent** (`rv_agent/cli/main.py`): Standalone LLM-driven testing (modes: pure_algorithm, llm_only, multimode)

### Core Flow
`ExperimentController` -> `ExecutionController` -> `Platform` -> `TaskExecutor` (component-based: emulator, static analysis, coverage, logcat, tool execution)

### RV-Agent Architecture
- **RVAgent** (`agent/rv_agent.py`): LangGraph workflow with externalized nodes in `agent/nodes/` (parse, decision, algorithm, llm, validation, execute, learn)
- **RVAgentStrategy** (`strategies/rvagent_strategy/`): DFS-based exploration with Successor Tracker, Plateau Detector, MOP Prioritization
- **LLMClient** (`llm/llm_client.py`): Qwen3-VL via SGLang (OpenAI-compatible API)

## Module Dependencies and Relationships

### Core Infrastructure Modules
- **rv-android-core**: Provides foundation services (ErrorHandler, LoggingManager, domain models)
- **rv-tools**: Tool registry and plugin system used by all testing components
- **rv-uiautomator**: Shared UIAutomator components for device interaction

### Analysis and Processing Modules
- **rv-static-analysis**: Provides static analysis data to other modules
- **rv-coverage**: Tracks coverage during task execution
- **rv-screen-parser**: UI parsing for state analysis in LLM-driven testing
- **rv-monitor-generator**: Creates runtime verification monitors for instrumentation

### Execution and Orchestration
- **rv-platform**: Central execution engine used by rv-experiment
- **rv-experiment**: Experiment orchestration with pre/post processing
- **rv-agent**: Main LLM-driven testing tool
- **rv-instrumentation-core**: ABC `Instrumenter` + shared types; depended on by every variant impl. Zero deps on impls (avoids cycle).
- **rv-instrumentation** (parent): `get_instrumenter(variant, config)` factory dispatching to ajc/dexlib2; shared `assets/keystore.jks`; re-exports the public API from `-core`.
- **rv-instrumentation-ajc**: AspectJ-based variant (`AjcInstrumentation`); depends on `-core` only — no parent dep, no sibling dep.
- **rv-instrumentation-dexlib2**: DEX-native variant (`DexlibInstrumentation`); depends on `-core` only.

## Configuration Management

### Environment Variables
- `RV_PYDANTIC=true`: Enable development validation (recommended during development)
- `RVSEC_HOME`: Required for monitor generation (path to RVSEC installation)
- `ANDROID_HOME`: Android SDK path for emulator management
- `RVAGENT_MODE`: Override rv-agent execution mode (pure_algorithm, llm_only, multimode)

### Configuration Files
- Tool configurations support unified configuration through Pydantic models
- Experiment configurations in JSON format with validation
- Module-specific configuration classes with composition patterns

## Directory Structure and Cleanup

Key directories: `out/` (temporary artifacts — monitors, instrumented APKs, static analysis), `results/` (persistent experiment results), `apks_examples/` (source APKs).

```bash
./clear.sh                 # Clean temporary artifacts (keeps results/)
./clear.sh --clean-results # Clean everything including results
```

**Gotcha**: When using `--skip-monitors`/`--skip-instrument`/`--skip-static` flags, `--apks-dir` must point to **instrumented APKs** from a previous run (`results/<id>/instrumented_apks/`), not original APKs — otherwise coverage will be 0%.

See `.claude/project-info.md` for full directory tree and pre-processed artifact locations.

## Key Architectural Patterns

### Component-Based Execution
- TaskExecutor uses pluggable components for different execution phases
- Components follow initialize/execute/cleanup lifecycle
- Proper resource management and error handling

### Factory and Registry Patterns
- ToolFactory creates configured tool instances
- ToolRegistry manages available tools and variants
- AgentFactory creates configured rv-agent instances

### Error Handling Strategy
- ErrorHandler decorator provides consistent error management
- Context-aware error reporting with proper logging
- Graceful degradation and recovery mechanisms

## Testing Strategy

RV-Agent test dirs: `unit/`, `integration/`, `smoke/`, `online/`, `performance/`, `regression/`, `system/` in `modules/rv-agent/tests/`. Run with `PYTHONPATH=../rv-android-core/src:src uv run pytest tests/<dir>/ -v`.

Test data: screenshots in `/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots` (28+ apps), fixtures in `modules/rv-agent/tests/fixtures/`. See `.claude/project-info.md` for full test commands.

## Development Principles

These four principles are **non-negotiable** and govern all code, comments, documentation, and specs.

### P1: Simplicity
Minimum complexity for the current task. Three similar lines > premature abstraction. Direct call > indirection with one subscriber. No speculative features, no validation for impossible scenarios, no helpers for one-time operations. Only validate at system boundaries (user input, external APIs). Prefer composition over inheritance, flat over nested.

### P2: Human-Readable Documentation
All docs (specs, proposals, design docs) must be narrative and self-contained. Explain *why*, not just *what*. Use WHEN/THEN/AND format with concrete values in scenarios. When behavior has a non-obvious reason, explain it inline.

### P3: No Backward Compatibility
Dead/superseded code is deleted entirely — no adapters, shims, wrappers, `# removed` comments, or `_unused` renames. Backup to `backup/` (gitignored) before deletion. All changes must be complete: update all callers, grep for dangling references, one commit = one consistent state.

### P4: Current-State Comments
Comments describe what the code does *now*. No migration history ("migrated from X", "replaces old Y"). No promotional language ("modern", "elegant", "advanced"). Names describe function, not lineage (`process_tasks` not `process_tasks_v2`). Reference thesis/ICST paper for historical context, don't embed it in comments.

---

## Development Guidelines

### Code Structure
- Use English for all code and comments
- When writing in Portuguese (Brazilian), always use correct accentuation (acentos, cedilha, til, etc.). The user may omit accents in their messages (non-ABNT keyboard), but Claude must always write Portuguese correctly.
- Include detailed comments at critical architectural points — explain *why*, not just *what*
- Follow the comment template in: `ExecutionManager`, `TaskExecutor`

### Git Commits
- NEVER add `Co-Authored-By` or any co-author trailer to commit messages. The user is the sole author.

### Emulator Management — DO NOT TOUCH
- **NEVER start, stop, or manage Android emulators manually.** rv-platform manages the entire emulator lifecycle automatically (start, boot wait, APK install, cleanup). This applies to ALL contexts: E2E validation, experiments, testing, debugging — no exceptions.
- Do NOT run `emulator` commands, `adb emu kill`, or any emulator-related shell commands. If a task requires an emulator, use `rv-experiment run` or `rv-platform run` — they handle everything.
- This rule is PERMANENT and must NEVER be removed from this file.

### Constants
- Use constants instead of magic values whenever possible
- Main constant files:
  - `modules/rv-android-core/src/rv_android_core/constants.py`
  - `modules/rv-experiment/src/rv_experiment/constants.py`
- Each module may have its own constants file

### Error Handling
- Use ErrorHandler decorators for consistent error management
- Provide meaningful error messages with context
- Implement proper cleanup in error scenarios
- Log errors with appropriate context information

### Configuration Management
- Use unified configuration objects instead of parameter duplication
- Validate configuration at module boundaries
- Provide clear configuration schemas and examples
- Support both programmatic and file-based configuration

### Performance Considerations
- Implement lazy initialization where appropriate
- Proper resource cleanup and lifecycle management
- Monitor memory usage in long-running operations

## Important Implementation Notes

### Module Interactions
- rv-experiment coordinates but does not duplicate rv-platform functionality
- rv-platform handles all task execution and result processing
- Clean separation between orchestration (rv-experiment) and execution (rv-platform)
- rv-agent integrates with rv-platform through the tool plugin system

### Instrumentation and Monitoring
- Monitor generation requires RVSEC_HOME environment variable
- APK instrumentation creates monitored versions for runtime verification
- Coverage tracking coordinates with tool execution timing
- Static analysis provides foundation data for other analysis modules

### Specification Sets (Runtime Verification)
The system supports two distinct specification sets for runtime verification:

1. **JCA Specifications**: Detect misuse of Java Cryptography Architecture (JCA) API
   - Example: Proper initialization of ciphers, key generation, secure random

2. **Generic Specifications**: Detect violations of general API usage patterns
   - Example: Must call `hasNext()` before `next()` on Iterator
   - Example: Must close streams after use

**Important**: These sets are used separately in experiments. In one experiment, APKs are instrumented with JCA specifications; in another, with generic specifications. The term "MOP" (Monitored Operations) refers to operations being monitored by ANY specification, not specifically security-related operations. Do not use "security" terminology when referring to MOP - use "monitored operations" instead.

### RV-Agent Specifics
- Uses LangGraph for workflow orchestration
- SGLang server required for LLM backend (default: http://192.168.0.36:30000/v1)
- Default model: Qwen/Qwen3-VL-4B-Instruct
- Multimode default: 70% LLM / 30% algorithm decisions

### Tool Calling Híbrido (Qwen3-VL + SGLang)
SGLang lacks official tool calling for Qwen3-VL (~50% native, ~50% XML). Hybrid approach: try `bind_tools()` native first, fallback to XML/JSON parsing via `rv_agent/llm/tools/tool_call_parser.py`. Both strategies achieve 100% success.

### Qwen3-VL Coordinate System
- Qwen3-VL returns coordinates in normalized [0, 1000) range for both x and y
- Conversion to device pixels: `pixel_x = int((x / 1000) * device_width)`
- `ActionNormalizer` in `domain/action.py` handles this conversion using `denormalize_qwen_coords()`
- Reference: https://github.com/QwenLM/Qwen3-VL/issues/1486
- Validated empirically: 84.2% hit rate with 20 apps (see `docs/20260107_rvagent_validacao_multimodal.md`)

---

## Current Work

**rv-agent key files**: `agent/rv_agent.py` (main), `agent/nodes/` (workflow nodes), `strategies/rvagent_strategy/` (DFS strategy), `services/transition_manager.py` (WTG integration), `services/navigation_guidance.py` (navigation), `llm/llm_client.py` (LLM client), `routing/` (LLM/algorithm routing). All paths relative to `modules/rv-agent/src/rv_agent/`.

**Plans**: `docs/20260105_rvagent_refactoring.md` (refactoring), `docs/20260213_plano_refatoracao.md` (current)

**WTG transitions sweep (2026-06-11)**: full-WTG static-analysis sweep on the 169 APKs of `experimento-20260604` (to populate `transitions[]`, missing in the skip-wtg dataset). Result in `out/sweep_20260604_wtg_spark/`: 169/169 complete (reach+windows+components), 72 with `transitions>0`. Plan + findings: `docs/20260609_sweep_wtg_completo_169.md`.
  - **⚠️ Uncommitted gator fix in `lib/gator/*.jar`**: `FlowgraphRebuilder.java` has an arity guard (working tree only, repo `rvsec`, build 2026-06-09 19:02) that fixes a deterministic `ArrayIndexOutOfBoundsException` crash in `WTGBuilder.build()` under SPARK CG delegation (`cgDelegation=true`). **Rebuilding gator without committing this loses the fix → crashes return.** See plan doc §5b.
  - WTG is timeout-bound: ~40% of APKs complete `transitions[]`; the rest time out (even tiny apps) regardless of `cgDelegation` or timeout (1800s↔3600s yields ~nothing extra). `transitions[]` is optional for the aperv consumer (`scoreWtg→0` degrades cleanly).

---

## Skills and Agents

**Full documentation**: See `.claude/AGENTS.md` for complete reference.

### Quick Reference

**Skills** (invoke via `/skill-name`):
- `/rv-analyze-*` - Code analysis (file: qualitative, complexity, dead-code; module: complexity, dependencies, dead-code, architecture)
- `/rv-refactor-*` - Refactoring (simplify, extract, cleanup, constants)
- `/rv-test-*` - Testing (run, add)
- `/rv-qa-*` - Quality (lint, lint-fix)
- `/rv-verify` - Run all checks (tests + lint + type)
- `/rv-impact-analyzer` - Change impact analysis
- `/rv-debug-regression` - Regression bug investigation
- `/rv-doc-*` - Documentation (code, readme, generate-claude-md, architecture, adr, docs-sync)

**Orchestrators** (invoke via `/skill-name`):
- `/rv-refactor` - Code restructuring workflow
- `/rv-feature` - Feature implementation workflow
- `/rv-tdd` - Test-driven development workflow
- `/rv-cleanup` - Dead code removal workflow

**Quality Gate** (invoke via `/rv-code-reviewer`):
- `/rv-code-reviewer` - Code review (chained from orchestrators or standalone)

### Directory Structure

```
.claude/
├── AGENTS.md                # Full skill documentation (authoritative)
├── project-info.md          # Quick reference (paths, env vars)
└── skills/                  # All skills (44 total)
    └── rv-*/SKILL.md        # Skill definitions
```

---

## SDD Artifacts (Spec-Driven Development)

The system is documented via Spec-Driven Development. Specs document current behavior; changes follow the OpenSpec workflow.

### Key Artifacts

| Artifact | Path | Description |
|----------|------|-------------|
| **PRD** | `docs/PRD.md` | Product Requirements Document (37 FRs, 8 NFRs) |
| **Plan** | `docs/20260209_plano_spec_driven.md` | SDD adoption plan |
| **Config** | `openspec/config.yaml` | OpenSpec configuration (default schema, context, rules) |
| **Schema: rv-sdd** | `openspec/schemas/rv-sdd/schema.yaml` | Full/FF SDD (proposal → specs → design → tasks) |
| **Schema: quick-path** | `openspec/schemas/quick-path/schema.yaml` | Quick Path (plan → tasks) |

### Domain Specifications (7)

| Domain | Path | Modules | FRs |
|--------|------|---------|-----|
| Core | `openspec/specs/core/spec.md` | rv-android-core | FR33-FR37 |
| Platform | `openspec/specs/platform/spec.md` | rv-platform | FR07-FR11, FR14 |
| Experiment | `openspec/specs/experiment/spec.md` | rv-experiment | FR15-FR17 |
| Agent | `openspec/specs/agent/spec.md` | rv-agent | FR21-FR32 |
| Instrumentation | `openspec/specs/instrumentation/spec.md` | rv-monitor-generator, rv-instrumentation-core, rv-instrumentation, rv-instrumentation-ajc, rv-instrumentation-dexlib2 | FR01-FR03 |
| Analysis | `openspec/specs/analysis/spec.md` | rv-static-analysis, rv-coverage, rv-screen-parser | FR04-FR06, FR12-FR13 |
| Tools | `openspec/specs/tools/spec.md` | rv-tools, rv-uiautomator, rvagent-tool, aperv-tool | FR18-FR20 |

### Templates

| Template | Path |
|----------|------|
| Spec | `docs/templates/spec-template.md` |
| Design | `docs/templates/design-template.md` |
| ADR | `.claude/skills/rv-doc-adr/templates/adr.md` |

### Making Changes

All non-trivial changes follow the OpenSpec workflow. See `docs/WORKFLOW.md` for track selection (Full SDD, Fast-Forward SDD, or Quick Path). Specs are updated via delta specs in changes, then synced to main specs via `/opsx:sync`.

**Cross-referencing convention**: OpenSpec change directories use the pattern `gh<N>-<short-name>` (lowercase, no date prefix — `openspec archive` adds the date). The `proposal.md` header includes `GitHub Issue: #N`. Commits use `refs #N` during work and `closes #N` in the final commit. PRs include `Closes #N` in the body.

---

## Development Workflows

**Full reference**: `docs/WORKFLOW.md` | **Skills/Agents**: `.claude/AGENTS.md` | **Backlog**: [GitHub Kanban](https://github.com/orgs/PAMunb/projects/7)

### MANDATORY: Use OpenSpec Skills, Never Write Artifacts Manually

**This rule is non-negotiable and overrides all other instincts.** When working on any change tracked under `openspec/changes/gh<N>-*/`, you MUST follow `docs/WORKFLOW.md` rigorously and invoke the skills via the `Skill` tool. Do NOT use `Write`/`Edit` directly to create or rewrite OpenSpec artifacts.

**Forbidden** (these are common failure modes — do NOT do them):
- Writing `proposal.md`, `specs/<domain>/spec.md`, `design.md`, `tasks.md`, `plan.md`, or any ADR file directly via `Write`/`Edit` when an OpenSpec skill exists for that artifact.
- Skipping `/opsx:explore`, `/rv-impact-analyzer`, `/rv-analyze-dependencies` and going straight to writing artifacts.
- Skipping `/rv-doc-adr` for architectural decisions; skipping `/rv-risk` for designs with new dependencies, external APIs, or multi-module coordination.
- Skipping `/opsx:apply` during Phase 4 (Implement) and editing source files freelance.
- Skipping `/rv-verify` + `/opsx:verify` during Phase 5 (Verify).
- Skipping `/opsx:archive` (or the `/opsx:sync` + `/opsx:archive --skip-specs` pair) during Phase 6 (Archive).

**Correct phase → skill mapping** (Full SDD `rv-sdd` schema; see `WORKFLOW.md §6`):

| Phase | What you produce | Skill to invoke (via `Skill` tool) |
|-------|------------------|-------------------------------------|
| 1. Explore | Understanding, impact, dependency map | `/opsx:explore` + `/rv-analyze-module` + `/rv-impact-analyzer` + `/rv-analyze-dependencies` |
| 2. Propose | `proposal.md` + `specs/<domain>/spec.md` (delta) | `/opsx:new` (creates dir) → `/opsx:continue` (proposal) → `/opsx:continue` (specs) |
| 3. Design | `design.md` + `tasks.md` + ADR (if architectural) + risk register (if multi-module/external) | `/opsx:continue` (design) → `/opsx:continue` (tasks) → `/rv-doc-adr` → `/rv-risk` |
| 4. Implement | Code changes + tests, checkboxes flipped in `tasks.md` | `/opsx:apply` + component skills (`/rv-test-run`, `/rv-test-add`, `/rv-doc-code`, `/rv-qa-lint-fix`) → `/rv-code-reviewer` |
| 5. Verify | Tests pass, lint clean, types check, specs match | `/rv-verify` + `/opsx:verify` |
| 6. Archive | Synced specs, change moved to `archive/`, docs updated | `/opsx:archive` (or `/opsx:sync` then `/opsx:archive --skip-specs`) + `/rv-docs-sync` |

**Fast-Forward SDD** (`/opsx:ff`) collapses Phases 2-3 into one skill invocation; **Quick Path** (`--schema quick-path`) uses `plan.md` + `tasks.md` only. See `WORKFLOW.md §7-§8`.

**OpenSpec CLI commands** (when invoking skills isn't enough — see `WORKFLOW.md §13`):

```bash
openspec list                                       # List active changes (all schemas)
openspec status --change "<name>"                   # Artifact completion status (all schemas)
openspec instructions <artifact> --change "<name>"  # Template + context for an artifact
openspec instructions apply --change "<name>"       # Implementation instructions
openspec validate "<name>"                          # Structural validation — rv-sdd only (positional, not --change)
openspec show "<name>" --json                       # Inspect a change/spec — rv-sdd only
openspec archive "<name>"                           # Archive + sync delta specs
openspec archive "<name>" --skip-specs              # Archive without syncing (Quick Path / docs-only)
```

**`validate`/`show` are rv-sdd-only**: both require a `proposal.md` in the change directory. Quick Path changes (`plan.md` + `tasks.md`, no `proposal.md`) report `Unknown item` — this is expected, not a malformed change. Use `openspec status --change "<name>"` and `openspec list` for Quick Path. See `WORKFLOW.md §13` (Quick Path caveat).

**Resume protocol** (when picking up an in-flight change in a new session):
1. Read `proposal.md`, `design.md` (or `plan.md` for Quick Path), and `tasks.md` in the change directory.
2. `openspec status --change "<name>"` to see which artifacts are done.
3. Count `[x]` vs `[ ]` checkboxes in `tasks.md` to find the first pending task.
4. Continue with the appropriate skill — `/opsx:continue` if artifacts are missing, `/opsx:apply` if implementation is in progress.
5. NEVER re-run `/opsx:apply` as if starting fresh — it reads checkboxes automatically.

**If a Phase 0 ideation document exists** (e.g. `docs/<date>_plano_*.md`), treat it as authoritative for decisions already taken — do NOT relitigate them in Phase 1/2 unless the user explicitly asks. Phase 0 outputs are inputs to `/opsx:explore` and `/opsx:new`.

### Track Selection

Select track by whether the change requires **design decisions** (not by file count — file count determines subagent use, not track):

| Track | When | Schema | Phases |
|-------|------|--------|--------|
| **Full SDD** | Design decisions + multi-module/architectural | `rv-sdd` | Explore -> Propose -> Design -> Implement -> Verify -> Archive |
| **FF SDD** | Design decisions + single module, clear requirements | `rv-sdd` | Explore -> FF -> Implement -> Close |
| **Quick Path** | No design decisions, mechanical/clear plan | `quick-path` | Analyze -> Plan -> Execute+Verify |

### Common Scenarios

Sequences below are abbreviated. See `docs/WORKFLOW.md` Sections 6-8 for full phase detail.

| Scenario | Track | Skill Sequence |
|----------|-------|----------------|
| New feature in rv-agent | Full | `opsx:explore` -> `opsx:new` -> `opsx:continue` (x4) -> `opsx:apply` -> `rv-verify` -> `opsx:verify` -> `opsx:archive` |
| Add config option | FF | `rv-analyze-file` -> `opsx:ff` -> `opsx:apply` -> `rv-verify` -> `opsx:verify` -> `opsx:archive` |
| Refactor internals | Quick | plan.md -> tasks.md -> `rv-refactor` -> `rv-verify` -> `archive --skip-specs` |
| Fix a bug | Quick | plan.md -> tasks.md -> `rv-tdd` -> `rv-verify` -> `archive --skip-specs` |
| Remove dead code | Quick | plan.md -> tasks.md -> `rv-cleanup` -> `rv-verify` -> `archive --skip-specs` |

### Subagent Orchestration

When a task touches **20+ files** or has **3+ independent task groups**, use subagents. Main window acts as orchestrator: reads plan, dispatches subagents (3-15 files each), collects summaries, runs final verification. See `docs/WORKFLOW.md` Section 5 for details.

---

## Claude Code Configuration

### MCP Servers (configurados via `claude mcp add --scope user`)
- **context7**: Docs atualizadas de bibliotecas (`npx -y @upstash/context7-mcp`)
- **sequential-thinking**: Raciocínio estruturado (`npx -y @modelcontextprotocol/server-sequential-thinking`)
- **memory**: Memória persistente entre sessões (`npx -y @modelcontextprotocol/server-memory`)
- **github**: GitHub API para issues, PRs, projects (`docker run ghcr.io/github/github-mcp-server`)

### Incompatibilidades Conhecidas
- **gemini MCP** (`github:aliargun/mcp-server-gemini`): Schema usa oneOf/allOf/anyOf - incompatível com API Anthropic
- **pyright-lsp plugin**: Causa erro de LSP na inicialização - não usar

### Arquivos Locais (gitignored)
- `.claude/.mcp.json` - Contém API keys
- `.claude/memory.json` - Estado local do MCP memory
- `.claude/settings.local.json` - Configuração local
