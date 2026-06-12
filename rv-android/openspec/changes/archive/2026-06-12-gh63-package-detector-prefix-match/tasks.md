## 1. Regression Tests (RED — write failing first)

- [x] 1.1 Create `modules/rv-android-core/tests/util/android/test_package_detector.py` with a lightweight APK stub (exposing `get_package`, `get_activities`, `get_services`, `get_receivers`)
- [x] 1.2 Add test: empty `app_components` → `detect_package()` returns `confidence="low"`, `detection_method="no_app_components"` (Defect 1)
- [x] 1.3 Add test: manifest `com.foo`, component `com.foobar.MainActivity` (sibling) → NOT `same_package` (Defect 2)
- [x] 1.4 Add test: manifest `com.foo`, component `com.foo.ui.MainActivity` (genuine sub-package) → still `same_package`, `confidence="high"`
- [x] 1.5 Run `/rv-test-run rv-android-core` — confirm new tests FAIL against current code

## 2. Core Fix (GREEN)

- [x] 2.1 Add private helper `_is_in_namespace(child: str, parent: str) -> bool` returning `child == parent or child.startswith(parent + ".")` in `package_detector.py`
- [x] 2.2 Defect 1+2 (`:538-542`): guard the fast-path — `same_package = bool(app_components) and all(self._is_in_namespace(c, manifest_pkg) for c in app_components)`; remove the now-redundant manual loop
- [x] 2.3 Defect 2 (`:586`): replace `any(manifest_pkg in pkg ...)` with `any(self._is_in_namespace(pkg, manifest_pkg) for pkg in app_packages)`
- [x] 2.4 Run `/rv-test-run rv-android-core` — confirm new tests PASS and existing tests unaffected

## 3. Verification

- [x] 3.1 Run `/rv-qa-lint-fix rv-android-core`
- [x] 3.2 Run `/rv-verify rv-android-core`
- [x] 3.3 Verify acceptance criteria from plan.md (both defects fixed, all three regression cases covered)
