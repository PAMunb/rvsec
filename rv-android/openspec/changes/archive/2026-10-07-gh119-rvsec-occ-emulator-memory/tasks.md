<!-- Execution plan and subagent dispatch (docs/WORKFLOW.md §5):

     WAVE 1 — six subagents in parallel (no two groups share a file):
       A = group 1 (Java collector, rvsec-logger-logcat: ErrorCollector.java + its test; owns the only Maven build, 1.6)
       B = group 2 (capture allowlist: rv-android-core util/logging/constants.py + util/android/logcat_manager.py,
                    rv-platform tests, rv-coverage tests + fixture)
       C = group 3 (emulator launch: rv-android-core constants.py + util/android/android.py + test_android.py)
       D = group 4 (docker/android cleanup: Dockerfile, scripts -> backup/gh119/, ADR 0006 one line)
       E = group 5 (documentation: logger README/CLAUDE.md, rv-android-core CLAUDE.md, rv-experiment-compare SKILL.md)
       F = group 6 (smoke preparation: experimento-smk119/ — apks symlinks, measure_occ.py + its test, README)
       B and C touch different files of rv-android-core (util/logging/constants.py vs rv_android_core/constants.py).
       A and E touch different files of rvsec-logger-logcat (.java vs .md).
       Only A runs Maven, once, from the reactor root, with JDK 21 in the prefix:
         export JAVA_HOME=$HOME/.sdkman/candidates/java/21.0.12-tem; export PATH=$JAVA_HOME/bin:$PATH

     WAVE 2 — main window, after wave 1: group 7 (lint, tests, code review). It runs before the smoke, because
       lint-fix and review fixes edit sources that the smoke's editable install would load mid-run.

     WAVE 3 — main window, after wave 2: group 8 (smoke run). One command, serial on the host's single emulator
       (~70 min: 5 × (600 s + instrumentation + boot)). Run in background; no emulator command by hand —
       rv-platform manages the emulator (CLAUDE.md).

     WAVE 4 — main window: group 9 (measurement, report, docs sync).

     Critical path: A(1.6) -> 7 -> 8 -> 9. About 25 files. -->

## 1. Collector: occurrence stream and thread safety (Java, `rvsec-logger-logcat`) — wave 1, subagent A

- [x] 1.1 In `rvsec/rvsec-android/rvsec-logger-logcat/src/main/java/br/unb/cic/mop/eh/ErrorCollector.java`, replace the lazy singleton with `private static final ErrorCollector INSTANCE = new ErrorCollector();` returned by `instance()`. Make `errors` a `final` `ConcurrentHashMap.newKeySet()`, and make `reset()` clear it in place. Keep `getErrors()` returning an unmodifiable view (INV-INS-173, design D5).
- [x] 1.2 Add the occurrence state (design D2, D4, D6):
  - a private static nested class `Occurrence`, holding `AtomicLong count` and an `AtomicLong lastLineNanos` initialised at construction;
  - `final ConcurrentHashMap<ErrorSummary, Occurrence> occurrences`, which `reset()` also clears;
  - `static final long OCC_INTERVAL_NANOS = 100_000_000L`;
  - the tag constants `RVSEC_TAG = "RVSEC"` and `OCC_TAG = "RVSEC-OCC"`.
- [x] 1.3 Add the package-private `String occurrenceLine(ErrorDescription err, long nowNanos)` (INV-INS-171, INV-INS-172):
  - `computeIfAbsent(summary, k -> new Occurrence(nowNanos))`, then `n = count.incrementAndGet()`;
  - return `summary.toString() + "," + summary.getCode() + "," + summary.getEvent() + "," + n` when `n == 1`, or when `nowNanos - last >= OCC_INTERVAL_NANOS` and `compareAndSet(last, nowNanos)` succeeds;
  - otherwise return `null`.
- [x] 1.4 In `addError(ErrorDescription)`, keep `if (errors.add(err)) Log.v(RVSEC_TAG, buildLine(err));` unchanged. Follow it with `String occ = occurrenceLine(err, System.nanoTime()); if (occ != null) Log.v(OCC_TAG, occ);` (INV-INS-170, design D1). The class Javadoc and the comments are in current-state terms (P4): what each stream carries, why the throttle exists, and that the last `n` is a lower bound.
- [x] 1.5 Add to `src/test/java/br/unb/cic/mop/eh/ErrorCollectorTest.java` (JUnit 4, no `Log`):
  - the first occurrence returns the line ending `,1`;
  - reports at `+10/+20/+90 ms` return `null`, and a report at `+120 ms` returns the line ending `,5`;
  - the six head fields equal the head of `buildLine` for the same report;
  - a three-argument report yields `UNSPECIFIED,UNSPECIFIED`;
  - 8 threads × 10 000 calls at one `nowNanos` give count 80 000 and exactly one non-null line;
  - `reset()` restarts `n` at 1.

  The existing `buildLine`/`escape` tests stay unchanged, because they pin INV-INS-170. The eager singleton is checked at review, because a cross-thread `instance()` test in this class cannot fail.
- [x] 1.6 From the reactor root, run `mvn clean install -DskipMopAgent -pl rvsec/rvsec-android/rvsec-logger-logcat -am -o`, with no `-DskipTests`. Then confirm:
  - `ErrorCollectorTest` ran and passed in the surefire report;
  - the installed `rvsec-logger-logcat-0.9.5-SNAPSHOT.jar` under `/home/pedro/desenvolvimento/repository` contains `RVSEC-OCC` (`javap -c -p` on `ErrorCollector.class`).

## 2. Capture allowlist admits `RVSEC-OCC` (rv-android-core, rv-platform, rv-coverage) — wave 1, subagent B

- [x] 2.1 Add `TAG_RVSEC_OCC = "RVSEC-OCC"` to `modules/rv-android-core/src/rv_android_core/util/logging/constants.py`, after `TAG_APERV_HEARTBEAT`. The comment says the value is a cross-repository contract with `ErrorCollector.OCC_TAG` in `rvsec-logger-logcat`, and that `-s` discards an unadmitted tag at the device (INV-CORE-53).
- [x] 2.2 In `modules/rv-android-core/src/rv_android_core/util/android/logcat_manager.py`, import the constant and set `default_tags` to `[TAG_RVSEC, TAG_RVSEC_COV, TAG_APERV_HEARTBEAT, TAG_RVSEC_OCC]`. Update the comments that describe the baseline (INV-CORE-37).
- [x] 2.3 Update `modules/rv-android-core/tests/util/android/test_logcat_manager.py`:
  - every expected baseline command and filter gains `RVSEC-OCC:V` after `ApeRvHb:V`;
  - `test_heartbeat_tag_declared_once` expects the four-tag `default_tags`;
  - add `test_occurrence_tag_declared_once`, which finds the literal `"RVSEC-OCC"` exactly once in the `rv-android-core` source tree, as the value of `TAG_RVSEC_OCC`.
- [x] 2.4 Update `modules/rv-platform/tests/components/test_logcat.py`: the baseline list `["RVSEC", "RVSEC-COV", "ApeRvHb", "RVSEC-OCC"]`, the flag-off command, and the flag-on filter prefix (INV-PLT-21, INV-CORE-38).
- [x] 2.5 Add the fixture `modules/rv-coverage/tests/parser/log/fixtures/occurrence_inert.logcat`: threadtime lines mixing `RVSEC`, `RVSEC-COV`, `ApeRvHb` and `RVSEC-OCC`, with one `RVSEC-OCC` line between two lines of a crash block. Add `test_occurrence_lines_change_no_parsed_value` to `test_logcat_parser.py`, mirroring `test_heartbeat_lines_change_no_parsed_value`. With and without the `RVSEC-OCC` lines, the metrics, errors, coverage and diagnostic events must be equal, and `lines_other_tag` must differ by the number of `RVSEC-OCC` lines (INV-CORE-65).
- [x] 2.6 Run `uv run pytest modules/rv-android-core/tests modules/rv-platform/tests modules/rv-coverage/tests --import-mode=importlib -o "addopts="`.

## 3. Emulator memory and data partition (rv-android-core) — wave 1, subagent C

- [x] 3.1 Add `EMULATOR_MEMORY_MB = 4096` and `EMULATOR_PARTITION_SIZE_MB = 8192` to `modules/rv-android-core/src/rv_android_core/constants.py`, near the emulator timeout constants. The comment states three things (INV-CORE-66):
  - the image AVD's `pixel` defaults are 1536 MB and 800 MB;
  - the values are an execution condition of a campaign, hence constants and not environment variables;
  - `hw.cpu.ncore` is left to the AVD.
- [x] 3.2 In `modules/rv-android-core/src/rv_android_core/util/android/android.py`, `Android.start_emulator`:
  - append `"-memory", str(EMULATOR_MEMORY_MB), "-partition-size", str(EMULATOR_PARTITION_SIZE_MB)` after `"-delay-adb"` and before the optional `"-no-window"`, each with a short inline comment like its neighbours;
  - do not add `-cores`;
  - read the constants through the module (`constants.EMULATOR_MEMORY_MB`) so a test can monkeypatch them.
- [x] 3.3 Update `modules/rv-android-core/tests/util/android/test_android.py::test_start_emulator` to the new argv. Add `test_start_emulator_reads_memory_and_partition_constants`: with `EMULATOR_MEMORY_MB` monkeypatched to `2048`, the argv carries `-memory 2048` and no `-cores`.
- [x] 3.4 Run `uv run pytest modules/rv-android-core/tests/util/android --import-mode=importlib -o "addopts="` and `uv run python scripts/check_env_vars_drift.py`. The drift check must report 0 violations, since no environment variable is added.

## 4. Dead emulator configuration in `docker/android` — wave 1, subagent D

- [x] 4.1 Copy `docker/android/scripts/start-emulator.sh` and `docker/android/scripts/emulator-monitoring.sh` to `backup/gh119/docker-android-scripts/`, then delete them from `docker/android/scripts/` (P3, design D9).
- [x] 4.2 In `docker/android/Dockerfile`, delete (design D9):
  - `ENV EMU_PARTITION`, `EMU_MEMORY`, `EMU_CORES`, `EMU_GPU_MODE` (`:26-29`);
  - `ARG GPU_ACCELERATED` (`:18`) and the `GPU_ACCELERATED=$GPU_ACCELERATED` entry of the `ENV` block (`:42`);
  - the commented `#COPY scripts/start-emulator.sh` and `#COPY scripts/emulator-monitoring.sh` (`:92-93`).

  Leave `install-sdk.sh` and its commented `COPY`/`RUN` (`:88-89`) untouched. Leave the AVD creation untouched. No image is built.
- [x] 4.3 In `docs/adr/0006-emulator-execution-profile-cold-boot-no-gpu.md`, add one line under *Consequences*: gh119 removed `EMU_GPU_MODE`, the `GPU_ACCELERATED` argument and the unshipped `start-emulator.sh`. The ADR's file references then point at something that exists, or say that it was removed.
- [x] 4.4 `git grep -n -E "EMU_(MEMORY|PARTITION|CORES|GPU_MODE)|GPU_ACCELERATED|start-emulator\.sh|emulator-monitoring\.sh"` outside `backup/`, `openspec/changes/archive/` and dated `docs/2026*` must return only the ADR 0006 lines.

## 5. Documentation — wave 1, subagent E

- [x] 5.1 `rvsec/rvsec-android/rvsec-logger-logcat/README.md` and `CLAUDE.md`: describe both streams as they are after this change.
  - `RVSEC` is the first occurrence, with the envelope.
  - `RVSEC-OCC` is every occurrence, throttled to 100 ms per identity, in the form `spec,classQualifiedName,className,methodName,location,errorType,code,event,n`. After an identity's last line, `n` is a lower bound.
  - The singleton is thread-safe.

  Remove the statements that are no longer true: `escapeSpecialCharacters` unused, and the `["RVSEC","RVSEC-COV"]` default tag set.
- [x] 5.2 `.claude/skills/rv-experiment-compare/SKILL.md` (lines ~206 and ~214): the default capture is `RVSEC:V RVSEC-COV:V ApeRvHb:V RVSEC-OCC:V`.
- [x] 5.3 `modules/rv-android-core/CLAUDE.md`: mention the four-tag baseline and the emulator memory and partition constants where the module documents `logcat_manager` and `android.py`.

## 6. Smoke preparation (`experimento-smk119/`) — wave 1, subagent F

- [x] 6.1 Create `experimento-smk119/apks/` with symlinks (never copies) to the five originals in `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec-dataset/jca_android/apks/`: `com.tananaev.passportreader_22.apk`, `app.michaelwuensch.bitbanana_79.apk`, `com.afkanerd.deku_83.apk`, `org.openhab.habdroid_589.apk`, `app.maskan.chat_90.apk`. Check that each link resolves.
- [x] 6.2 Write `experimento-smk119/scripts/measure_occ.py`. It is offline and read-only, and takes the results directory as an argument. For each `.logcat` it reports the five measures of design D10:
  - `RVSEC-OCC` lines per second, mean and peak over 1 s bins;
  - the maximum `n` per identity, with the top identities;
  - the `RVSEC` × `RVSEC-OCC n=1` pairing, both directions, on the nine-field key prefix;
  - the peak of all captured lines per second;
  - the placement on the timeline (`aperv-tool` `read_tagged_lines`, `place_on_timeline` and the heartbeat reader `clock_logcat_join` uses).

  It writes `experimento-smk119/results/measure_occ.json` and prints a table. Malformed or unreadable `RVSEC-OCC`/`RVSEC` lines are counted; the report is written either way, and the script exits with status 1 when any exist.
- [x] 6.3 Write `experimento-smk119/tests/test_measure_occ.py` on a synthetic logcat. It must cover: one `RVSEC` with its `n=1`; an `n=1` without its `RVSEC` (counted as loss); a `RVSEC-OCC` line before the first heartbeat; and a nine-field violation (rejected). Run it with `--import-mode=importlib -o "addopts="`.
- [x] 6.4 Write `experimento-smk119/README.md` in Portuguese. It covers the purpose, the exact command of design D10, the preconditions (groups 1 and 2 done, `RVSEC_HOME` set), the expected duration (~70 min) and how to run `measure_occ.py`. Results stay out of git.

## 7. Lint, tests and review — wave 2, main window, after wave 1

- [x] 7.1 Run `/rv-qa-lint-fix rv-android-core`
- [x] 7.2 Run `/rv-verify rv-android-core`
- [x] 7.3 Run `/rv-verify rv-platform`
- [x] 7.4 Run `/rv-verify rv-coverage`
- [x] 7.5 Invoke `/rv-code-reviewer` via the Skill tool on the Python changes, `ErrorCollector.java`, the Dockerfile and `measure_occ.py`. Confirm that the `RVSEC` path of `addError` is unchanged and that the occurrence call follows it unconditionally. Apply the accepted findings before the smoke.
- [x] 7.6 `git grep -n "ApeRvHb:V"` over `modules/`, `openspec/specs/` and living docs: no baseline command without `RVSEC-OCC:V` remains outside archived changes, dated docs and experiment folders.

## 8. Smoke run (host, `rv-experiment`) — wave 3, main window, after group 7

- [x] 8.1 Preconditions:
  - 1.6 is done (the jar with `RVSEC-OCC` is in the local repository);
  - 2.6 is green;
  - `echo $RVSEC_HOME` names the reactor;
  - no other experiment is using the host emulator.
- [x] 8.2 From `rv-android/`, in background, the two steps of design D10. No emulator or `adb emu` command is issued by hand.
  - Generate the monitors and instrument the five originals of `experimento-smk119/apks/` with `dexlib2` into `experimento-smk119/results/instrumented_apks/`.
  - Copy the five E6 `<apk>.apk.json` beside them, recording their sha256 in `e6_apk_json.sha256`, then run `uv run rv-experiment run --tools aperv:mop_off_llm_off --apks-dir experimento-smk119/results/instrumented_apks --specification-set jca_android --instrumentation-variant dexlib2 --skip-monitors --skip-instrument --skip-static --timeouts 600 --repetitions 1 --logcat-diagnostics --no-window --name smk119 --output-dir experimento-smk119/results`.
- [x] 8.3 After it ends, confirm that 5 tasks completed and that every `.logcat` contains `RVSEC-OCC` lines. A file without any means the APK carries the old collector, or the capture did not admit the tag; stop and diagnose before measuring.

## 9. Measurement, report and docs sync — wave 4, main window

- [x] 9.1 Run `uv run python experimento-smk119/scripts/measure_occ.py experimento-smk119/results`.
- [x] 9.2 Write `experimento-smk119/RELATORIO.md` in Portuguese:
  - the five runs' numbers, for each of the five measures;
  - any unpaired line, which is a measured loss;
  - the conditions: host AVD at 4096 MB / 8192 MB / 2 cores against the E6 container AVD at 1536 MB / 800 MB / 4 cores, with the statement that the numbers set against E6 are an approximation;
  - the statement that the memory/partition fix was not exercised by this run;
  - the provenance of the static-analysis artefacts: the E6 `.apk.json`, not an analysis of the re-instrumented APKs.
- [x] 9.3 Run `/rv-docs-sync rv-android-core`
