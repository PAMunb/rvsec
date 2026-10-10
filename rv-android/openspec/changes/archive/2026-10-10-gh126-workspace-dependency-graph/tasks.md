<!-- Execution plan (design D7). The main session is a thin orchestrator: it edits no file. It dispatches the
     subagents, reads their short reports, runs the barrier steps (Group 6), checks the evidence itself, archives
     and commits.

     Waves and barriers:
     - Wave 0, three subagents in parallel: R (Group 1, baseline), D1 (Group 2, guidance docs), D2 (Group 3,
       core architecture doc). No test reads the .md files D1/D2 edit, so the docs do not disturb the baseline.
     - Barrier 1: R done. The baseline must be taken before any edit it measures.
     - Wave 1, two subagents in parallel: A (Group 4, core code and tests) and P (Group 5, pyproject.toml + uv lock).
       Their files are disjoint. P runs `uv lock` only, never `uv sync`, because A's test run imports from the
       shared .venv.
     - Barrier 2: A and P done. Main runs Group 6: uv sync, the "after" evidence run, and its own checks.
     - Wave 3 (Group 7), after Group 6 and after D1/D2: lint on the two core files, /rv-verify, then
       /rv-code-reviewer and /opsx:verify in parallel (both read-only). Tests come before review.
     - Group 8 (main): archive, manual spec sync, issue, commit.
     - Critical path: R (~5 min) -> max(A, P) -> Group 6 (~5 min) -> Group 7 -> Group 8. D1 and D2 overlap with it.

     Rules every subagent prompt MUST carry:
     - Write only the files your group owns (table in design D7). Read anything.
     - Git: only diff, status, log, show, grep. Never stash, checkout, switch, restore, reset, branch, rebase,
       clean or commit. Other sessions share the working tree. To compare before/after, use
       `git show HEAD:<file>` into your own scratch directory.
     - Never run `uv sync`. Never run another group's test suite.
     - Evidence and logs go to rv-android/experimento-gh126/ (not committed), never to /tmp.
     - Docs: English, P2 (self-contained, explain why), P4 (current state only, no history, no promotional words).
     - Report: the files changed, the commands run with their final lines, and anything you did not do. Keep it short.
     - pytest flags: --import-mode=importlib -o "addopts=" -p no:cacheprovider
       -m "not (slow or online or sglang or performance or dataset)". -->

## 1. Baseline — subagent R (wave 0)

- [x] 1.1 Grep the whole rv-android tree (excluding `.venv/` and `backup/`) for the four `Task` methods (`get_repository`, `add_error`, `add_method_call`, `update_coverage`). Confirm that their only callers are in `modules/rv-android-core/tests/domain/test_task.py`. `CoverageComponent.get_repository` (rv-platform) and the `add_method_call` of rv-coverage's analyzer belong to other classes and stay. Report every other hit.
- [x] 1.2 Write `experimento-gh126/run_evidence.sh <label>` (design, Testing Strategy). In `experimento-gh126/<label>/` it writes:
  - `export-dev.txt` (`uv export --frozen --no-hashes`) and `export-nodev.txt` (same with `--no-dev`);
  - `workspace_deps.txt` (`python3 -I .claude/skills/rv-analyze-dependencies/scripts/workspace_deps.py`);
  - one log per pytest suite (rv-android-core, rv-platform, aperv-tool, rvagent-tool, rv-agent, rv-uiautomator, rv-experiment and the root `tests/`), the suites run in parallel;
  - `summary.txt`, one line per suite with its final pytest line and wall time.

  The script never runs `uv sync` or `uv lock`.
- [x] 1.3 Run `experimento-gh126/run_evidence.sh baseline`. `baseline/workspace_deps.txt` shows the cycle `rv-android-core -> rv-coverage -> rv-android-core`, and no suite in `baseline/summary.txt` has a failure. If a suite fails, report it and stop: a failure that exists before the change is not this change's to fix, and the author decides.

## 2. Guidance docs — subagent D1 (wave 0; owns root `CLAUDE.md` module-map rows, `modules/*/CLAUDE.md`, `.claude/skills/rv-analyze-dependencies/`)

- [x] 2.1 Root `CLAUDE.md` module map, "Key dep" column only:
  - rv-platform gains `aperv-tool`;
  - rv-uiautomator becomes `(none)`;
  - rv-agent lists `rv-screen-parser, rv-uiautomator` and notes `rv-static-analysis` as tests-only;
  - rvagent-tool becomes `rv-agent`;
  - aperv-tool becomes `(none)`.

  Leave every other line alone, because the file carries another session's uncommitted edit (design D6).
- [x] 2.2 Module `CLAUDE.md` files:
  - `rv-android-core` (`:90`): the undeclared-import bullet goes away, and the module has no workspace dependency;
  - `rv-platform` (`:105-106`): aperv-tool is declared;
  - `rv-coverage` (`:90`): drop "rv-android-core itself through an undeclared lazy import";
  - `rv-tools` (`:56`): the plugins do not declare rv-tools; they subclass `AbstractTool` from rv-android-core;
  - `rv-uiautomator` (`:42`);
  - `rv-agent` (`:214`): tests-only, in the `dev` group;
  - `rvagent-tool` (`:42`);
  - `aperv-tool` (`:40`).
- [x] 2.3 `.claude/skills/rv-analyze-dependencies/reference.md`, allowed-edge table (`:39`, `:43-47`). In `SKILL.md:113`, the example row: rv-platform → aperv-tool is no longer undeclared, so use the `aperv-tool → rv-coverage` lazy import as the example of a deliberate undeclared edge.
- [x] 2.4 Re-run the doc grep from the proposal's inventory over the files of this group: `get_repository`, `undeclared`, `imported but not declared`, and the six removed edges. Only statements that are true after the change remain.

## 3. Core architecture doc — subagent D2 (wave 0; owns `modules/rv-android-core/docs/architecture.md`)

`docs/architecture/*.md` is out of scope (design, Non-Goals): another session holds an uncommitted regeneration of it.

- [x] 3.1 `modules/rv-android-core/docs/architecture.md` (`:1062`): the cycle entry under known issues goes away. The `_new_repository()` description at `:752` stays true; leave it alone.
- [x] 3.2 Re-run the doc grep (as in 2.4) over the file of this group.

## 4. Core code — subagent A (wave 1, after Group 1; owns `task.py`, `test_task.py`, `backup/20261010-gh126-task-coverage-helpers/`)

- [x] 4.1 Copy `modules/rv-android-core/src/rv_android_core/domain/task.py` and `modules/rv-android-core/tests/domain/test_task.py` to `backup/20261010-gh126-task-coverage-helpers/` (P3, design D1).
- [x] 4.2 In `task.py`:
  - delete `add_error`, `add_method_call`, `update_coverage` and `get_repository`;
  - delete the `RvCoverageLog`/`RvErrorLog` import under `TYPE_CHECKING` and their `Any` fallbacks (design D2);
  - keep `LogcatRepository`, `_new_repository()` and `os`.
- [x] 4.3 Rewrite comments only, no code line (design D3):
  - the comment at `task.py:24-26`;
  - the comment at `:583-585`;
  - the `_new_repository()` docstring paragraph at `:602-603`;
  - the `__init__` docstring line `self.repository: ... None if coverage module unavailable`.

  The new text says that `LogcatRepository` is imported only for type checking, so `_new_repository()` returns `None` at runtime, and that `ResultProcessorComponent` reconstructs from the logcat only when `task.repository` is falsy.
- [x] 4.4 In `test_task.py`, delete `TestTaskRepositoryDelegation`, `TestTaskUpdateCoverage` and `TestTaskGetRepository`, plus any import or helper only they used. Report how many tests were deleted.
- [x] 4.5 `grep -rn "rv_coverage" modules/rv-android-core/src` returns nothing.
- [x] 4.6 Run the rv-android-core suite only. Its passed count equals the baseline's (`experimento-gh126/baseline/summary.txt`) minus the tests deleted in 4.4, and nothing fails.

## 5. Dependency declarations — subagent P (wave 1, after Group 1; owns the six `pyproject.toml` and `uv.lock`)

- [x] 5.1 `modules/rv-platform/pyproject.toml`: add `"aperv-tool"` to `dependencies` and `aperv-tool = { workspace = true }` to `[tool.uv.sources]`, next to `rvagent-tool` (`aperv` ApeRVTool Registration, INV-TOOL-26).
- [x] 5.2 `modules/aperv-tool/pyproject.toml`: remove `rv-tools` from `dependencies` and from `[tool.uv.sources]` (`aperv` uv Workspace Declaration).
- [x] 5.3 `modules/rvagent-tool/pyproject.toml`: remove `rv-tools` from `dependencies` and from `[tool.uv.sources]`.
- [x] 5.4 `modules/rv-uiautomator/pyproject.toml`: remove `rv-screen-parser` from `dependencies` and from `[tool.uv.sources]`.
- [x] 5.5 `modules/rv-experiment/pyproject.toml`: remove `rv-coverage` and `rv-screen-parser` from `dependencies` and from `[tool.uv.sources]`. Keep `rv-tools`, which `config.py` and `experiment_controller.py` import lazily.
- [x] 5.6 `modules/rv-agent/pyproject.toml`: move `rv-static-analysis` from `dependencies` to `[dependency-groups] dev`, and keep its `[tool.uv.sources]` entry (design D4).
- [x] 5.7 Run `uv lock` (not `uv sync`). Report `git diff --stat uv.lock` and the lock's member dependency lines that changed.

## 6. Barrier and evidence — main session (after Groups 4 and 5)

- [x] 6.1 Read the reports of A and P, and check `git diff --stat` on their owned paths: no file outside the ownership table in design D7 changed.
- [x] 6.2 Run `uv sync`.
- [x] 6.3 Run `experimento-gh126/run_evidence.sh after`.
- [x] 6.4 `diff` `baseline/export-dev.txt` against `after/export-dev.txt`, and the same for `export-nodev.txt`, with comment lines removed (`grep -v '^\s*#'`). Both diffs are empty (install set unchanged). The raw diff shows only `# via <member>` annotations: `uv export` writes them from the member edges, so they change with exactly the edges this change edits.
- [x] 6.5 `after/workspace_deps.txt` meets three conditions (`tools` INV-TOOL-26, `aperv` scenarios):
  - the CYCLES section is empty;
  - the `unused` line is `-` for every module;
  - the only `undeclared` entry is `aperv-tool: rv-coverage`.
- [x] 6.6 Smoke: `uv run python -c "import rv_platform; from rv_tools import ToolRegistry as R; r=R.get_instance(); print(r.is_tool_registered('aperv'), r.is_tool_registered('rvagent'))"` prints `True True`.
- [x] 6.7 Compare `after/summary.txt` with `baseline/summary.txt`. The counts are equal except for rv-android-core, which is lower by exactly the number of tests deleted in 4.4, and nothing newly fails. If anything differs, stop and report to the author before Group 7.

## 7. Quality — wave 3 (after Group 6, and after Groups 2 and 3)

- [x] 7.1 Subagent Q: `uv run ruff check --fix` and `uv run ruff format` on `modules/rv-android-core/src/rv_android_core/domain/task.py` and `modules/rv-android-core/tests/domain/test_task.py` only (design D8). If either file changes, re-run the rv-android-core suite and report the count.
- [x] 7.2 Run `/rv-verify rv-android-core` (read-only).
- [x] 7.3 Invoke `/rv-code-reviewer` via the Skill tool on the change diff: code, `pyproject.toml` files, `uv.lock` summary and documentation. Run it in parallel with 7.4.
- [x] 7.4 Run `/opsx:verify gh126-workspace-dependency-graph`.
- [x] 7.5 The main session triages the findings of 7.2–7.4 with the author. Fixes go back to the owning subagent's files, and Group 6 evidence is re-run if code or `pyproject.toml` changed. The author's decisions of 2026-10-10:
  - delta specs and plan: `INV-TOOL-21` becomes `INV-TOOL-26` (21–25 are taken), and its second sentence reads "MUST NOT declare";
  - `task.py`, comments only (design D3): drop the two `# Fallback ...` lines, reword the `:16` import comment and the `_new_repository()` docstring summary and "several of these construction sites" sentence;
  - `test_task.py`: one test pins that a new `Task` starts with `repository` set to `None`; the core count becomes baseline − 11 + 1 (1140);
  - docs (D1 scope): the `docs/architecture.md` of rv-uiautomator, rv-experiment, rv-coverage, rvagent-tool, aperv-tool and rv-platform (add the `aperv-tool` row), the `README.md` of rv-uiautomator, rvagent-tool, aperv-tool and rv-agent, the layer-rule sentence of `reference.md` (wording only, no module moves) and `SKILL.md` example row 2 (`0.67 → 0.75`);
  - re-run `run_evidence.sh` with a new label and repeat the checks of 6.4–6.7 against the baseline.

## 8. Archive and close — main session

- [x] 8.1 Run `/opsx:archive gh126-workspace-dependency-graph`. It merges the MODIFIED requirements of `tools` ("External Tool Support") and of `aperv` ("ApeRVTool Registration" and "uv Workspace Declaration").
- [x] 8.2 Subagent S (owns `openspec/specs/tools/spec.md` and `openspec/specs/aperv/spec.md`) edits the main specs by hand (design D5):
  - `tools` INV-TOOL-12 (both plugins) and the new INV-TOOL-26 in its Invariants section;
  - `tools` design decision 3 and the "Dependencies" entry for rv-screen-parser;
  - `aperv` Purpose paragraph ("optional uv workspace member") and the `rv-tools` entry under "Relationship with Other Domains".
- [x] 8.3 `grep -n "rvagent-tool depends on rv-agent + rv-tools\|rv-uiautomator depends on it\|optional uv workspace member" openspec/specs/*/spec.md` returns nothing.
- [x] 8.4 Tick the acceptance criteria in the body of issue #126. Before `gh issue edit --body-file`, check that the edited body file is non-empty.
- [x] 8.5 Ask the author how the root `CLAUDE.md` is committed, since it carries another session's edit (design D6). Then commit by path only (`git commit -- <paths>`), with `closes #126` and no `Co-Authored-By` trailer. The author pushes and moves the Kanban card.
