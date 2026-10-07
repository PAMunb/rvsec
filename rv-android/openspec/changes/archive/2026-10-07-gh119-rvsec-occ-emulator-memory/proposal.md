# Every Violation Occurrence in Logcat (`RVSEC-OCC`), a Thread-Safe Collector, and the Emulator's Memory and Data Partition

GitHub Issue: #119

## Why

The on-device collector reports a violation only the first time it happens in the app process. `ErrorCollector.addError` (`rvsec/rvsec-android/rvsec-logger-logcat`) writes the `RVSEC` line inside `if (errors.add(err))`, keyed by the seven-field `ErrorSummary` identity (specification, error type, class, method, `file:line`, `code`, `ev`). Every later occurrence of the same identity is silent. The offline join of the APE-RV exploration clock (`aperv-tool`, `clock_logcat_join.place_on_timeline`, which places a logcat line on the step of the last `ApeRvHb` heartbeat before it) can therefore attribute a violation to an action only once per process. After that, a step that re-executes violating code is indistinguishable from a step that executes nothing monitored. The Study 03 analysis records this as a limitation: the "re-firing" it can see is only what the dedup lets through, never every re-execution of violating code. A future campaign needs the repetitions in the capture.

Two defects sit next to this. The collector is not thread-safe: the singleton is created lazily without synchronisation and the set is a plain `HashSet`, so two threads can build two instances, or pass `add` together. A per-identity counter built on that state would inherit the race. Separately, the emulator runs with less memory and storage than the image declares. The AVD is created by `avdmanager` with the `pixel` profile defaults — `hw.ramSize=1536M` and `disk.dataPartition.size=800M`, read from `phtcosta/rvsec_android:0.9.4`. The `EMU_MEMORY=4096` and `EMU_PARTITION=8192` of `docker/android/Dockerfile` were read only by `docker/android/scripts/start-emulator.sh`, whose copy into the image is commented out. `Android.start_emulator` (`rv_android_core/util/android/android.py`) passes neither `-memory` nor `-partition-size`.

The logcat buffer does not change. It is 16 MiB per buffer since gh114 (INV-CORE-64). In the 516 `aperv` logcats of the E6 campaign, `RVSEC` peaked at 949 lines in a run and `RVSEC-COV` at 304 828, and the capture absorbed a peak of 6 673 lines in one second; at that rate 16 MiB gives the live reader seconds of slack. Enlarging the buffer instead would cost guest memory. `logcat -G` sizes each default buffer, so 3 × 64 MiB would take 192 MiB of a 1.5 GB guest, which is where the low-memory killer starts to kill the app under test.

## What Changes

- **New tag `RVSEC-OCC`.** After the unchanged first-occurrence `if`, `ErrorCollector.addError` counts every occurrence of the identity and writes one `RVSEC-OCC` line for it, including the first (`n=1`). It writes at most one line per identity every 100 ms. The counter `n` counts every occurrence, the suppressed ones included, so a jump in `n` shows occurrences that did not become a line. The line carries the identity key and `n`: the six fields `ErrorSummary.toString()` already writes at the head of the `RVSEC` line, plus `code`, `ev` and `n`. That is enough to name the error and to join the line to its `RVSEC` line by the key. The envelope is not repeated.
- **`RVSEC` is unchanged.** The line text, the tag, the level and the first-occurrence rule stay byte-identical. Every existing consumer reads tags by exact equality, so `RVSEC-OCC` lines enter no existing count.
- **Thread-safe collector.** The singleton is created when the class loads, and the first-occurrence set and the per-identity counters are backed by `ConcurrentHashMap`.
- **Capture admits `RVSEC-OCC`.** A new constant `TAG_RVSEC_OCC` joins `TAG_RVSEC`, `TAG_RVSEC_COV` and `TAG_APERV_HEARTBEAT`. `LogcatManager.default_tags` gains it. The baseline capture command becomes `-v threadtime -s RVSEC:V RVSEC-COV:V ApeRvHb:V RVSEC-OCC:V`. `-s` is a strict device-side filter, so a tag outside the list is discarded before capture.
- **Emulator memory and data partition.** `Android.start_emulator` passes `-memory 4096 -partition-size 8192`. The values are two constants in `rv_android_core/constants.py`; there is no new environment variable. `hw.cpu.ncore` (4 in the AVD) is not overridden.
- **Logcat buffer: no change** (`LOGCAT_BUFFER_SIZE = "16M"`).
- **Dead emulator configuration removed from `docker/android`.** The Dockerfile drops `EMU_PARTITION`, `EMU_MEMORY`, `EMU_CORES` and `EMU_GPU_MODE`, the `GPU_ACCELERATED` build argument and environment entry, and the two commented `COPY` lines. `docker/android/scripts/start-emulator.sh` and `emulator-monitoring.sh` are deleted, after a copy to `backup/`. Nothing in a running image reads any of them, because the `COPY` that would ship the scripts is commented out. `docs/adr/0006-emulator-execution-profile-cold-boot-no-gpu.md` already names `EMU_GPU_MODE` and the `GPU_ACCELERATED` branch as P3 deletion candidates. `EMU_MEMORY=4096` would otherwise restate a value that now lives in `constants.py`. No image is built.
- **A smoke run on the host measures the occurrence stream.** It uses `rv-experiment run`, and `rv-platform` manages the emulator. The run is the five APKs with the most `RVSEC` lines in E6 (`com.tananaev.passportreader_22`, `app.michaelwuensch.bitbanana_79`, `com.afkanerd.deku_83`, `org.openhab.habdroid_589`, `app.maskan.chat_90`), instrumented from the originals with `jca_android` and `dexlib2` and the new collector and run with the E6 static-analysis artefacts beside them (the arm needs them), under `aperv:mop_off_llm_off` for 600 s with one repetition and diagnostics on. It reports:
  - `RVSEC-OCC` lines per second and the maximum `n` per identity;
  - the pairing of every `RVSEC` line with its `RVSEC-OCC` line at `n=1`, a missing partner being a measured loss;
  - the peak of total captured lines per second against E6's 6 673;
  - where the `RVSEC-OCC` lines fall on the exploration timeline (`aperv-tool` `read_tagged_lines` + `place_on_timeline`).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `instrumentation`: the "Violation Line Emission by the Collector" requirement gains the `RVSEC-OCC` line — its trigger, its throttle, its content and its counter — and the collector's thread-safety. The `RVSEC` line it already specifies stays as written.
- `core`: INV-CORE-37 and INV-CORE-53 change to the four-tag baseline with `TAG_RVSEC_OCC`; INV-CORE-38 keeps `RVSEC-OCC:V` among the tags the diagnostic set never replaces. A new requirement fixes the memory and data-partition arguments of `Android.start_emulator` under "Android Emulator Management".
- `platform`: INV-PLT-21 restates the baseline tag set and the emitted command with `RVSEC-OCC`.

## Impact

- **rvsec (Java), `rvsec-android/rvsec-logger-logcat`**: `ErrorCollector` and its tests. This is the monitor runtime woven into every instrumented APK by both instrumenters (`rv-instrumentation-dexlib2`, `rv-instrumentation-ajc`) through `rvsec-logger-logcat.jar`. The jar is rebuilt by the reactor and copied into `rv-android/lib_tmp`, and already instrumented APKs keep the old collector until they are re-instrumented. `rvsec-core` (`ErrorSummary`, `ErrorDescription`) is read, not changed.
- **Frozen `jca` set**: the collector is shared runtime that `jca` references. Its `RVSEC` output is byte-identical; the thread-safety repair can only remove a duplicate line that a race produced. This is declared here, not enumerated site by site, because `jca` is out of use.
- **rv-android-core**: `util/logging/constants.py` (`TAG_RVSEC_OCC`), `util/android/logcat_manager.py` (`default_tags`), `constants.py` (two emulator constants), `util/android/android.py` (`start_emulator` arguments), and their tests.
- **rv-platform**: no code change. `LogcatComponent` passes `default_tags` through, as INV-PLT-21 requires. Its tests that assert the emitted command change.
- **Consumers**: `rv-coverage`'s `parse_logcat_line` dispatches on the exact tag, so an `RVSEC-OCC` line counts as `lines_other_tag`, as `ApeRvHb` lines already do; violation and coverage values are unchanged (the INV-CORE-54 argument applies unchanged). `aperv-tool`'s `read_tagged_lines(path, tag)` is tag-agnostic and can read `RVSEC-OCC` without a change.
- **Execution conditions**: E2 and E6 ran with 1536 MB and 800 MB. A campaign on the new image runs with 4096 MB and 8192 MB, which can change low-memory kills, app restarts and installation failures for large APKs. That difference has to be declared beside any comparison with those campaigns.
- **Docker**: no image is built in this change. A campaign sees the change only on an `rvandroid` image rebuilt after it, which carries the new modules, the new `rvsec-logger-logcat.jar` and, from the `docker/android` layer up, the Dockerfile without the dead variables.
- **Two AVDs named `RVSec`**: the campaign image's AVD (`/data/RVSec.avd/config.ini` in `phtcosta/rvsec_android:0.9.4`: 1536 MB, 800 MB, 4 cores) and the host's AVD (`~/.android/avd/RVSec.avd/config.ini`: 4096 MB, 8192 MB, 2 cores). The memory and partition fix matters for the first. The host smoke runs on the second, where `-memory 4096 -partition-size 8192` restate its own configuration. The fix is therefore verified by the argv tests only, and no run of this change exercises it. The smoke's conditions differ from E6's (2 cores instead of 4, 4096 MB instead of 1536 MB), so its numbers set against E6 are an approximation, and the smoke report says so.
- **Requirements**: FR11 (logcat capture and parsing), FR13 (specification violation detection), FR07 (emulator management).
