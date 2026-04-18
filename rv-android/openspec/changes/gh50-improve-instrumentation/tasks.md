## 1. Configuration: weaving_excludes.yaml + aop.xml generation

- [ ] 1.1 Create `modules/rv-instrumentation/src/rv_instrumentation/assets/weaving_excludes.yaml` with default exclude patterns: `com.google..*`, `androidx..*`, `kotlin..*`, `kotlinx..*`, `android.support..*`, `j$..*`, `org.apache..*`, `okhttp3..*`, `okio..*`, `com.squareup..*`, `com.facebook..*`, `io.reactivex..*`
- [ ] 1.2 Add `_load_weaving_excludes()` method to `RVInstrumentation` in `rvandroid.py`: loads YAML from `assets/weaving_excludes.yaml` via `importlib.resources`, returns list of pattern strings. Returns empty list if file not found (backward compatible).
- [ ] 1.3 Add `_generate_aop_xml(excludes, output_dir)` method to `RVInstrumentation` in `rvandroid.py`: writes `aop.xml` directly in `output_dir` (no `META-INF/` subdirectory — `-xmlConfigured` takes explicit path). Returns path to aop.xml or None if no patterns.
- [ ] 1.4 Add unit tests for `_load_weaving_excludes()` and `_generate_aop_xml()`:
  - Test YAML loading returns correct patterns
  - Test empty list when YAML not found
  - Test aop.xml content matches patterns
  - Test aop.xml returns None when empty list
- [ ] 1.5 Run `/rv-test-run rv-instrumentation`

## 2. Pipeline flags: d8 --no-desugaring + ajc -proceedOnError + -xmlConfigured

- [ ] 2.1 In `rvandroid.py:__d8()`, add `"--no-desugaring"` to the d8 command args list (after `"--release"`)
- [ ] 2.2 In `rvandroid.py:__weave_monitors()`, add `"-proceedOnError"` to the ajc command args list
- [ ] 2.3 In `rvandroid.py:__weave_monitors()`, before building the ajc command: call `_load_weaving_excludes()`, if patterns exist call `_generate_aop_xml(excludes, self.config.tmp_dir)`, if aop.xml generated add `"-xmlConfigured"` to ajc args
- [ ] 2.4 Add unit tests:
  - Test d8 command includes `--no-desugaring`
  - Test ajc command includes `-proceedOnError`
  - Test ajc command includes `-xmlConfigured` when YAML exists
  - Test ajc command does NOT include `-xmlConfigured` when YAML absent
- [ ] 2.5 Run `/rv-test-run rv-instrumentation`

## 3. Empirical validation

- [ ] 3.1 Select 10 APKs that failed JCA instrumentation from error dataset (mix of d8 AIOOBE, j$ prefix, ajc crash families)
- [ ] 3.2 Create test directory with these 10 APKs
- [ ] 3.3 Run instrumentation with new flags: `uv run rv-instrumentation batch --apks-dir <test-dir> --output /tmp/gh50_test --verbose --summary`
- [ ] 3.4 Compare results: count how many of the 10 now instrument successfully. Target: ≥5/10
- [ ] 3.5 If < 5/10 succeed, investigate remaining failures and decide on pre-filtering fallback
- [ ] 3.6 Run a larger batch (40 APKs from JCA error set) to measure overall improvement

## 4. Verification

- [ ] 4.1 Run `/rv-qa-lint-fix rv-instrumentation`
- [ ] 4.2 Run `/rv-verify rv-instrumentation`
- [ ] 4.3 Invoke `/rv-code-reviewer` via Skill tool
