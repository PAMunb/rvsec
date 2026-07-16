# Delta Specification: ApeRV Tool — Static Analysis JSON Compaction

## Purpose

This delta introduces a compaction step between locating the static analysis JSON and pushing it to the device, and revises the execution flow to place that step in order.

The motivation is a hard ceiling on the Java side. `MopData.java:202` applies a pre-read footprint guard before parsing: it rejects the file outright when `fileSize > maxMemory() / PARSE_FOOTPRINT_FACTOR`. With `PARSE_FOOTPRINT_FACTOR = 6` (`MopData.java:160`) and the ~192 MB heap available to the emulator process, the effective ceiling is roughly 32 MB. The guard exists because DOM-parsing a 50 MB document needs ~200 MB of heap (approximately 1x the bytes, plus ~2x for String chars, plus ~3x for the DOM), which reliably OOMs. When the guard fires, the tool aborts rather than exploring without MOP data — a deliberate choice, because running without MOP data while still labelled a MOP arm would silently mislabel the arm's identity.

The consequence is a per-app fairness gap rather than a crash. In the `cmpma` campaign, `org.quantumbadger.redreader_117` ships a 50.6 MB JSON; both MOP arms refuse to explore (0 steps) while `ape`, `ape_pure`, and `sata` run normally and reach roughly 14pp coverage. On that app the MOP treatment zeroes coverage the baselines obtain. That app is present in `cmpma`'s paired set (n=181), so the gap is not hypothetical — it is already inside a published comparison. This change prevents recurrence; it does not retroactively correct that campaign.

The file is large for reasons that carry no information. Of the 24,300 WTG `transitions` edges, 70.7% are exact duplicates (7,124 unique); pretty-printing at indent 2 across 1.25M lines costs a further ~13 MB. Removing both losslessly yields 21.0 MB, which clears the ceiling without dropping any field the tool consumes.

Two design constraints shape the requirement. First, the compacted document goes to a temporary file and the source at `<results_dir>/<apk_name>.json` is never modified. This is not because compaction would corrupt another consumer — it would not. The same file is parsed by `StaticAnalysisComponent.load_static_data()` in `rv-platform` to build the per-method coverage denominator, but that denominator is derived from `reachability`, and neither deduplicating `transitions` nor removing whitespace changes it: parsing `org.quantumbadger.redreader_117.apk.json` before and after compaction yields an identical 1,796 classes / 9,333 methods. The reasons are narrower. Compaction is a concern of the device-push path, while `copy_static_analysis_files()` runs for every tool including `monkey` and `ape`, which never push this file; and the source is an archived experiment artifact that offline consolidation and resume re-parse, so keeping it byte-identical to the producer's output preserves it as ground truth rather than a derived artifact. Second, compaction is unconditional rather than gated on a size threshold: a threshold would leave the compaction path exercised on roughly 1 app in 181 under the current static-analysis build (effectively untested in production), would duplicate the Java-side `PARSE_FOOTPRINT_FACTOR` as a second constant to keep in sync, and would forfeit the heap-pressure reduction on every other APK. The measured cost on the largest JSON in the dataset is ~0.5s of CPU, against exploration runs of 60–300s.

Deduplication is safe because no consumer of the edge list treats multiplicity as a signal. Six consumers in the sibling `ape` repository read `getWtgTransitions` / `wtgTransitions`, and each is either a set-membership test or a first-match-fixed-weight lookup, hence idempotent to duplicates: `MopScorer.scoreWtg` (`MopScorer.java:115`) returns `mopWeightWtg` on first match; `FrontierPass` (`FrontierPass.java:55`) builds a `HashSet` of visited targets and delegates to `StatefulAgent.frontierBoost` (`StatefulAgent.java:1066`), which returns `weight` on first match; `MopFrontierPass` (`MopFrontierPass.java:56,97,109`) builds a `HashSet` of targets plus first-match booleans; `rekeyDialogsToHost` (`MopData.java:884`) takes the first inbound edge and `break`s; `hasWtgData()` (`MopData.java:1000`) tests `!isEmpty()`. A repository-wide grep for `getWtgTransitions|getTransitions|wtgTransitions` finds no consumer that counts edges or accumulates weight across the list. Only `rekeyDialogsToHost` is order-sensitive — its `// first incoming edge wins (A3)` comment is explicit — which is why deduplication preserves first-occurrence order rather than reordering.

Note that `FrontierPass` and `MopFrontierPass` are distinct classes with distinct call sites; an enumeration that folds the former into `StatefulAgent.frontierBoost` undercounts the consumers. The safety argument rests on the property that none of them reads multiplicity, not on the count.

Field projection is deliberately excluded. Dropping unread sections is unnecessary — 21 MB already clears the ceiling — and would introduce silent schema-drift: a future Java `Pass` that begins reading a projected-away field would go inert with no error, which is precisely the failure mode the footprint guard was written to avoid.

## Data Contracts

### Input
- `static_json_path: str` — absolute path to `<task.results_dir>/<task.config.apk_name>.json`, returned by `_find_static_analysis_file(task)`; produced by rv-android static analysis pre-processing (GATOR/GESDA/REACH)

### Output
- `push_path: str` — absolute path of the file handed to `_push_file_to_device()`: the compacted temporary file on success, `static_json_path` unchanged on fallback

### Side-Effects
- **[Filesystem]**: on the success path, a temporary file holding the compacted document is created and unlinked after the push completes
- **[Filesystem]**: on the fallback path, any temporary file created before the failure is unlinked by the compaction function before it returns, so no temporary file exists at push time
- **[Device]**: `/data/local/tmp/static_analysis.json` receives the compacted document (or the source document, on fallback). This SUPERSEDES the existing Side-Effect line in `openspec/specs/aperv/spec.md` ("`static_analysis.json` pushed to `/data/local/tmp/static_analysis.json` (MOP variants only, when file is found)") — replace that line rather than appending alongside it.
- **[Filesystem]**: `<task.results_dir>/<task.config.apk_name>.json` is read and never written

### Error
- No new error class. Every failure mode of compaction is caught and degraded to the fallback push (NFR04).

## Invariants

- **INV-APV-06** (SUPERSEDES the existing INV-APV-06 in `openspec/specs/aperv/spec.md` — replace that text, do not append): The `sata_mop` variant SHALL set `mop_data` to `"static_analysis"`. When `mop_data == "static_analysis"`, `execute_tool_specific_logic()` SHALL locate the static analysis JSON, compact it (INV-APV-21), and push the compacted document to the device; when compaction fails, the source document SHALL be pushed instead (INV-APV-24). If the JSON is not found, execution SHALL continue without MOP data (graceful degradation). The existing wording — "SHALL locate and push the static analysis JSON to the device" — becomes false once compaction is in place, because the file that reaches the device is a compacted copy and never the source file (INV-APV-20).

- **INV-APV-20**: Compaction SHALL write to a temporary file. The source file at `<task.results_dir>/<task.config.apk_name>.json` SHALL remain byte-identical after `execute_tool_specific_logic()` returns. This file is an archived experiment artifact: offline consolidation and `ResultProcessorComponent._resolve_static_data` re-parse it on resume. Keeping it byte-identical to the producer's output preserves it as ground truth rather than a derived artifact, and confines this change to the device-push path.

- **INV-APV-21**: Compaction SHALL be lossless. It SHALL consist of exactly two operations: (a) removing exact-duplicate entries from `transitions`, and (b) serializing without pretty-print whitespace. Every top-level key present in the source document (`package`, `mainActivity`, `components`, `reachability`, `windows`, `transitions`, `complete`) SHALL be present in the compacted document. No field SHALL be projected away, renamed, or rewritten.

- **INV-APV-22**: Deduplication of `transitions` SHALL preserve the order of first occurrence. `rekeyDialogsToHost` (`MopData.java:884`) resolves the first inbound edge and breaks, making edge order semantically load-bearing even though edge multiplicity is not.

- **INV-APV-23**: Compaction SHALL run unconditionally on every MOP-arm push, with no size threshold gating it.

- **INV-APV-24**: Any failure during compaction SHALL be caught, SHALL log a warning, and SHALL fall back to pushing the source file unchanged. Compaction SHALL NOT raise, and SHALL NOT be a task-failure path. The fallback preserves the pre-change behavior as a floor.

- **INV-APV-25**: No temporary file SHALL survive `execute_tool_specific_logic()`, on either the success or the fallback path.

## ADDED Requirements

### Requirement: Static Analysis JSON Compaction (FR19, FR04, NFR04)

`ApeRVTool` SHALL compact the static analysis JSON into a temporary file before pushing it to the device, and SHALL push the compacted file rather than the source file.

Compaction SHALL consist of exactly two lossless operations. First, entries in the `transitions` array SHALL be deduplicated by exact equality of the whole entry, preserving first-occurrence order. Entries carry exactly the keys `sourceId`, `targetId`, and `events`, so whole-entry canonical equality is identical to the `(sourceId, targetId, events)` tuple and cannot silently ignore a field added later. Second, the document SHALL be serialized without pretty-print whitespace.

The source file SHALL NOT be modified (INV-APV-20). Compaction SHALL run unconditionally, not gated on file size (INV-APV-23). No field SHALL be projected away (INV-APV-21).

Any failure — malformed JSON, filesystem error writing the temporary file, or memory exhaustion loading the document — SHALL be caught, SHALL emit a warning, and SHALL degrade to pushing the source file unchanged (INV-APV-24). The temporary file SHALL be unlinked after the push on every path (INV-APV-25).

#### Scenario: Oversized JSON compacted below the Java footprint ceiling
- **WHEN** `execute_tool_specific_logic(task, app)` runs with `mop_data="static_analysis"`
- **AND** `_find_static_analysis_file(task)` returns a 50.6 MB JSON with 24,300 `transitions` entries of which 7,124 are unique (`org.quantumbadger.redreader_117.apk.json`)
- **THEN** the file pushed to `/data/local/tmp/static_analysis.json` SHALL be approximately 21.0 MB
- **AND** it SHALL contain exactly 7,124 `transitions` entries
- **AND** it SHALL be below the ~32 MB guard ceiling of `MopData.java:202`, so the MOP arm SHALL explore with more than 0 steps

#### Scenario: Source file is never modified
- **WHEN** compaction runs on `<task.results_dir>/<apk_name>.json`
- **THEN** the source file SHALL be byte-identical to its content before the call
- **AND** it SHALL remain byte-identical to the producer's output, so offline consolidation and `ResultProcessorComponent._resolve_static_data` on resume re-parse the archived artifact rather than a derived one

#### Scenario: Deduplication preserves first-occurrence order
- **WHEN** `transitions` is `[A, B, A, C, B]` where A, B, C are distinct entries
- **THEN** the compacted `transitions` SHALL be exactly `[A, B, C]`
- **AND** the relative order SHALL match first occurrence in the source

#### Scenario: All top-level keys survive compaction
- **WHEN** the source document has top-level keys `package`, `mainActivity`, `components`, `reachability`, `windows`, `transitions`, `complete`
- **THEN** the compacted document SHALL contain all seven keys
- **AND** the value of every key other than `transitions` SHALL be unchanged

#### Scenario: Small JSON is compacted anyway
- **WHEN** the source JSON is 100 KB, well below the ceiling
- **THEN** compaction SHALL still run (INV-APV-23)
- **AND** the compacted file SHALL be pushed

#### Scenario: JSON with no transitions key
- **WHEN** the source document has no `transitions` key
- **THEN** compaction SHALL succeed and minify the document
- **AND** no `transitions` key SHALL be added

#### Scenario: JSON with empty transitions array
- **WHEN** the source document has `transitions: []` (as in `sdmse` at 23.7 MB and `email` at 20.8 MB, the two next-largest JSONs in the `cmpma` set)
- **THEN** compaction SHALL succeed
- **AND** `transitions` SHALL remain `[]`

#### Scenario: Malformed JSON falls back to pushing the original
- **WHEN** the source file is not parseable as JSON
- **THEN** a warning SHALL be logged naming the file and the failure
- **AND** the source file SHALL be pushed unchanged to `/data/local/tmp/static_analysis.json`
- **AND** no exception SHALL propagate out of `execute_tool_specific_logic()`
- **AND** `ape.properties` SHALL still contain `ape.mopDataPath=/data/local/tmp/static_analysis.json`

#### Scenario: No temporary file leaks on the success path
- **WHEN** compaction succeeds and the push completes
- **THEN** the temporary file SHALL NOT exist after `execute_tool_specific_logic()` returns

#### Scenario: No temporary file leaks on the fallback path
- **WHEN** compaction fails after the temporary file was created
- **THEN** the temporary file SHALL NOT exist after `execute_tool_specific_logic()` returns
- **AND** the source file SHALL have been pushed

## MODIFIED Requirements

### Requirement: ApeRVTool Execution Flow (FR18, FR19)

`ApeRVTool.execute_tool_specific_logic(task, app)` SHALL perform the following steps in order:

1. **Extract execution parameters**: Resolve `device_serial` from `task.config.device_id` (default `"emulator-5554"`) and `timeout_seconds` from `task.config.timeout` (default 300).

2. **Push JAR**: Resolve `ape-rv.jar` via `_resolve_jar_path()` and push to `/data/local/tmp/ape-rv.jar` via `_push_file_to_device()`.

3. **Push broadcast catalog**: If `system-broadcast.json` exists in the module directory (`os.path.dirname(__file__)`), push it to `/data/local/tmp/system-broadcast.json`. This catalog provides typed extras for system broadcast intents used by APE-RV's component triggering. If the file is absent, skip (APE-RV degrades gracefully).

4. **Compact and push static analysis JSON** (MOP variants only): When `_tool_config.get("mop_data") == "static_analysis"`, locate `<task.results_dir>/<apk_name>.json` via `_find_static_analysis_file(task)`. If found, compact it into a temporary file (deduplicate `transitions`, serialize without pretty-print whitespace — see "Static Analysis JSON Compaction"), push the compacted file to `/data/local/tmp/static_analysis.json`, unlink the temporary file, and set `mop_json_pushed = True`. If compaction fails, log a warning and push the source file unchanged, still setting `mop_json_pushed = True`. If the JSON is not found, log a warning and continue without MOP data.

5. **Push ape.properties**: Generate `ape.properties` from `_tool_config` using `APERV_PROPERTY_MAPPING` to translate Python keys to Java property names. When `mop_json_pushed` is True, include `ape.mopDataPath=/data/local/tmp/static_analysis.json`. Push to `/data/local/tmp/ape.properties`.

6. **Build and execute command**: Build the `app_process` command via `_build_main_command()` and execute it, capturing stdout+stderr to `task.result.trace_file` in binary write mode. Command timeout is `timeout_seconds + 15` seconds.

7. **Handle timeout**: If `RVCommandTimeoutError` is raised, re-raise as `RVToolTimeoutError` (timeout is the expected exit path for exploration tools).

8. **Check empty trace**: Call `_check_empty_trace()` and log a warning if the trace file is empty.

The `app_process` invocation SHALL use:
```
adb -s <serial> shell CLASSPATH=/data/local/tmp/ape-rv.jar /system/bin/app_process /system/bin
  com.android.commands.monkey.Monkey -p <package_name>
  --running-minutes <max(1, timeout_seconds // 60)>
  --ape <strategy>
  [-s <seed>]
```

The trailing `-s <seed>` is appended only when a seed is configured (`tool.py:692-694`). This clause is reproduced here because a MODIFIED requirement must carry full content; the seed argument itself is owned by change `gh74-aperv-arm-variants` (INV-APV-18), which is implemented in code but whose delta is not yet synced. Whichever of the two changes archives first must not freeze the seedless form as the contract.

#### Scenario: Successful APE-RV execution with sata variant
- **WHEN** `execute_tool_specific_logic(task, app)` is called with `strategy="sata"`, timeout=60
- **THEN** `ape-rv.jar` SHALL be pushed to `/data/local/tmp/ape-rv.jar`
- **AND** the adb command SHALL include `--running-minutes 1` and `--ape sata`
- **AND** stdout+stderr SHALL be written to `task.result.trace_file`
- **AND** no static analysis JSON SHALL be pushed to the device
- **AND** no compaction SHALL be attempted

#### Scenario: sata_mop execution with static analysis JSON present
- **WHEN** `execute_tool_specific_logic(task, app)` is called with `mop_data="static_analysis"`
- **AND** `_find_static_analysis_file(task)` returns a valid path
- **THEN** the JSON SHALL be compacted into a temporary file
- **AND** the compacted file SHALL be pushed to `/data/local/tmp/static_analysis.json`
- **AND** the source file SHALL remain byte-identical
- **AND** `ape.properties` SHALL contain `ape.mopDataPath=/data/local/tmp/static_analysis.json`

#### Scenario: sata_mop execution when compaction fails
- **WHEN** `execute_tool_specific_logic(task, app)` is called with `mop_data="static_analysis"`
- **AND** `_find_static_analysis_file(task)` returns a path whose content is not parseable as JSON
- **THEN** a WARNING SHALL be logged
- **AND** the source file SHALL be pushed unchanged to `/data/local/tmp/static_analysis.json`
- **AND** `ape.properties` SHALL contain `ape.mopDataPath=/data/local/tmp/static_analysis.json`
- **AND** execution SHALL continue normally

#### Scenario: sata_mop execution with static analysis JSON absent
- **WHEN** `execute_tool_specific_logic(task, app)` is called with `mop_data="static_analysis"`
- **AND** no static analysis JSON file is found in `task.results_dir`
- **THEN** a WARNING SHALL be logged: `"sata_mop: static analysis file not found in results_dir, running without MOP data"`
- **AND** no compaction SHALL be attempted
- **AND** `ape.properties` SHALL NOT contain `ape.mopDataPath`
- **AND** execution SHALL continue (APE-RV runs as plain `sata`)

#### Scenario: Broadcast catalog pushed when present
- **WHEN** `system-broadcast.json` exists in the module directory
- **THEN** it SHALL be pushed to `/data/local/tmp/system-broadcast.json`
- **AND** APE-RV SHALL use it for component triggering with typed extras

#### Scenario: Broadcast catalog absent
- **WHEN** `system-broadcast.json` does not exist in the module directory
- **THEN** no broadcast catalog SHALL be pushed
- **AND** execution SHALL continue normally (APE-RV component triggering degrades gracefully)

#### Scenario: Execution timeout
- **WHEN** APE-RV runs for longer than `timeout_seconds + 15` seconds
- **THEN** `RVToolTimeoutError` SHALL be raised and logged
- **AND** the timeout SHALL be re-raised to the caller

#### Scenario: Non-zero exit code from APE-RV
- **WHEN** APE-RV exits with a non-zero exit code (e.g., 211)
- **THEN** execution SHALL NOT raise an error
- **AND** a debug log SHALL be emitted noting the exit code is normal when app crashes are detected

#### Scenario: Empty trace file
- **WHEN** APE-RV execution completes but writes nothing to stdout
- **THEN** a warning log line SHALL contain `"aperv produced empty trace file"`
