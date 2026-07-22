# Tasks: dexlib2 apk_paths contract — stop duplicating the apks_dir prefix

GitHub Issue: [#86](https://github.com/PAMunb/rvsec/issues/86) · Plan: `plan.md`

Single group of substance — no subagent dispatch (one module, <20 files).

## 1. Core Fix — dexlib2 path resolution

- [x] 1.1 `dexlib_instrumentation.py:214` — resolve the input as a complete path: replace `apk = apks_dir / name` with `apk = Path(name)` (do not re-join with `apks_dir`; `name` already carries the directory).
- [x] 1.2 `dexlib_instrumentation.py:253` — fix the success cross-check: replace `output_apk = results_dir / name` with `output_apk = results_dir / Path(name).name` (output is always `results_dir` + basename).
- [x] 1.3 `dexlib_instrumentation.py:174-177` — reword the `apk_paths` Args docstring: "complete paths" (not "basenames"); note `apks_dir` is ignored for input lookup when `apk_paths` is set. Keep the per-APK-invocation rationale.

## 2. Contract — ABC docstring

- [x] 2.1 `rv-instrumentation-core/instrumenter.py:36` — expand the `instrument_apks` docstring to state the canonical `apk_paths` contract: each item is a complete path to an APK (resolvable from cwd); when `apk_paths` is provided, `apks_dir` is ignored for input lookup.

## 3. Tests — migrate existing + regression

- [x] 3.1 `modules/rv-instrumentation-dexlib2/tests/test_dexlib_instrumentation.py` — update the four tests that pass bare basenames in `apk_paths` (old contract) to pass complete paths (`str(apks_dir / name)`): `test_subprocess_error_demoted_per_apk_not_propagated` (~:91), `test_persist_errors_json_writes_file` (~:135), `test_wrapper_guard_apk_paths_demotes_when_apk_missing` (~:380), `test_wrapper_guard_apk_paths_succeeds_when_apk_present` (~:409). Without this, they fail under the fix (lookup resolves from cwd).
- [x] 3.2 Add a test in `modules/rv-instrumentation-dexlib2/tests/` that calls `instrument_apks(apk_paths=[...])` with a relative-prefixed path (`apks_examples/x.apk`) and asserts the resolved input path has no duplicated `apks_dir` segment. Stub the CLI subprocess (offline); use `monkeypatch.chdir(tmp_path)` so the relative path resolves against a controlled cwd.
- [x] 3.3 Extend the test to an absolute-prefixed path and assert the output cross-check resolves to `results_dir/<basename>` in both cases.
- [x] 3.4 Run `uv run pytest modules/rv-instrumentation-dexlib2/tests/ --import-mode=importlib -o "addopts=" -v`.

## 4. Verification

- [x] 4.1 ~~Run `/rv-qa-lint-fix rv-instrumentation-dexlib2`~~ — skipped per user instruction (no rv-* skills). Lint verified directly instead: `black --check` clean (3 files unchanged) + `flake8` clean on the touched files.
- [x] 4.2 Run `uv run pytest modules/rv-instrumentation-core/tests/ --import-mode=importlib -o "addopts=" -v` (results-model tests, including the `variant="ajc"` retrocompat default, still pass after the docstring change).
- [x] 4.3 Verify all acceptance criteria from `plan.md` §5.
