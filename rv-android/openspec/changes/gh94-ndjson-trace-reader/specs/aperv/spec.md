# aperv Delta Specification — Native NDJSON Trace Reader, gzip at Collection, Frozen-Corpus Carve-Out

## Purpose

`aperv-tool` has two paths that touch the `.trace`, and stage 4 of the APE-RV re-architecture changes what that file contains for both of them. On the **collection** path the tool captures the jar's stdout into `task.result.trace_file`; from stage 4 onward that stream is NDJSON — one `StepRecord` per exploration step — rather than the `[APE-STEP]` / `[APE-OUTCOME]` / `[APE-LLM-TEL]` `key=value` line family. On the **analysis** path the module hosts two offline readers of that file: `coverage_dump.py`, which reads only the `[APE-RV] UICOV` / `UICOV-ACT` dump and is unaffected, and `clock_logcat_join.py`, which reads `[APE-STEP]` and therefore stops working the moment a stage-4 jar is deployed.

This delta adds the native reader those consumers need, adds the one collection-path step stage 4 asks for, and migrates the join. **There is no format conversion anywhere in it.** The `.trace` is the NDJSON and is never rewritten: reconstructing the `key=value` family over the primary artifact would invert which file is authoritative — the file everyone opens would become a derived reconstruction while the real records hid in a sidecar — and would re-impose the unescaped format whose line-breaking defect the jar's new serializer exists to eliminate. Analysis reads the records natively instead.

The migration of `clock_logcat_join.py` is a net deletion rather than a port. Most of that module's complexity today reconstructs the device's UTC offset, because the trace stamps `System.currentTimeMillis()` while logcat stamps local wall time with no year and no zone: three year candidates, rounding to the nearest quarter hour, an anchor choice, and a residual kept as evidence that the anchoring assumption held. Stage 4's write-only logcat heartbeat puts step and violation in the same file, on the same clock, in the same rendering, so the reconstruction has nothing left to reconstruct and is deleted with the regex it fed.

That deletion carries a precondition which is load-bearing, not procedural. rv-platform captures logcat as a live stream under a strict tag allowlist, so the heartbeat only reaches the joined file once its tag is in that allowlist — the `core` and `platform` deltas of this same change. Until a captured run demonstrably contains heartbeat lines, the reconstruction stays. Deleting a working fallback in favour of a mechanism never observed end to end would reproduce, on the analysis path, exactly the silent-inertness failure that stage 4 exists to remove elsewhere.

Finally, the delta records a carve-out in normative form so that a later cleanup sweep does not misread it. The archived legacy corpus — the traces behind the 2026-07-24 calibration report and the decisive run — will never be regenerated, and the scripts that read it keep their legacy parsers. They are not compatibility shims for new data; they are the readers of a dataset that is finished. P3 governs superseded *implementation*, not analysis code over frozen data.

## Data Contracts

### Input

- `trace_path: Path` — the run's `.trace`, an NDJSON stream produced by a stage-4 jar (source: `task.result.trace_file`)
- `RUN_START` record — carries `run_id` and the epoch base `t0` (source: the jar's run-spec capability)
- `ACT` / `STATE` dictionary records — `{"type":"ACT","id":N,"name":...,"mop":0|1}` and `{"type":"STATE","id":N,"key":...,"act":<actId>}`, each defined on a line earlier than any record referencing it
- `StepRecord` lines — envelope `s`/`t`/`act`/`st` plus optional `dec`, `llm[]`, `out` sections, with defaults omitted
- `logcat_path: Path` — the run's `.logcat` sibling, carrying `RVSEC` violation lines and, from stage 4, the per-step heartbeat lines (source: `task.result.logcat_file`)

### Output

- one typed step row per `StepRecord`, with dictionary references resolved to strings, omitted defaults materialized, and the record's `dec`, `llm[]` and `out` sections attached (destination: `clock_logcat_join.py` and any future offline analysis)
- reader diagnostics: counts of malformed records skipped, and whether `RUN_START` was present (destination: the caller, for reporting)
- `<trace>.ndjson.gz` — the compressed copy written at collection (destination: storage at rest)
- `RunJoin` / `JoinReport` rows as today, minus `alignment_residual_ms`

### Side-Effects

- **[Filesystem, collection path]**: one gzip file written next to `task.result.trace_file` after the run completes. No other file is created, and no existing file is modified.
- **[Filesystem, analysis path]**: none. The reader and the join are read-only.

### Error

- `FileNotFoundError` — the trace path does not exist (reader; the CLI surfaces it as a usage error with exit status 2, as today)
- gzip failure — caught, logged at WARNING, never raised; the uncompressed trace stays in place

## Invariants

- **INV-APV-48**: `trace_ndjson.py` SHALL be read-only and analysis-time only. It SHALL NOT write to the trace, SHALL NOT emit legacy `[APE-*]` lines, SHALL NOT be imported or invoked from `execute_tool_specific_logic()` or any other collection-path code, and SHALL NOT require a device, an emulator or `adb`.

- **INV-APV-49**: Default materialization SHALL be total for the fields whose absence means a default, and SHALL NOT be applied to the fields whose absence is itself information. The six boost fields (`mop`, `mopf`, `wtg`, `cov`, `menu`, `form`) SHALL be materialized at `0` when absent, and `out.new_state` / `out.act_changed` at `false`. `dec.patched` and `dec.cf` SHALL be preserved as absent when absent — defaulting `patched` to `0` would make "no resolved target" indistinguishable from "natively clickable node", which is a tri-state the jar emits explicitly for that reason.

- **INV-APV-50**: A malformed record SHALL be skipped and counted in the reader's diagnostics rather than aborting the read. A record referencing an `act`, `st` or `out.target` ID that no earlier dictionary record defined is malformed by this rule; the reader SHALL NOT invent a placeholder string for it.

- **INV-APV-51**: The reader SHALL NOT fabricate an absolute clock. When `RUN_START` is absent from the trace — a truncated capture, or a pre-stage-4 file — the run-relative `t` SHALL still be reported and the epoch expansion SHALL be reported as unavailable. A base SHALL NOT be inferred from file mtime, from the logcat, or from any other source.

- **INV-APV-52**: The gzip step SHALL be non-fatal and write-only. Its failure SHALL log a WARNING and leave the uncompressed trace in place, and the task SHALL complete with the status it would otherwise have had. `task.result.trace_file` SHALL be byte-identical before and after collection completes: no step of the flow rewrites, reformats, truncates or converts it.

- **INV-APV-53**: No code path in this module SHALL read, validate or act on the `RUN_END` record. There SHALL be no sentinel check, no exit-code interpretation beyond the existing debug log, no task-status change and no retry logic keyed on it (owner decision D5 on the jar side). Truncated-run identification remains post-hoc analysis over trace and logcat timestamps.

- **INV-APV-54**: `_align_clocks()` and the UTC-offset reconstruction SHALL NOT be deleted before a captured run is shown to contain heartbeat lines in the task's `.logcat`. This is the counterpart of `event-sink` INV-SNK-14 on the jar side: the heartbeat is filtered at the device under any tag outside the capture allowlist, so a deletion that precedes the observation trades a working mechanism for an inert one and does so silently.

- **INV-APV-55**: The frozen legacy-corpus readers SHALL NOT be migrated, adapted or deleted by this change: `scripts/cmpm_stratify.py`, `scripts/analyze_cmpv2_llm.py`, `experimento-cal/scripts/*`, `experimento-20260721/scripts/*` and `calibracao/*`. They read an archived dataset that will not be regenerated, and are not compatibility shims.

## MODIFIED Requirements

### Requirement: ApeRVTool Execution Flow (FR18, FR19)

`ApeRVTool.execute_tool_specific_logic(task, app)` SHALL perform the following steps in order:

1. **Extract execution parameters**: Resolve `device_serial` from `task.config.device_id` (default `"emulator-5554"`) and `timeout_seconds` from `task.config.timeout` (default 300).

2. **Push JAR**: Resolve `ape-rv.jar` via `_resolve_jar_path()` and push to `/data/local/tmp/ape-rv.jar` via `_push_file_to_device()`.

3. **Push broadcast catalog**: If `system-broadcast.json` exists in the module directory (`os.path.dirname(__file__)`), push it to `/data/local/tmp/system-broadcast.json`. This catalog provides typed extras for system broadcast intents used by APE-RV's component triggering. If the file is absent, skip (APE-RV degrades gracefully).

4. **Derive and push the MOP artifact** (MOP variants only): When `_tool_config.get("mop_data") == "static_analysis"`, locate `<task.results_dir>/<apk_name>.json`, derive `<task.results_dir>/<apk_name>.mop.json` from it, and push **only that artifact** to `/data/local/tmp/mop-artifact.json`. The source document is never modified and never pushed. A MOP arm with no static-analysis JSON, or whose derivation fails, raises `RVToolExecutionError`.

5. **Push ape.properties**: Generate `ape.properties` from `_tool_config` using `APERV_PROPERTY_MAPPING` to translate Python keys to Java property names. When the MOP artifact was pushed, include its device path. Push to `/data/local/tmp/ape.properties`.

6. **Capture LLM backend provenance** (LLM arms only): query `GET {llm_url}/v1/models` once and record the result in the task output -- see "Per-Run LLM Backend Provenance". A failed query is encoded, never inferred from configuration, and never aborts the run (INV-APV-33).

7. **Build and execute command**: Build the `app_process` command via `_build_main_command()` and execute it, capturing stdout+stderr to `task.result.trace_file` in binary write mode. From stage 4 onward the captured stream is the NDJSON trace. **Command timeout is `timeout_seconds + 45` seconds** — widened from `+ 15`; see the grace-window rationale below.

8. **Handle timeout**: If `RVCommandTimeoutError` is raised, log it as the expected exit path for an exploration tool, run the collection step 10 below on the trace captured up to the kill, and only then re-raise as `RVToolTimeoutError`. Collection MUST NOT be skipped on the timeout path — timeout is how a normal exploration run ends, so skipping it there would exempt the majority of runs from collection. The `RVToolTimeoutError` contract SHALL be stated as `task.config.timeout + 45` seconds wherever it is documented.

9. **Check empty trace**: Call `_check_empty_trace()` and log a warning if the trace file is empty. This step is unchanged — a 0-byte NDJSON trace is still 0 bytes.

10. **Gzip at collection**: Compress the raw capture to `<trace>.ndjson.gz` next to the trace file. On failure, log a WARNING and continue.

Step 10 SHALL NOT inspect, validate or act on the trace's content: no `RUN_START` or `RUN_END` presence check, no exit-code interpretation beyond the existing debug log, no task-status change (INV-APV-53). `task.result.trace_file` SHALL remain the raw capture, byte-for-byte, after collection completes — no step of this flow rewrites, reformats or truncates it, and no NDJSON→legacy conversion step exists anywhere in the tool (INV-APV-52).

No health-check step is required (APE has no `--health-check` flag).

**Capture grace window: why 45 s.** The window exists so the agent's teardown can finish writing before the harness kills the capture. The 15 s it replaces is where the losses concentrate: among runs whose teardown completed, the overrun beyond the exploration budget reaches **12,991 ms** with 32 runs stacked against that ceiling and none beyond it — the signature of a hard wall rather than a natural distribution. Runs that lose the dump end inside the model serialization step, before the dump would have run.

This is recorded as a **hypothesis, not a measurement**. The true teardown duration of the runs that were cut is unobservable — that is what censoring means — so the widened window cannot be credited with a predicted recovery rate in advance. It is complementary to, not redundant with, the jar-side reordering (`ape` design D9): the reordering moves the dump ahead of the expensive write, this gives the chain room to finish. The smoke SHALL report the observed teardown durations under the new window so the assumption is checked rather than carried.

The `app_process` invocation SHALL use:
```
adb -s <serial> shell CLASSPATH=/data/local/tmp/ape-rv.jar /system/bin/app_process /system/bin
  com.android.commands.monkey.Monkey -p <package_name>
  --running-minutes <max(1, timeout_seconds // 60)>
  --ape <strategy>
  [-s <seed>]
```

The trailing `-s <seed>` is appended only when a seed is configured (INV-APV-18).

#### Scenario: Successful APE-RV execution with sata variant
- **WHEN** `execute_tool_specific_logic(task, app)` is called with `strategy="sata"`, timeout=60
- **THEN** `ape-rv.jar` SHALL be pushed to `/data/local/tmp/ape-rv.jar`
- **AND** the adb command SHALL include `--running-minutes 1` and `--ape sata`
- **AND** stdout+stderr SHALL be written to `task.result.trace_file`
- **AND** no MOP artifact SHALL be pushed to the device

#### Scenario: Collection leaves the NDJSON trace intact
- **WHEN** a run completes and `task.result.trace_file` holds 1,603 NDJSON records
- **THEN** after step 10 the file SHALL still hold exactly those 1,603 records, byte-for-byte
- **AND** `<trace>.ndjson.gz` SHALL decompress to the identical byte sequence
- **AND** no `[APE-STEP]`, `[APE-OUTCOME]` or `[APE-LLM-TEL]` line SHALL have been written anywhere by the tool

#### Scenario: Gzip failure is non-fatal and changes no status
- **WHEN** compression raises (for example, no space left on the results volume)
- **THEN** a WARNING SHALL be logged naming the trace path
- **AND** the uncompressed trace SHALL remain at `task.result.trace_file`
- **AND** the task SHALL complete with the same status it would have had otherwise

#### Scenario: Timeout during exploration still collects
- **WHEN** the exploration runs past `task.config.timeout + 45` seconds and `RVCommandTimeoutError` is raised
- **THEN** step 10 SHALL run on the trace captured up to the kill
- **AND** only then SHALL `RVToolTimeoutError` be re-raised
- **AND** the trace SHALL retain the records written before the kill, including a truncated final line if the kill landed mid-write

#### Scenario: No exit contract
- **WHEN** a trace ends without a `RUN_END` record because the process was killed before teardown
- **THEN** the tool SHALL NOT detect, log or act on its absence
- **AND** the task status SHALL be identical to that of a run whose trace ends with `RUN_END`

#### Scenario: Broadcast catalog pushed when present
- **WHEN** `system-broadcast.json` exists in the module directory
- **THEN** it SHALL be pushed to `/data/local/tmp/system-broadcast.json`
- **AND** APE-RV SHALL use it for component triggering with typed extras

#### Scenario: Broadcast catalog absent
- **WHEN** `system-broadcast.json` does not exist in the module directory
- **THEN** no broadcast catalog SHALL be pushed
- **AND** execution SHALL continue normally (APE-RV component triggering degrades gracefully)

#### Scenario: Execution timeout
- **WHEN** APE-RV runs for longer than `timeout_seconds + 45` seconds
- **THEN** `RVToolTimeoutError` SHALL be raised and logged
- **AND** the timeout SHALL be re-raised to the caller after collection has run

#### Scenario: Non-zero exit code from APE-RV
- **WHEN** APE-RV exits with a non-zero exit code (e.g., 211)
- **THEN** execution SHALL NOT raise an error
- **AND** a debug log SHALL be emitted noting the exit code is normal when app crashes are detected

#### Scenario: Empty trace file
- **WHEN** APE-RV execution completes but writes nothing to stdout
- **THEN** a warning log line SHALL contain `"aperv produced empty trace file"`

#### Scenario: Timeout budget includes the widened grace window
- **WHEN** a task is dispatched with an exploration timeout of `T` seconds
- **THEN** the `adb` command SHALL be given `T + 45` seconds before termination
- **AND** `RVToolTimeoutError` SHALL be raised only after `T + 45` seconds, not `T + 15`

#### Scenario: Smoke reports what the window actually cost
- **WHEN** the integration smoke completes
- **THEN** the observed teardown overrun SHALL be reported per run
- **AND** a run whose overrun still reaches the new ceiling SHALL be flagged as evidence the hypothesis was insufficient

#### Scenario: Provenance query does not delay the run
- **WHEN** the `/v1/models` query at step 6 fails or times out
- **THEN** the flow SHALL proceed to step 7
- **AND** the provenance fields SHALL record the failure (INV-APV-33)

---

### Requirement: Offline Clock-to-Violation Join (FR11, FR13, NFR03)

`aperv_tool` SHALL provide a utility that joins a run's step clock against the `RVSEC:` violation lines recorded for that run, producing per-run rows that correlate when the exploration reached a given point with when a monitor fired.

The utility exists to test the premise the whole MOP-frontier mechanism rests on: that *reaching* a MOP screen is sufficient to fire its monitor. That premise is plausible — the monitored operation fires in `onCreate` for 84% of the apps and UI handlers account for 0.4% of direct reach — but it has never been measured, and if it is false the frontier mechanism is steering toward screens that need interaction rather than arrival. The join is also the evidence base for the deferred decision on reading logcat at runtime (item N5): it establishes what signal a runtime reader would have had, and with what latency, before any runtime mechanism is proposed.

The utility SHALL live in the `aperv_tool` package rather than in a per-campaign script directory, because the real thesis experiment consumes it, not only the calibration campaign. It SHALL be offline and read-only over recorded artifacts, and SHALL NOT read logcat from a device or require an emulator (INV-APV-35).

**The step series comes from the native reader, and both series come from the same clock.** The utility SHALL obtain its steps from `trace_ndjson.py` rather than from a regex over the trace, and SHALL place violations on the exploration timeline using the per-step heartbeat lines the jar writes into logcat — the same file, the same clock and the same rendering as the `RVSEC` violation lines. Consequently the module SHALL contain no UTC-offset reconstruction: no year-candidate search, no quarter-hour rounding, no anchor selection, and no `alignment_residual_ms` field on `RunJoin`. These are deleted rather than disabled (P3), and their deletion is ordered by INV-APV-54: it lands only after a captured run is shown to contain heartbeat lines, because until then the reconstruction is the only working mechanism and the heartbeat is unobserved.

The distinction between a launch-time monitor and a leftover from an earlier run on the same device is preserved and still matters: a logcat buffer is not always cleared between runs, so a violation before the first step is reported as `PRE_EXPLORATION` with its signed distance from that step, and the analysis draws the line.

#### Scenario: Join reproduces the recorded corpus totals
- **WHEN** the utility runs over the recorded iter0 corpus of 880 runs
- **THEN** it SHALL account for 9,586 `RVSEC:` lines
- **AND** those lines SHALL be distributed across exactly 605 runs and 32 distinct APKs
- **AND** a mismatch in any of the three totals SHALL fail the validation gate

#### Scenario: Join runs without offset reconstruction
- **WHEN** the utility joins a stage-4 trace against a logcat containing the per-step heartbeat lines
- **THEN** each violation SHALL be placed against the heartbeat whose step is the last at or before it, read directly from the shared logcat clock
- **AND** the module SHALL contain no year-candidate search, no quarter-hour rounding and no `alignment_residual_ms`
- **AND** `RunJoin` SHALL carry no `alignment_residual_ms` field

#### Scenario: Run with no violations produces an empty but valid result
- **WHEN** the utility runs over one of the 275 iter0 runs with no `RVSEC:` lines
- **THEN** it SHALL produce a row set with zero violations for that run
- **AND** it SHALL NOT raise, and SHALL NOT omit the run from the report

#### Scenario: Run whose logcat carries no heartbeat
- **WHEN** the utility runs over a run whose `.logcat` contains `RVSEC` lines but no heartbeat line at all
- **THEN** every violation of that run SHALL be reported with phase `UNALIGNED`
- **AND** the run SHALL be reported rather than dropped, so the denominator survives
- **AND** no offset SHALL be reconstructed to place them anyway

#### Scenario: Artifacts are never modified
- **WHEN** the utility completes over any run directory
- **THEN** every artifact it read SHALL be byte-identical to its prior content (INV-APV-35)

#### Scenario: Missing run directory is a usage error
- **WHEN** the utility is invoked against a path that does not exist
- **THEN** it SHALL exit with status 2
- **AND** the message SHALL name the missing path

## ADDED Requirements

### Requirement: Native NDJSON Trace Reader (FR11, FR13, NFR03, NFR06)

The module SHALL provide `modules/aperv-tool/src/aperv_tool/analysis/trace_ndjson.py`, a read-only streaming reader of the NDJSON trace, and it SHALL be the sole mechanism by which analysis code in this module consumes a stage-4 trace. It follows the shape of its sibling `analysis/coverage_dump.py`: a pure offline component with a typed row model, never in the run path.

The reader SHALL stream the file — the trace is the largest artifact a run produces, and the reader must not require it in memory — and SHALL yield one typed row per `StepRecord`, having already:

- resolved the `act` and `st` integer references, and `out.target`, against the `ACT` / `STATE` dictionary records defined earlier in the same trace;
- materialized the fields the sink omits at their documented defaults, and left the tri-state fields absent (INV-APV-49);
- re-derived `activity_has_mop` on the step side from the record's `ACT` entry, and on the outcome side via `out.target` → `STATE.act` → `ACT.mop`, since the jar records that static per-activity fact once on the dictionary entry rather than on every step;
- expanded the run-relative `t` to epoch milliseconds via `RUN_START.t0` where an absolute clock is wanted, and reported the expansion as unavailable when `RUN_START` is absent (INV-APV-51);
- attached the step's `llm[]` sub-events, in occurrence order, and its `out` section to the same row — so that the three-way join by `step=` that the legacy format required ceases to exist for every consumer.

The reader SHALL NOT convert between formats in either direction, SHALL NOT write to the trace, and SHALL NOT run on the collection path (INV-APV-48). A malformed record SHALL be skipped and counted rather than aborting the read (INV-APV-50): a trace truncated by a `SIGKILL` ends in a partial line by construction, and losing the whole run's analysis over its last line would be a worse failure than losing the line.

**The `ape` change `rearch-04-step-ndjson-telemetry` is the authority for the wire format.** Its `event-sink` spec defines the `StepRecord` schema, the dictionary encoding, the omitted-default rules and the heartbeat payload; its design carries the legacy-field → new-schema mapping table. The format is defined jointly and cut once, and this reader conforms to it rather than restating it.

The golden fixture that exercises this requirement SHALL be `modules/aperv-tool/tests/fixtures/trace_ndjson_golden.ndjson`, a hand-written stage-4 trace containing, at minimum: a `RUN_START` with `t0`; `ACT` entries with `mop:1` and `mop:0`; two `STATE` entries; a step whose `dec` carries no boost fields at all; a step carrying `patched:0`; a step carrying no `patched` member; a step with two `llm[]` entries in occurrence order; a step whose `out` resolves to a new state; a step closed with no `out` member; a step flushed with `out:{"resolved":false}`; a malformed line; and a truncated final line. Every scenario below names the fixture element that exercises it, so no rule is asserted against an input that cannot reach it.

#### Scenario: Reader yields a joined step row
- **WHEN** the reader runs over the golden fixture, whose step 42 carries a `dec` with no boost fields, two `llm[]` sub-events and an `out` closed at step 43
- **THEN** it SHALL yield exactly one row for step 42
- **AND** that row SHALL carry the activity and state resolved to their dictionary strings, not their integer IDs
- **AND** it SHALL carry `mop=0`, `mopf=0`, `wtg=0`, `cov=0`, `menu=0` and `form=0` as explicit zeros
- **AND** it SHALL carry both LLM sub-events in occurrence order and the outcome fields
- **AND** no second pass over the trace SHALL be required to join them

#### Scenario: Tri-state patched is not defaulted
- **WHEN** the reader runs over the fixture's step carrying `dec.patched:0` and the fixture's step carrying no `patched` member
- **THEN** the first row SHALL report `patched` as `0` and the second SHALL report it as absent
- **AND** the two SHALL be distinguishable in the row model, because absence means "no resolved target" and `0` means "natively clickable node"

#### Scenario: activity_has_mop re-derived on both sides
- **WHEN** the reader runs over a step whose `act` refers to an `ACT` entry with `mop:1` and whose `out.target` refers to a `STATE` whose `act` refers to an `ACT` entry with `mop:0`
- **THEN** the row SHALL report the step-side flag as true and the outcome-side flag as false
- **AND** neither value SHALL be read from the step record itself, which does not carry them

#### Scenario: Malformed record is skipped and counted
- **WHEN** the reader runs over the golden fixture, whose content includes one unparseable line and one truncated final line
- **THEN** the reader SHALL yield rows for every well-formed record in the file
- **AND** SHALL report exactly 2 skipped records in its diagnostics
- **AND** SHALL NOT raise

#### Scenario: Reference to an undefined dictionary ID is malformed
- **WHEN** a record references `st:99`, for which no `STATE` record appears earlier in the trace
- **THEN** that record SHALL be counted as malformed and skipped
- **AND** the reader SHALL NOT emit a row carrying a placeholder or empty state string

#### Scenario: Trace without RUN_START reports epoch as unavailable
- **WHEN** the reader runs over a trace whose capture began after `RUN_START` was written, so no `t0` is present
- **THEN** every row SHALL still carry its run-relative `t`
- **AND** the epoch expansion SHALL be reported as unavailable
- **AND** no base SHALL be inferred from the file's mtime or from the logcat

#### Scenario: Reader stays off the collection path
- **WHEN** the module's tests assert the import graph of `tools/aperv/tool.py`
- **THEN** `trace_ndjson` SHALL NOT be reachable from it
- **AND** no collection-path function SHALL reference `RUN_END` (INV-APV-53)

### Requirement: Frozen Legacy-Corpus Readers Are Not Migrated (FR11, NFR03)

The archived legacy corpus — the traces behind the 2026-07-24 calibration report and the decisive run — will not be regenerated, so the scripts that read it SHALL keep parsing the legacy `[APE-*]` `key=value` format and SHALL NOT be migrated, adapted or deleted by this change: `scripts/cmpm_stratify.py`, `scripts/analyze_cmpv2_llm.py`, `experimento-cal/scripts/*`, `experimento-20260721/scripts/*` and `calibracao/*` (INV-APV-55).

This carve-out is normative, and it is stated here rather than in a comment so that it is not mistaken for a P3 violation by a later cleanup sweep. Those scripts are not compatibility shims keeping a superseded implementation alive for new data; they are the readers of a dataset that is finished. P3 governs superseded *implementation*, not analysis code over frozen data. The distinction is operational and easy to apply: `clock_logcat_join.py` migrates because it must read *new* traces; these do not, because they never will. Should the archived corpus ever be regenerated against a stage-4 jar, the carve-out expires with it and these scripts migrate or die then — not before.

`analysis/coverage_dump.py` is likewise untouched, for a different reason: it reads only the `[APE-RV] UICOV` and `UICOV-ACT` lines, which stage 4 does not modify, and it will keep reading them from a stage-4 trace unchanged.

The carve-out SHALL also be recorded in `modules/aperv-tool/CLAUDE.md`, so that a reader of the module's own documentation finds it without going through the spec.

#### Scenario: A frozen-corpus script keeps its legacy parser
- **WHEN** this change is applied and a stage-4 jar is deployed, so no emitter of the legacy line family remains
- **THEN** `scripts/cmpm_stratify.py`, `scripts/analyze_cmpv2_llm.py` and the `experimento-cal` / `experimento-20260721` / `calibracao` scripts SHALL be unchanged by this change
- **AND** they SHALL still parse the archived legacy traces they were written for

#### Scenario: The carve-out is discoverable from the module docs
- **WHEN** a developer reads `modules/aperv-tool/CLAUDE.md` looking for why two trace formats are parsed in the same repository
- **THEN** the document SHALL name the frozen-corpus scripts and state that they are deliberately not migrated
- **AND** SHALL state that `clock_logcat_join.py` migrated because it reads new traces
