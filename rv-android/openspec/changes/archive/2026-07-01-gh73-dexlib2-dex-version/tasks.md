<!-- Group 1 (primary fix) must complete first — Group 2 consumes the max-input-API it computes.
     Group 4 (local build + dexdump) runs after 1–3. Group 5 (emulator) requires a user-booted AVD.
     Group 6 (image + report + close) runs last. -->

## 1. Primary fix — preserve input DEX version (`BatchRunner.extractDexes`)

- [x] 1.1 In `cli/src/main/java/br/unb/cic/rv/cli/BatchRunner.java` `extractDexes` (325–344): read each `classes*.dex` ZIP entry fully into a `byte[]` (instead of streaming straight into `fromInputStream`).
- [x] 1.2 Parse the DEX magic version from bytes `[4,7)` (`dex\n0XY\0` → int `XY`); build the `DexBackedDexFile` with `Opcodes.forDexVersion(version)` in place of `Opcodes.getDefault()`.
- [x] 1.3 Guard with try/catch: if `forDexVersion` throws `RuntimeException("Unsupported dex version")` (e.g. `dex036`), fall back to `Opcodes.getDefault()` and log the entry name + raw version.
- [x] 1.4 Compute and retain the max input-DEX API across the APK's dexes (`VersionMap.mapDexVersionToApi`, or the resolved `opcodes.api`) for Group 2. Confirm line 240 (`DexPool.writeTo`) is left unchanged.

## 2. Monitor-dex fix — d8 `--min-api` (`MonitorBuilder.runD8`) — required

Required so the monitor dex (produced by d8, not dexlib2) is also ≥ `037`; without it the dexdump criteria in Group 4 fail for the monitor dex even after Group 1.

- [x] 2.1 Thread the max input-DEX API from `BatchRunner` (call site line 287) into `MonitorBuilder.build(Path,Path)` / `BuilderConfig` (extend the signature — minimal surface, P1).
- [x] 2.2 In `monitor-builder/src/main/java/br/unb/cic/rv/builder/MonitorBuilder.java` `runD8` (100–141): add `--min-api <api>` to the `d8` command (~line 115). Do NOT add `--lib android.jar` (P1: monitor sources are plain Java 1.8, runtime jars already on the d8 input) unless a desugaring gap surfaces.

## 3. Tests

- [x] 3.1 If a `cli`/`monitor-builder` test harness exists (`mvn` JUnit): add a unit test asserting a `dex038` input round-trips to `dex038` after read + `DexPool.writeTo`, and a `dex035` input stays `dex035`. If no harness exists, note it in the change and rely on the Group 4/5 empirical checks. — DONE: `cli/src/test/java/br/unb/cic/rv/cli/DexVersionPreservationTest.java` (2 tests, both green; exercises `BatchRunner.opcodesForDex` + `DexPool.writeTo` round-trip for dex038 and dex035).

## 4. Local build + DEX-version check (no emulator)

- [x] 4.1 Build: `mvn -q -pl cli -am package` at the instrumenter root → `cli/target/instr-cli.jar`. — DONE: BUILD SUCCESS, `cli/target/instr-cli.jar` (6.9 MB); full `cli -am` test suite green incl. new round-trip test.
- [x] 4.2 PREREQUISITE for local re-instrumentation: ensure `RVSEC_HOME` is set and generate the descriptor + monitors + classpath for openbible & lumo via the rv-android wrapper `modules/rv-instrumentation-dexlib2/src/rv_instrumentation_dexlib2/dexlib_instrumentation.py` (`prepare_instrumentation`) or the Docker image. The pilot work-dir was cleaned — no descriptor exists on the host, so this must be regenerated before 4.3/4.4. — DONE via `rv-experiment run --instrumentation-variant dexlib2 --specification-set jca --skip-static --skip-execution` (monitors + classpath regenerated under `results/gh73_verify/`).
- [x] 4.3 Re-instrument openbible locally with the fixed jar and confirm every output `classes*.dex` — app dexes AND the monitor dex — is `dex038` (magic check: `head -c8 <dex> | tr -d '\0'`), NOT `035`. — DONE: all 10 DEXes in instrumented `com.schwegelbin.openbible_46.apk` are dex038, 0 dex035.
- [x] 4.4 Re-instrument lumo and confirm every output `classes*.dex` (app + monitor) is `dex039`, NOT `035`. — DONE: all 20 DEXes in instrumented `me.proton.android.lumo_50.apk` are dex039, 0 dex035.
- [x] 4.5 Confirm a `dex035`-origin app (e.g. termux/wikipedia) still emits `dex035` (round-trip unchanged). — DONE: `cryptoapp.apk` (dex035 origin) → all 7 instrumented DEXes stay dex035, 0 spurious upgrades.

## 5. Real re-verification on AVD (user boots emulator)

- [x] 5.1 ASK the user to boot AVD `RVSec` (API 30 / google_apis / x86_64); confirm exactly 1 device online via `$ANDROID_HOME/platform-tools/adb devices` before installing. Do NOT start the emulator. — DONE: user booted emulator; `emulator-5554` single device online, `sys.boot_completed=1`.
- [x] 5.2 openbible (`com.schwegelbin.openbible`): `adb uninstall`; `adb install -r -g <instrumented>`; `adb logcat -c`; `monkey -p <pkg> -c android.intent.category.LAUNCHER 1`; wait ~15s → logcat has no `IncompatibleClassChange`/`FATAL EXCEPTION`, `Displayed <pkg>` present, `RVSEC-COV` count > 0 (ref 208); `adb uninstall`. — PASS: no crash, `Displayed com.schwegelbin.openbible/.MainActivity`, RVSEC-COV=208 (== ref); uninstalled.
- [x] 5.3 lumo (manifest pkg `me.proton.lumo`; resolve via `aapt2 dump badging`): same launch sequence → no crash, `Displayed` present, `RVSEC-COV` > 0 (ref 2424); `adb uninstall`. — PASS: no crash, `Displayed me.proton.lumo/me.proton.android.lumo.MainActivity`, RVSEC-COV=2424 (== ref); uninstalled.

## 6. Image rebuild, report, close-out

- [x] 6.1 Commit the fix on `modules` (`closes #73`; NO co-author trailer — user is sole author) and push to `origin/modules`. — DONE: commit `d73ebc41`, pushed `c2083c92..d73ebc41`.
- [~] 6.2 Rebuild the image via `docker/rvandroid/build.sh` (clones `PAMunb/rvsec@modules`); confirm `instr-cli.jar` inside `phtcosta/rvandroid:0.9.1` carries the fix. — DEFERRED (no network for days): full `--no-cache` rebuild not viable. Delivery changed to a surgical, offline swap of the fixed fat jar (`.../rv-android/modules/rv-instrumentation-dexlib2/lib/instr-cli.jar`, has `opcodesForDex`) into the existing image — either a thin `FROM phtcosta/rvandroid:0.9.1` + `COPY` layer (→ `:0.9.1-gh73`) or a runtime `-v` mount over `/opt/rvsec/rv-android/modules/rv-instrumentation-dexlib2/lib/instr-cli.jar`. Handed to the rvsec-dataset session (prompt provided) to execute + validate on the 2 pilots before the 225-APK run.
- [x] 6.3 Update report §7.1 (absolute path in plan.md) to APPLIED + VERIFIED with commit hash + re-verification numbers. — DONE: §7.1 UPDATE block added (commit `d73ebc41`, openbible 208 / lumo 2424 / cryptoapp dex035).
- [x] 6.4 Verify all acceptance criteria in plan.md §5 are met; move the Kanban card (#73) to Done. — DONE: all code/empirical criteria in §5 met; Kanban #73 → Done; issue #73 CLOSED (manually — `closes #73` doesn't auto-fire from non-default `modules`). Only the image-delivery bullet is deferred to the surgical jar swap (see 6.2).

## 7. Verification (final)

- [x] 7.1 `mvn -pl cli -am test` (or module test goal) green where a harness exists. — DONE: full `cli -am` suite green (all modules 0 failures/0 errors), incl. `DexVersionPreservationTest` (2/2).
- [x] 7.2 Diff review: changes limited to the read-opcodes call site, the d8 `--min-api` arg, the threaded API value, and tests — weave/coverage/merger untouched. — DONE: `git diff` = `BatchRunner.java` (+51/-9), `MonitorBuilder.java` (+17/-3), new `DexVersionPreservationTest.java`; no other files.
- [x] 7.3 All acceptance criteria from plan.md §5 checked. — DONE: all code + empirical criteria checked in plan.md §5 (opcodes fix, `--min-api`, build, openbible 10×dex038/COV=208, lumo 20×dex039/COV=2424, cryptoapp dex035 round-trip, unit test, diff scope). The two delivery-only bullets (image rebuilt / report VERIFIED): report done (6.3); image delivery deferred to the offline surgical jar swap (6.2).
