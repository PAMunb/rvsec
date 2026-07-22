# Change Plan: dexlib2 apk_paths contract — stop duplicating the apks_dir prefix

**Date**: 2026-07-22
**Track**: Quick Path
**Priority**: High
**GitHub Issue**: [#86](https://github.com/PAMunb/rvsec/issues/86)
**PRD Reference**: FR17 (just-in-time instrumentation config); INV-INS-36 (variant dispatch through the canonical factory)
**Domains**: instrumentation

## 1. Context

Running the experiment pipeline with the dexlib2 instrumentation variant and a
**relative** `--apks-dir` fails every APK before it is instrumented:

```
uv run rv-experiment run --tools ape --specification-set jca \
  --apks-dir ./apks_examples --timeouts 60 --instrumentation-variant dexlib2

Processing APK 1/1: apks_examples/cryptoapp.apk
ERROR - APK not found at apks_examples/apks_examples/cryptoapp.apk
Batch complete: 0/1 successful, 1 errors
Skipping static analysis for cryptoapp.apk: not instrumented
```

The `apks_examples/` prefix appears twice. The `ajc` variant, run identically,
works.

**Root cause — ambiguous `apk_paths` contract.** The `Instrumenter` ABC
(`rv-instrumentation-core/instrumenter.py:36`) has a one-line docstring and never
states whether each `apk_paths` item is a *basename relative to `apks_dir`* or a
*complete path*. The producer and the two variants diverged, and the producer
agrees with `ajc`:

| Site | Code | Treats `apk_paths[i]` as |
|---|---|---|
| Producer — `rv-experiment/config.py:524` (`get_apk_list`) | `str(p) for p in apks_dir_path.glob("*.apk")` | complete path (glob keeps the `apks_examples/` prefix) |
| ajc — `ajc_instrumentation.py:192` | `App(p)` → `App.path = os.path.abspath(app_path)` (`app.py:98-100`) | complete path — matches producer ✅ |
| dexlib2 — `dexlib_instrumentation.py:214` | `apk = apks_dir / name` | basename — re-joins → duplicates ❌ |

`get_apk_list()` emits complete paths; `ajc` consumes them directly; `dexlib2` is
the sole variant that re-joins with `apks_dir`, so the prefix is added twice.

**Second, latent defect at the same site.** The success cross-check
(`dexlib_instrumentation.py:253`, `output_apk = results_dir / name`) has the mirror
problem. When `name` is a complete path it points at the wrong location; when `name`
is *absolute* (the relative→absolute workaround) pathlib discards `results_dir`
entirely and the check silently inspects the **input** APK — defeating the guard
(lines 248-259) that exists precisely to catch a silent javac/d8 failure where the
CLI exits 0 without emitting the APK. The output path must always be
`results_dir / basename`.

**Why the absolute-`--apks-dir` workaround "works" and is not a fix.** With an
absolute `apks_dir`, `get_apk_list()` emits absolute paths; in `apks_dir / name`
pathlib drops the left operand when `name` is absolute, so the re-join is a no-op.
That is an accidental pathlib property, and it activates the latent output-check
defect above. The contract must be fixed, not left to path-shape luck.

**Decision (forced, not a design choice).** The contract is **complete paths**:
that is what `get_apk_list()` already produces and what `ajc` already consumes
correctly. dexlib2 is the single deviant. We fix dexlib2 (two sites) and formalize
the contract in the ABC docstring so future variants cannot re-diverge. The producer
(`config.py`) and `ajc` are already correct and are not modified.

## 2. Scope

Single group — one behavioral fix plus a documentation clarification, both in the
instrumentation domain. Small enough that no subagent dispatch is warranted.

- **rv-instrumentation-dexlib2** — the two path-resolution sites (behavioral fix)
  and a regression test.
- **rv-instrumentation-core** — the `Instrumenter.instrument_apks` docstring
  (contract clarification; no behavior change).

Explicitly **out of scope**: `rv-experiment/config.py` (`get_apk_list` already
emits the contract-correct complete paths) and `rv-instrumentation-ajc` (already
honors the contract). Touching either would risk regressing the working variant.

## 3. File Inventory

| File | Action | Detail |
|------|--------|--------|
| `modules/rv-instrumentation-dexlib2/src/rv_instrumentation_dexlib2/dexlib_instrumentation.py` | Edit (input lookup) | Line 214: `apk = apks_dir / name` → resolve `name` as a complete path (`apk = Path(name)`). `name` already carries the directory; do not re-join with `apks_dir`. |
| `modules/rv-instrumentation-dexlib2/src/rv_instrumentation_dexlib2/dexlib_instrumentation.py` | Edit (output cross-check) | Line 253: `output_apk = results_dir / name` → `output_apk = results_dir / Path(name).name`. Output is always `results_dir` + basename (the Java CLI writes by basename); strip any directory from `name`. |
| `modules/rv-instrumentation-dexlib2/src/rv_instrumentation_dexlib2/dexlib_instrumentation.py` | Edit (docstring) | Lines 174-177 (`apk_paths` Args): reword "Optional subset of basenames" → complete paths; note `apks_dir` is not used to locate inputs when `apk_paths` is set. Keep the per-APK-invocation rationale. |
| `modules/rv-instrumentation-core/src/rv_instrumentation_core/instrumenter.py` | Edit (ABC contract) | Line 36 docstring: state explicitly that each `apk_paths` item is a **complete path** to an APK (resolvable from cwd); when `apk_paths` is provided, `apks_dir` is ignored for input lookup. This is the canonical contract every variant must honor. |
| `modules/rv-instrumentation-dexlib2/tests/test_dexlib_instrumentation.py` | Edit (contract migration) | Four existing tests encode the old basename interpretation — they pass bare basenames in `apk_paths` and would fail under the complete-path contract (lookup would resolve from cwd, not `apks_dir`): `test_subprocess_error_demoted_per_apk_not_propagated` (~:91), `test_persist_errors_json_writes_file` (~:135), `test_wrapper_guard_apk_paths_demotes_when_apk_missing` (~:380), `test_wrapper_guard_apk_paths_succeeds_when_apk_present` (~:409). Update each to pass complete paths (`str(apks_dir / name)`). |
| `modules/rv-instrumentation-dexlib2/tests/` | Add | Regression test: `instrument_apks(apk_paths=[...])` with both relative-prefixed (`apks_examples/x.apk`) and absolute-prefixed paths resolves the input to the given path (no `apks_dir` duplication) and computes the output cross-check as `results_dir/<basename>`. Mock/stub the CLI subprocess so the test is offline. The relative-prefixed case needs `monkeypatch.chdir(tmp_path)` so the relative path resolves against a controlled cwd. |

Note: the fix uses `Path`, already imported inside `instrument_apks`
(`dexlib_instrumentation.py:183`).

## 4. Execution Order

Single group, sequential within the file:
1. Fix the two path sites + local docstring in `dexlib_instrumentation.py`.
2. Clarify the ABC contract docstring in `instrumenter.py`.
3. Migrate the four existing basename-contract tests to complete paths, add the
   regression test, and run the suite.

No parallelism / no subagent dispatch (well under the 20-file threshold, one
module of substance).

## 5. Acceptance Criteria

- [x] `dexlib2` instruments APKs with a **relative** `--apks-dir` — the resolved input path contains no duplicated `apks_dir` segment (`apks_examples/cryptoapp.apk`, not `apks_examples/apks_examples/cryptoapp.apk`). — `test_apk_paths_complete_path_no_duplicate_prefix[False]` asserts `captured["apk_arg"] == "apks_examples/cryptoapp.apk"` and no `apks_examples/apks_examples` segment; the buggy re-join would have produced `APK not found`.
- [x] `dexlib2` instruments APKs with an **absolute** `--apks-dir` (no regression to the previously-working shape). — `...[True]` param + empirical baseline run `results/cli_experiment_20260722_105341_5b788187` (task COMPLETED end-to-end).
- [x] Success cross-check resolves `output_apk` to `results_dir/<basename>` in both relative and absolute cases — the silent-javac/d8-failure guard is effective again (latent defect closed). — both params assert `success_count == 1`, which is credited only when the guard finds `results_dir/cryptoapp.apk`; the buggy `results_dir/<name>` would look under `results_dir/apks_examples/` (relative) and demote to error.
- [x] `Instrumenter.instrument_apks` docstring (`instrumenter.py`) states the `apk_paths` contract explicitly: complete paths; `apks_dir` ignored for input lookup when `apk_paths` is set.
- [x] dexlib2 `apk_paths` docstring matches the ABC contract (no "basenames" wording).
- [x] The four existing basename-contract tests in `test_dexlib_instrumentation.py` are updated to pass complete paths and pass.
- [x] Regression test in `rv-instrumentation-dexlib2/tests/` covers relative- and absolute-prefixed `apk_paths`; passes with `--import-mode=importlib -o "addopts="`.
- [x] Full `rv-instrumentation-dexlib2` suite passes (18 passed); `rv-instrumentation-core` tests pass unchanged (11 passed; `ajc` untouched — no behavior change there).
