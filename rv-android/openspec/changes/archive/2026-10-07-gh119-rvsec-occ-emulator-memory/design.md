## Context

GitHub Issue: #119. Proposal: `proposal.md`. Requirements: FR11 (logcat capture and parsing), FR13 (specification violation detection), FR07 (emulator management).

The change touches three places that are already in production and have no common owner:

1. **The monitor runtime's collector**, `rvsec/rvsec-android/rvsec-logger-logcat/src/main/java/br/unb/cic/mop/eh/ErrorCollector.java` (Java, `rvsec` reactor). Today it writes one `RVSEC` line per identity per process: `if (errors.add(err)) Log.v("RVSEC", buildLine(err))` (`:51-55`). The identity is `ErrorSummary` (`rvsec/rvsec-core/.../ErrorSummary.java`), with `equals`/`hashCode` over seven fields: spec, error, class, method, location, code, event. The singleton is lazy and unsynchronised (`:32-37`), and `errors` is a `HashSet`. The module's tests (`src/test/java/br/unb/cic/mop/eh/ErrorCollectorTest.java`) never call `addError`, because `android.util.Log` in the `provided` stub jar throws `RuntimeException("Stub!")`. They test the pure line builders `buildLine` and `escape` instead.
2. **The capture allowlist**, `modules/rv-android-core/src/rv_android_core/util/android/logcat_manager.py:80-83` (`default_tags`), built from constants in `modules/rv-android-core/src/rv_android_core/util/logging/constants.py:23-33`. `LogcatComponent` (`modules/rv-platform/src/rv_platform/components/logcat.py:144`) passes the list through.
3. **The emulator launch**, `modules/rv-android-core/src/rv_android_core/util/android/android.py:120-158` (`Android.start_emulator`). It passes `-avd -port -read-only -no-cache -no-boot-anim -noaudio -no-snapshot-save -delay-adb [-no-window]` and nothing about memory or storage, so the AVD's `config.ini` governs: `hw.ramSize=1536M`, `disk.dataPartition.size=800M`, `hw.cpu.ncore=4` (read from `phtcosta/rvsec_android:0.9.4`, `/data/RVSec.avd/config.ini`).

How the collector reaches an APK matters for the rollout. Both instrumenters resolve the runtime jars with `mvn dependency:copy-dependencies` against `rv-android/pom.xml` (`rv_instrumentation_dexlib2/dexlib_instrumentation.py:92-135`). The jar therefore comes from the local Maven repository after the reactor's `install`, and inside the image from the reactor build of the `rvandroid` Dockerfile. An APK instrumented before the rebuild keeps the old collector.

Measured on the 516 `aperv` logcats of the E6 campaign: `RVSEC` ≤ 949 lines per run, `RVSEC-COV` ≤ 304 828, a peak of 6 673 captured lines in one second, and a mean `RVSEC` line of 393 bytes. How often an identity repeats is unknown, because the first-occurrence rule hides exactly that.

## Architecture

```
 instrumented APK (device)                                   host
 ─────────────────────────                                   ────
 spec handler ──addError(ErrorDescription)──► ErrorCollector
                                               │ errors.add(err)?  ──yes──► Log.v("RVSEC",     buildLine)
                                               │ occurrenceLine(err, nanoTime) != null
                                               │                    ──yes──► Log.v("RVSEC-OCC", line)
                                               ▼
                                         logd main buffer (16 MiB, INV-CORE-64)
                                               │
              adb logcat -v threadtime -s RVSEC:V RVSEC-COV:V ApeRvHb:V RVSEC-OCC:V
                                               │  (LogcatManager.default_tags, INV-CORE-37/53)
                                               ▼
                                     task.result.logcat_file
                       ┌───────────────────────┴────────────────────────┐
         rv-coverage parse_logcat_line                    aperv-tool read_tagged_lines(path, "RVSEC-OCC")
         (exact tag; RVSEC-OCC → lines_other_tag,         + place_on_timeline (ApeRvHb) — offline, by the analysis
          INV-CORE-65)

 Android.start_emulator ──► emulator ... -delay-adb -memory 4096 -partition-size 8192 [-no-window]
```

### Key Components

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| `ErrorCollector.addError(ErrorDescription)` (Java) | Decide the `RVSEC` line (first occurrence), then the `RVSEC-OCC` line (throttled) | `ErrorDescription` | 0–2 `Log.v` calls |
| `ErrorCollector.occurrenceLine(ErrorDescription, long)` (Java, package-private) | Count the occurrence, apply the 100 ms throttle, build the line | report, `System.nanoTime()` | `String` or `null` |
| `ErrorCollector.Occurrence` (Java, private static nested class) | Per-identity counter and time of the last written line | — | — |
| `TAG_RVSEC_OCC` (`util/logging/constants.py`) | The single host-side spelling of the tag | — | `"RVSEC-OCC"` |
| `LogcatManager.default_tags` | Baseline allowlist | constants | `[RVSEC, RVSEC-COV, ApeRvHb, RVSEC-OCC]` |
| `EMULATOR_MEMORY_MB`, `EMULATOR_PARTITION_SIZE_MB` (`rv_android_core/constants.py`) | Guest memory and `/data` size | — | `4096`, `8192` |
| `Android.start_emulator` | Launch argv | avd, port, window | emulator process |

## Mapping: Spec → Implementation → Test

| Requirement | Implementation | Test |
|-------------|---------------|------|
| INV-INS-170 (`RVSEC` unchanged, decided first) | `ErrorCollector.addError` order | `ErrorCollectorTest.buildLine*` (existing, unchanged); the order of the two decisions is read in `addError` at review (see Testing) |
| INV-INS-171 (counter + 100 ms throttle) | `occurrenceLine`, `Occurrence` | `occurrenceLineWritesTheFirstOccurrence`, `occurrenceLineSuppressesInsideTheWindow`, `occurrenceLineWritesAgainAfterTheWindow`, `occurrenceLineCountsSuppressedOccurrences` |
| INV-INS-172 (line shape) | `occurrenceLine` | `occurrenceLineSharesTheSixKeyFieldsWithTheRvsecLine`, `occurrenceLineCarriesTheSentinelWithoutEnvelope` |
| INV-INS-173 (thread safety) | eager `INSTANCE`, `ConcurrentHashMap` | `concurrentReportsCountEveryOccurrenceAndWriteOneFirstLine`, `resetClearsBothStates`; the eager `INSTANCE` is read at review (see Testing) |
| INV-CORE-37, INV-CORE-38 | `default_tags`, `start_capture` | `test_logcat_manager.py` command assertions (updated), `test_logcat.py::test_flag_off_emits_baseline_command` (updated) |
| INV-CORE-53 | `TAG_RVSEC_OCC`, `default_tags` | `test_logcat_manager.py::test_occurrence_tag_declared_once` (new), `test_heartbeat_tag_declared_once` (updated list) |
| INV-CORE-65 | `parse_logcat_line` exact dispatch (no change) | `rv-coverage/tests/parser/log/test_logcat_parser.py::test_occurrence_lines_change_no_parsed_value` (new) + fixture `occurrence_inert.logcat` |
| INV-CORE-66 | `Android.start_emulator` argv | `rv-android-core/tests/util/android/test_android.py::test_start_emulator` (updated), `test_start_emulator_reads_memory_and_partition_constants` (new) |
| INV-PLT-21 | `LogcatComponent` (no change) | `rv-platform/tests/components/test_logcat.py` baseline list and command (updated) |

## Goals / Non-Goals

**Goals:**
- Measure, on the host, how much the occurrence stream writes under real exploration, and whether any of it is lost.
- Remove the dead emulator configuration from `docker/android`.
- Every violation occurrence reaches the capture as a counted stream, at most one line per identity per 100 ms, joinable to its `RVSEC` line by key.
- `RVSEC` output unchanged byte for byte.
- A collector that is correct under concurrent reports.
- The guest boots with 4096 MB and an 8192 MB `/data` on every launch.

**Non-Goals:**
- No reader for `RVSEC-OCC` in any analysis module. `aperv-tool`'s `read_tagged_lines` already reads any tag, and the Study 03 analysis that consumes the stream lives outside `rv-android`.
- No change to `RVSEC-COV` (first execution per method stays; logging every method entry is not viable at its volume).
- No change to the logcat buffer size.
- No Docker image is built (no 0.9.5 build). The `docker/android` Dockerfile loses its dead variables, but nothing is rebuilt.
- No change to the AVD baked into the image. The launch flags override it.
- No campaign. The smoke measures the stream on five APKs; it does not estimate any study quantity.

## Decisions

**D1 — The occurrence line is decided after the first-occurrence `if`, on every call.** `addError` keeps `if (errors.add(err)) Log.v("RVSEC", buildLine(err))` verbatim and then calls `occurrenceLine(err, System.nanoTime())`. That call is unconditional, so its counter sees every report. On a first occurrence the `RVSEC` line is therefore written before the `RVSEC-OCC` line with `n=1`, and a reader scanning forward meets the full record first. *Alternative:* one shared map whose `putIfAbsent` decides both lines. That would merge the two identities into one structure, but it means rewriting the `RVSEC` path, which INV-INS-170 freezes, and `getErrors()` still needs the `Set<ErrorDescription>`. Rejected.

**D2 — The throttle is per identity, on `System.nanoTime()`, with the window opened at creation.** `occurrences.computeIfAbsent(summary, k -> new Occurrence(nowNanos))` creates the state with `lastLineNanos = nowNanos`. `long n = occ.count.incrementAndGet()`. The line is returned when `n == 1`, or when `nowNanos - last >= OCC_INTERVAL_NANOS` and `occ.lastLineNanos.compareAndSet(last, nowNanos)` succeeds. Otherwise `null` is returned.
- Opening the window at creation is what stops a second thread, arriving with `n == 2` in the same instant, from seeing `last == 0` and writing a second line in the first window.
- The compare-and-set makes the threads that see an expired window race for one line, and exactly one of them wins it (INV-INS-171).
- The subtraction is overflow-safe for `nanoTime`, and a monotonic clock cannot be moved by a wall-clock change on the device.
- *Alternative:* a global rate limit across identities. Rejected: one hot identity would starve the rest, and the analysis needs each identity on its step.
- *Alternative:* synchronising on the `Occurrence`. Rejected: it is correct, but it holds a monitor lock on the monitored thread for every occurrence, where the atomics do not.

**D3 — Positional line, nine fields.** The line is `summary.toString() + "," + summary.getCode() + "," + summary.getEvent() + "," + n`. `ErrorSummary.toString()` writes `spec,classQualifiedName,className,methodName,location,error`, the head of the `RVSEC` line, so the first six fields match by construction and a reader splits both lines the same way. `code` and `event` are read from the summary, not re-parsed from the envelope; they are `UNSPECIFIED` for a report without an envelope. The envelope is left out, because the occurrence line answers *when* and the `RVSEC` line already holds *what*.
- *Alternative:* `key=value` pairs (`code=… ev=… n=…`). Self-describing, but it would be a second grammar next to the positional one every consumer of `RVSEC` already reads. Rejected.
- *Alternative:* a short numeric id per identity in place of the six fields. The line would shrink to about 30 bytes, but it needs the id on the `RVSEC` line too, which INV-INS-170 forbids. Rejected.

**D4 — The `Occurrence` map is keyed by `ErrorSummary`.** `ErrorDescription.equals`/`hashCode` delegate to the summary, so the two structures share one identity. Keying the counters by the summary keeps no reference to the report's `expecting` text. Memory grows with distinct identities only; E6 had at most 949 in a run.

**D5 — Eager singleton, concurrent structures, `reset()` clears in place.** `private static final ErrorCollector INSTANCE = new ErrorCollector();` and `instance()` returns it. `errors = ConcurrentHashMap.newKeySet()` and `occurrences = new ConcurrentHashMap<>()`; both are `final`, and `reset()` clears both. Today `reset()` swaps in a new `HashSet`, which with concurrent readers is a publication race. `getErrors()` keeps returning an unmodifiable view.

**D6 — Level and tag spelling.** `RVSEC-OCC` is written with `Log.v`, as `RVSEC` is; the capture admits it at `:V`. The Java side names both tags as constants in `ErrorCollector` (`RVSEC_TAG`, `OCC_TAG`). The host side names `RVSEC-OCC` once, as `TAG_RVSEC_OCC` (INV-CORE-53). The string is 9 characters, inside the device's 23-character tag bound.

**D7 — The emulator values are constants, appended after `-delay-adb`.** `EMULATOR_MEMORY_MB = 4096` and `EMULATOR_PARTITION_SIZE_MB = 8192` go in `rv_android_core/constants.py`, next to the timeout constants. The argv gains `"-memory", str(EMULATOR_MEMORY_MB), "-partition-size", str(EMULATOR_PARTITION_SIZE_MB)` before the optional `-no-window`. `-cores` is not passed, so `hw.cpu.ncore=4` from the AVD stays in force.
- *Alternative:* `RV_EMULATOR_MEMORY` / `RV_EMULATOR_PARTITION` environment variables. Rejected by the researcher: the values are an execution condition of a campaign, and an environment override would let the containers of one campaign differ. It would also need the §14 registry process.
- *Alternative:* editing `config.ini` in `docker/android/Dockerfile`. Rejected: it means rebuilding the whole image chain, and it moves the condition out of the module that launches the emulator.

**D8 — No other consumer changes.** `rv-coverage`'s `parse_logcat_line` dispatches on `tag == TAG_RVSEC` and `tag == TAG_RVSEC_COV`, and anything else is counted in `lines_other_tag`, as `ApeRvHb` already is. `aperv-tool` reads tags by exact match (`read_tagged_lines`). The experiment scripts match `\bRVSEC\s*:`, which `RVSEC-OCC   :` does not satisfy. Nothing that counts violations today sees the new lines.

**D9 — The dead emulator configuration is deleted, not rewired.** `docker/android/Dockerfile` keeps the AVD creation (`avdmanager create avd`) and drops:
- `ENV EMU_PARTITION`, `EMU_MEMORY`, `EMU_CORES` and `EMU_GPU_MODE` (`:26-29`);
- `ARG GPU_ACCELERATED` (`:18`) and the `GPU_ACCELERATED=$GPU_ACCELERATED` entry of the `ENV` block (`:42`);
- the commented `#COPY scripts/start-emulator.sh` and `#COPY scripts/emulator-monitoring.sh` (`:92-93`).

`docker/android/scripts/start-emulator.sh` and `emulator-monitoring.sh` move to `backup/gh119/docker-android-scripts/` and are deleted from `docker/android/scripts/`. `install-sdk.sh` is just as unshipped — its `COPY` and `RUN` are commented at `:88-89` — but it is outside the researcher's decision, so it and those two lines stay.

The only readers of those names are the two scripts, and the image does not ship them. The GPU path goes with them on its own grounds as well: the emulator never uses the GPU, because in the campaigns the host GPU serves vLLM (researcher, 2026-10-07; ADR 0006 D5). The emulator is launched by `Android.start_emulator`, and with D7 that is the one place memory and storage are set. ADR 0006 named `EMU_GPU_MODE` and the `GPU_ACCELERATED` branch as deletion candidates and left the deletion to a later change; its *Consequences* gain one line stating that gh119 removed them, so the ADR does not point at files that are gone.
- *Alternative:* wire `EMU_MEMORY` and `EMU_PARTITION` into `start_emulator` through the environment. Rejected by the researcher in D7: the values are constants.

**D10 — The smoke runs on the host through `rv-experiment`, never on a hand-started emulator.**
- **Arm**: `aperv:mop_off_llm_off` needs no SGLang, but it does need each APK's static-analysis artefact. The arm carries `mop_data: "static_analysis"` by design (INV-APV-29, `aperv-tool` `tool.py:423-435`): the MOP-off control keeps the MOP document and zeroes the MOP weights, so the WTG and frontier navigation stay alive. A MOP arm without `<results_dir>/<apk>.apk.json` fails the task at arming (`tool.py:1205-1215`). The volume of the occurrence stream depends on what the exploration executes, not on MOP guidance.
- **Procedure**, from `rv-android/`, in two steps; `rv-platform` boots and tears down the host AVD `RVSec` itself, and nobody touches the emulator:
  1. *Instrument from the originals.* `experimento-smk119/apks/` holds symlinks to the five originals in `rvsec-dataset/jca_android/apks/`, never copies. Monitor generation and `dexlib2` instrumentation into `experimento-smk119/results/instrumented_apks/` use the collector built by group 1.
  2. *Run with the E6 static-analysis artefacts.* The researcher decided (2026-10-07) to reuse the E6 artefacts instead of running GATOR: the five `<apk>.apk.json` from `/home/pedro/desenvolvimento/RV_ANDROID_DATASET_FINAL/APKS_INSTRUMENTED_jca_android_dexlib2/` (dated 2026-09-02) are copied beside the instrumented APKs, with their sha256 in `instrumented_apks/e6_apk_json.sha256`. `StaticAnalysisComponent` copies each one into the task's results directory, where the arm finds it. Command: `uv run rv-experiment run --tools aperv:mop_off_llm_off --apks-dir experimento-smk119/results/instrumented_apks --specification-set jca_android --instrumentation-variant dexlib2 --skip-monitors --skip-instrument --skip-static --timeouts 600 --repetitions 1 --logcat-diagnostics --no-window --name smk119 --output-dir experimento-smk119/results`.
- **Caveat**: the artefacts come from the E6 analysis, not from an analysis of these re-instrumented APKs. The application code is the same; the report states the provenance.
- **Preconditions**:
  - The reactor `install` of group 1 has put the new `rvsec-logger-logcat` jar in the local Maven repository that `mvn dependency:copy-dependencies` reads.
  - Group 2 has admitted `RVSEC-OCC` to the capture.
  - `RVSEC_HOME` points at the reactor.
- **Measurement**: `experimento-smk119/scripts/measure_occ.py` reads each run's `.logcat` and `.trace`, offline and read-only. It uses `aperv-tool`'s `read_tagged_lines(path, "RVSEC")`, `read_tagged_lines(path, "RVSEC-OCC")` and `place_on_timeline` with the heartbeat reader `clock_logcat_join` already uses. Per run it reports:
  1. `RVSEC-OCC` lines per second: mean, and peak over 1 s bins;
  2. the maximum `n` per identity, and the identities with the largest `n`;
  3. the pairing: every `RVSEC` line must have an `RVSEC-OCC` line with the same nine-field key prefix and `n=1`, and every `n=1` line must have its `RVSEC` line. An unpaired line on either side is a measured loss;
  4. the peak of all captured lines per second, against E6's 6 673;
  5. the placement of the `RVSEC-OCC` lines: before the first step, on a step, after the last step, or unaligned.

  The script parses the nine-field line itself and counts every `RVSEC-OCC` or `RVSEC` line that is malformed or unreadable. It writes the report either way and exits with status 1 when any such line exists, so a format drift fails the run.
- **Report**: `experimento-smk119/RELATORIO.md`, in Portuguese. It holds the five runs' numbers, the conditions (host AVD at 4096 MB / 8192 MB / 2 cores, against E6's container AVD at 1536 MB / 800 MB / 4 cores), the statement that no comparison with E6 is exact, and the provenance of the static-analysis artefacts. The raw results stay out of git; only the report and the script are committed.
- *Alternative:* a container of the campaign image. Rejected: the image would need rebuilding to carry the new collector, and no 0.9.5 image is built (researcher's decision of 2026-10-07).

## API Design

### `void ErrorCollector.addError(ErrorDescription err)` (Java)

- **Pre:** `err` non-null with a non-null summary (as today).
- **Post:**
  - The identity's count is one higher.
  - At most one `RVSEC` line is written: exactly one if this was the identity's first report since the last `reset()`.
  - At most one `RVSEC-OCC` line is written, under INV-INS-171.
- **Errors:** none thrown. `android.util.Log` drops what the logger cannot accept.

### `String ErrorCollector.occurrenceLine(ErrorDescription err, long nowNanos)` (Java, package-private)

- **Pre:** `nowNanos` comes from `System.nanoTime()`; in tests, any monotonic sequence.
- **Post:**
  - Increments the identity's count to `n`.
  - Returns `summary.toString() + "," + code + "," + event + "," + n` when `n == 1`, or when the window has expired and this call won the compare-and-set.
  - Otherwise returns `null`.
- It is free of `android.util.Log`, which is what makes it testable against the stub jar.

### `static final long ErrorCollector.OCC_INTERVAL_NANOS = 100_000_000L`

### `TAG_RVSEC_OCC = "RVSEC-OCC"` (`rv_android_core/util/logging/constants.py`)

### `EMULATOR_MEMORY_MB = 4096`, `EMULATOR_PARTITION_SIZE_MB = 8192` (`rv_android_core/constants.py`)

### `Android.start_emulator(avd_name, no_window, device_port=5554)` — argv only changes (INV-CORE-66).

## Data Flow

1. A specification handler builds an `ErrorDescription` and calls `addError`. As today, the constructor has already parsed the frame and the envelope into the `ErrorSummary`.
2. `errors.add(err)`: if this is the identity's first report, the collector writes `RVSEC` with the full envelope.
3. `occurrenceLine(err, nanoTime)` counts the report and, if the window allows, the collector writes `RVSEC-OCC` with the key and `n`.
4. `logd` stores both lines in the `main` buffer. `adb logcat -s … RVSEC-OCC:V` streams them to `task.result.logcat_file`.
5. Offline, an analysis reads `RVSEC-OCC` by tag, places each line on the step of the last `ApeRvHb` before it, and joins it to its `RVSEC` line on the first six fields plus `code` and `event`.

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| `logd` socket full | `Log.v` under a burst | The line is dropped by `android.util.Log`; nothing is thrown | The next line's `n` shows the gap; the throttle bounds bursts per identity |
| Ring buffer pruned before the reader | `logd` under reader lag | No marker in the file (known since gh114) | 16 MiB holds seconds of lag at the measured peak; the gap in `n` makes the loss visible for `RVSEC-OCC` |
| Emulator rejects `-memory` / `-partition-size` | emulator binary | Boot wait times out | `TimeoutError` → `EmulatorError`, as for any failed launch |
| Host short of memory for 4 GB guests | Docker host | — | E6 containers have a 10 GB limit and the host 123 GB; 8 × 4 GB fits |

## Risks / Trade-offs

- [A violation in a tight loop on the UI thread now also costs a counter update and, every 100 ms, a log write.] → The `ErrorDescription` and its regex parsing are already paid per report, before the first-occurrence check. The added cost is two atomic operations per report and at most ten writes per second per identity.
- [Occurrences after an identity's last written line are never written.] → Declared in the requirement: the last `n` is a lower bound. A flush at process exit is not attempted, because Android gives no reliable exit hook for an app the tool kills.
- [Identical consecutive lines could be collapsed by `logd` ("chatty").] → Every `RVSEC-OCC` line of an identity carries a different `n`, so no two consecutive lines of one identity are identical.
- [4096 MB and 8192 MB change execution conditions against E2/E6.] → Declared in the proposal and in the core requirement; a comparison states it.
- [The read-only AVD writes an 8192 MB data image per emulator.] → The image is a temporary file of the emulator process; only the space the guest actually writes is used on the host's disk. The first smoke run checks the container's disk use.
- [The memory/partition fix is not exercised by any run of this change: the host AVD already has 4096 MB and 8192 MB, and no image is rebuilt.] → The argv tests pin the flags. The first campaign on a rebuilt image is the first run that exercises them.
- [The smoke's conditions differ from E6's: host AVD with 2 cores and 4096 MB against the container AVD with 4 cores and 1536 MB.] → Stated in `RELATORIO.md`; the smoke measures the stream, not the study.
- [Already instrumented APKs keep the old collector.] → Re-instrument for any campaign that needs `RVSEC-OCC`; the absence of the tag in a capture identifies such an APK.

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Unit (Java, JUnit 4) | `occurrenceLine`: first line, suppression, window expiry, counting, line shape, sentinel | Synthetic `ErrorDescription` and explicit `nowNanos` values; no `Log` | ~7 |
| Unit (Java) | Thread safety: 8 threads × 10 000 calls to `occurrenceLine` with one identity and one fixed `nowNanos` → final count 80 000 and exactly one non-null line; `reset()` clears both structures | `CyclicBarrier` + threads | ~2 |
| Unit (Python) | Capture command and `default_tags` | Update `rv-android-core/tests/util/android/test_logcat_manager.py` and `rv-platform/tests/components/test_logcat.py`; new declared-once test | ~5 |
| Unit (Python) | Emulator argv | Update `rv-android-core/tests/util/android/test_android.py::test_start_emulator`; new constants test | ~2 |
| Integration (Python) | `RVSEC-OCC` inert to the parser | New fixture `occurrence_inert.logcat` in `rv-coverage/tests/parser/log/fixtures/`, compared with the same file without the lines | ~1 |
| Smoke (host) | Volume, loss and placement of `RVSEC-OCC` under real exploration | `rv-experiment run` on 5 APKs × `aperv:mop_off_llm_off` × 600 s; `measure_occ.py`; its parser unit-tested on a synthetic logcat first | 5 runs |
| Build | Reactor build with the logger module's tests running | `mvn clean install -DskipMopAgent -pl rvsec/rvsec-android/rvsec-logger-logcat -am` under JDK 21 | 1 |

`addError` itself is not called by any test. Its body is the unchanged first-occurrence `if` followed by the occurrence call, and both decisions are tested through their `Log`-free helpers (`buildLine`, `occurrenceLine`). Calling it off the device would need either a Robolectric dependency, which the module has never had, or a test-only seam around `android.util.Log`, which this change does not add. The order of the two calls (INV-INS-170) and the eager `INSTANCE` (INV-INS-173) are checked by reading the code at review. A test of `instance()` across threads cannot fail inside this test class, which has already initialised `ErrorCollector` before it runs, so a lazy singleton would pass it too.

## Open Questions

None open. Resolved on 2026-10-07:
- Dead `EMU_*` and GPU configuration in `docker/android`: deleted (D9), with no image rebuild.
- Smoke: on the host through `rv-experiment` (D10). Five APKs, `aperv:mop_off_llm_off`, 600 s, 1 repetition, diagnostics on. Measures: lines per second, maximum `n`, `RVSEC` × `n=1` pairing, total peak, and placement per step.
