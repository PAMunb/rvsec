# Capability: aperv

## Purpose

This delta extends the `aperv` capability with what the E3 decisive run needs on the Python side: an enumerated arm set that includes the experiment's first **control** arm, an offline enrichment of the static-analysis document that gives the scoring pipeline's direct/transitive axis a real meaning, per-run provenance of the LLM backend, and an offline join between the trace clock and the violation log.

The unifying concern is **attributability**. `aperv-tool` is the component that decides what an APE-RV arm *is*: it resolves a variant name into a dictionary of Python keys, maps those keys into `ape.properties`, discovers and pushes the static-analysis document, and hands the run to rv-platform. Every experimental claim the thesis makes about MOP guidance is therefore a claim about what this component configured. Today that chain has three holes. There has never been an arm with MOP guidance switched off, so no measured difference can be attributed to MOP guidance rather than to APE's baseline exploration. The `handlerDirectlyReachesTarget` field that would separate direct from transitive reach is never populated by the producer, so `mop_weight_direct=500` is unreachable by construction and the direct/transitive decomposition measures nothing. And the LLM backend that actually served a run is never recorded, so a result cannot be tied to the model and sampling that produced it.

The MOP-off arm's shape is not a free choice — it is forced by two verified behaviours of the jar, and getting it wrong silently destroys the experiment. Setting `ape.mopDataPath` to a file that fails to load raises `StopTestingException` and **aborts the whole run** (`StatefulAgent.java:216-223`, INV-MOP-22), so "point at nothing" is not an option. Leaving `mop_data` out of the arm entirely does avoid the abort, but `WtgPass:29` and `FrontierPass:35` both require `mopData != null`, so it also disables the *generic* WTG and frontier navigation — the contrast would then be "full substrate versus almost no substrate", not "MOP guidance on versus off". The only shape that isolates MOP guidance is therefore: document **present and loading**, MOP weights zeroed, activity trigger off. The short-circuits become no-ops because they require `mopBoost > 0`, and the frontier machinery keeps running on generic WTG signal.

The offline enrichment (N6) exists because the fix belongs to the producer but the producer must not be touched. `rvsec-gator` is under a standing rule of no modification except for gross error, and any change there would require re-running static analysis over hundreds of APKs — impossible inside the deadline. The enrichment is possible without the producer because the consumer already reads the two fields with precedence over its own local join (`MopData.java:516-517,531-533`) and the data needed to compute them is already inside the same document: the `reachability` section lists, per method, whether it reaches a JCA target. The compaction step already loads that document into memory and rewrites it before pushing, so populating the two fields costs one pass over the widgets and zero additional I/O. The semantics are redefined deliberately: the producer's `directlyReachesTarget` means 0-hop (the method's own body invokes JCA), which is why it is 0 for every UI handler in the corpus — handlers delegate. The redefined **direct** means *the handler of this widget reaches a JCA target at any depth*, which is the property the scoring pipeline actually wants to reward.

Scope boundaries this delta does not cross: source `.apk.json` files are never modified (the archived artifact must stay byte-identical to the producer's output, because offline consolidation re-parses it); the static analysis is never re-run; `rvsec-gator` is not touched; no mock LLM is introduced; and Android emulators are never started, stopped, or otherwise managed outside rv-platform.

## Data Contracts

### Input
- `variant: str` — arm name resolved through `ApeRVTool.get_variants()` (`modules/aperv-tool/src/aperv_tool/tools/aperv/tool.py`), the single source of truth for arm key dictionaries.
- `llm_url: str` — OpenAI-compatible base URL already held by the tool configuration; the source of the `/v1/models` provenance query.
- `<task.results_dir>/<apk_name>.json` — static-analysis document produced by `rvsec-analysis-client.jar`. Sections consumed by the enrichment: `windows[].widgets[].listeners[].handler` (handler signatures) and `reachability[].methods[]` (`signature`, `reachable`, `reachesTarget`, `directlyReachesTarget`).
- Recorded run artifacts for the offline join: per-run trace files carrying the step clock, and the logcat lines matching `RVSEC:`.

### Output
- `ape.properties` — arm configuration, including the zeroed MOP weights and `activity_trigger_enabled=false` for the control arm.
- Compacted static-analysis document pushed to `/data/local/tmp/static_analysis.json`, now additionally carrying `listeners[].handlerReachesTarget: bool` and `listeners[].handlerDirectlyReachesTarget: bool`.
- Task output provenance fields: `llm_backend`, `llm_model`, `llm_sampling` — recorded per run.
- Join report (A9): per-run rows correlating step clock positions with `RVSEC:` violation timestamps.

### Side-Effects
- **[Device]**: the compacted document is pushed to `/data/local/tmp/static_analysis.json`; unchanged from current behaviour except for the two added boolean fields.
- **[Network]**: one `GET /v1/models` per run at preflight time.
- **[Filesystem]**: the join utility reads recorded artifacts and writes its report; it never writes into `results/` trees it did not create.

### Error
- `SystemExit(2)` — the join utility on usage error (missing or unreadable run directory).
- Enrichment failures are non-fatal: they degrade to the un-enriched document (see INV-APV-31) and emit a warning.
- Provenance query failures are non-fatal: the run proceeds and the provenance fields record the failure rather than a fabricated value (INV-APV-33).

## Invariants

- **INV-APV-21** (amended by this change): Compaction SHALL be lossless with respect to the producer's content. It SHALL consist of exactly **three** operations: (a) removing exact-duplicate entries from `transitions`, (b) adding the two handler-reach booleans to existing `listeners[]` objects, and (c) serializing without pretty-print whitespace. Operations (a) and (c) are lossless; (b) is purely additive and constrained by INV-APV-31. Every top-level key present in the source document (`package`, `mainActivity`, `components`, `reachability`, `windows`, `transitions`, `complete`) SHALL be present in the compacted document. No field SHALL be projected away, renamed, or rewritten. *This supersedes the "exactly two operations" form of INV-APV-21 in the main `aperv` spec; the amendment is stated here because INV-APV-21 is a capability-level invariant and a MODIFIED requirement cannot displace it implicitly.*
- **INV-APV-29**: The MOP-off control arm SHALL set `mop_data` to a **present and loadable** document, SHALL set `mop_weight_direct`, `mop_weight_transitive`, `mop_weight_open_menu`, `mop_weight_wtg`, and `mop_frontier_weight` all to `0`, and SHALL set `activity_trigger_enabled=false`. It SHALL NOT achieve MOP-off by omitting `mop_data` or by pointing `ape.mopDataPath` at a missing file — the first disables the generic WTG and frontier passes as collateral, the second aborts the run.
- **INV-APV-30**: Every arm of the decisive run SHALL use the frontier substrate (`sata_mop_act_frontier` lineage). No arm SHALL abandon the frontier mechanism, including the control arm — the control removes MOP guidance, not navigation.
- **INV-APV-31**: Enrichment SHALL add only the keys `handlerReachesTarget` and `handlerDirectlyReachesTarget` to existing `listeners[]` objects. It SHALL NOT add, remove, reorder, or alter any other key anywhere in the document, SHALL NOT modify the source file (INV-APV-20 continues to hold), and on any failure SHALL degrade to pushing the document without enrichment rather than propagating an exception.
- **INV-APV-32**: `handlerDirectlyReachesTarget` SHALL mean *the handler method of this widget reaches a JCA target at any call depth*, computed from the document's own `reachability` section. It SHALL NOT be copied from the producer's method-level `directlyReachesTarget`, whose 0-hop semantics make it `false` for every UI handler in the corpus.
- **INV-APV-33**: Backend provenance SHALL be obtained from a live `/v1/models` query performed at the start of each run, never from static configuration. When the query fails, the provenance fields SHALL record the failure explicitly; the run SHALL NOT be aborted and a value SHALL NOT be inferred from configuration.
- **INV-APV-34**: `llm_snap_tolerance_px=150` SHALL be applied only in an arm that also declares the git sha of the `ape-rv.jar` build containing the dead-pair ban (sister change `telemetry-proof-llm-efficacy`, item B1). The declaration and the value SHALL be present together or absent together — a guard test SHALL fail on either alone. The declared sha SHALL be verified against the `git_sha` field of the run's `[APE-BUILD]` banner (INV-BUILD-11 in the `ape` repository) before the decisive run consumes wall-clock. Against a jar without B1, the wider radius amplifies repeated dead taps instead of rescuing near-misses.
- **INV-APV-35**: The clock↔logcat join SHALL be an offline, read-only computation over recorded artifacts. It SHALL NOT read logcat from a running device, SHALL NOT require an emulator, and SHALL NOT modify any artifact it reads.
- **INV-APV-36**: Any coverage figure aggregated across runs, replicas or arms SHALL be derived from `UICOV-ACT` (Activity grain). `UICOV` state keys SHALL NOT be used as a cross-run join key — they embed a JVM identity hash whose measured cross-replica pairing rate is zero (Jaccard 0.000 at mean, median and maximum).
- **INV-APV-37**: The coverage-dump parser SHALL report every run in its input with an explicit dump status — complete, partial, or absent — and SHALL NOT omit a run for lacking a dump. Any coverage rate it produces SHALL carry the denominator it was computed over, so that a figure computed on the runs that dumped is never mistaken for a figure over all runs.

## MODIFIED Requirements

### Requirement: Static Analysis JSON Compaction (FR19, FR04, NFR04)

`ApeRVTool` SHALL compact the static analysis JSON into a temporary file before pushing it to the device, and SHALL push the compacted file rather than the source file.

Compaction SHALL consist of exactly three operations on the in-memory document. First, entries in the `transitions` array SHALL be deduplicated by exact equality of the whole entry, preserving first-occurrence order. Entries carry exactly the keys `sourceId`, `targetId`, and `events`, so whole-entry canonical equality is identical to the `(sourceId, targetId, events)` tuple and cannot silently ignore a field added later. Second, every `listeners[]` object SHALL be enriched with the two handler-reach booleans described below. Third, the document SHALL be serialized without pretty-print whitespace.

The first and third operations are lossless. The second is purely additive: it SHALL add only the keys `handlerReachesTarget` and `handlerDirectlyReachesTarget` to existing listener objects and SHALL NOT touch anything else in the document (INV-APV-31).

**Enrichment semantics.** For each `windows[].widgets[].listeners[]` entry, the handler signature is looked up in the document's own `reachability` section, whose entries carry `signature`, `reachable`, `reachesTarget`, and `directlyReachesTarget` per method. `handlerReachesTarget` SHALL be the `reachesTarget` value of the matching method. `handlerDirectlyReachesTarget` SHALL be `true` when the handler of *this* widget reaches a JCA target at any call depth — that is, it SHALL be derived from the same `reachesTarget` bit of the handler itself, **not** copied from the producer's method-level `directlyReachesTarget` (INV-APV-32). The producer's field means 0-hop reach, which is `false` for every UI handler in the corpus because handlers delegate; copying it would reproduce the `[DM]=0` defect this change exists to fix. When a handler signature has no match in `reachability`, both fields SHALL be `false`.

The consumer reads both fields with precedence over its own local join (`MopData.java:516-517,531-533`), so the enrichment reaches the scoring pipeline without any jar change.

The source file SHALL NOT be modified (INV-APV-20). Compaction SHALL run unconditionally, not gated on file size (INV-APV-23). No field SHALL be projected away (INV-APV-21).

Any failure -- malformed JSON, filesystem error writing the temporary file, memory exhaustion loading the document, or a malformed `reachability` section -- SHALL be caught, SHALL emit a warning, and SHALL degrade to pushing the source file unchanged (INV-APV-24). An enrichment failure specifically SHALL NOT abort the push: the document SHALL be pushed deduplicated and minified but un-enriched (INV-APV-31). The temporary file SHALL be unlinked after the push on every path (INV-APV-25).

#### Scenario: Oversized JSON compacted below the Java footprint ceiling
- **WHEN** `execute_tool_specific_logic(task, app)` runs with `mop_data="static_analysis"`
- **AND** `_find_static_analysis_file(task)` returns a 50.6 MB JSON with 24,300 `transitions` entries of which 7,124 are unique (`org.quantumbadger.redreader_117.apk.json`)
- **THEN** the file pushed to `/data/local/tmp/static_analysis.json` SHALL contain exactly 7,124 `transitions` entries
- **AND** it SHALL be below the ~32 MB guard ceiling of `MopData.java:202`, so the MOP arm SHALL explore with more than 0 steps

#### Scenario: Handler that reaches JCA transitively is flagged direct
- **WHEN** a widget's listener has handler `<com.example.MainActivity: void onEncryptClick(android.view.View)>`
- **AND** the `reachability` section contains that signature with `reachesTarget=true` and `directlyReachesTarget=false` (the handler delegates to a repository that calls `Cipher.getInstance`)
- **THEN** the pushed document SHALL carry `handlerReachesTarget=true` for that listener
- **AND** it SHALL carry `handlerDirectlyReachesTarget=true`, because the redefined semantics is any-depth reach of this widget's handler (INV-APV-32)

#### Scenario: Handler that reaches nothing is flagged false on both axes
- **WHEN** a widget's listener has handler `<com.example.MainActivity: void onAboutClick(android.view.View)>`
- **AND** the `reachability` section contains that signature with `reachesTarget=false`
- **THEN** both `handlerReachesTarget` and `handlerDirectlyReachesTarget` SHALL be `false` for that listener

#### Scenario: Handler absent from the reachability section
- **WHEN** a listener's handler signature has no matching entry in `reachability`
- **THEN** both fields SHALL be `false`
- **AND** no warning SHALL be emitted for the individual miss, and the push SHALL proceed

#### Scenario: App with no widgets is enriched trivially
- **WHEN** the document is one of the 58 apps of the 181-APK corpus whose `windows[].widgets` are all empty (a Compose-bundled app with no View-hierarchy widgets to enrich)
- **THEN** enrichment SHALL complete without error and add no fields
- **AND** the pushed document SHALL be identical to the un-enriched compaction result

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
- **AND** the value of every key other than `transitions` and the enriched `listeners[]` objects SHALL be unchanged

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

#### Scenario: Malformed reachability section degrades to un-enriched push
- **WHEN** the document parses but its `reachability` section is not a list of objects with `methods[]`
- **THEN** a warning SHALL be logged naming the file
- **AND** the document SHALL still be deduplicated, minified, and pushed
- **AND** no `handlerReachesTarget` or `handlerDirectlyReachesTarget` key SHALL be present in the pushed document

#### Scenario: No temporary file leaks on the success path
- **WHEN** compaction succeeds and the push completes
- **THEN** the temporary file SHALL NOT exist after `execute_tool_specific_logic()` returns

#### Scenario: No temporary file leaks on the fallback path
- **WHEN** compaction fails after the temporary file was created
- **THEN** the temporary file SHALL NOT exist after `execute_tool_specific_logic()` returns
- **AND** the source file SHALL have been pushed

### Requirement: ApeRVTool Execution Flow (FR18, FR19)

`ApeRVTool.execute_tool_specific_logic(task, app)` SHALL perform the following steps in order:

1. **Extract execution parameters**: Resolve `device_serial` from `task.config.device_id` (default `"emulator-5554"`) and `timeout_seconds` from `task.config.timeout` (default 300).

2. **Push JAR**: Resolve `ape-rv.jar` via `_resolve_jar_path()` and push to `/data/local/tmp/ape-rv.jar` via `_push_file_to_device()`.

3. **Push broadcast catalog**: If `system-broadcast.json` exists in the module directory (`os.path.dirname(__file__)`), push it to `/data/local/tmp/system-broadcast.json`. This catalog provides typed extras for system broadcast intents used by APE-RV's component triggering. If the file is absent, skip (APE-RV degrades gracefully).

4. **Compact and push static analysis JSON** (MOP variants only): When `_tool_config.get("mop_data") == "static_analysis"`, locate `<task.results_dir>/<apk_name>.json` via `_find_static_analysis_file(task)`. If found, compact it into a temporary file (deduplicate `transitions`, enrich `listeners[]` with the two handler-reach booleans, serialize without pretty-print whitespace -- see "Static Analysis JSON Compaction"), push the compacted file to `/data/local/tmp/static_analysis.json`, unlink the temporary file, and set `mop_json_pushed = True`. If compaction fails, log a warning and push the source file unchanged, still setting `mop_json_pushed = True`. If the JSON is not found, log a warning and continue without MOP data.

5. **Push ape.properties**: Generate `ape.properties` from `_tool_config` using `APERV_PROPERTY_MAPPING` to translate Python keys to Java property names. When `mop_json_pushed` is True, include `ape.mopDataPath=/data/local/tmp/static_analysis.json`. Push to `/data/local/tmp/ape.properties`.

6. **Capture LLM backend provenance** (LLM arms only): query `GET {llm_url}/v1/models` once and record the result in the task output -- see "Per-Run LLM Backend Provenance". A failed query is encoded, never inferred from configuration, and never aborts the run (INV-APV-33).

7. **Build and execute command**: Build the `app_process` command via `_build_main_command()` and execute it, capturing stdout+stderr to `task.result.trace_file` in binary write mode. **Command timeout is `timeout_seconds + 45` seconds** — widened from `+ 15`; see the grace-window rationale below.

8. **Handle timeout**: If `RVCommandTimeoutError` is raised, re-raise as `RVToolTimeoutError` (timeout is the expected exit path for exploration tools). The `RVToolTimeoutError` contract SHALL be stated as `task.config.timeout + 45` seconds wherever it is documented.

9. **Check empty trace**: Call `_check_empty_trace()` and log a warning if the trace file is empty.

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

The trailing `-s <seed>` is appended only when a seed is configured. The seed argument itself is owned by change `gh74-aperv-arm-variants` (INV-APV-18), which is implemented in code but whose delta is not yet synced; it is reproduced here so this spec does not freeze the seedless form as the contract.

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

## ADDED Requirements

### Requirement: Decisive Run Arm Set (FR20)

`aperv-tool` SHALL define the three arms of the E3 decisive run as named variants, so that each arm's identity comes from its variant dictionary and never from a jar default. The three arms SHALL be:

1. **`mop_on_llm_off`** — reference: MOP guidance on, LLM off. The shared baseline of both contrasts.
2. **`mop_off_llm_off`** — control: MOP guidance off, LLM off. Isolates the effect of MOP guidance (the study's central hypothesis).
3. **`mop_on_llm_70`** — LLM arm: MOP guidance on, LLM on at `llm_percentage=0.7`. Isolates the effect of adding the LLM.

The variant names are normative, not cosmetic: the variant string is the resume identity key and the consolidation column key, so a rename silently splits a campaign's results.

The reference arm and the LLM arm differ only in the LLM keys; the reference arm and the control arm differ only in the MOP keys. This is what makes each contrast a single-factor comparison.

All three arms SHALL use the frontier substrate (INV-APV-30). The control arm SHALL follow the shape fixed by INV-APV-29: `mop_data` present and loadable, all four MOP weights and `mop_frontier_weight` zeroed, `activity_trigger_enabled=false`. All three arms SHALL set `mop_activity_source_components=true` rather than inheriting the jar's `false` default (`Config.java:159`), whose suppression of the MOP-activity signal is measured at 20.0% → 85.0% of activities flagged on the subset40 and 17.7% → 86.2% offline across the 181 apps.

The arms SHALL satisfy the existing arm-flag guards: every key in `ARM_DEFINING_KEYS` set explicitly (INV-APV-14), every such key present in `APERV_PROPERTY_MAPPING` (INV-APV-13). The MOP weight keys, though not members of `ARM_DEFINING_KEYS`, SHALL be set explicitly in all three arms for auditability — for the control arm this is not merely auditability but the mechanism itself.

Arm 3 SHALL declare every key of `LLM_ARM_KEYS` explicitly, at `llm_percentage=0.7` with prompt variant `v13`, temperature 0, `top_p` 0.6, `top_k` 50, and both routing triggers on. Because that guard is scoped to `cal_`-prefixed variants, its scope SHALL be extended to cover arm 3 — an unscoped arm would satisfy the guard vacuously (INV-APV-26).

#### Scenario: Control arm keeps the frontier alive while MOP guidance is off
- **WHEN** the control arm's variant dictionary is resolved
- **THEN** it SHALL contain `mop_data="static_analysis"`
- **AND** `mop_weight_direct=0`, `mop_weight_transitive=0`, `mop_weight_open_menu=0`, `mop_weight_wtg=0`, `mop_frontier_weight=0`
- **AND** `activity_trigger_enabled=false`
- **AND** `frontier_boost_weight` SHALL remain at its frontier-substrate value, so generic WTG and frontier navigation stay enabled (INV-APV-30)

#### Scenario: Control arm never omits the static analysis document
- **WHEN** the guard test inspects the control arm's variant dictionary
- **THEN** `mop_data` SHALL be present
- **AND** the test SHALL fail with a message naming INV-APV-29 if `mop_data` is absent, because an absent document disables `WtgPass` and `FrontierPass` as collateral damage

#### Scenario: Reference and control differ only in MOP keys
- **WHEN** the guard test diffs the reference arm's dictionary against the control arm's
- **THEN** the differing keys SHALL be exactly the five MOP weight keys and `activity_trigger_enabled`
- **AND** every other key SHALL be identical, so the contrast is single-factor

#### Scenario: Reference and LLM arm differ only in LLM keys
- **WHEN** the guard test diffs the reference arm's dictionary against the LLM arm's
- **THEN** every differing key SHALL be an LLM key
- **AND** no MOP weight, frontier, or RV exploration flag SHALL differ

#### Scenario: Source components flag is explicit in all three arms
- **WHEN** the guard test iterates the three decisive-run arms
- **THEN** each SHALL set `mop_activity_source_components=true` explicitly
- **AND** none SHALL rely on the jar default

#### Scenario: The LLM arm is inside the LLM key guard
- **WHEN** the `LLM_ARM_KEYS` guard collects the variants it audits
- **THEN** `mop_on_llm_70` SHALL be among them despite not carrying the `cal_` prefix
- **AND** the guard SHALL fail if any key of `LLM_ARM_KEYS` is left implicit in that arm

### Requirement: Snap Tolerance Gating on the Dead-Pair Ban (FR19, FR20)

`aperv-tool` SHALL apply `llm_snap_tolerance_px=150` only in an arm that also declares the git sha of the `ape-rv.jar` build containing the dead-pair ban (item B1 of the sister change `telemetry-proof-llm-efficacy`). Widening the snap radius makes more LLM answers resolve to a widget; without the ban, the additional resolutions include repeated taps on pairs already known to produce no new state, so the wider radius amplifies the measured 25.6% dead-call waste instead of rescuing near-misses. With the ban in place the same widening rescues genuine near-misses only.

The gate SHALL be a **declaration in the arm plus a verification against reality**, not a claim the tool can check by itself. The jar cannot be introspected from Python for this purpose: the build provenance is a generated Java constant dexed into `classes.dex`, deliberately not a packaged resource, because `d8` converts only `.class` entries and would drop a resource from the output jar (INV-BUILD-09 in the `ape` repository). The only readable form of the stamp is the `[APE-BUILD]` banner the agent emits once per session, which carries `git_sha`, `jar_built`, and `schema` (INV-BUILD-11).

The gate therefore has two halves. At configuration time, an arm carrying `llm_snap_tolerance_px=150` SHALL also carry the expected jar git sha, and a guard test SHALL fail when one is present without the other — this makes the coupling visible in the source and enforced by the suite rather than left to the operator's memory. At verification time, the `git_sha` observed in the run's `[APE-BUILD]` banner SHALL be compared against the declared value, and a mismatch SHALL fail the smoke gate before the decisive run starts (INV-APV-34).

#### Scenario: Tolerance and jar declaration travel together
- **WHEN** the guard test inspects an arm containing `llm_snap_tolerance_px=150`
- **THEN** the arm SHALL also declare the expected jar git sha
- **AND** the test SHALL fail naming INV-APV-34 when the tolerance is present without the declaration

#### Scenario: Declaration without the raised tolerance also fails
- **WHEN** the guard test inspects an arm declaring an expected jar git sha but leaving `llm_snap_tolerance_px` at 50
- **THEN** the test SHALL fail, because a dangling declaration is a stale coupling that will silently mislead the next reader

#### Scenario: Observed banner contradicts the declaration
- **WHEN** the smoke run's `[APE-BUILD]` banner reports a `git_sha` different from the arm's declared value
- **THEN** the smoke gate SHALL fail naming both shas
- **AND** the decisive run SHALL NOT be launched with that configuration

#### Scenario: Tolerance stays at the jar default when no arm declares the ban
- **WHEN** no arm declares an expected jar git sha
- **THEN** `llm_snap_tolerance_px` SHALL remain at the jar default of 50 (`Config.java:223`)
- **AND** the run provenance SHALL record that the raise was not applied

### Requirement: Per-Run LLM Backend Provenance (FR19, NFR06)

`aperv-tool` SHALL record, at the start of every run that uses an LLM, the backend actually serving that run. The record SHALL be obtained by querying the OpenAI-compatible `/v1/models` endpoint at the configured `llm_url`, and SHALL be written into the task output alongside the run's other results.

The query is required rather than reading configuration because the failure mode this requirement exists to prevent is precisely the case where configuration and reality disagree: a server restarted with a different model, a different quantization, or different sampling defaults produces results that the configuration cannot distinguish from the intended ones. A live query is the only evidence of what actually served the run (INV-APV-33).

The provenance capture SHALL apply to any experiment — calibration and the real thesis experiment alike — because both consume the same arm definitions and both need the same auditability.

A failed query SHALL NOT abort the run: the provenance fields SHALL record the failure explicitly so downstream analysis can distinguish "not recorded" from "recorded as X", and SHALL NOT be filled in from configuration.

#### Scenario: Backend recorded from a live query
- **WHEN** a run with an LLM arm starts and `GET {llm_url}/v1/models` returns a model list containing `Qwen/Qwen3-VL-4B-Instruct`
- **THEN** the task output SHALL record that model identifier
- **AND** it SHALL record the backend endpoint and the sampling parameters in effect for the run

#### Scenario: Query failure is recorded, not inferred
- **WHEN** the `/v1/models` query fails with a connection error
- **THEN** the run SHALL proceed
- **AND** the provenance fields SHALL record the failure explicitly
- **AND** they SHALL NOT be populated from the configured model name (INV-APV-33)

#### Scenario: Non-LLM arms need no query
- **WHEN** a run uses an arm with no LLM keys
- **THEN** no `/v1/models` query SHALL be issued
- **AND** the absence of provenance fields SHALL NOT be treated as a failure

### Requirement: Offline Clock-to-Violation Join (FR11, FR13, NFR03)

`aperv_tool` SHALL provide a utility that joins a run's step clock against the `RVSEC:` violation lines recorded for that run, producing per-run rows that correlate when the exploration reached a given point with when a monitor fired.

The utility exists to test the premise the whole MOP-frontier mechanism rests on: that *reaching* a MOP screen is sufficient to fire its monitor. That premise is plausible — the monitored operation fires in `onCreate` for 84% of the apps and UI handlers account for 0.4% of direct reach — but it has never been measured, and if it is false the frontier mechanism is steering toward screens that need interaction rather than arrival. The join is also the evidence base for the deferred decision on reading logcat at runtime (item N5): it establishes what signal a runtime reader would have had, and with what latency, before any runtime mechanism is proposed.

The utility SHALL live in the `aperv_tool` package rather than in a per-campaign script directory, because the real thesis experiment consumes it, not only the calibration campaign. It SHALL be offline and read-only over recorded artifacts, and SHALL NOT read logcat from a device or require an emulator (INV-APV-35).

#### Scenario: Join reproduces the recorded corpus totals
- **WHEN** the utility runs over the recorded iter0 corpus of 880 runs
- **THEN** it SHALL account for 9,586 `RVSEC:` lines
- **AND** those lines SHALL be distributed across exactly 605 runs and 32 distinct APKs
- **AND** a mismatch in any of the three totals SHALL fail the validation gate

#### Scenario: Run with no violations produces an empty but valid result
- **WHEN** the utility runs over one of the 275 iter0 runs with no `RVSEC:` lines
- **THEN** it SHALL produce a row set with zero violations for that run
- **AND** it SHALL NOT raise, and SHALL NOT omit the run from the report

#### Scenario: Artifacts are never modified
- **WHEN** the utility completes over any run directory
- **THEN** every artifact it read SHALL be byte-identical to its prior content (INV-APV-35)

#### Scenario: Missing run directory is a usage error
- **WHEN** the utility is invoked against a path that does not exist
- **THEN** it SHALL exit with status 2
- **AND** the message SHALL name the missing path

### Requirement: Offline Coverage-Dump Parser at Activity Grain (FR11, NFR03, NFR06)

`aperv_tool` SHALL provide a versioned, offline, read-only parser for the coverage dump emitted by the jar — the `[APE-RV] UICOV` (per state) and `[APE-RV] UICOV-ACT` (per Activity) lines — producing per-run rows consumable by the analysis path.

The parser exists because the dump has **no automated consumer today**: a search for `UICOV` across the whole rv-android tree returns zero hits in Python, and the only historical consumption was manual. The sister change (`ape`, `telemetry-proof-llm-efficacy`, item A10) hoists the dump to the front of the teardown chain, which recovers it in 333 of the 338 runs that lose it today; without a parser that recovery yields data nothing reads.

**Activity grain is mandatory, not a preference.** The per-state `UICOV` key embeds `StateKey.toString()`, whose hash includes the JVM identity hash of a `Naming` object that overrides neither `equals` nor `hashCode`. State keys are therefore not comparable across runs: the measured Jaccard between replicas of the same `(APK, arm)` is **0.000 — mean, median and maximum**, meaning not one state line in the corpus pairs with its counterpart in the other replica. Anything the parser reports across runs, replicas or arms SHALL be derived from `UICOV-ACT`; `UICOV` lines MAY be parsed for intra-run use and SHALL NOT be aggregated across runs.

**Partial dumps are valid input.** Hoisting the emission does not make it atomic — 3 of the 462 runs that dump today are truncated mid-`UICOV-ACT`. The parser SHALL accept a truncated final line as a partial dump, retain every complete line preceding it, and mark the run as partial rather than discarding it.

**Line format.** `gap` carries one decimal place under `Locale.ROOT` and SHALL NOT be used as a computation source; `discovered` and `interacted` are integers and are the authoritative fields. `byType` is `TYPE:interacted/discovered`. Note that `mopReach` appears on the `UICOV` line and **not** on `UICOV-ACT`, so MOP reach is not reconstructible at Activity grain from the current jar; the parser SHALL report its absence rather than infer it.

#### Scenario: Cross-run aggregation uses Activity grain only
- **WHEN** the parser aggregates coverage across two runs of the same APK and arm
- **THEN** it SHALL join on `UICOV-ACT` activity names
- **AND** it SHALL NOT join on `UICOV` state keys, whose cross-run pairing rate is measured at zero

#### Scenario: Truncated dump is retained as partial
- **WHEN** a run's trace ends mid-way through a `UICOV-ACT` line
- **THEN** the parser SHALL emit rows for every complete line that precedes it
- **AND** SHALL flag the run as carrying a partial dump

#### Scenario: Run without a dump is reported, not dropped
- **WHEN** a run carries no `UICOV` or `UICOV-ACT` line at all
- **THEN** the parser SHALL report that run with an explicit no-dump marker
- **AND** SHALL NOT silently omit it, so that any coverage rate computed downstream carries its own denominator

#### Scenario: Artifacts are never modified
- **WHEN** the parser completes over any run directory
- **THEN** every artifact it read SHALL be byte-identical to its prior content

*(The capture grace window is specified as an amendment of `ApeRVTool Execution Flow` under `## MODIFIED Requirements`, because the `+15 s` value it replaces is stated inside that requirement and in the `RVToolTimeoutError` contract. An ADDED requirement would have left both standing.)*
