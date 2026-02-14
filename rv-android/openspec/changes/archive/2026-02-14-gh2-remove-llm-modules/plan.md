# Change Plan: Remove Discontinued LLM Modules

**Date**: 2026-02-13
**Track**: Quick Path
**Priority**: Medium
**GitHub Issue**: [#2](https://github.com/PAMunb/rvsec/issues/2)
**PRD Reference**: Section 12.2 Item 6
**Domains**: agent, tools, experiment

## 1. Context

RV-Android explored three distinct approaches to integrating LLMs with Android test generation before converging on the agentic approach that became rv-agent. Each approach was implemented as a separate module with its own testing tool, and all three of the earlier approaches shared a common LLM abstraction layer called rv-llm. This plan removes those three discontinued modules and their shared dependency from the active codebase.

The first approach, **pure prompt engineering**, produced two tools. **rvandroid** was built on top of DroidBot's exploration engine — DroidBot's policy captured the device state and sent it via REST to rvandroid, which used rv-llm's PromptFramework (a 3-layer architecture with Information, Template, and Strategy layers) to construct prompts that the LLM converted into actions. The dependency on DroidBot's state-transition model severely constrained the LLM's ability to make autonomous decisions. **rvsmart** removed DroidBot and used UIAutomator directly for device interaction, but retained the same prompt engineering approach through rv-llm. Neither tool reached a functional state sufficient for the thesis experiments.

The second approach, **LLM as guidance**, produced **rvdroid**. Rather than having the LLM generate actions directly, rvdroid used a GuidanceService where the LLM returned GuidanceDecision objects — strategic advice, flow change recommendations, or deference to the algorithm. An algorithmic engine made the actual action decisions. Development was discontinued before the guidance integration was complete.

The third and final approach, **agentic**, produced **rv-agent**, which is the production tool. rv-agent uses LangGraph for workflow orchestration where the VLM (Qwen3-VL with vision capabilities) is a first-class decision-maker that generates device actions via tool calling, maintains structured memory systems, and participates in hybrid routing with algorithmic strategies. Critically, rv-agent uses langchain-openai directly for LLM communication rather than the rv-llm abstraction layer, which means rv-llm has zero active consumers.

The rvandroid-tool directory was already deleted in an earlier cleanup, but ghost references to it persist in experiment registration code, shell scripts, CLI examples, and documentation. This plan addresses those ghost references alongside the removal of the three modules that still exist in the workspace (rv-llm, rvsmart-tool, rvdroid-tool).

Per Principle P3 (No Backward Compatibility), module directories are moved to `backup/` rather than deleted outright, preserving the originals for thesis records while removing them from the active codebase. The `backup/` directory is gitignored.

## 2. Scope

### Modules to remove

Three module directories still exist under `modules/` and must be moved to `backup/`:

| Module | Package | Status | Why it has zero consumers |
|--------|---------|--------|---------------------------|
| `rv-llm` | `rv_llm` | Deprecated | rv-agent uses langchain-openai directly; rvsmart and rvdroid were the only consumers |
| `rvsmart-tool` | `rvsmart_tool` | Discontinued | Prompt engineering approach abandoned; never reached experiment-ready state |
| `rvdroid-tool` | `rvdroid_tool` | Discontinued | LLM-as-guidance approach abandoned; development incomplete |

### Ghost references to clean

In addition to the three modules above, **rvandroid-tool** (the DroidBot-based prompt engineering tool) was deleted from `modules/` in an earlier cleanup but left behind references throughout the codebase. These ghost references cause confusion when reading experiment code, CLI help text, and documentation — they suggest a tool that no longer exists. This plan cleans all four sets of references in a single pass.

| Module | Package | Status | Where ghosts remain |
|--------|---------|--------|---------------------|
| `rvandroid-tool` | `rvandroid_tool` | Deleted | experiment_tools.py registration, constants.py, CLI examples, shell script MODULES arrays, documentation |

## 3. Complete File Inventory

The inventory below lists every file that must be modified or moved, organized into eight groups. Groups A-C are prerequisite operations (moves and dependency changes). Groups D-E are Python and shell source edits. Groups F-H are Docker and documentation updates. Groups D-E and F-H are independent of each other and can be dispatched to parallel subagents.

### Group A — Move module directories to `backup/`

The three discontinued module directories are moved intact to `backup/`, preserving their full contents for thesis records. After this step, `modules/` contains only active modules.

| Source | Destination |
|--------|-------------|
| `modules/rv-llm/` | `backup/rv-llm/` |
| `modules/rvsmart-tool/` | `backup/rvsmart-tool/` |
| `modules/rvdroid-tool/` | `backup/rvdroid-tool/` |

### Group B — Move root test scripts to `backup/`

Twelve test scripts in the project root import from the discontinued modules. These scripts were used during development of the earlier LLM approaches and have no value in the active codebase. They are moved to `backup/teste_scripts/` to keep the backup directory organized.

| Script | Imports from discontinued modules |
|--------|-----------------------------------|
| `teste_rv_llm.py` | `rv_llm` |
| `teste_rv_llm_server.py` | `rv_llm`, `rvandroid_tool` |
| `teste_rv_llm_service.py` | `rv_llm` |
| `teste_rv_llm_frontier.py` | `rv_llm` |
| `teste_rv_llm_prompt.py` | `rv_llm`, `rvsmart_tool` |
| `teste_rv_llm_prompt_tutorial.py` | `rv_llm` |
| `teste_rvsmart.py` | `rv_llm`, `rvsmart_tool` |
| `teste_rvdroid.py` | `rv_llm`, `rvdroid_tool` |
| `teste_rvdroid_updated.py` | `rv_llm`, `rvdroid_tool` |
| `teste_rv_evaluator.py` | `rv_llm` |
| `teste_prompt_framework.py` | `rvandroid` (old monolithic package) |
| `teste_rv_experiment.py` | `rvandroid` ToolConfigs, `rvandroid_tool`, `rv_llm` |

Additionally, `main.py` (the legacy root entry point) imports `rv_llm.config.configuration`, `rv_llm.config.configuration_manager`, and `rv_llm.llm.ollama_llm`. This file predates the rv-experiment CLI and is no longer used. It is moved to `backup/main.py`.

### Group C — pyproject.toml cleanup

The Poetry workspace root and rv-experiment's own pyproject.toml both declare path dependencies on the discontinued modules. Removing these entries and re-locking ensures that `poetry install` no longer attempts to resolve modules that have been moved to `backup/`.

**Root `pyproject.toml`** — remove 3 dependency lines:
```
rv-llm = {path = "modules/rv-llm", develop = true}
rvsmart-tool = {path = "modules/rvsmart-tool", develop = true}
rvdroid-tool = {path = "modules/rvdroid-tool", develop = true}
```

**`modules/rv-experiment/pyproject.toml`** — remove 2 dependency lines:
```
rv-llm = {path = "../rv-llm", develop = true}
rvdroid-tool = {path = "../rvdroid-tool", develop = true}
```

After edits: `poetry lock && poetry install`

### Group D — rv-experiment Python source cleanup

rv-experiment is the module most heavily affected because it served as the integration point for all testing tools, including the discontinued ones. The experiment tool registry, configuration validation, CLI help text, and configuration factory all contain references that must be cleaned.

#### D1. `modules/rv-experiment/src/rv_experiment/tools/experiment_tools.py`

| Action | Lines | Detail |
|--------|-------|--------|
| Remove method | 110-124 | `_register_rvandroid_tool()` — dead import of `rvandroid_tool.tools.rvandroid.tool.RVAndroidTool` |
| Remove call | 94 | `self._register_rvandroid_tool()` |
| Remove method | 126-139 | `_register_rvdroid_tool()` — dead import of `rvdroid_tool.tools.tool.RVDroidTool` |
| Remove call | 97 | `self._register_rvdroid_tool()` |
| Update method | ~165 | `_log_registration_summary()` — remove RVANDROID and RVDROID from iteration list |
| Update docstring | 80-82 | Remove `rvandroid-tool` and `rvdroid-tool` references |

#### D2. `modules/rv-experiment/src/rv_experiment/constants.py`

| Action | Line | Detail |
|--------|------|--------|
| Remove constant | 64 | `EXTERNAL_TOOL_RVANDROID = "rvandroid"` |
| Remove constant | 65 | `EXTERNAL_TOOL_RVDROID = "rvdroid"` |

#### D3. `modules/rv-experiment/src/rv_experiment/config.py`

| Action | Line(s) | Detail |
|--------|---------|--------|
| Remove block | ~324 | `if tool_config.name == "rvandroid":` custom variant validation |
| Remove block | ~753-755 | `elif module_name == "rv-llm": return {}` fallback |
| Remove comments | ~590-594 | `# REMOVED: get_llm_config()...` dead comments (P4 violation) |
| Remove comment | ~739 | `# **rv-llm**: LLM integration configuration...` |

#### D4. `modules/rv-experiment/src/rv_experiment/__main__.py`

| Action | Line(s) | Detail |
|--------|---------|--------|
| Remove examples | 186-187 | rvandroid tool spec example in docstring |
| Remove examples | 269-271 | rvandroid variant/parameter examples |
| Remove example | 304 | rvandroid in `--tools` help text |
| Remove example | 383 | rvandroid in usage examples |
| Remove block | 661-663 | rvandroid availability note in `list-tools` |

#### D5. `modules/rv-experiment/src/rv_experiment/factories/configuration_factory.py`

| Action | Line | Detail |
|--------|------|--------|
| Update | ~244 | `create_llm_template()` — replace `ToolConfig(name="rvandroid", ...)` with `ToolConfig(name="rvagent", ...)` |

#### D6. `modules/rv-experiment/src/rv_experiment/experiment/workflow/workflow_factory.py`

| Action | Line | Detail |
|--------|------|--------|
| Fix P4 | 1 | Comment `# rvandroid/experiment_workflow/workflow_factory.py` — replace with current-state path |

#### D7. `modules/rv-experiment/src/rv_experiment/experiment/workflow/__init__.py`

| Action | Line | Detail |
|--------|------|--------|
| Fix P4 | 1 | Comment `# rvandroid/experiment/workflow/__init__.py` — replace with current-state path |

### Group E — Shell scripts (MODULES arrays)

The three shell utility scripts (`clean.sh`, `lock.sh`, `test.sh`) each contain a hardcoded `MODULES` array that is doubly outdated: it includes modules that no longer exist (`rv-llm`, `rvandroid-tool`) and is missing modules that were added after the arrays were last updated (`rv-agent`, `rvagent-tool`, `rv-agent-validation`, `rv-uiautomator`). The arrays must be corrected to reflect the current set of active modules.

#### E1. `modules/clean.sh` (lines 14-26)

Remove `rv-llm` and `rvandroid-tool`. Add `rv-uiautomator`, `rv-agent`, `rvagent-tool`, `rv-agent-validation`. Also update help text at lines 339-350.

#### E2. `modules/lock.sh` (lines 14-27)

Same corrections as clean.sh. Also update help text (lines 364-376) and example (line 382: replace `rv-llm` example with `rv-agent`).

#### E3. `modules/test.sh` (lines 14-27)

Same corrections as clean.sh. Also update help text (lines 396-407).

#### E4. `modules/install.sh`

No `MODULES` array — uses `poetry install` from root. The `verify_installation()` function checks only active modules. **No changes needed**.

### Group F — Docker cleanup

The development Dockerfile contains a sed hack that strips the discontinued module dependencies from pyproject.toml at image build time. After Group C removes these dependencies from the source files, the sed hack becomes unnecessary and should be deleted to avoid confusion.

**`docker/rvandroid_dev/Dockerfile`** — remove lines 45-49 (the sed hack) and simplify the comment at lines 29-30 that explains the excluded modules.

Note: Docker image names (`phtcosta/rvandroid_base`, `phtcosta/rvandroid_tools`, etc.) contain "rvandroid" as part of the project branding on Docker Hub. These are not references to the discontinued rvandroid-tool module and are left unchanged.

### Group G — Documentation updates (active source docs)

References to the discontinued modules appear throughout the project documentation — module lists, dependency tables, spec descriptions, and architecture diagrams. Each reference must be removed or updated to reflect the current module set where rv-agent is the sole LLM testing tool.

#### G1. `CLAUDE.md` (root)
- Remove rv-llm from "System Modules" list and "LLM Testing" block
- Remove rvandroid/rvdroid references from tool lists and execution flow
- Update module count and numbering

#### G2. `README.md` (root)
- Remove rv-llm and rvandroid-tool from the module directory tree and description table

#### G3. `docs/PRD.md`
- Remove `rv-llm (deprecated)` block from module diagram (line 140)
- Remove rv-llm row from dependency table (line 155)
- Remove `rv-llm (unused import)` from rv-experiment deps (line 163)
- Mark rv-llm as removed in module status table (line 944)
- Mark Section 12.2 Item 6 as **completed** (line 956)

#### G4. `docs/SDD.md`
- Remove `rv-llm` from agent spec description (line 1309)

#### G5. `openspec/specs/agent/spec.md`
- Remove rv-llm from domain scope description (lines 4-5)

#### G6. `openspec/specs/tools/spec.md`
- Remove rvandroid/rvdroid from external tool registration text (lines 14, 85)
- Remove tool registration scenario mentioning rvandroid and rvdroid (lines 220-226)

#### G7. `openspec/specs/README.md`
- Remove `rv-llm` from agent domain modules (line 12)

#### G8. `modules/rv-experiment/CLAUDE.md`
- Remove rvandroid/rvdroid from tool registration responsibilities and examples
- Update external tools list to show only rvagent

#### G9. `modules/rv-experiment/docs/architecture.md`
- Remove rv-llm dependency row (line 276) and configuration reference (line 715)

### Group H — Claude Code configuration docs

The `.claude/` directory contains project metadata and skill definitions that reference rv-llm in module lists, dependency trees, and release checklists. These must be updated so that Claude Code's context about the project accurately reflects the current module set.

#### H1. `.claude/project-info.md`
- Remove rv-llm from module table (line 21) and infrastructure list (line 131)

#### H2. `.claude/skills/` (7 files)

| File | Action |
|------|--------|
| `rv-feature/templates/discovery-report.md` | Remove rv-llm row from module table |
| `rv-analyze-dependencies/SKILL.md` | Remove rv-llm from dependency tree and layer list |
| `rv-release/SKILL.md` | Remove rv-llm from release order |
| `rv-analyze-module/SKILL.md` | Remove rv-llm from module list |
| `rv-release/checklists/release-checklist.md` | Remove rv-llm from release checklist (2 locations) |
| `rv-refactor/templates/analysis-report.md` | Remove rv-llm from module tree |
| `rv-refactor/examples/analysis-example.md` | Remove rv-llm from module tree |

### Additional fixes discovered during implementation

The following files were not in the original inventory but were found during the verification grep sweep. They contain P4 violations (historical comments referencing discontinued modules) or dead code:

| File | Issue | Fix |
|------|-------|-----|
| `modules/rv-uiautomator/src/rv_uiautomator/adapter/base.py` | Comment "Provides unified API for both rvsmart and rvdroid tools" | Update to "Provides unified API for all testing tools" |
| `modules/rv-agent/src/rv_agent/memory/agent_memory.py` | Comments "Inspired by rvsmart-tool's MemoryManager" | Remove historical attribution |
| `modules/rv-agent/src/rv_agent/domain/state.py` | Comment "inspired by rvsmart-tool" | Remove historical attribution |
| `modules/rv-android-core/src/rv_android_core/util/error/error_handler.py` | `_handle_rvandroid_tool_error()` method + registration — dead code, only backup/ modules raised this exception | Remove handler method, registration, and import |
| `modules/rv-android-core/src/rv_android_core/util/error/error_handler.py` | Line 1 comment `# rvandroid/util/error/error_handler.py` | Fix P4: update to current module path |
| `modules/rv-android-core/src/rv_android_core/util/error/exceptions.py` | Two `RVAndroidToolError` class definitions (lines 122, 204) — dead code, only backup/ modules raised this exception | Remove both class definitions |
| `modules/rv-android-core/tests/util/error/test_error_handler.py` | `test_builtin_handlers_registered` asserts 28 handlers | Update to 27 (removed RVAndroidToolError handler) |
| `modules/rv-android-core/tests/util/error/test_error_handler_comprehensive.py` | `test_all_builtin_handlers_registered` asserts 28 handlers | Update to 27 |
| `openspec/specs/core/spec.md` | ErrorHandler handler list mentions RVAndroidToolError | Remove from list, update count from "30+" to "27+" |
| `modules/rv-tools/README.md` | Code example creating `rvandroid` tool | Update example to use `rvagent` tool |
| `modules/rv-screen-parser/README.md` | References to rvandroid-tool and rv-llm in integration points | Update to rv-agent |
| `modules/rv-android-core/README.md` | Reference to rv-llm | Update to rv-agent |
| `openspec/config.yaml` | "agent: rv-agent + rv-llm" in domain list | Remove rv-llm |

## 4. Execution Order

Groups are ordered by dependency. Groups A-C must run sequentially (moves before dependency cleanup before poetry install). After that, D+E and F+G+H are independent and can run as parallel subagent dispatches per Section 5 of WORKFLOW.md.

1. **Group A**: Move module directories to `backup/`
2. **Group B**: Move root test scripts and `main.py` to `backup/`
3. **Group C**: Clean pyproject.toml files + `poetry lock && poetry install`
4. **Groups D+E** (subagent 1): Clean rv-experiment Python source + shell scripts (10 files)
5. **Groups F+G+H** (subagent 2): Docker + documentation + Claude Code config (18 files)
6. **Additional fixes**: P4 violations and dead code found during verification (9 files)
7. **Verification**: Run full acceptance criteria

## 5. Acceptance Criteria

- [x] 3 module dirs moved to `backup/`
- [x] 12 root test scripts + `main.py` moved to `backup/`
- [x] pyproject.toml files cleaned (root: 3 lines, rv-experiment: 2 lines)
- [x] `poetry install` succeeds without the 3 modules
- [x] `poetry run pytest modules/rv-experiment/tests/ -v` passes (11/11)
- [x] `poetry run pytest modules/rv-tools/tests/ -v` passes (3/3)
- [x] `poetry run pytest modules/rv-android-core/tests/util/error/ -v` — error handler tests pass (27 handlers)
- [x] Shell scripts (clean.sh, lock.sh, test.sh) MODULES arrays updated with correct active module list
- [x] Docker image builds without sed hack (`phtcosta/rvandroid_dev:test`)
- [x] Docker smoke test: only active tools registered (ape, monkey, ares, droidbot, fastbot, humanoid, rvagent — no rvandroid/rvdroid)
- [x] Zero grep hits for `rv_llm`, `rvsmart_tool`, `rvdroid_tool`, `rvandroid_tool` in active Python source (excluding `backup/`)
- [x] Zero grep hits for `rv-llm`, `rvsmart-tool`, `rvdroid-tool`, `rvandroid-tool` in active docs/config (excluding `backup/`, `plan.md`, `archive/`, PRD Section 6 historical narrative)
- [x] Zero grep hits for `RVAndroidToolError` in active source (excluding `backup/`, `plan.md`)
- [x] PRD Section 12.2 Item 6 marked as completed
- [x] All specs, CLAUDE.md, README.md, SDD.md updated
- [x] Claude Code skills/project-info updated
- [x] P4 violations in comments referencing discontinued modules fixed
- [x] Dead `RVAndroidToolError` class definitions removed from exceptions.py
- [x] Dead `RVAndroidToolError` handler removed from error_handler.py

## 6. File Count Summary

| Group | Files | Type |
|-------|-------|------|
| A | 3 dirs | Move to backup |
| B | 13 files | Move to backup (12 test scripts + main.py) |
| C | 2 files | Edit pyproject.toml |
| D | 7 files | Edit Python source |
| E | 3 files | Edit shell scripts |
| F | 1 file | Edit Dockerfile |
| G | 9 files | Edit docs/specs |
| H | 8 files | Edit Claude Code config |
| Extra | 12 files | P4 fixes + dead code + tests found during verification |
| **Total** | **~58 files** | |
