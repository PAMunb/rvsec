# Change Plan: package_detector — prefix matching + empty-components guard

**Date**: 2026-06-12
**Track**: Quick Path
**Priority**: Low
**GitHub Issue**: [#63](https://github.com/PAMunb/rvsec/issues/63)
**PRD Reference**: N/A (internal utility feeding static-analysis class filtering)
**Domains**: core

## 1. Context

`PackageDetector.detect_package()` in `modules/rv-android-core/src/rv_android_core/util/android/package_detector.py` decides, for each APK, whether the implementation (code) package differs from the manifest package. The result (`code_package`) feeds static-analysis class filtering and the app-vs-library split used in the experiment.

Two defects exist in the manifest-vs-code matching logic. Neither changes the numbers already published — the 169-APK `detected_package` is persisted in `apks_complete.csv`, and the 27/527 = 5.12% app-code split was independently recomputed with the correct prefix rule over those packages. The risk is confined to **future regenerations** with new apps.

**Defect 1 — Vacuous `same_package`** (`package_detector.py:538-551`). The fast-path initializes `same_package = True` and iterates over `app_components` to refute it. When `app_components` is empty (all components filtered as framework, or no Activities/Services/Receivers), the loop body never runs and the function returns `confidence="high"`, `detection_method="same_package"` with zero evidence. The correct `no_app_components` branch (`:594-599`, `confidence="low"`) is unreachable in that scenario because the function already returned.

**Defect 2 — Substring matching** (`package_detector.py:540` and `:586`). Both use Python's `in` operator (substring), not a namespace-prefix test. Manifest `com.foo` "matches" `com.foobar.MainActivity` (a sibling package, different app) because `"com.foo" in "com.foobar.MainActivity"` is `True`. The correct test is `component == pkg or component.startswith(pkg + ".")`.

See issue #63 for the full reproduction notes.

## 2. Scope

Single file, single module (`rv-android-core`). One logical change, executed TDD-first:

- **Group A** — Add regression tests covering the empty-components case (Defect 1) and the sibling-package non-match (Defect 2). Written first; expected to fail (RED).
- **Group B** — Fix both defects in `detect_package()` and reuse a single prefix-match helper for the two call sites, turning the tests green (GREEN).

The repo keeps `data-analysis/dataset/package_detector.py` as a byte-identical copy of the canonical file. That copy lives in the paper/analysis tree (not this repo) and is re-synced separately (analysis plan task 0.15, §9). It is **out of scope** here.

## 3. File Inventory

| Group | File | Action | Detail |
|-------|------|--------|--------|
| A | `modules/rv-android-core/tests/util/android/test_package_detector.py` | Create | Add regression tests: (1) empty `app_components` → `confidence="low"`, `detection_method="no_app_components"`; (2) sibling package `com.foobar.*` with manifest `com.foo` → NOT classified as `same_package`; (3) genuine sub-package `com.foo.ui.*` with manifest `com.foo` → still `same_package`. Use a lightweight APK stub exposing `get_package`/`get_activities`/`get_services`/`get_receivers`. |
| B | `modules/rv-android-core/src/rv_android_core/util/android/package_detector.py` | Edit | **Defect 1** (`:538-542`): guard the fast-path so an empty `app_components` does not yield `same_package`. Require `app_components` non-empty AND every component prefix-matched. **Defect 2** (`:540`): replace `manifest_pkg not in component` with a namespace-prefix test. **Defect 2** (`:586`): replace `any(manifest_pkg in pkg ...)` with the same prefix test. Introduce one small private helper `_is_in_namespace(child: str, parent: str) -> bool` returning `child == parent or child.startswith(parent + ".")` and use it at both sites. |

## 4. Execution Order

TDD order: Group A (regression tests, RED) before Group B (source fix, GREEN). Single-file change, no subagent dispatch needed. This matches the task numbering in `tasks.md` (§1 tests → §2 fix).

## 5. Acceptance Criteria

- [x] Defect 1: with empty `app_components`, `detect_package()` returns `confidence="low"` and `detection_method="no_app_components"` (no longer high-confidence `same_package`)
- [x] Defect 2: `:540` fast-path uses namespace-prefix matching — `com.foo` does NOT match sibling `com.foobar.MainActivity`, but DOES match `com.foo.ui.MainActivity`
- [x] Defect 2: `:586` game-engine `manifest_in_components` check uses the same prefix helper
- [x] Regression tests added for all three cases (empty, sibling non-match, genuine sub-package match)
- [x] `uv run pytest modules/rv-android-core/tests/ --import-mode=importlib -o "addopts="` passes (existing package_detector tests unaffected)
- [x] `uv run black` + `uv run flake8` clean on the touched file
