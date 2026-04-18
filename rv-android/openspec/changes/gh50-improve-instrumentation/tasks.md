## 1. Configuration: weaving_excludes.yaml + aop.xml generation

- [ ] 1.1 Create `modules/rv-instrumentation/src/rv_instrumentation/assets/weaving_excludes.yaml` with default exclude patterns aligned with `Coverage.aj`: `com.google..*`, `androidx..*`, `kotlin..*`, `kotlinx..*`, `android.support..*`, `android..*`, `com.android..*`, `j$..*`, `org.apache..*`, `com.facebook..*`, `okhttp3..*`, `okio..*`, `com.squareup..*`, `io.reactivex..*`
- [ ] 1.2 Add `_load_weaving_excludes()` method to `RVInstrumentation` in `rvandroid.py`: loads YAML from `assets/weaving_excludes.yaml` via `importlib.resources`, returns list of pattern strings. Returns empty list if file not found (backward compatible).
- [ ] 1.3 Add `_generate_aop_xml(excludes, output_dir)` method to `RVInstrumentation` in `rvandroid.py`: writes `aop.xml` directly in `output_dir` (no `META-INF/` subdirectory — `-xmlConfigured` takes explicit path). Returns path to aop.xml or None if no patterns.
- [ ] 1.4 Add unit tests for `_load_weaving_excludes()` and `_generate_aop_xml()`:
  - [ ] Test YAML loading returns correct patterns
  - [ ] Test empty list when YAML not found
  - [ ] Test aop.xml content matches patterns
  - [ ] Test aop.xml returns None when empty list
- [ ] 1.5 Run `/rv-test-run rv-instrumentation`

## 2. ASM COMPUTE_FRAMES post-weaving step

- [ ] 2.1 Create `rv-frame-computer.jar`: a small Java utility that takes a directory path and classpath as arguments, walks all `.class` files recursively, reads each with `ClassReader`, writes with `ClassWriter(ClassWriter.COMPUTE_FRAMES)`, and overwrites the file. Files that fail are logged and skipped. Reports count of processed/failed files. Uses ASM from `aspectjtools.jar` on classpath (no new dependency).
- [ ] 2.2 Add `__compute_stack_frames(app)` method to `RVInstrumentation` in `rvandroid.py`: invokes `rv-frame-computer.jar` via `Command("java", ["-jar", jar_path, tmp_dir, "--classpath", classpath])`. Decorated with `@ErrorHandler.handle_errors(phase="frame_computation", reraise=True)`.
- [ ] 2.3 Integrate `__compute_stack_frames()` in the pipeline: call after `__weave_monitors()` and before `__merge_support_classes()` (after source file cleanup, before library extraction).
- [ ] 2.4 Add `frame_computer_jar_path` to `RVInstrumentationConfig`: resolve from `assets/rv-frame-computer.jar`.
- [ ] 2.5 Place built `rv-frame-computer.jar` in `modules/rv-instrumentation/src/rv_instrumentation/assets/`.
- [ ] 2.6 Add unit tests:
  - [ ] Test `__compute_stack_frames` invokes correct command with classpath
  - [ ] Test pipeline calls frame computation after weaving
- [ ] 2.7 Run `/rv-test-run rv-instrumentation`

## 3. Pipeline flags: d8 --no-desugaring + ajc -proceedOnError + -xmlConfigured

- [ ] 3.1 In `rvandroid.py:__d8()`, add `"--no-desugaring"` to the d8 command args list (after `"--release"`)
- [ ] 3.2 In `rvandroid.py:__weave_monitors()`, add `"-proceedOnError"` to the ajc command args list
- [ ] 3.3 In `rvandroid.py:__weave_monitors()`, before building the ajc command: call `_load_weaving_excludes()`, if patterns exist call `_generate_aop_xml(excludes, self.config.tmp_dir)`, if aop.xml generated add `"-xmlConfigured", aop_xml_path` to ajc args
- [ ] 3.4 Add unit tests:
  - [ ] Test d8 command includes `--no-desugaring`
  - [ ] Test ajc command includes `-proceedOnError`
  - [ ] Test ajc command includes `-xmlConfigured` when YAML exists
  - [ ] Test ajc command does NOT include `-xmlConfigured` when YAML absent
- [ ] 3.5 Run `/rv-test-run rv-instrumentation`

## 4. Dynamic android.jar selection

- [ ] 4.1 Modify `__get_android_jar(app)` in `rvandroid.py`: try `android-{app.sdk_target}/android.jar`, fallback to highest available `android-XX` in `android_platforms_dir`, minimum `android-26`. Log the selected platform.
- [ ] 4.2 Add `android_platforms_dir` field to `RVInstrumentationConfig` if not present (resolve from `ANDROID_HOME/platforms/`).
- [ ] 4.3 Add unit tests:
  - [ ] Test exact match: sdk_target=34 → android-34/android.jar
  - [ ] Test fallback: sdk_target=36 (unavailable) → highest available
  - [ ] Test minimum: sdk_target=None → fallback to current behavior
- [ ] 4.4 Run `/rv-test-run rv-instrumentation`

## 5. AspectJ 1.9.25.1 upgrade

- [ ] 5.1 Update `rvsec/pom.xml:32`: change `<aspectj.version>1.9.24</aspectj.version>` to `<aspectj.version>1.9.25.1</aspectj.version>`
- [ ] 5.2 Update `docker/base/Dockerfile`: change AspectJ download URL from `1.9.24` to `1.9.25.1` and update version comment
- [ ] 5.3 Download AspectJ 1.9.25.1 binary locally and install to `/opt/aspectj` (or configured path)
- [ ] 5.4 Rebuild Docker base image and verify AspectJ version: `docker build -t phtcosta/rvsec_base:0.9.0 docker/base/`
- [ ] 5.5 Run `/rv-test-run rv-instrumentation` to verify no regressions

## 6. Empirical validation

- [ ] 6.1 Select 10 APKs that failed JCA instrumentation from error dataset (mix of d8 AIOOBE, j$ prefix, ajc crash families)
- [ ] 6.2 Create test directory with these 10 APKs
- [ ] 6.3 Run instrumentation with all changes: `uv run rv-instrumentation batch --apks-dir <test-dir> --output /tmp/gh50_test --verbose --summary`
- [ ] 6.4 Compare results: count how many of the 10 now instrument successfully. Target: ≥5/10
- [ ] 6.5 Verify zero-pointcut matches bucket in generic_new did not increase
- [ ] 6.6 Run a larger batch (40 APKs from JCA error set) to measure overall improvement
- [ ] 6.7 If results are below target, investigate: which failures remain? Are they d8 AIOOBE on app code? COMPUTE_FRAMES failures? Something else?

## 7. Verification

- [ ] 7.1 Run `/rv-qa-lint-fix rv-instrumentation`
- [ ] 7.2 Run `/rv-verify rv-instrumentation`
- [ ] 7.3 Invoke `/rv-code-reviewer` via Skill tool
