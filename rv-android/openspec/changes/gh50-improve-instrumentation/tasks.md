## 1. Configuration: weaving_excludes.yaml + aop.xml generation

- [x] 1.1 Create `modules/rv-instrumentation/assets/weaving_excludes.yaml` with default exclude patterns aligned with `Coverage.aj`: `com.google..*`, `androidx..*`, `kotlin..*`, `kotlinx..*`, `android.support..*`, `android..*`, `com.android..*`, `j$..*`, `org.apache..*`, `com.facebook..*`, `okhttp3..*`, `okio..*`, `com.squareup..*`, `io.reactivex..*`
- [x] 1.2 Add `_load_weaving_excludes()` method to `RVInstrumentation` in `rvandroid.py`: loads YAML from `assets/weaving_excludes.yaml` via Path resolution, returns list of pattern strings. Returns empty list if file not found (backward compatible). Added `pyyaml>=6.0` to `pyproject.toml` dependencies.
- [x] 1.3 Add `_generate_aop_xml(excludes, output_dir)` method to `RVInstrumentation` in `rvandroid.py`: writes `aop.xml` directly in `output_dir` (no `META-INF/` subdirectory — `-xmlConfigured` takes explicit path). Returns path to aop.xml or None if no patterns.
- [x] 1.4 Add unit tests for `_load_weaving_excludes()` and `_generate_aop_xml()`: TestLoadWeavingExcludes (2 tests), TestGenerateAopXml (3 tests)
- [x] 1.5 Run `/rv-test-run rv-instrumentation` — 61/61 passed

## 2. ASM COMPUTE_FRAMES post-weaving step

- [x] 2.1 Create Maven module `rvsec-frame-computer` under `rvsec/rvsec-android/`: pom.xml with `org.ow2.asm:asm:9.7.1` dependency, `maven-assembly-plugin` (fat JAR ~133KB), `maven-resources-plugin` (copy to `rv-android/lib/frame-computer/`). Java class `br.unb.cic.rvsec.frame.FrameComputer` walks `.class` files, reads with `ClassReader`, writes with `ClassWriter(COMPUTE_FRAMES)` via custom `FrameComputingClassWriter` that resolves type hierarchy through `URLClassLoader`. **Critical**: `ClassWriter` must NOT receive `ClassReader` as constructor arg — with reader, ASM optimizes by copying original frames (no-op when StackMapTable is absent). Without reader, forces full recomputation. Error handling catches `Throwable` (not just `Exception`) because dex2jar produces classes with illegal modifiers that trigger `ClassFormatError`.
- [x] 2.2 Register module in `rvsec/rvsec-android/pom.xml` `<modules>` list. Build and install: `mvn clean package && mvn install`.
- [x] 2.3 Add `__compute_stack_frames(app)` method to `RVInstrumentation` in `rvandroid.py`: invokes `rv-frame-computer.jar` from `lib/frame-computer/` via `Command("java", ["-jar", jar_path, tmp_dir, "--classpath", classpath])`. Decorated with `@ErrorHandler.handle_errors(phase="frame_computation", reraise=True)`. Graceful skip if jar not found.
- [x] 2.4 Integrate `__compute_stack_frames()` in the pipeline: call after `__weave_monitors()` (Phase 4) and before `__create_apk()` (Phase 5-7).
- [x] 2.5 Add unit tests: TestComputeStackFrames (2 tests — invocation with classpath, graceful skip when jar not found)
- [x] 2.6 Run `/rv-test-run rv-instrumentation` — 61/61 passed

## 3. Pipeline flags: d8 --no-desugaring + ajc -proceedOnError + -xmlConfigured + d8 skip_stderr

- [x] 3.1 In `rvandroid.py:__d8()`, add `"--no-desugaring"` to the d8 command args list (after `"--release"`)
- [x] 3.2 In `rvandroid.py:__weave_monitors()`, add `"-proceedOnError"` to the ajc command args list
- [x] 3.3 In `rvandroid.py:__weave_monitors()`, before building the ajc command: call `_load_weaving_excludes()`, if patterns exist call `_generate_aop_xml(excludes, self.config.tmp_dir)`, if aop.xml generated add `"-xmlConfigured", aop_xml_path` to ajc args
- [x] 3.4 In `rvandroid.py:__d8()`, add `skip_stderr=True` to d8 `execute_command` call. d8 emits non-fatal "Expected stack map table" warnings to stderr even on success (exit code 0). Same pattern as dex2jar which already uses `skip_stderr=True`. Real errors still caught via exit code != 0.
- [x] 3.5 Add unit tests: TestWeaveMonitorsFlags (3 tests), TestD8Flags (1 test — verifies both `--no-desugaring` and `skip_stderr=True`)
- [x] 3.6 Run `/rv-test-run rv-instrumentation` — 61/61 passed

## 4. Dynamic android.jar selection

- [x] 4.1 Modify `__get_android_jar(app)` in `rvandroid.py`: try `android-{app.sdk_target}/android.jar`, fallback to highest available via `_find_highest_android_platform()`, minimum `android-26`. Log the selected platform.
- [x] 4.2 `android_platforms_dir` field already exists in `RVInstrumentationConfig` (resolved from `ANDROID_HOME/platforms/`).
- [x] 4.3 Add unit tests: TestGetAndroidJar (4 tests — exact match, fallback to highest, fallback to config when no target, skips platforms below 26)
- [x] 4.4 Run `/rv-test-run rv-instrumentation` — 61/61 passed

## 5. AspectJ 1.9.25.1 upgrade

- [x] 5.1 Update `rvsec/pom.xml:32`: change `<aspectj.version>1.9.24</aspectj.version>` to `<aspectj.version>1.9.25.1</aspectj.version>`
- [x] 5.2 Update `docker/base/Dockerfile`: change AspectJ download URL from `1.9.24` to `1.9.25.1`, update version comment, increase `-Xmx` from `4096M` to `8192M`
- [x] 5.3 Download AspectJ 1.9.25.1 binary locally: installed to `~/desenvolvimento/aplicativos/aspectj1.9.25.1/`, updated symlink `aspectj1.9` → `aspectj1.9.25.1`, set `-Xmx8192M` in ajc script
- [x] 5.4 Rebuild Docker images via `build_all.sh`: all 6 images built. Verified in container: AspectJ 1.9.25.1, Bundle-Version 1.9.25.1, -Xmx8192M. Fixed `pyproject.toml` to exclude `modules/rvsmart-tool` from uv workspace (Maven's rvsmart creates this dir during install, but it has no pyproject.toml).
- [x] 5.5 Run `/rv-test-run rv-instrumentation` — 61/61 passed, no regressions

## 6. Empirical validation

- [x] 6.1 Select 10 APKs: cryptoapp (baseline) + 9 from F-Droid 2026 JCA failures (3 d8 code=0, 3 d8 code=1, 3 ajc code=255)
- [x] 6.2 Create test directory at `/tmp/gh50_test/apks/` with 10 APKs
- [x] 6.3 Run instrumentation: `rv-experiment run --tools monkey --apks-dir /tmp/gh50_test/apks --specification-set jca --skip-execution --skip-static --timeout 60`
- [x] 6.4 Result: **10/10 APKs instrumented successfully** (target was ≥5/10). All 3 failure families resolved: d8 code=1 (--no-desugaring + COMPUTE_FRAMES), d8 code=0 (COMPUTE_FRAMES + skip_stderr), ajc code=255 (-proceedOnError + COMPUTE_FRAMES).
- [x] 6.5 Full 400 APK JCA preprocessing via Docker (10 containers): **352/400 (88.0%) instrumented** (baseline 70/400 = 17.5%). 48 failures: 42 d8 code=1 (AIOOBE in app code), 3 dex2jar, 2 ajc, 1 unknown.
- [x] 6.6 Static analysis on 352 instrumented APKs: **97/352 (27.6%) with SA data** — same rate as baseline. Root cause of SA failures: Soot 3.3.0 `TypeResolver` crash (`Unexpected type null` in `DexBody.jimplify()`) on modern Kotlin bytecode. Instantaneous crash (7-50s), not timeout. Exit code 0 despite crash (Soot handles exception internally). Not fixable without Soot upgrade — out of gh50 scope. Installed `platforms;android-35` and `platforms;android-36` locally and in Docker (GATOR fails silently without matching android.jar).
- [x] 6.7 Investigation: confirmed via direct Java invocation that GATOR/Soot crash is structural (Soot 3.3.0 incompatible with Kotlin/Compose bytecode). APKs that work (e.g., be.chvp.nanoledger) take ~165s for SA. APKs that fail crash in Soot before reaching GUIAnalysis phase.

## 7. Verification

- [ ] 7.1 Run `/rv-qa-lint-fix rv-instrumentation`
- [ ] 7.2 Run `/rv-verify rv-instrumentation`
- [ ] 7.3 Invoke `/rv-code-reviewer` via Skill tool
