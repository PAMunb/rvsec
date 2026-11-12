## ADDED Requirements

### Requirement: The Weight Ladder Setting (FR19, NFR05)

`configure()` SHALL accept the override `mop_weights` as a tool-DSL string of 1 to 10 non-negative integers separated by `;`, or as a list or tuple of such integers from a variant dict, and SHALL normalize it to a tuple. Any other value SHALL raise `ConfigurationError` naming `mop_weights`, before any device interaction. `ape.properties` SHALL carry it as `ape.mopWeights=<w1>,<w2>,…`. `mop_weight_d1..d3` SHALL NOT be mapped.

#### Scenario: a ladder written in the DSL reaches the properties with commas
- **WHEN** a cell runs with the override `mop_weights=500;400;300;200`
- **THEN** `ape.properties` SHALL contain the line `ape.mopWeights=500,400,300,200`
- **AND** it SHALL contain no `ape.mopWeightD1`, `ape.mopWeightD2` or `ape.mopWeightD3` line

#### Scenario: a malformed ladder is refused before the device
- **WHEN** `mop_weights` is `""`, `"500;-1"`, `"500,400"`, `"a;b"` or eleven integers
- **THEN** `configure()` SHALL raise `ConfigurationError` naming `mop_weights`
- **AND** no `adb` command SHALL have run

#### Scenario: a retired per-level weight is an unmapped key
- **WHEN** a cell runs with the override `mop_weight_d1=500`
- **THEN** `configure()` SHALL raise `ConfigurationError`, as for any override without a mapping

### Requirement: Weighed Cut Follows the Weight Ladder (FR19, NFR05)

The artifact SHALL be derived at the cut max(`DIST_WEIGHED_MAX`, length of the cell's `mop_weights`), or at `DIST_WEIGHED_MAX` when the cell has no ladder (INV-APV-70). `derive()` SHALL take the cut as its argument `cut`, default `DIST_WEIGHED_MAX`, and SHALL raise `DerivationError` when it is not an integer from 1 to the document's horizon: its `distMax`, which SHALL be an integer ≥ 1, or 10 when it carries none (INV-APV-71).

#### Scenario: the default cell derives the artifact it derives today
- **WHEN** the `mop` cell runs without `mop_weights` on a document without `distMax`
- **THEN** the artifact SHALL be derived at cut 3
- **AND** it SHALL be byte-identical to the artifact `derive()` wrote before this change for the same document

#### Scenario: a longer ladder deepens the cut
- **WHEN** the `mop` cell runs with `mop_weights=500;450;400;350;300;250` on a full document
- **THEN** the artifact SHALL be derived at cut 6

#### Scenario: a shorter ladder keeps the cut at three
- **WHEN** the `mop` cell runs with `mop_weights=500;400`
- **THEN** the artifact SHALL be derived at cut 3, and the jar weighs only the first two levels

#### Scenario: a cut above the document's horizon is refused
- **WHEN** `derive(document, cut=6)` runs on a document carrying `distMax: 5`
- **THEN** it SHALL raise `DerivationError` naming the cut 6 and the horizon 5
- **AND** `derive(document, cut=11)` on a document without `distMax` SHALL raise naming the horizon 10

#### Scenario: a malformed horizon in the document is refused
- **WHEN** `derive(document)` runs on a document carrying `distMax: "15"`, `distMax: true` or `distMax: 0`
- **THEN** it SHALL raise `DerivationError` naming `distMax` and the value, checked right after the check that the
  document is an object, as `derive()` treats any section of the wrong type
- **AND** no artifact SHALL be returned

### Requirement: A Document That Cannot Carry the Cut Is Refused (FR19, NFR04)

`_derive_mop_artifact` SHALL raise `RVToolExecutionError` and write no artifact when the document cannot carry the cut: a compact document whose `distancePairs.weighedMax` is below the cut, a `distancePairs` marker without an integer `weighedMax`, or a horizon below the cut (INV-APV-71). A compact document keeps no pair beyond `weighedMax` except the 3 nearest, so deriving it deeper would run the shallower cut without notice.

#### Scenario: a compact document under a deeper ladder is refused
- **WHEN** the cell runs with a six-level ladder on a document carrying `distancePairs: {"weighedMax": 3, "k": 3}`
- **THEN** `_derive_mop_artifact` SHALL raise `RVToolExecutionError` naming `weighedMax=3` and the cut 6
- **AND** no artifact SHALL be written and nothing SHALL be pushed

#### Scenario: a malformed marker is refused, not guessed
- **WHEN** the document carries `distancePairs: {"k": 3}`
- **THEN** `_derive_mop_artifact` SHALL raise `RVToolExecutionError` naming the marker

### Requirement: The Cached Artifact Is Named by Its Cut (NFR04)

The cached artifact SHALL be `<task.results_dir>/<apk_name>.mop.json` at cut 3 and `<task.results_dir>/<apk_name>.cut<c>.mop.json` at any other cut `c` (INV-APV-72). The cut is not written into the artifact, so the name is what keeps an artifact derived at one cut from being reused at another.

#### Scenario: two cuts of one document are two artifacts
- **WHEN** `aperv:mop` runs on the same results directory once without a ladder and once with a six-level ladder
- **THEN** `<apk_name>.mop.json` and `<apk_name>.cut6.mop.json` SHALL both exist
- **AND** each run SHALL push its own

### Requirement: APE Heap Growth Limit (FR18, FR19)

Before the main command, `execute_tool_specific_logic()` SHALL set `dalvik.vm.heapgrowthlimit` to `APE_HEAP_GROWTH_LIMIT` (`rv_android_core.constants`, `512m`) in every cell, through `Android.set_ape_heap_growth_limit`, the call the `ape` built-in also makes (`tools` INV-TOOL-30). When the set fails or the read-back is not `512m`, it SHALL raise `RVToolExecutionError` and SHALL NOT start the exploration (INV-APV-73).

What is measured and what is only inferred about the heap: design D12.

#### Scenario: every cell starts the APE with the larger limit
- **WHEN** any of `base`, `mop`, `as`, `as_mop`, `as_llm`, `as_mop_llm` or `mop_nolaunch` runs
- **THEN** the setprop and the getprop SHALL run before the `app_process` command

#### Scenario: a limit that does not hold stops the task
- **WHEN** `getprop dalvik.vm.heapgrowthlimit` reads `192m` after the setprop
- **THEN** `RVToolExecutionError` SHALL be raised naming the value read back
- **AND** no `app_process` command SHALL be executed

#### Scenario: base and the APE run with the same heap
- **WHEN** `aperv:base` and the `ape` built-in run on the same AVD
- **THEN** both SHALL set `512m` through `Android.set_ape_heap_growth_limit`, which runs
  `adb -s <serial> shell su 0 setprop dalvik.vm.heapgrowthlimit 512m` and then `getprop`

## MODIFIED Requirements

### Requirement: ApeRVTool Execution Flow (FR18, FR19)

`ApeRVTool.execute_tool_specific_logic(task, app)` SHALL perform the following steps in order:

1. **Extract execution parameters**: Resolve `device_serial` from `task.config.device_id` (default `"emulator-5554"`) and `timeout_seconds` from `task.config.timeout` (default 300).

2. **Push JAR**: Resolve `ape-rv.jar` via `_resolve_jar_path()` and push to `/data/local/tmp/ape-rv.jar` via `_push_file_to_device()`.

3. **Push broadcast catalog**: When the variant carries `broadcast_catalog=True` and `system-broadcast.json` exists in the module directory (`os.path.dirname(__file__)`), push it to `/data/local/tmp/system-broadcast.json`. The catalog provides typed extras for the system broadcast intents of APE-RV's component triggering, a STATIC member that the four `as*` presets mount at `componentPercentage=0.03` and that is the catalog's only reader in the jar. `base` and `mop` do not mount STATIC and push no catalog (INV-APV-10). If the file is absent, skip (APE-RV degrades gracefully).

4. **Derive and push the artifact** (every cell except `base`): When `_tool_config.get("static_data") == "static_analysis"`, locate `<task.results_dir>/<apk_name>.json`, derive the artifact from it at the cell's cut (`<task.results_dir>/<apk_name>.mop.json`, or `<apk_name>.cut<c>.mop.json` at a cut `c` other than 3; Requirement: The Cached Artifact Is Named by Its Cut), and push **only that artifact** to `/data/local/tmp/mop-artifact.json`. The source document is never modified and never pushed. A variant with no static-analysis JSON, or whose derivation fails, raises `RVToolExecutionError`.

5. **Push ape.properties**: Generate `ape.properties` as `ape.preset=<preset>` first, `ape.variant=<variant>` second, then `ape.staticDataPath=<artifact device path>` when the artifact was pushed, then one `ape.<key>=<value>` line per entry of `overrides`, translated through `APERV_PROPERTY_MAPPING`. Push to `/data/local/tmp/ape.properties`.

6. **Capture LLM backend provenance** (LLM cells only): query `GET {llm_url}/v1/models` once and record the result in the task output -- see "Per-Run LLM Backend Provenance". A failed query is encoded, never inferred from configuration, and never aborts the run (INV-APV-33).

7. **Set the heap growth limit, build and execute the command**: Set `dalvik.vm.heapgrowthlimit` to `512m` and read it back (Requirement: APE Heap Growth Limit). Then build the `app_process` command via `_build_main_command()` and execute it, capturing stdout+stderr to `task.result.trace_file` in binary write mode. From stage 4 onward the captured stream is the NDJSON trace. **Command timeout is `timeout_seconds + 45` seconds** — widened from `+ 15`; see the grace-window rationale below.

8. **Handle timeout**: If `RVCommandTimeoutError` is raised, log it as the expected exit path for an exploration tool, run the collection step 10 below on the trace captured up to the kill, and only then re-raise as `RVToolTimeoutError`. Collection MUST NOT be skipped on the timeout path — timeout is how a normal exploration run ends, so skipping it there would exempt the majority of runs from collection. The `RVToolTimeoutError` contract SHALL be stated as `task.config.timeout + 45` seconds wherever it is documented.

9. **Check empty trace**: Call `_check_empty_trace()` and log a warning if the trace file is empty. This step is unchanged — a 0-byte NDJSON trace is still 0 bytes.

10. **Gzip at collection**: Compress the raw capture to `<trace>.ndjson.gz` next to the trace file. On failure, log a WARNING and continue.

Step 10 SHALL NOT inspect, validate or act on the trace's content: no `RUN_START` or `RUN_END` presence check, no exit-code interpretation beyond the existing debug log, no task-status change (INV-APV-53). `task.result.trace_file` SHALL remain the raw capture, byte-for-byte, after collection completes — no step of this flow rewrites, reformats or truncates it, and no NDJSON→legacy conversion step exists anywhere in the tool (INV-APV-52).

The tool SHALL NOT read back, parse or validate any jar output, `RUN_START` included (INV-APV-43, owner decision D1). The effective plan the jar resolved, and the variant name it received, are echoed write-only into the trace; reconstructing which cell ran a task is post-hoc analysis, not a runtime check.

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
- **WHEN** `execute_tool_specific_logic(task, app)` is called for `aperv:base`, timeout=60
- **THEN** `ape-rv.jar` SHALL be pushed to `/data/local/tmp/ape-rv.jar`
- **AND** the adb command SHALL include `--running-minutes 1` and `--ape sata`
- **AND** stdout+stderr SHALL be written to `task.result.trace_file`
- **AND** no artifact and no broadcast catalog SHALL be pushed to the device

#### Scenario: Properties file carries preset plus deltas only
- **WHEN** step 5 runs for `as_mop` with the artifact pushed
- **THEN** the generated file SHALL be exactly the three lines `ape.preset=as_mop`, `ape.variant=as_mop`,
  `ape.staticDataPath=/data/local/tmp/mop-artifact.json`
- **AND** it SHALL contain no `ape.mopDataPath` line

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

#### Scenario: No echo read-back
- **WHEN** the run completes and the trace's first record is the jar's `RUN_START` echo of the
  resolved plan, carrying `variant: "as_mop"`
- **THEN** the tool SHALL NOT have parsed, validated or branched on it (INV-APV-43)

#### Scenario: Broadcast catalog pushed when present
- **WHEN** `aperv:as_mop` runs and `system-broadcast.json` exists in the module directory
- **THEN** it SHALL be pushed to `/data/local/tmp/system-broadcast.json`
- **AND** APE-RV SHALL use it for component triggering with typed extras
- **AND** `ape.properties` SHALL carry no `ape.componentPercentage` line, because the dose comes from the preset

#### Scenario: The cells without STATIC push no catalog
- **WHEN** `aperv:base` or `aperv:mop` runs and `system-broadcast.json` exists in the module directory
- **THEN** no file SHALL be pushed to `/data/local/tmp/system-broadcast.json`

#### Scenario: Broadcast catalog absent
- **WHEN** `aperv:as` runs and `system-broadcast.json` does not exist in the module directory
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

### Requirement: Derived MOP Artifact Generation and Caching (FR19, NFR04)

`ApeRVTool._derive_mop_artifact(task)` SHALL return the host path of the compact MOP artifact for the
task's APK, generating it when needed:

1. Determine the cut: max(`DIST_WEIGHED_MAX`, length of the cell's `mop_weights`), or `DIST_WEIGHED_MAX`
   without a ladder (INV-APV-70). Compute the SHA-256 of the current full JSON at
   `<results_dir>/<apk_name>.json`, reading the file in chunks.
2. When the cut's artifact exists (`<results_dir>/<apk_name>.mop.json` at cut 3,
   `<results_dir>/<apk_name>.cut<c>.mop.json` at any other cut `c`, INV-APV-72), its `source.digest` equals `"sha256:" + <hex>`
   **and** its `formatVersion` equals `derive_mop_artifact.FORMAT_VERSION`, reuse it without
   regenerating and without parsing the full JSON.
3. Otherwise read the full JSON in streaming as UTF-8, reducing each method's `targetDistances` to the
   pairs the artifact can carry at the cut (INV-APV-64), refuse a document that cannot carry the cut
   (INV-APV-71), call `derive(…, cut=cut)` + `serialize_canonical()` on the result,
   and write the artifact atomically (write-temp-then-rename in the same directory). A failed
   derivation SHALL write nothing.

The method SHALL NOT hold the file's text, nor any `targetDistances` pair that cannot reach the
artifact. A gh120 document is large — up to 9.34 GB in the Study 03 corpus — and a whole-document
parse peaked at 3.1 times the file size (gh122 task 7.7). The digest and the streaming read each read
the file on their own, and a cache hit never parses.

The reduction is exact, not an approximation. `derive()` merges distances by the minimum per target
and cuts only at emission: every pair at `d ≤ cut` for a widget or handler, the
`DIST_K` nearest by `(d, i)` for an activity (INV-DRV-10). A pair dropped by the reduction is beyond
the cut and has at least `DIST_K` targets ahead of it in its own method; after any merge
those targets are still ahead of it, so it can be in no emitted list.

The artifact is cached next to its source so it is inspectable and diffable, and it is a pure function
of the full JSON, the generator's format and the cut (INV-APV-47, INV-DRV-05). The cut is not written
into the artifact, so it enters the cache key through the file name (INV-APV-72). The format is part of the cache
key because the digest alone names the input, not the derivation: after a format bump a cached
artifact of the old format matches its source's digest and would be pushed to a jar that rejects it,
and every cell that reads the artifact would abort (`ape` INV-MOP-34). There is no condition under
which the full JSON reaches the device (INV-APV-46).

The same artifact serves every cell that reads it. The jar's loader separates the static GUI model (read by
STATIC) from the MOP targets (read by MOP) at load time, so the host-side derivation and the format are the same
for `mop`, `as` and the cells that mount both.

Derivation failure means the document is structurally unusable, not that the analysis stopped early.
An unreadable, non-UTF-8, unparseable or truncated file fails here, in the streaming read, before
`derive()` is reached; a well-formed document that lacks the WTG stage does not fail at all
(INV-DRV-08).

#### Scenario: cache hit skips derivation
- **WHEN** `<results_dir>/com.example_1.apk.mop.json` exists carrying
  `source.digest == "sha256:ab12…"` and the SHA-256 of `com.example_1.apk.json` is `ab12…`
- **THEN** `_derive_mop_artifact(task)` SHALL return that path
- **AND** `derive()` SHALL NOT be called
- **AND** the full JSON SHALL NOT be parsed

#### Scenario: a cached artifact of another cut is not reused
- **WHEN** `<results_dir>/com.example_1.apk.mop.json` exists with a matching digest and format, and
  the cell runs with a five-level `mop_weights`
- **THEN** `_derive_mop_artifact(task)` SHALL derive at cut 5 and return
  `<results_dir>/com.example_1.apk.cut5.mop.json`
- **AND** `com.example_1.apk.mop.json` SHALL be left as it was

#### Scenario: stale cache regenerates
- **WHEN** the cached artifact records `source.digest == "sha256:ab12…"` but the current full JSON
  hashes to `cd34…`
- **THEN** the artifact SHALL be regenerated and overwritten
- **AND** the pushed bytes SHALL equal a fresh derivation of the current full JSON

#### Scenario: failed derivation leaves no artifact behind
- **WHEN** `derive()` raises `DerivationError` because `document["windows"]` is the string `"none"`
  instead of a list
- **THEN** no `<apk_name>.mop.json` SHALL exist afterwards, and any partially written temporary file
  SHALL be removed
- **AND** `RVToolExecutionError` SHALL be raised carrying the derivation error

#### Scenario: WTG-less document arms both aperv arms
- **WHEN** `<results_dir>/app.pachli_50.apk.json` carries 6336 `reachability` entries, 45 `windows`,
  `transitions: []` and no `complete` key
- **THEN** `_derive_mop_artifact(task)` SHALL return the path of a written `app.pachli_50.apk.mop.json`
- **AND** the task SHALL NOT fail, for the `as` cell and for the `as_mop` cell alike
- **AND** the artifact SHALL carry `wtg == {}` and `stats["wtgEdges"] == 0`

#### Scenario: cached artifact of an older format regenerates
- **WHEN** `<results_dir>/com.example_1.apk.mop.json` carries `formatVersion: 1` and
  `source.digest == "sha256:ab12…"`, the SHA-256 of `com.example_1.apk.json` is `ab12…`, and
  `FORMAT_VERSION` is 2
- **THEN** `derive()` SHALL be called and the artifact overwritten
- **AND** the pushed artifact SHALL carry `formatVersion: 2`

#### Scenario: the streaming derivation is byte-identical to the whole-document one
- **WHEN** the artifact of `cryptoapp.apk.json`, and of each of `org.wikipedia_50595`,
  `at.techbee.jtx_216000015` and three smaller Study 03 documents, is derived once by streaming and
  once by `derive(json.load(...))`
- **THEN** the two serialized artifacts SHALL be byte-identical for every document

#### Scenario: the largest corpus document derives inside a campaign container
- **WHEN** `_derive_mop_artifact` derives `eu.darken.sdmse_10705000.apk.json` (9.34 GB) on a cache miss
- **THEN** the process's peak resident memory SHALL stay below 3 GiB
- **AND** the artifact SHALL be written

### Requirement: ape.properties Composition

`ApeRVTool._push_properties()` SHALL generate an `ape.properties` file and push it to
`/data/local/tmp/ape.properties` on the device. The file SHALL be composed in a fixed order so that
two runs of the same variant produce byte-identical output:

```text
ape.preset=<preset>                                   # always first
ape.variant=<variant>                                 # always second
ape.staticDataPath=/data/local/tmp/mop-artifact.json  # only when the artifact was pushed
ape.<mapped-override-key>=<value>                     # one line per overrides entry, mapping order
```

Only the entries of `_tool_config["overrides"]` are translated through the mapping. `preset` and `variant` have
their own fixed lines. The other Python-only keys (`strategy`, `static_data`, `seed`, and the three
device-addressing keys) have no mapping entry and never reach the file. Python bools SHALL be serialized
lowercase (`True` → `true`). An `overrides` key with no `APERV_PROPERTY_MAPPING` entry SHALL raise
`ConfigurationError` **in `configure()`**, which is what makes the rejection precede every `adb push` of the run.

The data line is `ape.staticDataPath`, not `ape.mopDataPath`. The jar renamed the key because the artifact feeds
STATIC as well as MOP (`ape` D-B2) and retired the old name, so a file that still writes it aborts with
`retired_key`. The device path of the artifact is unchanged: it is a file name on the device, not a key the jar
resolves.

`APERV_PROPERTY_MAPPING` is a pass-through translation table and nothing more (see "Arm Property
Overrides Pass-Through"). It SHALL contain only keys the deployed jar accepts (INV-APV-41). The 64
entries are:

| Python Key | Java Property | Notes |
|------------|--------------|-------|
| `addons` | `ape.addons` | ADDONS group key; stated by the `as*` presets |
| `static` | `ape.static` | STATIC group key; requires the artifact |
| `mop` | `ape.mop` | MOP group key; requires the artifact |
| `llm` | `ape.llm` | LLM group key; requires `llm_url` |
| `throttle_ms` | `ape.defaultGUIThrottle` | BASE |
| `default_epsilon` | `ape.defaultEpsilon` | BASE |
| `graph_stable_restart_threshold` | `ape.graphStableRestartThreshold` | BASE |
| `state_stable_restart_threshold` | `ape.stateStableRestartThreshold` | BASE |
| `fuzzing_rate` | `ape.fuzzingRate` | `FUZZING` sub-parameter |
| `do_fuzzing` | `ape.doFuzzing` | `FUZZING` activation |
| `throttle_for_activity_transition` | `ape.throttleForActivityTransition` | BASE |
| `max_extra_priority_aliased_actions` | `ape.maxExtraPriorityAliasedActions` | BASE |
| `max_states_per_activity` | `ape.maxStatesPerActivity` | BASE |
| `trivial_activity_rank_threshold` | `ape.trivialActivityRankThreshold` | BASE |
| `do_back_to_trivial_activity` | `ape.doBackToTrivialActivity` | BASE |
| `max_idle_timeout_ms` | `ape.maxIdleTimeoutMs` | BASE tuning knob |
| `take_screenshot_for_every_step` | `ape.takeScreenshotForEveryStep` | BASE diagnostic |
| `save_gui_tree_to_xml_every_step` | `ape.saveGUITreeToXmlEveryStep` | BASE diagnostic |
| `back_menu_pick_cap` | `ape.backMenuPickCap` | `BACK_MENU_CAP` (ADDONS) |
| `activity_stable_restart_threshold` | `ape.activityStableRestartThreshold` | `ACTIVITY_STABLE_RESTART` (ADDONS) |
| `foreign_activity_guard` | `ape.foreignActivityGuard` | `FOREIGN_ACTIVITY_GUARD` (ADDONS) |
| `tree_package_guard` | `ape.treePackageGuard` | `TREE_PACKAGE_GUARD` (ADDONS) |
| `dynamic_epsilon` | `ape.dynamicEpsilon` | `DYNAMIC_EPSILON` (ADDONS) |
| `heuristic_input` | `ape.heuristicInput` | `HEURISTIC_INPUT` (ADDONS) |
| `form_completion_enabled` | `ape.formCompletionEnabled` | `FORM_COMPLETION` (ADDONS) |
| `model_menu_enabled` | `ape.modelMenuEnabled` | `MODEL_MENU` (ADDONS) |
| `tree_enhancements_enabled` | `ape.treeEnhancementsEnabled` | `TREE_ENHANCEMENTS` (ADDONS) |
| `activity_budget_enabled` | `ape.activityBudgetEnabled` | `ACTIVITY_BUDGET` (ADDONS) |
| `coverage_boost_weight` | `ape.coverageBoostWeight` | `COVERAGE_BOOST` (ADDONS) |
| `frontier_boost_weight` | `ape.frontierBoostWeight` | `NAV_FRONTIER` (STATIC) |
| `fuzz_input_typed` | `ape.fuzzInputTyped` | `TYPED_FUZZ` (STATIC) |
| `mop_weight_direct` | `ape.mopWeightDirect` | `MOP` sub-parameter, read under `flag` |
| `mop_weight_transitive` | `ape.mopWeightTransitive` | `MOP` sub-parameter, read under `flag` |
| `mop_weight_open_menu` | `ape.mopWeightOpenMenu` | `MENU_GATEWAY` activation (MOP; also requires `MODEL_MENU`) |
| `mop_weight_wtg` | `ape.mopWeightWtg` | `WTG` activation (MOP) |
| `mop_activity_source_components` | `ape.mopActivitySourceComponents` | `MOP_ACTIVITY_SOURCE` (MOP) |
| `mop_frontier_weight` | `ape.mopFrontierWeight` | `MOP_FRONTIER` activation (MOP) |
| `activity_trigger_enabled` | `ape.activityTriggerEnabled` | `MOP_LAUNCHER` activation (MOP) |
| `activity_trigger_stagnation_step` | `ape.activityTriggerStagnationStep` | `MOP_LAUNCHER` sub-parameter; the launcher cadence |
| `activity_trigger_max_per_run` | `ape.activityTriggerMaxPerRun` | `MOP_LAUNCHER` sub-parameter |
| `component_percentage` | `ape.componentPercentage` | `COMPONENT_TRIGGER` activation (STATIC); the STATIC block states 0.03 |
| `mop_scoring` | `ape.mopScoring` | `MOP` sub-parameter; the MOP block states `distance` |
| `mop_weights` | `ape.mopWeights` | `MOP` sub-parameter, read under `distance` only; a ladder of 1 to 10 non-negative integers, `;`-separated in the tool DSL and `,`-separated in `ape.properties`; its length deepens the derive's cut (Requirement: Weighed Cut Follows the Weight Ladder) |
| `mop_retire_after` | `ape.mopRetireAfter` | `MOP` sub-parameter, read under `distance` only |
| `mop_launcher_dmax` | `ape.mopLauncherDmax` | `MOP` sub-parameter, read under `distance` only |
| `mop_coin_percentage` | `ape.mopCoinPercentage` | `MOP_COIN` activation (MOP); `p_M`, jar default 1.0 |
| `mop_coin_ledger_max_interactions` | `ape.mopCoinLedgerMaxInteractions` | `MOP_COIN` sub-parameter; the coin's picks per (activity, widget) key, values below 1 read as 1; the paired jar's default is 4 (calibration v6 F1) and no cell states it, so the key serves DSL ablations |
| `llm_url` | `ape.llmUrl` | `LLM` dependency; required on both LLM cells (INV-APV-38) |
| `llm_on_new_state` | `ape.llmOnNewState` | `LLM_NEW_STATE` activation |
| `llm_on_stagnation` | `ape.llmOnStagnation` | `LLM_STAGNATION` activation |
| `llm_model` | `ape.llmModel` | `LLM` sub-parameter |
| `llm_temperature` | `ape.llmTemperature` | `LLM` sub-parameter |
| `llm_top_p` | `ape.llmTopP` | `LLM` sub-parameter |
| `llm_top_k` | `ape.llmTopK` | `LLM` sub-parameter |
| `llm_timeout_ms` | `ape.llmTimeoutMs` | `LLM` sub-parameter |
| `llm_percentage` | `ape.llmPercentage` | `LLM_COIN` activation; `p_L`, the LLM block states 0.9 |
| `llm_prompt_variant` | `ape.llmPromptVariant` | `LLM` sub-parameter |
| `llm_max_tokens` | `ape.llmMaxTokens` | `LLM` sub-parameter |
| `llm_snap_tolerance_px` | `ape.llmSnapTolerancePx` | `LLM` sub-parameter |
| `llm_boundary_top_pct` | `ape.llmBoundaryTopPct` | `LLM` sub-parameter |
| `llm_gate_min_actions` | `ape.llmGateMinActions` | `LLM` sub-parameter; `0` leaves the gate unmounted |
| `llm_breaker_failures` | `ape.llmBreakerFailures` | `LLM` sub-parameter; `0` leaves the gate unmounted |
| `llm_breaker_open_ms` | `ape.llmBreakerOpenMs` | `LLM` sub-parameter |
| `corpus_basis` | `ape.corpusBasis` | deployment provenance, echoed into `RUN_START` and read nowhere ("Corpus Basis Provenance") |

Two entries leave the table because the jar retires their keys, and a properties file carrying either now aborts
with `retired_key`: `mop_target_pick_cap` (`ape.mopTargetPickCap`, replaced by
`ape.mopCoinLedgerMaxInteractions`, the MOP coin's budget of picks per activity and widget) and `least_visited_priority_tiebreak` (`ape.leastVisitedPriorityTiebreak`, replaced by the scorer-sum tie X1,
which equals APE with zero scorers). Thirteen enter, so the table goes from 56 to 67 entries: the four group keys,
the MOP coin dose and its ledger budget, the three LLM gate parameters, and four existing jar keys the table lacked
(`activity_stable_restart_threshold`, `take_screenshot_for_every_step`, `save_gui_tree_to_xml_every_step`,
`llm_boundary_top_pct`). The jar then retired `ape.llmPercentageNoSubstrate` (ape `isolate-guidance-groups`
D-B24: it never had a consumer), so `llm_percentage_no_substrate` left the table, which then held 66 entries. The
jar on the `ape` master replaced `ape.mopWeightD1..D3` with the list `ape.mopWeights` and retired the three keys, so
`mop_weight_d1`, `mop_weight_d2` and `mop_weight_d3` left the table and `mop_weights` entered it, which holds 64
entries. `ape.variant` and
`ape.staticDataPath` are not in the table: the tool writes them from the variant and from the push, never from an
override, so an operator cannot set either through the DSL. The jar has no launcher-mode key, no X1 key and no
X3/X4 key (the cadence is fixed and the MOP variant of each extension point is mounted with MOP), so the table
carries none.

A key the jar does not recognise is not inert. Under stage-2 resolution an unknown key, a
retired key, or a non-neutral value of an inactive feature aborts before step 1 — which is what makes
the mapping's contents a correctness property rather than a tidiness one.

#### Scenario: Preset and variant lines come first
- **WHEN** `_push_properties()` is called for `as_mop_llm` with the artifact pushed
- **THEN** the first line SHALL be `ape.preset=as_mop_llm` and the second `ape.variant=as_mop_llm`
- **AND** the third SHALL be `ape.staticDataPath=/data/local/tmp/mop-artifact.json`
- **AND** the fourth and last line SHALL be `ape.llmUrl=http://10.0.2.2:30000/v1`

#### Scenario: Base cell writes two lines
- **WHEN** `_push_properties()` is called for the `base` variant
- **THEN** the file SHALL contain exactly `ape.preset=base` and `ape.variant=base`
- **AND** it SHALL NOT contain `ape.staticDataPath`, `ape.mopDataPath` or any `ape.llm*` line

#### Scenario: The default variant runs as base
- **WHEN** `_push_properties()` is called for `aperv` with no variant, which resolves `default`
- **THEN** the file SHALL contain exactly `ape.preset=base` and `ape.variant=base`

#### Scenario: Bools are serialized lowercase
- **WHEN** `_push_properties()` is called for `aperv:as@heuristic_input=False`
- **THEN** the file SHALL contain `ape.heuristicInput=false`, not `False`

#### Scenario: Unmapped override key aborts before push
- **WHEN** a variant's `overrides` contains `mop_coin_percentag` (a typo absent from `APERV_PROPERTY_MAPPING`)
- **THEN** `ConfigurationError` SHALL be raised naming the key
- **AND** no `adb push` SHALL have been issued

#### Scenario: The mapping holds the group-isolation vocabulary
- **WHEN** `APERV_PROPERTY_MAPPING` is inspected after this change
- **THEN** it SHALL contain exactly 64 entries
- **AND** it SHALL contain `addons`, `static`, `mop`, `llm`, `mop_coin_percentage`,
  `mop_coin_ledger_max_interactions`, `llm_gate_min_actions`,
  `llm_breaker_failures`, `llm_breaker_open_ms`, `activity_stable_restart_threshold`,
  `take_screenshot_for_every_step`, `save_gui_tree_to_xml_every_step`, `llm_boundary_top_pct` and `mop_weights`
- **AND** it SHALL NOT contain `mop_target_pick_cap`, `least_visited_priority_tiebreak`, `mop_weight_activity`,
  `step_telemetry_enabled`, `llm_percentage_no_substrate`, `mop_weight_d1`, `mop_weight_d2`, `mop_weight_d3`,
  `variant` or any key mapping to `ape.mopDataPath` or `ape.staticDataPath`

#### Scenario: Python-only keys are still excluded
- **WHEN** `_push_properties()` is called for `aperv:as_mop@seed=42`, whose `_tool_config` carries
  `strategy`, `static_data` and `seed`
- **THEN** the properties file SHALL contain none of those three names

#### Scenario: A dose ablation writes the dose
- **WHEN** `_push_properties()` is called for `aperv:as_mop_llm@llm_percentage=0.7` with the artifact pushed
- **THEN** the file SHALL contain `ape.llmPercentage=0.7`
- **AND** it SHALL contain no `ape.mopCoinPercentage` line, because the cell takes the MOP block's 1.0

### Requirement: MOP Artifact Projection and Handler Table (FR04, FR05, FR06, FR19)

`derive_mop_artifact.derive(document)` SHALL produce a `formatVersion: 2` artifact containing exactly
the projection the explorer consumes. Format 2 keeps every format-1 member with its meaning (except the
A′ source-3 constructor exclusion of "MOP-Activity Sets and OPTIONSMENU Records") and adds item 9,
which is the wire contract of the `ape` change `llm-coordinate-single-base` (its design D15 and its
`static-analysis-entrypoints` delta). The jar of that change reads format 2 only, and earlier jars
read format 1 only, so the two sides ship together.

1. **Scalars**: `package` and `mainActivity` copied verbatim from the full JSON.
2. **Provenance**: `source.digest` (`"sha256:" + hex` of the full-JSON bytes), `source.file`
   (basename) and `source.generator` (`"aperv-derive/2"`).
3. **Widgets** (`widgets.<baseActivity>.<shortId>`): a per-normalized-eventType `mop` map with values
   `none|direct|transitive|both`, plus the consumed metadata fields `inputType`, `hint`, `prompt`,
   `spinnerMode`, `contentDescription`, `tooltipText` and `entries`, each emitted only when non-empty,
   plus the distance map `dist` of item 9.
   A widget SHALL be emitted only when it is MOP-flagged OR carries at least one metadata field. The
   keys `id`, `type`, `text` and the raw `listeners` array SHALL NOT be emitted. Map keys SHALL be
   pre-normalized (lowercased, `_` and `-` removed), matching the query-side normalization.
4. **Activity sets**: `mopActivities` (widget-derived, per INV-DRV-02 and the dialog promotion of
   INV-DRV-03) and `mopActivitiesAugmented` (the A′ union, without activity constructors in source 3),
   both always emitted so the on-device
   `mopActivitySourceComponents` flag keeps selecting between them at run time.
5. **OPTIONSMENU records**: `optionsMenus: [{activity, hasFlaggedWidget}]`, where `hasFlaggedWidget`
   is true when any widget of that menu window is MOP-flagged — tested over the window's parsed
   widgets, before the empty-id drop, for the same reason INV-DRV-02 states.
6. **WTG**: `wtg.<sourceBaseActivity> = [{widget, target}]` per INV-DRV-03. `widgetClass` SHALL NOT be
   emitted.
7. **Components**: `activities[]` (`className`, `isMain`, `permission`, `reachesMop`,
   `deepLinkUri`), `receivers[]`/`services[]` (adding `intentFilters`, plus the boolean
   `hasTargetMethods`), `providers[]` (adding `authorities`). `reachesMop` is the wire rename of
   `reachesTarget`. Every component of the document SHALL be projected, whatever its `reachesTarget`:
   the jar's component trigger is a STATIC member and its pool reads no MOP data (`ape` D-B13), so a
   receiver, service or provider left off the wire is one the trigger can never fire.
   Each `intentFilters[]` entry SHALL carry `actions` and `categories`, and SHALL carry a reduced
   `data` member `{"schemes": […], "hosts": […], "paths": […], "pathPrefixes": […], "mimeTypes": […]}`,
   taken from the producer's `data` block. A list that is empty SHALL be omitted, and `data` SHALL be
   omitted when all five are empty. The member exists because a receiver or service that filters on a
   scheme or a MIME type matches no intent built from its action alone, so without it the trigger
   fires intents that the platform never delivers. The jar builds one intent from the first scheme,
   host and MIME type, and from the first path, or the first path prefix when the filter declares no
   path, which is why `pathPrefixes` travels and `ports` and `pathPatterns` SHALL NOT be emitted: a
   port is not part of the intent's matching data the jar sets, and a pattern is not a literal path.
   The member is additive: the artifact stays `formatVersion: 2`, and the jar reads its absence as
   "no data". `readPermission`, `writePermission`, the `targetMethods` signature list and `exported`
   SHALL NOT be emitted.
   `exported` is on that list because no consumer reads it and none may: the jar's activity launcher
   is required to ignore export status (the dispatch runs from uid 2000 and opens non-exported
   activities), so keeping the field on the wire would ship a value whose only possible use is
   forbidden.
8. **Stats**: `windows`, `widgetsTotal`, `flagged`, `droppedFlaggedNoId`, `orphanDialogs`,
   `handlersUnmatched`, `syntheticLambda`, `recovered`, `wtgEdges`, `dedupedTransitions`.
   `widgetsTotal` and `flagged` SHALL count the widget map after the dialog merge and before the
   emission filter of item 3, so they remain the numbers the jar's load record reported. Format 2
   adds no counter: the jar's load record reports `targets`, the size of `handlers` and the pairs it
   drops.
9. **Targets and distances** (format 2):
   - **`targets`**: the number of entries of the document's `distanceTargets` (direct targets C,
     followed by boundary targets B \ C; `analysis` spec, `distanceTargets`). Every pair `[i, d]` of
     the artifact SHALL satisfy `0 ≤ i < targets` (INV-DRV-10). No signature and no `kind` is
     emitted: the jar weighs boundary targets as direct ones. A document without `distanceTargets`
     yields `targets: 0` and no pair; nothing refuses it (gh120 design D9 left the September
     artefacts to the corpus hand-off).
   - **The distance of a method.** A method's distance to target `i` is its `targetDistances` entry
     for `i`: 0 when the method is the target, from 1 to the document's horizon otherwise (its `distMax`, 10 when
     it carries none); a target
     absent from its entries is unreachable. An entry that is not a pair of integers, whose index is
     outside `[0, targets)` or whose distance is negative is skipped, like any malformed entry inside
     a well-typed section. A method the producer marks reaching and gives no `targetDistances` is
     one whose every target is beyond the document's horizon: gh120 computes reach without a depth
     bound and distances with the cut. It has flags and no distance, and the derive does not invent
     one, so a widget or handler whose reaching methods are all that far is flagged and carries no
     pair. Under `distance` scoring that is the weight the exact distance would give, since a target
     beyond the cut gives none.
   - **The distance of a handler.** A listener's handler SHALL resolve to its method by the same
     exact signature join that gives its flags (INV-DRV-01, INV-DRV-09). A D8 synthetic-lambda wrapper
     absent from that index SHALL resolve by the same class recovery, and its distance to `i` is the
     minimum over the enclosing class's reaching `lambda$…` methods. A listener whose flags come from
     the producer-precedence tier (`handlerReachesTarget`/`handlerDirectlyReachesTarget`) still takes
     its distances from the join, because the producer supplies no distance.
   - **Per widget, `dist: {<event>: [[i, d], …]}`**, beside `mop`, under the same normalized event keys:
     for each target, the minimum over the widget's handlers for that event. A null-event listener
     contributes to the `""` key exactly when `mop` carries `""`. On a `shortId` collision
     (INV-DRV-02) and in the dialog merge (INV-DRV-03) the flags keep the strongest-flag rule while
     the `dist` maps of both widgets SHALL merge by the minimum distance per target.
   - **Per activity, `activityDist: {<base activity>: [[i, d], …]}`**: for each target, the minimum over
     the pairs of every widget of the activity, all events, after the dialog merge and including the
     widgets the empty-short-id rule keeps off the wire, and over the `targetDistances` of the methods
     of the activity's own class (the `reachability[]` entries with `componentType == "activity"` whose
     base name is the activity) **except that class's `<init>` and `<clinit>`**. Launching any activity
     runs its own constructor, and gh120 keeps every activity constructor as a boundary target (its
     D12), so without the exclusion every activity would sit at `d = 0`. A dialog's activity pairs
     move to its host with its widgets.
   - **`handlers: {<binary class name>: {mop: {<event>: flag}, dist: {<event>: [[i, d], …]}}}`**: one
     record per `reachability[]` class that declares a handler method. The handler methods, matched by
     name and parameter list in the method's signature, are `onClick(android.view.View)`, which fills
     `click`; `onLongClick(android.view.View)`, which fills `longclick`; and `java.lang.Object invoke()`
     and `java.lang.Object invoke(java.lang.Object)`, which fill both. A Compose node's stamp is the
     class of a `Function0`, and a toggleable's is the class of its `onValueChange`, a `Function1`
     (`instrumentation` INV-INS-178); the node's extras key, not the method, tells the event.
     The app callbacks that a library dispatcher calls — `onOptionsItemSelected`,
     `onNavigationItemSelected`, `onMenuItemClick`, `onMenuItemSelected`, `onPreferenceClick`,
     `onPreferenceTreeClick`, `onPreferenceChange` and `onClick(android.content.DialogInterface,int)` —
     are not handler methods and fill no event (INV-DRV-11), although the View stamp names their class
     in `rvsec.click` (`instrumentation` INV-INS-181). In the e03igg4 campaign these menu, navigation,
     preference and dialog targets took 798 MOP coin steps in `mop` (11 % of the coin's steps, 90 tasks,
     33 APKs) and no MOP misuse followed any of them, nor any of 800 in `as_mop`; leaving their class
     unlisted gives them no MOP information, for the coin and for SATA's MOP weight alike. The table
     cannot carry the family of a handler, only its class, which is why the cut is made here and not in
     the jar. **Known limit:** the stamp names a class, not a method, so a class that declares one of
     these callbacks and also a View handler method stays listed, and a tap stamped with it reads the
     View handler's record; on the e7 corpus this is 9 of 3109 classes declaring such a callback, in 8
     APKs.
     `<init>` and `<clinit>` are never handler methods. An event's flag is derived from the method's
     own `directlyReachesTarget`/`reachesTarget` on INV-DRV-01's two axes, and its pairs are the
     method's distances; two methods filling one event OR their flags and merge their pairs by the
     minimum per target. A class whose handler methods reach nothing SHALL still be listed, with
     `none` for each of its events and no `dist`: on the device a listed class states that the
     stamped handler reaches no target. The key is the class's binary name as `reachability[].className`
     writes it, which is the `Class.getName()` form gh121 stamps.
   - **Cut, order, omission** (INV-DRV-10). A widget's and a handler's pair list SHALL keep every
     target at `d ≤ cut` and drop every pair beyond it, where `cut` is `derive()`'s argument, 3 by
     default (Requirement: Weighed Cut Follows the Weight Ladder). These are the lists that weigh an
     action, and the jar gives no weight beyond the length of its ladder `ape.mopWeights`, 3 by default. Under the three-pair cut, 4,024 of the 21,485
     targets at `d ≤ 3` of some widget or handler list (18.7 %) sat at `d ≤ 3` in no list after the
     cut, so they could never weigh an action or retire (`ape` D15, amendment of 2026-10-09,
     measured on the 163 round-A gh120 documents). An `activityDist` list SHALL keep the three pairs
     of smallest `d`, because the launcher only orders the activities the census already makes
     eligible. Every list is sorted by `d` ascending, then `i` ascending, and merges are applied to
     the full per-target minima before the cut; an activity starts from its widgets' uncut minima.
     An event with no pair after the cut SHALL have no key in a `dist` map, and an empty `dist` map
     and an `activityDist` entry with no pair SHALL be omitted. `targets` and `handlers` SHALL always
     be emitted, `0` and `{}` when empty. The widget emission filter of item 3 is unchanged: pairs do
     not make an unflagged, metadata-less widget emitted.

Derivation preconditions: the document is an object, carries a non-null `package`, and every section
it does carry is of the expected type; otherwise `DerivationError`. The producer's `"complete": true`
sentinel is NOT a precondition (INV-DRV-08). A document written by the producer's first pass — valid
JSON with populated `reachability` and `windows` per INV-ANA-20, and an empty `transitions` array —
SHALL yield an artifact whose `wtg` is empty, which the device reads through `MopData.hasWtgData()`
to disable the WTG-dependent scoring passes on its own. Structural corruption from a write interrupted
mid-pass is caught earlier, by the parse in `_derive_mop_artifact()`, because the producer truncates
its output file on open and cannot leave a parseable stale tail.

#### Scenario: cryptoapp derivation matches the known ground truth
- **WHEN** `derive()` runs on the test fixture `cryptoapp.apk.json`, a byte copy of the gh120
  baseline `modules/rv-static-analysis/tests/resources/cryptoapp.apk.json` (the gh120 producer
  output for `br.unb.cic.cryptoapp`), where the Execute button's wrapper
  `CryptographyActivity$$ExternalSyntheticLambda0.onClick` carries `reachesTarget: true`
- **THEN** `mopActivities` SHALL equal
  `{MessageDigestActivity, CipherActivity, CryptographyActivity}` (base names).
  `CryptographyActivity` enters through the exact join: the producer links the wrapper to its own
  `lambda$setupExecuteButton$0` body (`analysis` INV-ANA-77), so the wrapper is listed reaching and
  the class recovery is not consulted (INV-DRV-09)
- **AND** `optionsMenus` SHALL contain the `MainActivity` record, and `wtg` SHALL carry the click
  edges from `MainActivity` to all three MOP sub-activities
- **AND** `components.activities` SHALL have 4 entries and `components.providers` 1 entry with
  `authorities == "br.unb.cic.cryptoapp.androidx-startup"`, every component `reachesMop == false`
- **AND** `stats.windows` SHALL be 5, `stats.flagged` 3 and `stats.recovered` 0
- **AND** `formatVersion` SHALL be 2, `source.generator` `"aperv-derive/2"` and `targets` 27 (23 direct
  targets, then the 4 activity constructors as boundary targets)
- **AND** the `click` pairs SHALL be `[[22,2]]` for `buttonGenerateHash` and `[[16,3],[17,3],[18,3]]`
  for `executeButton`, the three of its wrapper's ten pairs at `d ≤ 3`
- **AND** `btn_cipher_encrypt` SHALL be emitted with `mop == {"click": "transitive"}` and no `dist`,
  because its handler `CipherActivity$1.onClick` reaches its two targets only at `d = 4`
- **AND** `handlers` SHALL have exactly two keys: `br.unb.cic.cryptoapp.cipher.CipherActivity$1` and
  `br.unb.cic.cryptoapp.generated.CryptographyActivity$$ExternalSyntheticLambda0`, each with
  `mop == {"click": "transitive"}`, the second carrying `dist == {"click": [[16,3],[17,3],[18,3]]}`
  and the first no `dist`; `br.unb.cic.cryptoapp.MainActivity` (its
  `onOptionsItemSelected(android.view.MenuItem)`) and `br.unb.cic.cryptoapp.MainActivity$1` (its
  `onMenuItemClick(android.view.MenuItem)`) SHALL NOT be keys, because those callbacks are not handler
  methods (INV-DRV-11)
- **AND** `activityDist` SHALL be exactly `{CipherActivity: [[0,2],[1,2]], CryptographyActivity:
  [[12,0],[13,0],[14,0]], MessageDigestActivity: [[22,2]]}` (fully qualified keys), with no entry
  for `MainActivity`, whose only reaching method is its own constructor

#### Scenario: absent sentinel does not stop derivation
- **WHEN** `derive()` runs on a document with a valid `package`, well-typed sections, `transitions: []`
  and no `complete` key
- **THEN** an artifact SHALL be returned
- **AND** `artifact["wtg"]` SHALL equal `{}` and `artifact["stats"]["wtgEdges"]` SHALL equal `0`
- **AND** `mopActivities`, `optionsMenus` and `widgets` SHALL be derived from `reachability` and
  `windows` exactly as they would be with the sentinel present

#### Scenario: false sentinel does not stop derivation
- **WHEN** `derive()` runs on the same document with `complete: False` written explicitly
- **THEN** the emitted artifact SHALL be byte-identical to the one derived with the key absent

#### Scenario: missing package still refuses
- **WHEN** `derive()` runs on a document carrying `complete: True` and no `package` key
- **THEN** `DerivationError` SHALL be raised
- **AND** no artifact SHALL be returned

#### Scenario: malformed section still refuses
- **WHEN** `derive()` runs on a document whose `reachability` is the integer `7` instead of a list
- **THEN** `DerivationError` SHALL be raised
- **AND** no artifact SHALL be returned

#### Scenario: no Target vocabulary and no call graph on the wire
- **WHEN** an artifact is generated from a document declaring receivers and services
- **THEN** the only key containing `Target` anywhere in it SHALL be `hasTargetMethods` (the lowercase
  `targets` does not match)
- **AND** it SHALL contain no `reachability`, `windows`, `transitions`, `listeners` or
  `distanceTargets` section, and no string in the shape of a Soot method signature (INV-DRV-06)
- **AND** the check SHALL be exercised against components, not only against a fixture whose
  component lists are empty

#### Scenario: unflagged metadata-less widgets are projected away
- **WHEN** a widget has no MOP-reaching listener and none of `inputType`, `hint`, `prompt`,
  `spinnerMode`, `contentDescription`, `tooltipText`, `entries`
- **THEN** the artifact SHALL NOT contain that widget
- **AND** an unflagged widget carrying a non-empty `hint` SHALL be emitted, because typed input reads it

#### Scenario: stats count the map, not the wire
- **WHEN** a base activity holds 40 widgets after the dialog merge, of which 2 are flagged and 35 are
  unflagged and metadata-less
- **THEN** `stats.widgetsTotal` SHALL be 40 and `stats.flagged` SHALL be 2
- **AND** the emitted `widgets` map for that activity SHALL contain 5 entries

#### Scenario: a widget's distance is the minimum over its handlers, every target within three calls
- **WHEN** a widget's two `click` listeners resolve to methods with `targetDistances`
  `[[2,3],[5,1],[7,4],[8,3]]` and `[[2,2],[9,6],[11,1],[12,3]]`
- **THEN** its `dist` SHALL be `{"click": [[5,1],[11,1],[2,2],[8,3],[12,3]]}`, five pairs
- **AND** target 2 SHALL appear once, at the smaller distance 2
- **AND** targets 7 (`d = 4`) and 9 (`d = 6`) SHALL NOT appear

#### Scenario: a deeper cut keeps the farther targets
- **WHEN** the same widget is derived with `derive(document, cut=6)`
- **THEN** its `dist` SHALL be `{"click": [[5,1],[11,1],[2,2],[8,3],[12,3],[7,4],[9,6]]}`

#### Scenario: a widget whose targets are all four calls or more away carries no pair
- **WHEN** a widget's only `click` listener resolves to a method reaching a target, flagged
  `transitive`, with `targetDistances` `[[0,4],[1,5]]`, and its activity has no other pair
- **THEN** the widget SHALL be emitted with `mop == {"click": "transitive"}` and no `dist`
- **AND** its activity's `activityDist` SHALL be `[[0,4],[1,5]]`, because an activity starts from its
  widgets' uncut minima

#### Scenario: activityDist keeps the three nearest targets
- **WHEN** an activity's widgets carry the `click` pairs `[[1,0],[2,1]]` and `[[3,1],[4,2]]`, and its
  own class's methods carry none
- **THEN** its `activityDist` SHALL be `[[1,0],[2,1],[3,1]]`
- **AND** each widget SHALL keep its own two pairs

#### Scenario: an unlisted wrapper takes its distances from the recovered lambdas
- **WHEN** a click handler `<com.example.MainActivity$$ExternalSyntheticLambda0: void onClick(android.view.View)>`
  is absent from `reachability[]`, and `com.example.MainActivity` has reaching `lambda$onCreate$0`
  with `targetDistances [[4,2]]` and `lambda$onCreate$1` with `[[4,1],[6,3]]`
- **THEN** the widget's `click` pairs SHALL be `[[4,1],[6,3]]`

#### Scenario: colliding widgets merge their distances by the minimum
- **WHEN** two widgets of one base activity share `shortId == "submit"`, the first `direct` on `click`
  with pairs `[[3,0]]`, the second `transitive` with `[[3,1],[5,2]]`
- **THEN** the emitted entry SHALL carry the `direct` flag and the `click` pairs `[[3,0],[5,2]]`

#### Scenario: an activity's own constructor does not count toward its distance
- **WHEN** the only methods of activity class `com.example.A` carrying `targetDistances` are
  `<init>` with `[[23,0]]` and `onResume` with `[[2,5]]`, and its widgets carry no pair
- **THEN** `activityDist["com.example.A"]` SHALL be `[[2,5]]`
- **AND** with `onResume` reaching nothing, `com.example.A` SHALL have no `activityDist` entry

#### Scenario: the handler table lists a class that reaches nothing
- **WHEN** `reachability[]` lists `com.example.ui.ScreenKt$Body$1$1` with one method
  `<com.example.ui.ScreenKt$Body$1$1: java.lang.Object invoke()>`, `reachesTarget: false`
- **THEN** `handlers["com.example.ui.ScreenKt$Body$1$1"]` SHALL be
  `{"mop": {"click": "none", "longclick": "none"}}`, with no `dist`
- **AND** a class declaring `invoke(java.lang.Object)` reaching target 3 at distance 2 SHALL carry
  `dist == {"click": [[3,2]], "longclick": [[3,2]]}`

#### Scenario: a document without distances derives with no target
- **WHEN** `derive()` runs on a well-typed document with no `distanceTargets` key and no
  `targetDistances` on any method
- **THEN** an artifact SHALL be returned with `targets == 0`, `handlers` listing the handler classes
  with flags only, no `dist` on any widget and no `activityDist` entry

#### Scenario: a receiver's intent filter keeps its reduced data
- **WHEN** a document declares a receiver whose `intentFilters` are
  `[{"actions": ["android.intent.action.VIEW"], "categories": [], "data": {"schemes": ["myapp"], "hosts": ["x.org"], "ports": ["80"], "paths": [], "pathPrefixes": ["/a"], "pathPatterns": [], "mimeTypes": ["text/plain"]}}]`
- **THEN** the projected filter SHALL be
  `{"actions": ["android.intent.action.VIEW"], "categories": [], "data": {"schemes": ["myapp"], "hosts": ["x.org"], "pathPrefixes": ["/a"], "mimeTypes": ["text/plain"]}}`
- **AND** it SHALL carry no `ports`, `paths` or `pathPatterns` key
- **AND** a filter whose `data` lists are all empty SHALL carry no `data` member
- **AND** `formatVersion` SHALL still be 2

#### Scenario: components that reach no target are still projected
- **WHEN** a document declares two receivers and one service, all with `reachesTarget: false`
- **THEN** `components.receivers` SHALL have 2 entries and `components.services` 1, each with `reachesMop == false`

#### Scenario: the app callbacks behind library dispatchers are not handler methods
- **WHEN** `reachability[]` lists `com.example.app.MainActivity` whose only method is `<com.example.app.MainActivity: boolean onOptionsItemSelected(android.view.MenuItem)>` at distance 2 from target 0, `com.example.app.SettingsFragment$$ExternalSyntheticLambda5` whose only method is `<...: boolean onPreferenceClick(androidx.preference.Preference)>` at distance 1 from target 1, and `com.example.app.Dialogs$$ExternalSyntheticLambda3` whose only method is `<...: void onClick(android.content.DialogInterface,int)>` at distance 3 from target 0
- **THEN** `handlers` SHALL have none of the keys `com.example.app.MainActivity`, `com.example.app.SettingsFragment$$ExternalSyntheticLambda5` and `com.example.app.Dialogs$$ExternalSyntheticLambda3`

#### Scenario: a class with a view listener and an options-menu callback keeps only the view listener
- **WHEN** `com.example.app.MainActivity` declares `onClick(android.view.View)` at distances `{0: 3}`, reaching no target directly, and `onOptionsItemSelected(android.view.MenuItem)` at distances `{0: 1, 2: 2}`, reaching target 0 directly
- **THEN** `handlers["com.example.app.MainActivity"]` SHALL carry `dist.click == [[0, 3]]`
- **AND** its `click` flag SHALL be the one of `onClick(android.view.View)` alone, `transitive`

### Requirement: ApeRVTool Configuration (FR19)

`ApeRVTool.configure(config)` SHALL store the resolved variant configuration in `self._tool_config`
after validation. It SHALL validate that `config["strategy"]` is one of `["sata", "random"]`, that
`config["preset"]` and `config["variant"]` are present and non-empty, and that `config.get("overrides", {})` is a
dict. If any check fails, it SHALL raise `ConfigurationError` before any device interaction.

**Tool-DSL overrides SHALL be folded into `overrides`** (INV-APV-39). `ToolFactory` merges
`{**variant_config, **tool_config.parameters}` (`modules/rv-tools/src/rv_tools/registry/factory.py:127`),
so a DSL override written as `aperv:as_mop@mop_coin_percentage=0.5` arrives as a **top-level** key,
while `_push_properties()` reads only `overrides`. `configure()` SHALL therefore move every top-level
key that has an `APERV_PROPERTY_MAPPING` entry into `overrides`, where a DSL value takes precedence
over a variant's own entry for the same key — the DSL is the operator's last word, which is what makes it
useful for smokes and ablations without declaring a variant.

Any remaining top-level key that is neither mapped nor one of `preset`, `variant`, `overrides`, `strategy`,
`static_data`, `broadcast_catalog`, `seed`, `device_port`, `device_serial`, `device_id` SHALL raise
`ConfigurationError` naming it.
`expected_jar_git_sha` and `expected_jar_sha256` are not on that list and SHALL therefore be rejected like any
other unhonourable key, which is what stops the retired declaration from being reintroduced through experiment
YAML (INV-APV-59). `mop_data` is not on the list either: it was renamed `static_data` because the `as` cell pushes
the artifact with MOP off, and an experiment YAML that still names it SHALL fail loudly rather than run a cell
without its data. Without both halves of this rule a DSL override would be discarded in silence: no property line,
no error, and a run executing a configuration nobody asked for. A key that cannot be honoured fails loudly.

The three device keys are the platform's own injection, not an operator's: `ExecutionController`
adds `device_port`, `device_serial` and `device_id` to every tool's parameters whenever
`--device-port` is set, so every containerized and parallel run carries them. They address a device
rather than configure the jar — `execute_tool_specific_logic()` takes the serial from
`task.config.device_id` — so `configure()` SHALL accept and ignore them, and they SHALL never reach
`ape.properties`.

**Unmappable `overrides` keys SHALL be rejected in `configure()`**, not at push time. `_push_properties()`
runs after the jar, the broadcast catalog and the derived artifact have been pushed, so a check
living there would already have cost three pushes and a derivation. Validating in `configure()` puts
one rule over both sources of an override key — a variant's own dict and the DSL keys just folded into
it — and is what makes "before any `adb push`" true as written.

The strategy whitelist is `["sata", "random"]`. `bfs` and `dfs` are not agent types: `ApeAgent.createAgent`
recognises `sata`, `random` and `replay` and nothing else, so accepting them Python-side would let a run pass local
validation only to fail on the emulator. `replay` is legal in the jar but SHALL NOT be accepted here: it requires
`--ape-replay <log>`, which this tool never passes.

The `APERV_LLM_BASE_URL` environment variable redirects the LLM cells to another endpoint without a variant
change, which Docker and physical-device setups need because `10.0.2.2` is the emulator's alias for the host.
`configure()` SHALL NOT read it (INV-TOOL-20). The `rv-experiment` entry point reads it and places the value in the
`aperv` LLM cells' `ToolConfig.parameters` as `llm_url` (experiment "aperv LLM URL Resolved at the Entry Point").
The factory merges it at the top level, and the DSL fold above moves it into `overrides`, where it replaces the
cell's default. A `@llm_url` written in the tool DSL is the operator's explicit value and wins over the variable.
The cells without the LLM group never receive it (INV-APV-09).

#### Scenario: Valid preset arm configured
- **WHEN** `configure({"strategy": "sata", "preset": "mop", "variant": "mop", "static_data": "static_analysis", "overrides": {}})` is called
- **THEN** `self._tool_config["preset"]` SHALL equal `"mop"` and `self._tool_config["variant"]` SHALL equal `"mop"`
- **AND** no exception SHALL be raised

#### Scenario: Missing preset raises ConfigurationError
- **WHEN** `configure({"strategy": "sata", "variant": "base"})` is called
- **THEN** `ConfigurationError` SHALL be raised naming the missing `preset` key

#### Scenario: Missing variant raises ConfigurationError
- **WHEN** `configure({"strategy": "sata", "preset": "base", "overrides": {}})` is called
- **THEN** `ConfigurationError` SHALL be raised naming the missing `variant` key
- **AND** no `adb push` SHALL have been issued

#### Scenario: Invalid strategy raises ConfigurationError
- **WHEN** `configure({"strategy": "unknown", "preset": "base", "variant": "base"})` is called
- **THEN** `ConfigurationError` SHALL be raised with a message listing valid strategies

#### Scenario: Retired strategy rejected before the device
- **WHEN** `configure({"strategy": "bfs", "preset": "base", "variant": "base"})` or the same with `"dfs"` is called
- **THEN** `ConfigurationError` SHALL be raised before any device interaction
- **AND** the run SHALL NOT reach the jar, where an unknown `--ape` value aborts

#### Scenario: Non-dict overrides rejected
- **WHEN** `configure({"strategy": "sata", "preset": "as", "variant": "as", "overrides": ["frontier_boost_weight"]})`
  is called
- **THEN** `ConfigurationError` SHALL be raised naming the `overrides` key

#### Scenario: The renamed data key is rejected under its old name
- **WHEN** `configure({"strategy": "sata", "preset": "as", "variant": "as", "mop_data": "static_analysis", "overrides": {}})` is called
- **THEN** `ConfigurationError` SHALL be raised naming `mop_data`

#### Scenario: DSL override reaches the properties file
- **WHEN** `aperv:as_mop@mop_coin_percentage=0.5` is resolved and `configure()` runs
- **THEN** `self._tool_config["overrides"]["mop_coin_percentage"]` SHALL equal `0.5`
- **AND** `_push_properties()` SHALL write `ape.mopCoinPercentage=0.5`
- **AND** no top-level `mop_coin_percentage` key SHALL remain in `_tool_config`

#### Scenario: DSL override wins over the arm's own value
- **WHEN** `aperv:as_mop_llm@llm_url=http://192.168.0.36:30000/v1` is resolved, and the variant's `overrides`
  already carries `llm_url="http://10.0.2.2:30000/v1"`
- **THEN** the folded value SHALL be `"http://192.168.0.36:30000/v1"`
- **AND** exactly one `ape.llmUrl` line SHALL be written

#### Scenario: The platform's device addressing is accepted and never written

- **WHEN** a containerized run resolves `aperv:as_mop` with `--device-port 5554`, so
  `ExecutionController` has injected `device_port=5554`, `device_serial="emulator-5554"` and
  `device_id="emulator-5554"` at the top level
- **THEN** `configure()` SHALL accept the configuration without raising
- **AND** the generated `ape.properties` SHALL contain no line naming any of the three keys and no
  occurrence of the port value
- **AND** the variant SHALL still resolve as exactly `ape.preset=as_mop`, `ape.variant=as_mop` and
  `ape.staticDataPath`

#### Scenario: Unhonourable top-level key fails loudly
- **WHEN** `aperv:as_mop@mop_coin_percentag=0.5` is resolved (a typo absent from `APERV_PROPERTY_MAPPING`)
- **THEN** `ConfigurationError` SHALL be raised naming the key
- **AND** the key SHALL NOT be silently dropped, which would run the cell unchanged under an operator's
  belief that it had been overridden

#### Scenario: LLM URL override via environment variable
- **WHEN** `APERV_LLM_BASE_URL` is set to `"http://192.168.1.100:30000/v1"` and `rv-experiment run --tools aperv:as_llm` resolves the tool, so `ToolConfig.parameters` carries `llm_url="http://192.168.1.100:30000/v1"`
- **AND** the factory calls `configure({"strategy": "sata", "preset": "as_llm", "variant": "as_llm", "static_data": "static_analysis", "broadcast_catalog": True, "overrides": {"llm_url": "http://10.0.2.2:30000/v1"}, "llm_url": "http://192.168.1.100:30000/v1"})`
- **THEN** the effective `llm_url` SHALL be `"http://192.168.1.100:30000/v1"` and exactly one `ape.llmUrl` line SHALL carry it
- **AND** `configure()` called directly with the variable set and no top-level `llm_url` SHALL keep `"http://10.0.2.2:30000/v1"`, because the tool does not read the environment

### Requirement: ApeRVTool Cell Variants (FR20)

`ApeRVTool` SHALL define one variant per experimental cell and nothing else. Every variant SHALL consist of a
`preset` name, a `variant` name, an `overrides` dict, and Python-only orchestration keys (INV-APV-40).

`get_variants()` SHALL return exactly these **eight** names, carrying **seven** distinct configurations: the six
cells, `default`, and one ablation variant, `mop_nolaunch`:

| Variant | preset | static_data | broadcast_catalog | overrides | Groups mounted by the preset |
|---|---|---|---|---|---|
| `default` | `base` | — | — | _(empty)_ — bound to the same object as `base` (INV-TOOL-02) | — |
| `base` | `base` | — | — | _(empty)_ | — |
| `mop` | `mop` | `"static_analysis"` | — | _(empty)_ | MOP |
| `as` | `as` | `"static_analysis"` | `True` | _(empty)_ | ADDONS, STATIC |
| `as_mop` | `as_mop` | `"static_analysis"` | `True` | _(empty)_ | ADDONS, STATIC, MOP |
| `as_llm` | `as_llm` | `"static_analysis"` | `True` | `llm_url` | ADDONS, STATIC, LLM |
| `as_mop_llm` | `as_mop_llm` | `"static_analysis"` | `True` | `llm_url` | ADDONS, STATIC, MOP, LLM |
| `mop_nolaunch` | `mop` | `"static_analysis"` | — | `activity_trigger_enabled: False` | MOP without `MOP_LAUNCHER` |

Every variant carries `strategy="sata"` and `variant` equal to its own name; `default` carries `"base"`.

**What a cell means lives in the jar.** Each preset is the union of the jar's group blocks (the `ape` design's
§ "Group blocks and cells"): ADDONS is the former `aperv` vector, STATIC is the frontier at 200 plus typed input,
MOP is E6 arm 3's MOP configuration plus `p_M = 1.0`, LLM is E6 arm 4's sampling configuration with `p_L = 0.9`.
On a cell, `overrides` SHALL carry only what the jar cannot know, the server URL. No cell states a MOP parameter:
the MOP coin's ledger budget, the weight ladder, the retirement and the launcher cadence take the jar's defaults,
which on the paired jar are calibration v6's finalist F1, with the coin taking each (activity, widget) key up to
four times (author's decision, 2026-11-11). An unstated key of a mounted feature takes the jar's default, so the
same cell runs another budget on a jar with other defaults; the migration tier checks the default the cells rely
on (Requirement: Cell Configuration Matches the Jar's Cell Echo). A dose (`llm_percentage`,
`mop_coin_percentage`) or any other mapped key is an ablation, expressed through the tool DSL
(`aperv:as_mop@mop_coin_percentage=0.5`), and never as a new preset. The preset vocabulary belongs to the jar.

**An ablation that shares a container with its cell needs a name of its own.** The platform's resume identity is
`(apk, tool, variant, repetition, timeout)`, without the parameters (`rv-platform` "Skip Completed Tasks During
Resume"), and the result file names are built from the same fields. `aperv:mop` and `aperv:mop@k=2` in one
campaign would therefore be the same task: the second would be skipped as completed, or would overwrite the first.
An ablation run beside its cell is therefore a named variant: the cell's preset, its own `variant` name, and the
cell's `overrides` plus the ablated key. There is one such variant (author's decision, 2026-10-18), on the `mop`
cell, with one key added and nothing else. `mop_nolaunch` sets `ape.activityTriggerEnabled=false`,
which unmounts `MOP_LAUNCHER`: the launcher stage leaves the pipeline, and the null-tree recovery the launcher owns
goes with it, so the jar's recovery falls back to APE's. Every other MOP member runs as in `mop`; none depends on
the launcher. An ablation that never shares a container with its cell stays a DSL
parameter.

**The artifact follows the groups.** `static_data="static_analysis"` is set on every cell that mounts STATIC or
MOP, which is every cell except `base` (INV-APV-66). The `mop` cell reads the artifact with ADDONS and STATIC off;
the `as` cell reads it with MOP off, which is why the key and the jar property are named after the static data and
not after MOP (`ape` D-B2).

**The broadcast catalog follows STATIC.** Component triggering is a STATIC member, which the four `as*` presets
mount at `componentPercentage=0.03` (`ape` D-B13). Those four cells carry `broadcast_catalog=True`, so the catalog
reaches the device exactly where its only reader runs (INV-APV-10). The flag is set on the variant rather than
inferred from the preset name, because the Python side does not know what a preset mounts and does not branch on a
preset name.

**The variant name reaches the trace.** The tool writes `ape.variant=<variant>` (INV-APV-65). The jar echoes it as
`RUN_START.variant` outside the plan digest, so a trace names its cell without relying on the file name and two
cells with the same effective plan keep the same digest.

#### Deleted variants

The ten names below are deleted. None survives as an alias: the jar they configured is not the jar this tree
deploys, and a name that resolved would claim a configuration that no longer runs. Recorded results are
unaffected; campaigns recorded under these names resume from the frozen image whose `tool.py` still defines them
(`rvandroid:0.9.5`). The nearest cell is documentation only, not an equivalence: the cells differ from every old
arm at least in the MOP coin, the owner order of the step and the X1–X4 defaults.

| Deleted | What it was | Nearest cell |
|---|---|---|
| `sata` | APE-RV without MOP and without LLM (`aperv` preset) | `as` minus STATIC; no exact cell |
| `sata_mop` | `mop` preset, flag scoring | `as_mop` |
| `sata_llm` | `llm` preset | `as_llm` minus STATIC; no exact cell |
| `sata_mop_llm` | `llm_mop` preset | `as_mop_llm` |
| `mop_on_llm_off` | E3 reference, reach package | `as_mop` |
| `mop_off_llm_off` | E3 control and E6 arm 2, still reading static and MOP data | `as` |
| `mop_on_llm_70` | E3 LLM arm, `llm_percentage=0.7` | `as_mop_llm@llm_percentage=0.7` |
| `mopd_on_llm_off` | E6 arm 3, distance scoring | `as_mop` |
| `mopd_on_llm_90` | E6 arm 4 | `as_mop_llm` |
| `default` (old binding) | same object as `sata` | the name survives, rebound to `base` |

#### Scenario: The variant set is the six cells and default

- **WHEN** `get_variants()` is read
- **THEN** its keys SHALL be exactly `default`, `base`, `mop`, `as`, `as_mop`, `as_llm`, `as_mop_llm`,
  `mop_nolaunch`
- **AND** `get_variants()["default"] is get_variants()["base"]` SHALL be true
- **AND** none of `sata`, `sata_mop`, `sata_llm`, `sata_mop_llm`, `mop_on_llm_off`, `mop_off_llm_off`,
  `mop_on_llm_70`, `mopd_on_llm_off`, `mopd_on_llm_90`, `mop_k2` SHALL be a key

#### Scenario: Each cell names its own preset and itself

- **WHEN** any of the six cells `v` is read from `get_variants()`
- **THEN** `v["preset"]` SHALL equal its key and `v["variant"]` SHALL equal its key
- **AND** `v["strategy"]` SHALL be `"sata"`

#### Scenario: The base cell carries no data and no overrides

- **WHEN** `get_variants()["base"]` is read
- **THEN** `preset` SHALL be `"base"`, `overrides` SHALL be empty, and no `static_data` key SHALL be present

#### Scenario: Each cell carries the server URL or the ledger budget, and nothing else

- **WHEN** `get_variants()["as_mop_llm"]` is read
- **THEN** `overrides` SHALL be exactly `{"llm_url": "http://10.0.2.2:30000/v1"}`
- **AND** `get_variants()["as_llm"]["overrides"]` SHALL be exactly `{"llm_url": "http://10.0.2.2:30000/v1"}`
- **AND** the `base`, `mop`, `as` and `as_mop` cells' `overrides` SHALL be empty

#### Scenario: The MOP cells write the ledger budget

- **WHEN** `_push_properties()` runs for the `mop` cell with the artifact pushed
- **THEN** it SHALL write exactly `ape.preset=mop`, `ape.variant=mop` and
  `ape.staticDataPath=/data/local/tmp/mop-artifact.json`, in that order
- **AND** for the `as_mop_llm` cell the fourth and last line SHALL be `ape.llmUrl=http://10.0.2.2:30000/v1`
- **AND** without a DSL override, no variant's file SHALL contain `ape.mopCoinLedgerMaxInteractions`, `ape.mopWeights`,
  `ape.mopRetireAfter` or `ape.activityTriggerStagnationStep`

#### Scenario: The launcher ablation is the mop cell without its launcher

- **WHEN** `get_variants()["mop_nolaunch"]` is read
- **THEN** `preset` SHALL be `"mop"`, `variant` SHALL be `"mop_nolaunch"` and `strategy` SHALL be `"sata"`
- **AND** `overrides` SHALL be exactly `{"activity_trigger_enabled": False}`, the `mop` cell's plus one key
- **AND** every other top-level key SHALL equal the `mop` cell's
- **AND** `_push_properties()` with the artifact pushed SHALL write exactly `ape.preset=mop`,
  `ape.variant=mop_nolaunch`, `ape.staticDataPath=/data/local/tmp/mop-artifact.json` and
  `ape.activityTriggerEnabled=false`, in that order

#### Scenario: Every cell but base carries the static data

- **WHEN** the variants `mop`, `as`, `as_mop`, `as_llm`, `as_mop_llm`, `mop_nolaunch` are read
- **THEN** each SHALL carry `static_data="static_analysis"` at the top level
- **AND** none SHALL carry `mop_data`

#### Scenario: No variant carries a property expansion

- **WHEN** any variant returned by `get_variants()` is inspected
- **THEN** its top-level keys SHALL be drawn only from `preset`, `variant`, `overrides`, `strategy`,
  `static_data` and `broadcast_catalog`
- **AND** no variant SHALL carry `expected_jar_git_sha` or `expected_jar_sha256` (INV-APV-59)
- **AND** no variant SHALL carry `throttle_ms`, `llm_percentage` or `mop_coin_percentage` in its `overrides`

### Requirement: Cell Configuration Matches the Jar's Cell Echo (FR20, NFR06)

Each cell's configuration on the Python side SHALL be checked against what the jar resolves for it, on two levels
that answer different questions.

**Offline, against the jar source.** A test that reads the `ape` checkout `$APE_REPO` names (skipped without it,
like the other `tests/migration` checks) SHALL assert four things. The jar's preset vocabulary is exactly the six
cell names. Each preset is the union of the group blocks the cell names. The `RUN_START` fixture of each cell
(`src/test/resources/cells/<cell>.run_start.json`) carries `preset` and `variant` equal to the variant's own
`preset` and `variant`. No MOP variant states `mop_coin_ledger_max_interactions`, no MOP fixture's `params`
carries `ape.mopCoinLedgerMaxInteractions`, and the jar's default for that key is `4`, calibration v6's F1 value,
which is the budget the MOP cells rely on. The jar's default `ape.mopWeights` has at most `DIST_WEIGHED_MAX` (3)
levels, because a cell that states no ladder derives its artifact at that cut, and a longer default ladder would
weigh levels the artifact carries no pair for. This catches a renamed cell, a moved block, or a jar whose ledger
default is not the one the cells were planned for, before any device is started.

**On the device, against the trace.** The integration smoke SHALL run each cell it covers on an instrumented APK with its
`.apk.json` beside it and compare the recorded `RUN_START` with the cell's fixture on `preset`, `variant`, `features`, `params`, `inert`
and `digest`. The comparison masks the members that differ by construction: `run_id`, `t0`, `seed`, `build` and
`props_digest`. This is the gate of the cross-repository pairing (plan §9.3). A jar and a `tool.py` from different
sides of the key change cannot pass it, because the run aborts at resolution and writes no `RUN_START`. A pair
that passes it runs what each cell claims.

**The six cells are compared on every member, `digest` included.** `as_llm`'s and `as_mop_llm`'s only override,
`llm_url`, states the value their fixtures already carry (`http://10.0.2.2:30000/v1`), and the other four cells
state no override, so the jar resolves for each cell the plan its fixture was resolved from.

**The ablation variant is checked with its delta set apart.** The jar's echo rules predict how an override moves
the echo: `params` carries a non-default value and the activation key of each active feature, and a key of an
inactive feature stated at its neutral value is reported in `inert`. `digest` is not compared for the ablation,
because it hashes every plan value and so differs by construction. `mop_nolaunch` is compared against
`cells/mop.run_start.json`, because the jar ships no preset for an ablation variant: `preset` SHALL be `mop` and
`variant` SHALL be `mop_nolaunch`; `features` is the fixture's without `MOP_LAUNCHER`; `params` is the fixture's
without `ape.activityTriggerEnabled`, because an inactive feature's activation key is not echoed and `false` is
that key's neutral value; `inert` is `["ape.activityTriggerEnabled"]`.
Offline, the test checks that the ablation variant names the `mop` preset and that the launcher override maps to a
key the jar accepts.

The comparison is post-hoc analysis over a recorded trace, done by a test or a smoke script through `TraceReader`.
It SHALL NOT be done in `tool.py`, which never reads the echo (INV-APV-43, INV-APV-57).

#### Scenario: The jar's presets are the six cells
- **WHEN** the offline cell test reads `Presets.java` from the `ape` checkout
- **THEN** the preset names SHALL be exactly `base`, `mop`, `as`, `as_mop`, `as_llm`, `as_mop_llm`
- **AND** the key set of `as_mop_llm` SHALL equal the union of the ADDONS, STATIC, MOP and LLM blocks

#### Scenario: Each variant names the fixture's cell
- **WHEN** the offline cell test reads `cells/as_llm.run_start.json`
- **THEN** its `preset` and `variant` SHALL both equal `get_variants()["as_llm"]["preset"]` and
  `get_variants()["as_llm"]["variant"]`
- **AND** its `features` SHALL contain `LLM_COIN` and SHALL NOT contain `MOP` or `MOP_COIN`

#### Scenario: A device run echoes the cell it was given
- **WHEN** the smoke runs `aperv:as` on an instrumented APK with its `.apk.json`, with the paired jar
- **THEN** the trace's `RUN_START.variant` SHALL be `"as"`
- **AND** its `features`, `params` and `inert` SHALL equal those of `cells/as.run_start.json`
- **AND** its `digest` SHALL equal the fixture's

#### Scenario: The MOP cells rely on the jar's calibrated ledger default
- **WHEN** the offline cell test reads the `ape` checkout's key table and the fixtures of `mop`, `as_mop` and
  `as_mop_llm`
- **THEN** the default of `ape.mopCoinLedgerMaxInteractions` SHALL be `4`
- **AND** none of `mop`, `as_mop`, `as_mop_llm`, `mop_nolaunch` SHALL state `mop_coin_ledger_max_interactions`
- **AND** no MOP fixture's `params` SHALL carry `ape.mopCoinLedgerMaxInteractions`
- **AND** the default of `ape.mopWeights` SHALL have at most 3 levels
- **AND** against a checkout whose ledger default is `1`, as at the `ape` master `a0fb5c16`, the ledger test SHALL
  fail

#### Scenario: A MOP cell echoes its fixture plus the ledger budget
- **WHEN** the smoke runs `aperv:mop` on an instrumented APK with its `.apk.json`, with the paired jar
- **THEN** the trace's `RUN_START.preset` and `RUN_START.variant` SHALL be `"mop"`
- **AND** its `features` SHALL equal the fixture's `FUZZING`, `STATIC_DATA`, `MOP`, `WTG`, `MOP_FRONTIER`,
  `MOP_LAUNCHER`, `MOP_ACTIVITY_SOURCE`, `MOP_COIN`, with no `MENU_GATEWAY`
- **AND** its `params`, its `inert` and its `digest` SHALL equal the fixture's

#### Scenario: The launcher ablation echoes its cell without the launcher
- **WHEN** the smoke runs `aperv:mop_nolaunch` on an instrumented APK with its `.apk.json`, with the paired jar
- **THEN** the trace's `RUN_START.preset` SHALL be `"mop"` and `RUN_START.variant` SHALL be `"mop_nolaunch"`
- **AND** its `features` SHALL be those of `cells/mop.run_start.json` without `MOP_LAUNCHER`
- **AND** its `params` SHALL equal the fixture's without `ape.activityTriggerEnabled`, and its `inert` SHALL be
  `["ape.activityTriggerEnabled"]`
- **AND** its `RUN_END.counters.launches` and `nullRelaunches` SHALL be `0`

#### Scenario: A mismatched pair fails at resolution
- **WHEN** a jar that predates the group keys is deployed under this `tool.py` and `aperv:base` runs
- **THEN** the jar SHALL abort before step 1 on the unknown preset `base` or the unknown key `ape.variant`
- **AND** the smoke SHALL report the cell as failed, because no `RUN_START` was recorded
