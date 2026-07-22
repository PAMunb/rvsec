# Tasks: Fix ErrorType.DIALOG / ErrorType.BANNER AttributeError in ErrorDetector

GitHub Issue: [#82](https://github.com/PAMunb/rvsec/issues/82)

Group 1 (enum) must complete before Group 2 (banner call site) and Group 3 (tests), both
of which reference `ErrorType.BANNER`. Group 4 (Verification) runs last. Three files, one
module — no subagent dispatch.

## 1. Enum member

- [x] 1.1 Add `BANNER = "banner"` to the `ErrorType` enum in `modules/rv-screen-parser/src/rv_screen_parser/screenshot/models.py` (near the dialog-family members, after `TOAST_NOTIFICATION`).

## 2. Call sites

- [x] 2.1 `modules/rv-screen-parser/src/rv_screen_parser/screenshot/detectors/error_detector.py:617`: change `ErrorType.DIALOG` → `ErrorType.DIALOG_ERROR`.
- [x] 2.2 Confirm `error_detector.py:696` `ErrorType.BANNER` now resolves (valid after task 1.1) — no edit needed beyond verifying.
- [x] 2.3 Grep `modules/` to confirm no other `ErrorType.DIALOG` / `ErrorType.BANNER` references remain outside the (now valid) call sites and tests.

## 3. Tests

- [x] 3.1 In `modules/rv-screen-parser/tests/test_error_detector.py`, flip `test_detect_error_dialogs_centered` (class `TestErrorDetectorBranchCoverage`, ~line 641) from `pytest.raises(AttributeError)` to assert a single `ErrorIndicator` with `error_type == ErrorType.DIALOG_ERROR` and no exception. Remove the production-bug docstring.
- [x] 3.2 In the same file, flip `test_detect_banner_errors_thin_wide` (~line 676) from `pytest.raises(AttributeError)` to assert a single `ErrorIndicator` with `error_type == ErrorType.BANNER` and no exception. Remove the production-bug docstring.

## 4. Verification

- [x] 4.1 Correctness (no coverage): `cd modules/rv-screen-parser && uv run pytest tests/test_error_detector.py --import-mode=importlib -o addopts= -q`.
- [x] 4.2 Scoped coverage == 100% (cv2/numpy workaround — `pytest --cov` crashes): `uv run coverage run -m pytest tests/test_error_detector.py tests/test_error_detector_integration.py --import-mode=importlib -o addopts= -p no:cov -q && uv run coverage report -m | grep error_detector && uv run coverage erase`.
- [x] 4.3 Full rv-screen-parser suite passes: `uv run pytest tests --import-mode=importlib -o addopts= -q`.
- [x] 4.4 Verify all acceptance criteria from plan.md are met.
