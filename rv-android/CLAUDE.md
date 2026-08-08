# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Architecture Overview

RV-Android is a modular framework for runtime verification of Android applications with LLM-driven testing. It uses a uv workspace: modules live under `modules/`, installed in editable mode into a shared `.venv` by a single `uv sync` at root.

### Core Architecture Principles
- **Modular Design**: uv workspace modules in editable mode with clear dependencies and interfaces.
- **Component-Based Execution**: `TaskExecutor` uses pluggable components (initialize/execute/cleanup lifecycle) for each execution phase.
- **Configuration Management**: unified configuration across modules via Pydantic models; validate at module boundaries.
- **Error Handling**: `ErrorHandler` decorators for context-aware errors, cleanup, and graceful degradation.

## Module map

Each module has its own `CLAUDE.md` — consult it for module-scoped detail. The instrumentation family is: `rv-instrumentation-core` (pure ABC + types) ← the `ajc`/`dexlib2` variant impls, with `rv-instrumentation` (parent) providing the `get_instrumenter()` factory. The canonical production set is 16 modules (`aperv-llm-validation` is a temporary validation module, excluded).

| Module | 1-line role | Key dep |
|---|---|---|
| rv-android-core | Foundation: domain models, `ErrorHandler`, `LoggingManager` | (none) |
| rv-platform | Central execution platform; coordinates `TaskExecutor` + result processing | rv-android-core, rv-tools |
| rv-tools | Testing-tool plugin system (registry + factory) | rv-android-core |
| rv-uiautomator | Shared UIAutomator components for direct device interaction | rv-android-core |
| rv-monitor-generator | JavaMOP/RV-Monitor integration → runtime verification monitors | rv-android-core |
| rv-instrumentation-core | `Instrumenter` ABC + shared Pydantic result types; zero impl deps (avoids cycle) | rv-android-core |
| rv-instrumentation | Parent canonical: `get_instrumenter(variant, config)` factory; shared `assets/keystore.jks`; re-exports `-core` API | rv-instrumentation-core |
| rv-instrumentation-ajc | AspectJ variant `AjcInstrumentation` (dex2jar+ajc+d8) | rv-instrumentation-core only |
| rv-instrumentation-dexlib2 | DEX-native variant `DexlibInstrumentation` (gh52) | rv-instrumentation-core only |
| rv-static-analysis | Unified GATOR-based static analysis | rv-android-core |
| rv-coverage | Coverage analysis/tracking for monitored operations | rv-android-core |
| rv-screen-parser | Android UI parsing (visitor patterns) for state analysis | rv-android-core |
| rv-agent | LLM-driven testing tool; LangGraph workflow orchestration | rv-android-core |
| rvagent-tool | rv-platform plugin wrapping rv-agent as an `AbstractTool` | rv-tools, rv-agent |
| aperv-tool | rv-platform plugin wrapping the APE-RV binary (`ape-rv.jar`) | rv-tools |
| rv-experiment | Experiment orchestration (pre/post processing); does not duplicate rv-platform | rv-platform |
| aperv-llm-validation | Temporary: offline validation for APE-RV LLM coordinate mapping | (temporary) |

Child aggregator with its own `CLAUDE.md`: `experimento-20260604/CLAUDE.md`.

## Development Commands

### Environment and Installation
```bash
uv sync                      # install ALL modules (editable, shared .venv); or: cd modules && ./install.sh
```
Source changes are immediate — no reinstall unless a `pyproject.toml` changes.

| Env var | Purpose |
|---|---|
| `RVSEC_HOME` | Required for monitor generation + static analysis (path to RVSEC install). Without it, both are skipped. |
| `ANDROID_HOME` | Android SDK path for emulator management. |
| `RV_PYDANTIC=true` | Enable dev validation (recommended during development). |
| `RVAGENT_MODE` | Override rv-agent mode (`pure_algorithm`, `llm_only`, `multimode`). |
| `RV_EMULATOR_BOOT_TIMEOUT` | Total emulator boot budget in seconds (default 300, provisional). Raise it when boot timeouts appear. |
| `RV_ADB_CMD_TIMEOUT` | Timeout in seconds for each individual ADB probe during the boot wait (default 30). |
| `RV_APK_INSTALL_TIMEOUT` | Timeout in seconds for `adb install` (default 600). |

See `.claude/project-info.md` for the full env-var, Docker, and command reference.

### Testing and Quality
**CI contract**: always run pytest with `--import-mode=importlib -o "addopts="`. Without these, conftest isolation breaks across modules and collection fails; CI (`.github/workflows/ci.yml`) runs each module's tests in isolation with these flags. Full loop and lint commands: `.claude/project-info.md`.

### Experiment Execution
```bash
uv run rv-experiment run --tools monkey,droidbot:dfs_greedy --specification-set jca
uv run rv-experiment run --tools monkey --name my_experiment   # auto-resume on re-run
uv run rv-platform run --tools monkey --apks-dir ./apks_examples
```

### RV-Agent
Two modes: **standalone CLI** (`rv-agent` — user manages emulator/APK) or **via rv-experiment** (`rvagent` tool — platform manages everything).
```bash
uv run rv-experiment run --tools rvagent:pure_algorithm --apks-dir ./apks_examples --timeouts 60
cd modules/rv-agent && uv run rv-agent run --package br.unb.cic.cryptoapp --mode pure_algorithm --timeout 60
```

## Execution Flow

### Entry Points
- **rv-experiment** (`rv_experiment/__main__.py`): orchestration — pre-processing (instrumentation, static analysis) → execution → post-processing.
- **rv-platform** (`rv_platform/__main__.py`): direct task execution without the experiment wrapper.
- **rv-agent** (`rv_agent/cli/main.py`): standalone LLM-driven testing (modes: pure_algorithm, llm_only, multimode).

### Core Flow
`ExperimentController` → `ExecutionController` → `Platform` → `TaskExecutor` (component-based: emulator, static analysis, coverage, logcat, tool execution).

### RV-Agent Architecture
- **RVAgent** (`agent/rv_agent.py`): LangGraph workflow with externalized nodes in `agent/nodes/` (parse, decision, algorithm, llm, validation, execute, learn).
- **RVAgentStrategy** (`strategies/rvagent_strategy/`): DFS-based exploration with Successor Tracker, Plateau Detector, MOP Prioritization.
- **LLMClient** (`llm/llm_client.py`): Qwen3-VL via SGLang (OpenAI-compatible API).

## Directory Structure and Cleanup

Key directories: `out/` (temporary artifacts — monitors, instrumented APKs, static analysis), `results/` (persistent experiment results), `apks_examples/` (source APKs).
```bash
./clear.sh                 # clean temporary artifacts (keeps results/)
./clear.sh --clean-results # clean everything including results
```
**Gotcha**: with `--skip-monitors`/`--skip-instrument`/`--skip-static`, `--apks-dir` must point to **instrumented** APKs from a previous run (`results/<id>/instrumented_apks/`), not original APKs — otherwise coverage is 0%.

See `.claude/project-info.md` for the full directory tree and pre-processed artifact locations.

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

## Development Guidelines

### Code Structure
- Use English for all code and comments.
- When writing in Portuguese (Brazilian), always use correct accentuation (acentos, cedilha, til, etc.). The user may omit accents in their messages (non-ABNT keyboard), but Claude must always write Portuguese correctly.
- Include detailed comments at critical architectural points — explain *why*, not just *what*. Follow the comment template in `ExecutionManager`, `TaskExecutor`.

### Git Commits
- NEVER add `Co-Authored-By` or any co-author trailer to commit messages. The user is the sole author.

### Emulator Management — DO NOT TOUCH
- **NEVER start, stop, or manage Android emulators manually.** rv-platform manages the entire emulator lifecycle automatically (start, boot wait, APK install, cleanup). This applies to ALL contexts: E2E validation, experiments, testing, debugging — no exceptions.
- Do NOT run `emulator` commands, `adb emu kill`, or any emulator-related shell commands. If a task requires an emulator, use `rv-experiment run` or `rv-platform run` — they handle everything.
- This rule is PERMANENT and must NEVER be removed from this file.

### Constants
- Use constants instead of magic values whenever possible. Main constant files:
  - `modules/rv-android-core/src/rv_android_core/constants.py`
  - `modules/rv-experiment/src/rv_experiment/constants.py`
- Each module may have its own constants file.

## Important Implementation Notes

### Specification Sets (Runtime Verification)
The system supports three distinct specification sets, used **separately** across experiments (one experiment instruments with JCA, another with generic):

1. **JCA Specifications** (`--specification-set jca`): detect misuse of the Java Cryptography Architecture (JCA) API — e.g. proper cipher initialization, key generation, secure random.
2. **JCA Android Specifications** (`--specification-set jca_android`): the same 23 specifications derived against generated CrySL rules for a declared Android API level. It is the set that carries the specification repairs; `jca` is frozen against the measurements published from it.
3. **Generic Specifications** (`--specification-set generic`): detect violations of general API usage — e.g. `hasNext()` before `next()` on Iterator; close streams after use.

A fourth value, `custom`, takes a directory of `.mop` files via `--custom-specs-dir`.

**Important**: "MOP" (Monitored Operations) refers to operations monitored by ANY specification, not specifically security-related ones. Do NOT use "security" terminology for MOP — use "monitored operations".

### RV-Agent Specifics
- Uses LangGraph for workflow orchestration.
- SGLang server required for the LLM backend (default: `http://192.168.0.36:30000/v1`).
- Default model: `Qwen/Qwen3-VL-4B-Instruct`.
- Multimode default: 70% LLM / 30% algorithm decisions.

### Tool Calling Híbrido (Qwen3-VL + SGLang)
SGLang lacks official tool calling for Qwen3-VL (~50% native, ~50% XML). Hybrid approach: try `bind_tools()` native first, fallback to XML/JSON parsing via `rv_agent/llm/tools/tool_call_parser.py`. Both strategies achieve 100% success.

### Qwen3-VL Coordinate System
- Qwen3-VL returns coordinates in normalized `[0, 1000)` range for both x and y.
- Conversion to device pixels: `pixel_x = int((x / 1000) * device_width)`.
- `ActionNormalizer` in `domain/action.py` handles this via `denormalize_qwen_coords()`.
- Reference: https://github.com/QwenLM/Qwen3-VL/issues/1486
- Validated empirically: 84.2% hit rate with 20 apps (see `docs/20260107_rvagent_validacao_multimodal.md`).

## Skills and Agents

Full documentation: see `.claude/AGENTS.md` (authoritative reference for skills and orchestrators). Quick paths/env vars: `.claude/project-info.md`.

## SDD Artifacts (Spec-Driven Development)

The system is documented via Spec-Driven Development: specs document current behavior; changes follow the OpenSpec workflow. Key entry points:
- Domain specs and the 7-domain → module → FR/NFR mapping: `openspec/specs/README.md`.
- Product requirements (37 FRs, 8 NFRs): `docs/PRD.md`.
- Workflow (track selection, phase→skill mapping, CLI, resume protocol): `docs/WORKFLOW.md`.

**Cross-referencing convention**: OpenSpec change directories use `gh<N>-<short-name>` (lowercase, no date prefix — `openspec archive` adds the date). `proposal.md` header includes `GitHub Issue: #N`; commits use `refs #N` during work and `closes #N` in the final commit; PRs include `Closes #N`.

## Development Workflows

Full reference: `docs/WORKFLOW.md`. Skills/Agents: `.claude/AGENTS.md`. Backlog: [GitHub Kanban](https://github.com/orgs/PAMunb/projects/7).

### MANDATORY: Use OpenSpec Skills, Never Write Artifacts Manually

**This rule is non-negotiable and overrides all other instincts.** When working on any change tracked under `openspec/changes/gh<N>-*/`, you MUST follow `docs/WORKFLOW.md` rigorously and invoke the skills via the `Skill` tool. Do NOT use `Write`/`Edit` directly to create or rewrite OpenSpec artifacts.

## Claude Code Configuration

MCP servers (user scope) — see `.claude/project-info.md` for the full list/setup. **Known incompatibilities**: `gemini` MCP (`github:aliargun/mcp-server-gemini`) uses oneOf/allOf/anyOf schemas incompatible with the Anthropic API; the `pyright-lsp` plugin errors on LSP init — do not use either.
