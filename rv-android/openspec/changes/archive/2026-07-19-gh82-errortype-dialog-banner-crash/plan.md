# Change Plan: Fix ErrorType.DIALOG / ErrorType.BANNER AttributeError in ErrorDetector

**Date**: 2026-07-19
**Track**: Quick Path
**Priority**: Medium
**GitHub Issue**: [#82](https://github.com/PAMunb/rvsec/issues/82)
**PRD Reference**: N/A
**Domains**: analysis (rv-screen-parser)

## 1. Context

`ErrorDetector` in rv-screen-parser references two `ErrorType` enum members that do not
exist, causing an uncaught `AttributeError` at runtime. The defect was found while adding
branch-coverage tests for `error_detector.py` — two of the detection paths could never
complete because the enum lookup fails before the error indicator is built.

Two detection paths are affected:

- `_detect_error_dialogs()` (`error_detector.py:617`) passes `ErrorType.DIALOG`. That
  member does not exist on `ErrorType`. A `DIALOG` member exists only on the unrelated
  `DetectionMethod` enum, which makes the mistake easy to overlook.
- `_detect_banner_errors()` (`error_detector.py:696`) passes `ErrorType.BANNER`. There is
  no banner member on `ErrorType` at all.

`ErrorType` (`screenshot/models.py`, lines 72-96) defines `DIALOG_ERROR`,
`DIALOG_TEXT_ERROR`, `TOAST_NOTIFICATION`, and related members, but neither a bare
`DIALOG` nor any banner member. The enum member is evaluated as a call argument **before**
`_create_error_indicator()` runs, and neither method wraps the call in try/except, so the
`AttributeError` escapes `_detect_pattern_errors` and then `detect_errors`.

Impact — `detect_errors` is called from two production sites:

- `screenshot/screenshot_analyzer.py:220` — `detect_errors` is decorated with
  `reraise=True`, so the `AttributeError` propagates and aborts screenshot analysis for
  that frame.
- `rv-agent/services/error_detection.py:188` — the call is wrapped in try/except; the
  crash is swallowed and the method returns `detected=False`, silently disabling visual
  error detection for any frame that contains a dialog or banner.

The bug is latent: it only fires when the dialog-cluster or banner geometric conditions
are met, which is why it went unnoticed. The fix is low-risk because nothing downstream
branches on the specific `ErrorType` value — only `converters.py` references
`UNKNOWN_ERROR` as a fallback.

## 2. Scope

Single module (rv-screen-parser), three files, one logical change: give the two detection
paths valid enum members. The `rv-agent` consumer benefits automatically (error detection
stops silently failing on dialog/banner frames) but needs no code change.

- **Group A** — add the missing `BANNER` member to the `ErrorType` enum.
- **Group B** — point the two `error_detector.py` call sites at valid members.
- **Group C** — flip the two tests that currently pin the crash to assert the corrected
  behavior.

## 3. File Inventory

| File | Action | Detail |
|------|--------|--------|
| `modules/rv-screen-parser/src/rv_screen_parser/screenshot/models.py` | Edit | Add `BANNER = "banner"` to the `ErrorType` enum (near the dialog-family members, after `TOAST_NOTIFICATION`, lines ~93-96). Parallels the existing `DIALOG_ERROR` / `TOAST_NOTIFICATION` granularity; `_detect_banner_errors` is a first-class detection path. |
| `modules/rv-screen-parser/src/rv_screen_parser/screenshot/detectors/error_detector.py` | Edit | Line 617: `ErrorType.DIALOG` → `ErrorType.DIALOG_ERROR`. Line 696: `ErrorType.BANNER` stays (valid once the enum member exists). |
| `modules/rv-screen-parser/tests/test_error_detector.py` | Edit | Two tests in class `TestErrorDetectorBranchCoverage` currently pin the crash via `pytest.raises(AttributeError)` (`test_detect_error_dialogs_centered` ~line 641, `test_detect_banner_errors_thin_wide` ~line 676). Flip to assert corrected behavior: dialog → single `ErrorIndicator`, `error_type == ErrorType.DIALOG_ERROR`, no exception; banner → single `ErrorIndicator`, `error_type == ErrorType.BANNER`, no exception. Remove the now-obsolete production-bug docstrings. This makes the append lines 620-621 / 699-700 reachable. |

## 4. Execution Order

Group A (enum member) must precede Group B's banner edit and Group C's test updates, since
both reference `ErrorType.BANNER`. All three files live in one module and the change is
small — single session, no subagent dispatch needed.

Order: **A** (enum) → **B** (both `error_detector.py` lines) → **C** (tests) → verify.

## 5. Acceptance Criteria

- [ ] `ErrorType.BANNER` exists on the enum; `getattr(ErrorType, "BANNER")` no longer raises.
- [ ] `error_detector.py:617` uses `ErrorType.DIALOG_ERROR`; `:696` uses `ErrorType.BANNER`; no other `ErrorType.DIALOG` / `ErrorType.BANNER` references remain (grep across `modules/`).
- [ ] `_detect_error_dialogs` produces an `ErrorIndicator` with `error_type == ErrorType.DIALOG_ERROR` for a centered dialog-sized error-text cluster, with no exception.
- [ ] `_detect_banner_errors` produces an `ErrorIndicator` with `error_type == ErrorType.BANNER` for a wide/thin error text, with no exception.
- [ ] The two affected tests assert the corrected behavior (not `pytest.raises(AttributeError)`).
- [ ] `error_detector.py` scoped coverage == 100% (lines 620-621, 699-700 now reachable). Command (cv2/numpy workaround — `pytest --cov` crashes on numpy double-import): `cd modules/rv-screen-parser && uv run coverage run -m pytest tests/test_error_detector.py tests/test_error_detector_integration.py --import-mode=importlib -o addopts= -p no:cov -q && uv run coverage report -m | grep error_detector && uv run coverage erase`.
- [ ] Full rv-screen-parser suite passes: `uv run pytest tests --import-mode=importlib -o addopts= -q`.
