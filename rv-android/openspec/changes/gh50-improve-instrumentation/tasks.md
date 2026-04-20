## 1. Configuration: weaving_excludes.yaml + aop.xml generation — REVERTED (see Section 8)

- [~] 1.1 ~~Create `modules/rv-instrumentation/assets/weaving_excludes.yaml`~~ — Reverted Apr 2026 (D-REVERT). File moved to `backup/`.
- [~] 1.2 ~~Add `_load_weaving_excludes()` method~~ — Reverted. Method deleted; `pyyaml` dependency removed from `pyproject.toml`.
- [~] 1.3 ~~Add `_generate_aop_xml()` method~~ — Reverted. Method deleted.
- [~] 1.4 ~~Unit tests for YAML loading / aop.xml generation~~ — Reverted. Tests deleted.
- [~] 1.5 ~~/rv-test-run rv-instrumentation~~ — Superseded by Section 8.

## 2. ASM COMPUTE_FRAMES post-weaving step

- [x] 2.1 Create Maven module `rvsec-frame-computer` under `rvsec/rvsec-android/`: pom.xml with `org.ow2.asm:asm:9.7.1` dependency, `maven-assembly-plugin` (fat JAR ~133KB), `maven-resources-plugin` (copy to `rv-android/lib/frame-computer/`). Java class `br.unb.cic.rvsec.frame.FrameComputer` walks `.class` files, reads with `ClassReader`, writes with `ClassWriter(COMPUTE_FRAMES)` via custom `FrameComputingClassWriter` that resolves type hierarchy through `URLClassLoader`. **Critical**: `ClassWriter` must NOT receive `ClassReader` as constructor arg — with reader, ASM optimizes by copying original frames (no-op when StackMapTable is absent). Without reader, forces full recomputation. Error handling catches `Throwable` (not just `Exception`) because dex2jar produces classes with illegal modifiers that trigger `ClassFormatError`.
- [x] 2.2 Register module in `rvsec/rvsec-android/pom.xml` `<modules>` list. Build and install: `mvn clean package && mvn install`.
- [x] 2.3 Add `__compute_stack_frames(app)` method to `RVInstrumentation` in `rvandroid.py`: invokes `rv-frame-computer.jar` from `lib/frame-computer/` via `Command("java", ["-jar", jar_path, tmp_dir, "--classpath", classpath])`. Decorated with `@ErrorHandler.handle_errors(phase="frame_computation", reraise=True)`. Graceful skip if jar not found.
- [x] 2.4 Integrate `__compute_stack_frames()` in the pipeline: call after `__weave_monitors()` (Phase 4) and before `__create_apk()` (Phase 5-7).
- [x] 2.5 Add unit tests: TestComputeStackFrames (2 tests — invocation with classpath, graceful skip when jar not found)
- [x] 2.6 Run `/rv-test-run rv-instrumentation` — 61/61 passed

## 3. Pipeline flags: ajc -proceedOnError + d8 skip_stderr (partial revert — see Section 8)

- [~] 3.1 ~~d8 `--no-desugaring`~~ — Reverted Apr 2026 (D-REVERT).
- [x] 3.2 In `rvandroid.py:__weave_monitors()`, add `"-proceedOnError"` to the ajc command args list.
- [~] 3.3 ~~ajc `-xmlConfigured` + aop.xml~~ — Reverted Apr 2026 (D-REVERT).
- [x] 3.4 In `rvandroid.py:__d8()`, add `skip_stderr=True` to d8 `execute_command` call. d8 emits non-fatal "Expected stack map table" warnings to stderr even on success (exit code 0). Same pattern as dex2jar which already uses `skip_stderr=True`. Real errors still caught via exit code != 0.
- [x] 3.5 Unit tests: `test_ajc_includes_proceed_on_error`, `test_d8_skip_stderr`. The original `test_ajc_includes_xml_configured_when_yaml_exists`, `test_ajc_no_xml_configured_when_yaml_absent`, `test_d8_includes_no_desugaring` were deleted in Section 8.
- [x] 3.6 Run `/rv-test-run rv-instrumentation` — tests pass after Section 8 cleanup.

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

## 6. Empirical validation (initial — pre-regression)

- [x] 6.1 Select 10 APKs: cryptoapp (baseline) + 9 from F-Droid 2026 JCA failures (3 d8 code=0, 3 d8 code=1, 3 ajc code=255)
- [x] 6.2 Create test directory at `/tmp/gh50_test/apks/` with 10 APKs
- [x] 6.3 Run instrumentation: `rv-experiment run --tools monkey --apks-dir /tmp/gh50_test/apks --specification-set jca --skip-execution --skip-static --timeout 60`
- [x] 6.4 Result: **10/10 APKs instrumented successfully** at *pipeline* level (APKs generated without errors). ⚠️ This validation only verified that the instrumentation pipeline completed and produced signed APKs — it did NOT verify runtime weaving effectiveness. Regression discovered in Section 8.
- [x] 6.5 Full 400 APK JCA preprocessing via Docker (10 containers): **352/400 (88.0%) instrumented** (baseline 70/400 = 17.5%) at pipeline level. Same caveat as 6.4.
- [x] 6.6 Static analysis on 352 instrumented APKs: **97/352 (27.6%) with SA data** — same rate as baseline. Root cause of SA failures: Soot 3.3.0 `TypeResolver` crash (`Unexpected type null` in `DexBody.jimplify()`) on modern Kotlin bytecode. Instantaneous crash (7-50s), not timeout. Exit code 0 despite crash (Soot handles exception internally). Not fixable without Soot upgrade — out of gh50 scope. Installed `platforms;android-35` and `platforms;android-36` locally and in Docker (GATOR fails silently without matching android.jar).
- [x] 6.7 Investigation: confirmed via direct Java invocation that GATOR/Soot crash is structural (Soot 3.3.0 incompatible with Kotlin/Compose bytecode). APKs that work (e.g., be.chvp.nanoledger) take ~165s for SA. APKs that fail crash in Soot before reaching GUIAnalysis phase.

## 7. Verification

- [ ] 7.1 Run `/rv-qa-lint-fix rv-instrumentation`
- [ ] 7.2 Run `/rv-verify rv-instrumentation`
- [ ] 7.3 Invoke `/rv-code-reviewer` via Skill tool

## 8. Regression investigation & revert (Apr 2026)

Two flags landed in Sections 1 and 3 produced APKs that **passed all pipeline checks** but failed at runtime: the app either crashed on launch (`IllegalAccessError`) or produced zero `RVSEC-COV` / `RVSEC` events. Root causes identified on `cryptoapp.apk` and fixed by reverting the two flags.

### 8.1 Discovery

- [x] 8.1.1 Run full `rv-experiment` end-to-end (`cryptoapp.apk`, 60s timeout, aperv tool) with static analysis enabled → pipeline reports success, `results/gh51_e2e_full/` contains signed APKs + SA JSON, but logcat file contains only 2 header lines and Coverage CSV reports 0% for every metric.
- [x] 8.1.2 Confirm APK was actually generated (file present, monitor `.aj` and `.java` files present under `results/.../monitors/`) and structurally valid (apksigner accepts it; installs on emulator).
- [x] 8.1.3 Launch APK manually via `adb shell am start -n br.unb.cic.cryptoapp/.MainActivity`, capture full logcat → observe `FATAL EXCEPTION: MonitorCleaner / java.lang.IllegalAccessError: Field '…TerminatedMonitorCleaner.removedEntries' is inaccessible to class '…TerminatedMonitorCleaner$Runner'`.

### 8.2 Diagnose bug #1 — `-xmlConfigured` + aop.xml

- [x] 8.2.1 Extract `cryptoapp.apk` and inspect DEX with `dexdump -d`. `classes.dex` contains the compiled `Coverage` and `MultiSpec_1MonitorAspect` classes (from `.aj` sources). App DEX files `classes2.dex…classes6.dex` contain `br.unb.cic.cryptoapp.*` classes but **zero `aspectOf` invocations**. No pointcut is applied in app bytecode.
- [x] 8.2.2 Inspect generated `aop.xml`: it contains only `<aspectj><weaver><exclude within="…"/></weaver></aspectj>` — no `<aspects>` element.
- [x] 8.2.3 Map to AspectJ CTW semantics: when `-xmlConfigured <path>` is passed, ajc switches to XML-driven weaving. Aspects in `-sourceroots` are compiled to `.class` but **are not activated for weaving unless declared under `<aspects>`** in the XML. Net effect: aspects present as classes in the DEX, zero advice injected into app bytecode.
- [x] 8.2.4 Revert `-xmlConfigured` block in `__weave_monitors()`, rebuild APK. Re-inspect DEX: `classes.dex` now shows `MultiSpec_1MonitorAspect.ajc$afterReturning$mop_MultiSpec_1MonitorAspect$72$9ebf9b72(Ljava/security/MessageDigest;)V` invoked immediately after `MessageDigest.getInstance()` in `MessageDigestUtil` — bytecode-level proof that weaving is active. `aspectOf` count: 0 (before revert) → 231 (after revert) in classes.dex.

### 8.3 Diagnose bug #2 — `--no-desugaring`

- [x] 8.3.1 Launch revert-#1 APK on emulator → Coverage events fire (`RVSEC-COV: br.unb.cic.cryptoapp.MainActivity.onCreate`) but app still crashes on first `MonitorCleaner` tick with `IllegalAccessError`.
- [x] 8.3.2 Inspect `TerminatedMonitorCleaner$Runner.updateEntries()` bytecode in `classes.dex`: first instruction is `sget-object v0, TerminatedMonitorCleaner.removedEntries:Ljava/util/List;` — **direct static field read** against a private field of the outer class.
- [x] 8.3.3 List methods of outer `TerminatedMonitorCleaner`: only `<clinit>`, `<init>`, `addSet`, `getThread`, `removeSet`, `start` — no `access$000` / `access$100` synthetic accessors.
- [x] 8.3.4 Map to JVM spec: JDK 11+ nest-based access control (JEP 181) allows direct access between nest-mates without synthetic accessors. `rv-monitor-rt.jar` is compiled with JDK 11+ bytecode. Dalvik with `--min-api 26` (Android 8.0-10.0) does not implement nest-based access control; d8 normally desugars nest-mate access into synthetic accessors unless `--no-desugaring` is set.
- [x] 8.3.5 Revert `--no-desugaring` from `__d8()`, rebuild APK. Re-launch on emulator: no crash; `MonitorCleaner` thread runs normally; logcat shows 12 `RVSEC-COV` events (app-method coverage) and 2 `RVSEC` events (`MessageDigestSpec, UnsafeAlgorithm, expecting one of {SHA-256, SHA-384, SHA-512} but found MD5` and `InvalidSequenceOfMethodCalls, unknown`) during manual interaction.

### 8.4 Apply definitive fix

- [x] 8.4.1 Delete the `-xmlConfigured` code path from `__weave_monitors()` in `rvandroid.py`.
- [x] 8.4.2 Delete helper methods `_load_weaving_excludes()` and `_generate_aop_xml()` from `rvandroid.py`. Remove `import yaml` at the top.
- [x] 8.4.3 Remove `pyyaml>=6.0` from `modules/rv-instrumentation/pyproject.toml` dependencies.
- [x] 8.4.4 Move `modules/rv-instrumentation/assets/weaving_excludes.yaml` to `backup/gh50-reverts/weaving_excludes.yaml` (P3 — no shim, preserved for history).
- [x] 8.4.5 Delete `--no-desugaring` from `__d8()` command args in `rvandroid.py`.
- [x] 8.4.6 Update comment at top of `__d8()` and `__weave_monitors()` to reflect current flags; no migration/history narratives in code (P4).
- [x] 8.4.7 Delete obsolete unit tests in `tests/test_rvandroid.py`: `TestLoadWeavingExcludes`, `TestGenerateAopXml`, `test_ajc_includes_xml_configured_when_yaml_exists`, `test_ajc_no_xml_configured_when_yaml_absent`, `test_d8_includes_no_desugaring`. Keep `test_ajc_includes_proceed_on_error` and rename `TestD8Flags.test_d8_includes_no_desugaring` → `test_d8_skip_stderr_enabled` (only `skip_stderr=True` is asserted).
- [x] 8.4.8 Update `proposal.md`, `design.md`, `specs/instrumentation/spec.md`: remove reverted mitigations from the canonical narrative; add `D-REVERT` decision block with the evidence above; remove INV-INS-13 / INV-INS-15 / INV-INS-16 from the spec.

### 8.5 Re-run verification (open)

- [ ] 8.5.1 Run `/rv-test-run rv-instrumentation` — expect all remaining tests to pass.
- [ ] 8.5.2 Run `/rv-qa-lint-fix rv-instrumentation`.
- [ ] 8.5.3 Run `/rv-verify rv-instrumentation`.
- [ ] 8.5.4 Re-run the 10-APK JCA validation from Section 6.1 with the fixed pipeline; capture logcat and verify that **each successfully instrumented APK emits at least one `RVSEC-COV` event during a 60s `monkey` run**. This closes the validation gap identified by 8.1 (pipeline success ≠ runtime effectiveness).
- [ ] 8.5.5 (Optional, large-scale) Re-run the 400-APK JCA preprocessing and compare instrumentation success rate against Section 6.5.

### 8.6 Evidence artifacts (committed)

- [x] 8.6.1 `results/gh50_val/` — end-to-end rv-experiment run on cryptoapp after revert #1 (weaving restored, monkey exited before full 60s, but logcat shows `RVSEC-COV: MainActivity.onCreate`).
- [x] 8.6.2 `/tmp/cryptoapp_crash.log`, `/tmp/cryptoapp_test2.log` — raw logcat traces (before / after revert #2). Not committed; reproducible via Section 8.1.3 + 8.3.5 commands.
- [x] 8.6.3 DEX inspection commands (dexdump) and exact outputs captured in the corresponding commit message / PR discussion.
