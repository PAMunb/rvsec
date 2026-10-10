GitHub Issue: #126

## Why

The workspace dependency graph that the `pyproject.toml` files declare does not match the one the code imports, in both directions, and the foundation module sits in a cycle. The skill script `.claude/skills/rv-analyze-dependencies/scripts/workspace_deps.py` (run on 2026-10-10 from the rv-android root) reports three kinds of deviation:

- **A cycle `rv-android-core → rv-coverage → rv-android-core`.** `Task.get_repository()` (`rv_android_core/domain/task.py:690`) lazily imports `rv_coverage.parser.log.logcat_parser.parse_logcat_file` (`:709`) to re-read a persisted logcat, and rv-coverage imports the core. No code under any module's `src/` calls `get_repository()`; only `tests/domain/test_task.py:933-1017` does. Re-reading the logcat on resume belongs to rv-platform (`ResultProcessorComponent._reconstruct_repository_from_logcat`, `result_processor.py:445`). rv-platform already depends on rv-coverage, and it also forwards `tool_execution_start` (INV-PLT-23), which `get_repository()` does not. Three sibling methods, `Task.add_error`, `Task.add_method_call` and `Task.update_coverage`, have no `src/` caller either.
- **One import the graph does not declare.** `rv_platform/__init__.py:32` imports `aperv_tool` to register `ApeRVTool`. rv-platform's `pyproject.toml` declares `rvagent-tool`, the other external plugin it registers the same way, but does not declare `aperv-tool`.
- **Six declared edges with no import under `src/`:** `aperv-tool → rv-tools`, `rvagent-tool → rv-tools`, `rv-agent → rv-static-analysis` (imported only by six test files), `rv-uiautomator → rv-screen-parser`, `rv-experiment → rv-coverage` and `rv-experiment → rv-screen-parser`.

Nothing fails today, because the root `uv sync` installs every workspace member. The cost is that the graph cannot be trusted. The module map in `CLAUDE.md`, the `tools` and `aperv` specs and the architecture documents state edges that do not exist, and they hide one that does. The layer rule that `rv-android-core` depends on no workspace module is broken by an import nobody calls.

## What Changes

The author's decisions of 2026-10-10 (#126): one change for the three findings, and **no behaviour change**.

- **Remove the dead `Task` coverage helpers.** `Task.get_repository`, `Task.add_error`, `Task.add_method_call` and `Task.update_coverage` are deleted, with a copy in `backup/` first (P3), together with their tests (`TestTaskRepositoryDelegation`, `TestTaskUpdateCoverage`, `TestTaskGetRepository`). One new test pins that a new `Task` starts with `repository` set to `None`, the condition the resume path relies on; the deleted classes held the only core test that touched it. The deletion removes the only import of `rv_coverage` from the core, so the cycle disappears. The `RvCoverageLog`/`RvErrorLog` type aliases in `task.py` lose their last users and go too.
- **Correct two comments, not the code, in `task.py`.** The comments at `:583-585` and in the `_new_repository()` docstring at `:602` say `LogcatRepository` is `Any` when "rv-coverage is not installed". In fact it is always `Any` at runtime, because it is imported under `TYPE_CHECKING`, and `_new_repository()` always returns `None`. The comments are rewritten to say that, and to say that the resume path relies on it (`result_processor.py:1021` reconstructs only when `task.repository` is falsy, and an empty `LogcatRepository` is truthy). The `__init__` docstring line "None if coverage module unavailable" gets the same correction, and so do the other comments that make the same claim: the two `# Fallback for when full dependencies aren't available` lines and the import comment at `:16`, and the `_new_repository()` docstring summary.
- **rv-platform declares `aperv-tool`.** It goes into `dependencies` and `[tool.uv.sources]`, the same way as `rvagent-tool`. The guarded import in `_register_external_tools()` is unchanged.
- **The six unused edges are removed.** `rv-static-analysis` moves to the `dev` dependency group of `rv-agent`, because its tests still import it. `uv.lock` is regenerated.

**Not in this change:**
- The code of `_new_repository()`. Making it build a real repository would change what resume reports.
- The `try/except` around plugin registration in `rv_platform/__init__.py`.
- The lazy, undeclared import of `rv_coverage` in `aperv_tool/analysis/step_bundle.py:193`. Its docstring records it as deliberate: the diagnostic stream is opt-in, and its absence degrades to "not read".
- The SDP edge `rvagent-tool (I=0.75) → rv-agent (I=0.80)` that the script also reports.
- The Views-and-Beyond documents in `docs/architecture/` (`rv-android.md`, `rv-platform.md`, `ape-rv.md`, `rv-experiment.md`), although they state the old edges. Another session holds an uncommitted regeneration of those files (author's decision, 2026-10-10). That work, or a later `/rv-doc-arch` run, brings their edges in line with the graph this change leaves.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `tools`: "External Tool Support" names both external plugins (`rvagent-tool` and `aperv-tool`) and the dependency each one declares, and INV-TOOL-12 covers the idempotency check for both. The narrative sections that state `rvagent-tool → rv-tools` and `rv-uiautomator → rv-screen-parser` are corrected by hand when the change is archived.
- `aperv`: "ApeRVTool Registration" states that rv-platform declares `aperv-tool`, and that the `ImportError` guard covers a broken import rather than an optional install. "uv Workspace Declaration" requires `rv-android-core` alone. The Purpose paragraph that calls the module "optional" and the "Relationship with Other Domains" entry for rv-tools are corrected by hand when the change is archived.

## Impact

- **Modules, code:** `rv-android-core` (`domain/task.py`, `tests/domain/test_task.py`).
- **Modules, `pyproject.toml` only:** `rv-platform`, `aperv-tool`, `rvagent-tool`, `rv-agent`, `rv-uiautomator`, `rv-experiment`; root `uv.lock`.
- **Unchanged:** all runtime paths. No production code calls the removed methods. The set of packages the root `uv sync` installs into `.venv` is the same before and after. Only a module installed on its own, outside the workspace, sees a different dependency closure.
- **Documentation that states the old graph:**
  - the root `CLAUDE.md` module map;
  - the `CLAUDE.md` of `rv-android-core`, `rv-platform`, `rv-coverage`, `rv-tools`, `rv-uiautomator`, `rv-agent`, `rvagent-tool` and `aperv-tool`;
  - the known-issues entry for the cycle in `modules/rv-android-core/docs/architecture.md`;
  - the `docs/architecture.md` of `rv-uiautomator`, `rv-experiment`, `rv-coverage`, `rvagent-tool`, `aperv-tool` and `rv-platform` (whose internal-dependency table lacks `aperv-tool`);
  - the `README.md` of `rv-uiautomator`, `rvagent-tool`, `aperv-tool` and `rv-agent`;
  - the allowed-edge table and the layer-rule sentence in `.claude/skills/rv-analyze-dependencies/reference.md`, and the example rows in its `SKILL.md`.
- **FR/NFR:** NFR01 (modularity: one declared, acyclic dependency direction), NFR03 (testability: the dead helpers' tests go with them).
