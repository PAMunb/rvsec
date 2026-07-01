<!-- Group 1 (primary fix) must complete first — Group 2 consumes the max-input-API it computes.
     Group 4 (local build + dexdump) runs after 1–3. Group 5 (emulator) requires a user-booted AVD.
     Group 6 (image + report + close) runs last. -->

## 1. Primary fix — preserve input DEX version (`BatchRunner.extractDexes`)

- [ ] 1.1 In `cli/src/main/java/br/unb/cic/rv/cli/BatchRunner.java` `extractDexes` (325–344): read each `classes*.dex` ZIP entry fully into a `byte[]` (instead of streaming straight into `fromInputStream`).
- [ ] 1.2 Parse the DEX magic version from bytes `[4,7)` (`dex\n0XY\0` → int `XY`); build the `DexBackedDexFile` with `Opcodes.forDexVersion(version)` in place of `Opcodes.getDefault()`.
- [ ] 1.3 Guard with try/catch: if `forDexVersion` throws `RuntimeException("Unsupported dex version")` (e.g. `dex036`), fall back to `Opcodes.getDefault()` and log the entry name + raw version.
- [ ] 1.4 Compute and retain the max input-DEX API across the APK's dexes (`VersionMap.mapDexVersionToApi`, or the resolved `opcodes.api`) for Group 2. Confirm line 240 (`DexPool.writeTo`) is left unchanged.

## 2. Monitor-dex fix — d8 `--min-api` (`MonitorBuilder.runD8`) — required

Required so the monitor dex (produced by d8, not dexlib2) is also ≥ `037`; without it the dexdump criteria in Group 4 fail for the monitor dex even after Group 1.

- [ ] 2.1 Thread the max input-DEX API from `BatchRunner` (call site line 287) into `MonitorBuilder.build(Path,Path)` / `BuilderConfig` (extend the signature — minimal surface, P1).
- [ ] 2.2 In `monitor-builder/src/main/java/br/unb/cic/rv/builder/MonitorBuilder.java` `runD8` (100–141): add `--min-api <api>` to the `d8` command (~line 115). Do NOT add `--lib android.jar` (P1: monitor sources are plain Java 1.8, runtime jars already on the d8 input) unless a desugaring gap surfaces.

## 3. Tests

- [ ] 3.1 If a `cli`/`monitor-builder` test harness exists (`mvn` JUnit): add a unit test asserting a `dex038` input round-trips to `dex038` after read + `DexPool.writeTo`, and a `dex035` input stays `dex035`. If no harness exists, note it in the change and rely on the Group 4/5 empirical checks.

## 4. Local build + DEX-version check (no emulator)

- [ ] 4.1 Build: `mvn -q -pl cli -am package` at the instrumenter root → `cli/target/instr-cli.jar`.
- [ ] 4.2 PREREQUISITE for local re-instrumentation: ensure `RVSEC_HOME` is set and generate the descriptor + monitors + classpath for openbible & lumo via the rv-android wrapper `modules/rv-instrumentation-dexlib2/src/rv_instrumentation_dexlib2/dexlib_instrumentation.py` (`prepare_instrumentation`) or the Docker image. The pilot work-dir was cleaned — no descriptor exists on the host, so this must be regenerated before 4.3/4.4.
- [ ] 4.3 Re-instrument openbible locally with the fixed jar and confirm every output `classes*.dex` — app dexes AND the monitor dex — is `dex038` (magic check: `head -c8 <dex> | tr -d '\0'`), NOT `035`.
- [ ] 4.4 Re-instrument lumo and confirm every output `classes*.dex` (app + monitor) is `dex039`, NOT `035`.
- [ ] 4.5 Confirm a `dex035`-origin app (e.g. termux/wikipedia) still emits `dex035` (round-trip unchanged).

## 5. Real re-verification on AVD (user boots emulator)

- [ ] 5.1 ASK the user to boot AVD `RVSec` (API 30 / google_apis / x86_64); confirm exactly 1 device online via `$ANDROID_HOME/platform-tools/adb devices` before installing. Do NOT start the emulator.
- [ ] 5.2 openbible (`com.schwegelbin.openbible`): `adb uninstall`; `adb install -r -g <instrumented>`; `adb logcat -c`; `monkey -p <pkg> -c android.intent.category.LAUNCHER 1`; wait ~15s → logcat has no `IncompatibleClassChange`/`FATAL EXCEPTION`, `Displayed <pkg>` present, `RVSEC-COV` count > 0 (ref 208); `adb uninstall`.
- [ ] 5.3 lumo (manifest pkg `me.proton.lumo`; resolve via `aapt2 dump badging`): same launch sequence → no crash, `Displayed` present, `RVSEC-COV` > 0 (ref 2424); `adb uninstall`.

## 6. Image rebuild, report, close-out

- [ ] 6.1 Commit the fix on `modules` (`closes #73`; trailer `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`) and push to `origin/modules`.
- [ ] 6.2 Rebuild the image via `docker/rvandroid/build.sh` (clones `PAMunb/rvsec@modules`); confirm `instr-cli.jar` inside `phtcosta/rvandroid:0.9.1` carries the fix.
- [ ] 6.3 Update report §7.1 (absolute path in plan.md) to APPLIED + VERIFIED with commit hash + re-verification numbers.
- [ ] 6.4 Verify all acceptance criteria in plan.md §5 are met; move the Kanban card (#73) to Done.

## 7. Verification (final)

- [ ] 7.1 `mvn -pl cli -am test` (or module test goal) green where a harness exists.
- [ ] 7.2 Diff review: changes limited to the read-opcodes call site, the d8 `--min-api` arg, the threaded API value, and tests — weave/coverage/merger untouched.
- [ ] 7.3 All acceptance criteria from plan.md §5 checked.
