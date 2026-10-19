# Specification: ApeRV Tool

## Purpose

`aperv-tool` is an rv-platform external tool module that wraps the APE-RV binary (`ape-rv.jar`) for integration into the rv-android experiment framework. APE-RV is an enhanced fork of APE (Ape Explores Apps, ICSE 2019), a model-based Android UI exploration tool that uses adaptive random testing with a Widget Table Graph model. The enhanced version adds AndroidX ViewPager support, systematic OptionsMenu exploration (`MODEL_MENU` action), optional MOP-guided action scoring from static analysis data, optional LLM-guided action selection via an SGLang server, and probabilistic component triggering for Services and BroadcastReceivers.

APE-RV mounts these mechanisms in five behaviour groups. BASE is the APE algorithm, ADDONS holds the fork's own improvements, STATIC holds the consumers of the static GUI model, MOP holds the consumers of the specification targets, and LLM is the vision-language model. A **cell** is a union of groups, and the jar ships one preset per cell: `base`, `mop`, `as` (ADDONS + STATIC), `as_mop`, `as_llm` and `as_mop_llm`. What a group switches on is defined in the jar, so each `aperv` variant names a cell and supplies only what the jar cannot know: the server URL, the static-analysis artifact and the variant name the jar echoes into `RUN_START`. The one exception is the MOP coin's ledger budget, which the three MOP cells set to 2 on this side while the jar's default stays 1 (author's decision, 2026-10-19). The ablation variant `mop_nolaunch` runs the `mop` cell without its launcher, and `default` is bound to `base`.

The tool runs on the Android device using the `app_process` execution model. The JAR is pushed to `/data/local/tmp/ape-rv.jar` via ADB, and execution is launched via `adb shell CLASSPATH=... /system/bin/app_process /system/bin com.android.commands.monkey.Monkey`. This execution model is necessary because APE requires internal Android APIs (`android.app.UiAutomationConnection`, `android.hardware.display.DisplayManagerGlobal`) that are inaccessible from the host via `adb shell monkey`.

The module is a uv workspace member, auto-discovered by `members = ["modules/*"]` in the root `pyproject.toml`. rv-platform declares `aperv-tool` as a dependency, because its `_register_external_tools()` imports the module (`tools` INV-TOOL-26). The only workspace dependency of `aperv-tool` is `rv-android-core`, which provides `AbstractTool` and `ToolSpec`. The `ImportError` guard in `_register_external_tools()` covers a module that is present but fails to import: rv-platform logs a warning and keeps working with the other tools, and the `aperv` tool is absent from the registry.

The lazy import of `rv_coverage.parser.log.diagnostic_parser` in `aperv_tool/analysis/step_bundle.py` is not declared, on purpose. The diagnostic stream is opt-in on the capture side (`RV_LOGCAT_DIAGNOSTICS`), and a missing parser degrades to "not read" instead of breaking every bundle.

Coverage metrics (method calls, MOP violations) are collected by the rv-android Python infrastructure via logcat `RVSEC-COV` tags -- the same pipeline used by all other tools. No special output parsing is required.

### APE-RV Java Capabilities

The `ape-rv.jar` binary supports several capabilities that `aperv-tool` configures via `ape.properties`:

1. **MOP-Guided Scoring**: When `ape.staticDataPath` points to the derived compact MOP artifact on the device, APE-RV reads the widget-to-MOP mappings it already carries and applies priority boosts (+500 direct, +300 transitive, +100 activity-level) to actions whose handlers reach monitored operations. This biases exploration toward code paths under runtime verification. The device receives only that artifact and never the full static-analysis JSON (INV-APV-46): the derivation the jar used to perform at load time — per-widget MOP flags, the two MOP-activity sets, the OPTIONSMENU gateway inputs, the click-only WTG view and the component trigger surface — happens host-side, so the call-graph section that dominates the file never crosses to the device and no on-device parse footprint guard can abort a MOP cell at 0 steps while the baseline explores normally.

2. **LLM-Guided Action Selection**: When `ape.llmUrl` points to an SGLang server, APE-RV captures screenshots and consults a vision-language model (Qwen3-VL) at two decision points: (a) first visit to a new state (`llmOnNewState`), and (b) stagnation midpoint (`llmOnStagnation`). A probabilistic mode (`llmPercentage`) routes a configurable fraction of steps through the LLM. A circuit breaker (3 failures, 60s recovery) protects the exploration loop from cascading LLM failures. All LLM failures fall back to SATA transparently.

3. **Component Triggering**: When MOP data includes a `components{}` section with receivers and services, APE-RV probabilistically fires broadcast intents and starts services during exploration. A `system-broadcast.json` catalog provides typed extras for known system broadcast actions.

4. **Prompt Variants**: The `llm_prompt_variant` property selects which prompt template APE-RV uses for LLM calls (e.g., `ape_current`, `ape_reasoning`, `compact_v1`, `v13`, `v17`, `visual_only`), enabling controlled prompt ablation experiments.

### Relationship with Other Domains

- **rv-platform**: Consumes `ApeRVTool` via `ToolFactory.create_tool()` in `ToolExecutionComponent`. Registration via `_register_external_tools()`.
- **rv-experiment**: Orchestrates experiments using `aperv` tool variants. APK instrumentation and static analysis happen in pre-processing; `aperv-tool` receives the instrumented APK already installed on the emulator.
- **rv-static-analysis**: Produces the full static-analysis JSON that every cell except `base` derives its artifact from. It maps activities to widgets with MOP reachability flags and includes component data for triggering, and it remains the host-side source of truth: `aperv-tool` reads it, never writes to it, and projects it into the compact artifact the device receives. It also stays the sole input to offline metrics, which read the full document rather than the projection (`analysis` INV-ANA-53, INV-ANA-54).
- **rv-tools**: Holds the `ToolRegistry` and `ToolFactory` that register and instantiate `ApeRVTool`, reached through rv-platform. `aperv-tool` imports nothing from rv-tools and does not declare it: `ApeRVTool` subclasses `AbstractTool` and uses `ToolSpec` from rv-android-core (`rv_android_core.tools.abstract_tool`).
- **builtin ape tool**: Shares `process_pattern` (`com.android.commands.monkey`). The two tools must not run concurrently on the same device.

## Data Contracts

### Input

- `task.config.device_id: str` -- ADB device serial (default `"emulator-5554"`)
- `task.config.timeout: int` -- exploration duration in seconds (default 300)
- `task.result.trace_file: str` -- path where stdout/stderr from APE-RV is written
- `task.results_dir: str` -- directory containing static analysis JSON (for every cell except `base`)
- `task.config.apk_name: str` -- APK filename used to locate the static analysis JSON
- `app.package_name: str` -- Android package name passed to APE's `-p` flag
- `self._tool_config: Dict[str, Any]` -- resolved variant configuration from `configure()`
- `variant dict: Dict[str, Any]` -- per cell: `preset: str` (one of `base`, `mop`, `as`, `as_mop`, `as_llm`, `as_mop_llm`), `variant: str` (the cell's own name), `overrides: Dict[str, Any]` (the server URL on the two LLM cells and `mop_coin_ledger_max_interactions: 2` on `mop`, `as_mop` and `as_mop_llm`, otherwise empty), `strategy: "sata"`, `static_data: "static_analysis"` on every cell except `base`, and `broadcast_catalog: True` on the four cells that mount STATIC; the ablation variant `mop_nolaunch` is the `mop` cell with `variant: "mop_nolaunch"` and `activity_trigger_enabled: False` added to its `overrides` (source: `ApeRVTool.get_variants()`, merged with experiment parameters by `ToolFactory`). No variant declares the revision or the digest of an `ape-rv.jar` build (INV-APV-59)
- `tool_config.parameters: Dict[str, Any]` -- tool-DSL overrides (`aperv:<variant>@key=value`), merged **at the top level** over the variant dict by `ToolFactory` (`registry/factory.py:127`) and folded into `overrides` by `configure()` (INV-APV-39)
- `APERV_PROPERTY_MAPPING: Dict[str, str]` -- 67 entries: override key → `ape.*` property name; contains only keys the deployed jar accepts (source: `tool.py` module constant)
- `<ape>/src/test/resources/cells/<cell>.run_start.json` -- the jar's expected `RUN_START` per cell, with `run_id`, `t0`, `seed`, `build` and `props_digest` masked (source: the `ape` repository; read by the cell gate tests only, never at run time)
- preset vectors and the accepted-key vocabulary -- read from the `ape` source checkout (`runtime/Presets.java`, `runtime/KeyOwnership.java`) by the migration tooling only; not a runtime dependency of `aperv-tool`
- `ape-rv.jar` -- Dalvik JAR resolved at execution time via priority search
- `system-broadcast.json` -- optional broadcast catalog file shipped alongside the tool module
- `<task.results_dir>/<task.config.apk_name>.json` -- static-analysis document produced by `rvsec-analysis-client.jar`. Sections consumed by the handler-reach enrichment: `windows[].widgets[].listeners[].handler` (handler signatures) and `reachability[].methods[]` (`signature`, `reachable`, `reachesTarget`, `directlyReachesTarget`)
- `llm_url: str` -- OpenAI-compatible base URL already held by the tool configuration; the source of the `/v1/models` provenance query (LLM cells)
- `corpus_basis: str` -- optional key identifying the application list a run was drawn from, supplied through the same configuration path as any other mapped key and resting at `self._tool_config["overrides"]["corpus_basis"]`, which is where validation reads it. The nesting is not incidental: `configure()` folds every `APERV_PROPERTY_MAPPING` key from the top level of the configuration into `overrides` before validating anything, so an arm that declares the basis in its own `overrides` dict and a campaign that supplies it as an `@corpus_basis=…` DSL parameter arrive at the same place, and one rule covers both. Format `<corpus-id>:<sha256>`, where `<corpus-id>` is a short human-readable identifier of the list (e.g. `subset40`) and `<sha256>` is the lowercase hexadecimal SHA-256 of the list file's bytes
- Recorded run artifacts for the offline join and the coverage-dump parser: per-run trace files carrying the step clock and the `[APE-RV] UICOV`/`UICOV-ACT` dump lines, and the logcat lines matching `RVSEC:`
- `reachability[].methods[].{signature, reachesTarget, directlyReachesTarget}` — from the full `.apk.json`; wrappers now carry their own flags (source: GATOR, `analysis` INV-ANA-77)
- `windows[]` of types `ACTIVITY`, `DIALOG`, `OPTIONSMENU`, `FRAGMENT`, `HOSTED` (source: GATOR)
- `distanceTargets: list[{signature, kind}]` — top-level key of the full `.apk.json`; only its length is read (source: GATOR, gh120)
- `reachability[].methods[].targetDistances: list[[int, int]]` — per-method pairs `[i, d]`, `0 ≤ d ≤ 10`, omitted when empty (source: GATOR, gh120); `name` excludes `<init>`/`<clinit>` from the A′ source 3 and from `activityDist`
- Trace records of the group-isolation jar (`RUN_START.v == 2`; source: the jar's `NdjsonSink` and `RunSpecEcho`), read by the offline `TraceReader`:
  - `RUN_START.variant: str`, omitted when the jar received no `ape.variant`;
  - `dec.src: str` — one of `budget`, `restart`, `llm`, `launcher`, `mop`, `sata` (the owner that took the step); on a `v == 1` trace, the stage whose boost was largest;
  - `dec.ch: str` — `mop_coin`, `budget`, `restart`, `launcher`, `llm` or one of the SATA channels;
  - `dec.own: {"i": str, "trg"?: "new_state"|"stagnation"|"coin", "uL"?: float, "uM"?: float, "g"?: "min_actions"|"breaker", "fb"?: "gate"|"screenshot"|"error"|"decline"|"no_match"|"ineligible"}` — written on every step record;
  - `dec.cfc: {<scorer>: 0|1}` over `mop`, `mopf`, `wtg`, `navf`, `cov`, `menu`, `form`;
  - `dec.draw: [int, int]`; `dec.nav: {"x": "X1"|"X3"|"X4", "c": "ape"|"mop", "alt": 0|1, "drew": 0|1}`;
  - `dec.trig: {"k": "broadcast"|"service"|"provider", "c": str}`; `dec.inp: "typed"|"heuristic"|"random"|"form"|"llm"`; `dec.restart: "graph"|"state"|"activity"|"periodic"`;
  - `dec.bmc: int`; `dec.strat: str` (one of the fifteen SATA path names); `dec.rot: int` in `-1..3`; `dec.buf: str` (an owner name);
  - `dec.navf: int`; `dec.mopd: int`; `dec.mops: "s"|"i"`; `dec.ret: [int, …]`; `dec.hnd: str` (the binary class name of the handler stamp, written exactly when `dec.mops` is `"s"`);
  - `RUN_END: {reason, detail?, steps, t_first_step?, t_last_step?, counters: {acts, states, stampNodes, stampHits, retired, launches, gateMinActions, gateBreaker, guardBacks, bufAbandoned, restarts, coinLlm, coinMop, nullRelaunches, llm?: {…}}}`

### Output

- `task.result.trace_file` -- populated with APE-RV stdout+stderr (binary write mode)
- `ape.properties` on device -- `ape.preset=<cell>` first, `ape.variant=<variant>` second, `ape.staticDataPath=/data/local/tmp/mop-artifact.json` third when the artifact was pushed, then one `ape.<key>=<value>` line per `overrides` entry in mapping order (destination: `/data/local/tmp/ape.properties`, consumed by the jar's key resolution)
- Task output provenance fields: `llm_backend`, `llm_model`, `llm_sampling` -- recorded per run (LLM cells)
- Join report (A9): per-run rows correlating step clock positions with `RVSEC:` violation timestamps
- Per-run coverage rows at Activity grain from the offline coverage-dump parser, each carrying an explicit dump status (complete, partial, or absent)
- `ape.corpusBasis=<corpus-id>:<sha256>` -- one line appended to the generated `ape.properties`, pushed to `/data/local/tmp/ape.properties`. Consumed by the jar's resolver, echoed into `RUN_START.corpus_basis`, and read by no runtime component on either side
- `*.mop.json` with `formatVersion: 2`, `source.generator: "aperv-derive/2"`, and the members `targets: int`, `widgets.<a>.<id>.dist: {event: [[i, d], …]}`, `activityDist: {activity: [[i, d], …]}`, `handlers: {class: {mop: {event: flag}, dist: {event: [[i, d], …]}}}`; a listed wrapper whose own flags are false is `none` (destination: APE-RV `MopData`, `ape` `llm-coordinate-single-base`)
- `ape.properties` lines `ape.mopWeightD1..3`, `ape.mopRetireAfter`, `ape.mopLauncherDmax` only when a DSL override sets them (destination: the jar's plan resolution)
- `TraceReader.run_end: Optional[Dict[str, Any]]` -- the `RUN_END` record minus `type`, verbatim; `None` when the trace carries none (destination: offline analysis)
- `StepRow` -- carries `owner`, `scorer_cf`, `draw`, `nav`, `input_source`, `restart_kind`, `back_menu_capped`, `sata_path`, `rotation`, `buffer_abandoned_by`, `component_trigger`, `nav_frontier`, `mop_distance`, `mop_stamp`, `retired_targets`, `mop_handler` (destination: `analysis/*` consumers and the baseline frames, which write `None` for each)
- `RunStart.variant: Optional[str]` -- the jar's echo of `ape.variant`

### Side-Effects

- **[Device]**: `ape-rv.jar` pushed to `/data/local/tmp/ape-rv.jar`
- **[Device]**: `system-broadcast.json` pushed to `/data/local/tmp/system-broadcast.json` on the four cells that mount STATIC (`as`, `as_mop`, `as_llm`, `as_mop_llm`), if the file exists in the module directory; never on `base` or `mop`
- **[Device]**: `/data/local/tmp/mop-artifact.json` receives the derived compact MOP artifact -- every cell except `base`. One pushed file per run, and never the full static-analysis JSON (INV-APV-46)
- **[Host filesystem]**: one cached `<task.results_dir>/<task.config.apk_name>.mop.json` per (apk, full-JSON digest, format), written atomically in canonical bytes and regenerated transparently when missing or stale
- **[Filesystem]**: `<task.results_dir>/<task.config.apk_name>.json` is read and never written
- **[Device]**: `ape.properties` pushed to `/data/local/tmp/ape.properties` (when `_tool_config` is non-empty); the pushed file gains one `ape.corpusBasis` line when a corpus basis is configured, and no other device state changes
- **[Trace]**: `RUN_START.corpus_basis` becomes present in every trace of a run configured with a corpus basis
- **[Trace]**: `RUN_START.variant` is present in every trace of an `aperv` run
- **[Logcat]**: APE-RV writes `RVSEC-COV` log lines during execution (read by rv-android coverage infrastructure)
- **[Network]**: LLM cells send HTTP requests from the emulator to the SGLang server (via `10.0.2.2` loopback or overridden URL)
- **[Network]**: one `GET /v1/models` per LLM-cell run at preflight time (backend provenance)
- **[Filesystem]**: the offline join utility and the coverage-dump parser read recorded artifacts and write their reports; they never write into `results/` trees they did not create

### Error

- `ConfigurationError` -- raised by `configure()` when `strategy` is absent or outside `["sata", "random"]`, when `preset` or `variant` is absent or empty, when `overrides` is not a dict, when a top-level key is neither mapped nor a recognised orchestration key (INV-APV-39), when an `overrides` key has no `APERV_PROPERTY_MAPPING` entry, and when `corpus_basis` is present but does not match `^[A-Za-z0-9._-]+:[0-9a-f]{64}$`. All are raised before any device interaction, so a malformed value costs no emulator time and produces no partially-configured run
- Jar-side abort -- an unknown key, a retired key, an invalid type, or a non-neutral value of an inactive feature aborts the run before step 1; visible in the trace, never silent. A properties file that still sets `ape.mopDataPath`, `ape.mopTargetPickCap` or `ape.leastVisitedPriorityTiebreak` aborts with `retired_key`
- `RVToolExecutionError` -- raised when `ape-rv.jar` cannot be found in any search path, when an ADB push fails, when a cell other than `base` has no full JSON or its derivation fails, or when the exploration returns materially short of its budget (INV-APV-60). The `base` cell is unaffected by the artifact cases
- `DerivationError` -- raised by `derive()` when the document is structurally unusable (not an object, missing `package`, a section of the wrong type). The absence or falsity of `complete` is NOT among the causes. No partial artifact is produced; the caller re-raises it as `RVToolExecutionError`
- `RVToolTimeoutError` -- raised when execution exceeds `task.config.timeout + 45` seconds (expected normal exit for exploration tools)
- `SystemExit(2)` -- the offline clock-to-violation join utility on usage error (missing or unreadable run directory)
- Provenance query failures are non-fatal: the run proceeds and the provenance fields record the failure rather than a fabricated value (INV-APV-33)
- Streaming-read failure -- an unreadable, non-UTF-8, unparseable or truncated full JSON fails in the streaming read of `_derive_mop_artifact` on a cache miss and is raised as `RVToolExecutionError` before `derive()` is reached (INV-APV-64)

## Invariants

- **INV-APV-01**: `ApeRVTool` SHALL locate `ape-rv.jar` using `JarResolver` with search paths in priority order: (a) `os.path.dirname(__file__)` -- module directory populated by `mvn install`, (b) `$RVSEC_HOME/ape/target/` -- development Maven build, (c) `$TOOLS_DIR/aperv/` -- manual placement. First match wins. If no path resolves, a `RVToolExecutionError` SHALL be raised listing all searched paths.

- **INV-APV-02**: `ApeRVTool.configure()` SHALL validate that the `strategy` key exists in `config` and its value is one of `["sata", "random", "bfs", "dfs"]`. An absent or invalid strategy SHALL raise `ConfigurationError` before any device interaction.

- **INV-APV-03**: `ApeRVTool` SHALL use device path `/data/local/tmp/ape-rv.jar` (not `/data/local/tmp/ape.jar`) to avoid collision with the builtin `ape` tool's device artifact.

- **INV-APV-04**: The `app_process` working directory SHALL be `/system/bin` (not `/data/local/tmp/`). The enhanced APE binary references system-level resources relative to its working directory during startup; using `/data/local/tmp/` causes startup failures. This intentionally diverges from the builtin `ape` tool, which uses `/data/local/tmp/` as working directory.

- **INV-APV-05**: `get_variants()` SHALL return a dict whose keys are exactly `default`, `base`, `mop`, `as`, `as_mop`, `as_llm`, `as_mop_llm` and the ablation variant `mop_nolaunch`, with `default` bound to the same object as `base` (INV-TOOL-02).

- **INV-APV-06**: every cell except `base` SHALL set `static_data` to `"static_analysis"`. When `static_data == "static_analysis"`, `execute_tool_specific_logic()` SHALL locate the full static-analysis JSON, obtain the derived compact artifact from it (cache-or-generate), and push only that artifact. If the JSON is not found, or its derivation fails, the task SHALL fail before the jar is launched (INV-APV-45).

- **INV-APV-07**: `ApeRVTool.TOOL_SPEC.process_pattern` SHALL be `"com.android.commands.monkey"`. This is the same value used by the builtin `ape` tool. `AbstractTool.kill_related_processes()` uses this pattern to terminate device-side processes after execution. As a consequence, `ape` and `aperv` MUST NOT run concurrently on the same device -- each cleanup would terminate the other's process. Experiments using `aperv` SHALL NOT include the builtin `ape` tool in the same run.

- **INV-APV-08**: `ape.properties` generation SHALL use `APERV_PROPERTY_MAPPING` to translate the `overrides` keys. Python-only keys (`strategy`, `static_data`, `seed`, the three device-addressing keys) have no mapping entry and are never written; `preset` and `variant` are written by their own fixed lines.

- **INV-APV-09**: the LLM cells (`as_llm`, `as_mop_llm`) SHALL carry `http://10.0.2.2:30000/v1` as their default `llm_url`; `10.0.2.2` is the Android emulator's alias for the host loopback interface. The `APERV_LLM_BASE_URL` environment variable SHALL replace that default when set, through the `rv-experiment` entry point and `ToolConfig.parameters`, never through a read in this module (INV-TOOL-20). A DSL `@llm_url` SHALL win over the variable. A cell without the LLM group SHALL NOT receive `llm_url` from the variable.

- **INV-APV-10**: `system-broadcast.json` SHALL be pushed when it is present in the module directory and the variant carries `broadcast_catalog=True`, and SHALL NOT be pushed otherwise. `broadcast_catalog` SHALL be `True` exactly on the cells whose preset mounts STATIC, because the catalog's only reader in the jar is `COMPONENT_TRIGGER`, a STATIC member (`ape` D-B13). When the catalog is absent from the module directory the jar degrades gracefully: component triggering proceeds without typed extras for system broadcasts.

- **INV-APV-11**: Timeout is ALWAYS controlled by `task.config.timeout` (set by rv-platform). The `running_minutes` passed to APE is derived from `max(1, task.config.timeout // 60)`. Variants MUST NOT hardcode a timeout.

- **INV-APV-12**: Non-zero exit codes from APE-RV SHALL NOT be treated as failures. APE-RV exits with non-zero codes when it detects app crashes during exploration (e.g., exit code 211). Coverage is collected via logcat regardless. Only `RVCommandTimeoutError` is re-raised as `RVToolTimeoutError`.

- **INV-APV-18**: When a `seed` is present in `_tool_config`, `_build_main_command` MUST append `-s <seed>`
  to the `app_process` argument vector (after `--ape <strategy>`). When no seed is configured, the command
  MUST NOT include `-s` (preserving the current non-deterministic default). The seed value is passed
  verbatim as a string. The `mop-fairtest` jar honors this seed (it parses `-s SEED` and seeds both
  `Monkey.mRandom` and APE's `RandomHelper`, INV-EXPL-14); this invariant closes the rv-android-side gap
  that previously dropped the seed.

- **INV-APV-33**: Backend provenance SHALL be obtained from a live `/v1/models` query performed at the start of each run, never from static configuration. When the query fails, the provenance fields SHALL record the failure explicitly; the run SHALL NOT be aborted and a value SHALL NOT be inferred from configuration.

- **INV-APV-35**: The clock↔logcat join SHALL be an offline, read-only computation over recorded artifacts. It SHALL NOT read logcat from a running device, SHALL NOT require an emulator, and SHALL NOT modify any artifact it reads.

- **INV-APV-36**: Any coverage figure aggregated across runs, replicas or arms SHALL be derived from `UICOV-ACT` (Activity grain). `UICOV` state keys SHALL NOT be used as a cross-run join key — they embed a JVM identity hash whose measured cross-replica pairing rate is zero (Jaccard 0.000 at mean, median and maximum).

- **INV-APV-37**: The coverage-dump parser SHALL report every run in its input with an explicit dump status — complete, partial, or absent — and SHALL NOT omit a run for lacking a dump. Any coverage rate it produces SHALL carry the denominator it was computed over, so that a figure computed on the runs that dumped is never mistaken for a figure over all runs.

Numbering note: `INV-APV-38` through `INV-APV-44` are deliberately left free for `gh95-thin-python-arms`,
which the sibling `ape` change already references by number.

- **INV-APV-45**: a variant configured with `static_data == "static_analysis"` SHALL either push a freshly validated derived artifact and write `ape.staticDataPath`, or fail the task before the jar is launched. There SHALL be no execution path in which such a variant launches the jar without `ape.staticDataPath` set.

- **INV-APV-46**: The device SHALL only ever receive the derived compact artifact. No code path SHALL
  push the full static-analysis JSON, under any cache state or failure mode.

- **INV-APV-47**: Cache freshness SHALL be keyed on the source digest and the format. A cached `<apk_name>.mop.json` is reused only when its recorded `source.digest` equals the SHA-256 of the current full JSON **and** its `formatVersion` equals `FORMAT_VERSION`. Cache state SHALL NOT change what the device receives for a given full JSON and generator.
- **INV-DRV-01**: Widget MOP flags SHALL be derived per listener and per normalized `eventType` and
  OR-aggregated across a widget's listeners. The two axes SHALL remain independent and SHALL NOT be
  collapsed into each other: `direct` is the handler's own `directlyReachesTarget` (a monitored
  operation invoked in the handler's own body) and `transitive` is its `reachesTarget` OR `direct`,
  so `direct` implies `transitive` and the converse does not hold. A producer-supplied
  `handlerReachesTarget`/`handlerDirectlyReachesTarget` pair takes precedence over the local
  cross-reference when either is non-null. A handler with no exact `reachability[].methods[].signature`
  match that is a D8 synthetic-lambda wrapper (`X$$ExternalSyntheticLambdaN`) SHALL be recovered from
  `X`'s reaching `lambda$…` methods, and SHALL NOT be flagged when `X` has no reaching lambda method.
- **INV-DRV-02**: On a `shortId` collision within a base activity the emitted widget SHALL carry the
  strongest MOP flag (direct > transitive > unflagged), ties keeping the first occurrence, so the
  outcome is independent of iteration order. Widgets with an empty short id SHALL NOT be emitted and
  the count of MOP-flagged widgets so dropped SHALL be recorded in `stats.droppedFlaggedNoId`. **A
  MOP-flagged widget SHALL add its base activity to the widget-derived MOP-activity set before the
  empty-short-id drop is applied**: the widget is unscorable, the activity is not.
- **INV-DRV-03**: DIALOG windows SHALL be merged into their host activity — first incoming transition
  wins, `mopRank` collision policy, the dialog's widget-map key is moved and not copied, a flagged
  merge adds the host to the widget-derived activity set, and the dialog class's own activity-set
  entry is retained. WTG edges SHALL be keyed by base source activity with base target activities,
  click events only, exact duplicates removed. Orphan dialogs SHALL be counted in
  `stats.orphanDialogs`.
- **INV-DRV-04**: All `stats` fields SHALL be pure counters over the derivation. Their values SHALL
  NOT influence any emitted set, flag or edge.
- **INV-DRV-05**: Derivation SHALL be deterministic at the byte level: identical full-JSON input bytes
  SHALL yield an identical artifact byte sequence, on any host and in any process.
- **INV-DRV-06**: The artifact SHALL contain no call-graph data: no `reachability` section, no method signature, no call edge, no raw `windows`/`transitions`/`listeners`/`distanceTargets`. It SHALL contain no `*Target` key other than `hasTargetMethods` on receivers and services. That single exception is deliberate: it is the boolean the `targetMethods` signature list compacts to, its name is fixed by the jointly defined wire format, and the jar reads it by that name. Format 2 MAY carry integer target indices and integer distances (`targets`, `dist`, `activityDist`, the `dist` of a `handlers` record) and binary class names (the keys of `handlers`). A target index is joined to its signature only offline, through `source.digest` and the full JSON it names. The full JSON SHALL remain unmodified on the host.
- **INV-DRV-07**: Each emitted activity SHALL carry `deepLinkUri` derived by the rule the jar applies
  today; the intent-filter structure itself SHALL NOT be on the wire.

- **INV-DRV-08**: `derive()` SHALL NOT read `document["complete"]` for any control-flow decision. A
  document whose sections are well-typed SHALL yield an artifact regardless of the sentinel's
  presence, falsity or absence. WTG absence SHALL be expressed as an empty `wtg` map with
  `stats["wtgEdges"] == 0`, never as a refusal.

- **INV-DRV-09**: The derive's exact-join index SHALL hold every signature listed in `reachability[].methods[]`, reaching or not; the D8 class recovery SHALL apply only to a wrapper whose signature is absent from that index.

- **INV-DRV-10**: Every distance pair `[i, d]` in the artifact SHALL satisfy `0 ≤ i < targets` and `d ≥ 0`. A pair list SHALL hold each index at most once and SHALL be sorted by `d` ascending, then `i` ascending. A widget's or a handler's list SHALL hold exactly the targets of its per-target minima at `d ≤ 3` and no pair at `d ≥ 4`. An `activityDist` list SHALL hold the three pairs of smallest `d`. Every list is cut from the full per-target minima after every merge (listener, collision, dialog, class), never before, and an activity's minima start from its widgets' uncut minima. An empty pair list SHALL NOT be emitted. `targets` and `handlers` SHALL always be emitted.

- **INV-DRV-11**: A `reachability[]` method SHALL fill the `click` event of its class's `handlers` record exactly when its name and parameter list are one of `onClick(android.view.View)`, `onOptionsItemSelected(android.view.MenuItem)`, `onNavigationItemSelected(android.view.MenuItem)`, `onMenuItemClick(android.view.MenuItem)`, `onMenuItemSelected(android.view.MenuItem)`, `onPreferenceClick(androidx.preference.Preference)`, `onPreferenceTreeClick(androidx.preference.Preference)`, `onPreferenceChange(androidx.preference.Preference,java.lang.Object)`, `onClick(android.content.DialogInterface,int)`, or `java.lang.Object invoke()` / `java.lang.Object invoke(java.lang.Object)`; `onLongClick(android.view.View)` and the two `invoke` forms fill `longclick`. A name with any other parameter list SHALL fill no event. All methods that fill one event of one class SHALL OR their flags and merge their pairs by the minimum per target before the cut of INV-DRV-10, so no method's contribution is lost.

- **INV-APV-38**: every variant whose preset mounts the LLM group (`as_llm`, `as_mop_llm`) MUST carry `llm_url` in its `overrides`. The cell preset states `ape.llm=true` without the URL, which names a machine rather than a cell, so a variant without it aborts at resolution (`MISSING_DEPENDENCY`). This is a fail-fast, not a fallback.

- **INV-APV-39**: `configure()` MUST fold every top-level config key that has an
  `APERV_PROPERTY_MAPPING` entry into `overrides`, and MUST raise `ConfigurationError` for any
  top-level key that is neither mapped nor one of the recognised orchestration keys (`preset`,
  `variant`, `overrides`, `strategy`, `static_data`, `broadcast_catalog`, `seed`, `device_port`,
  `device_serial`, `device_id`). The three device keys are addressing rather than
  configuration: rv-experiment's `ExecutionController` injects all three into every tool's
  parameters whenever `--device-port` is set, which every Docker compose file does, and the tool
  reads the serial from `task.config.device_id` at execution time rather than from `_tool_config`.
  Rejecting them would abort every containerized and parallel run inside `Platform._load_tool`,
  before a device is touched. The
  tool DSL (`aperv:<variant>@key=value`) delivers its overrides at the top level — `ToolFactory`
  merges `{**variant_config, **tool_config.parameters}` — while `_push_properties()` reads only
  `overrides`. Without the fold, a DSL override would be silently discarded: no property line, no
  error, and a run executing a configuration nobody asked for. A key that cannot be honoured MUST
  fail loudly rather than vanish.

- **INV-APV-40**: Every variant returned by `get_variants()` MUST consist of a `preset` name, an
  `overrides` dict (possibly empty), and Python-only orchestration keys. No variant may carry a full
  property expansion; the substrate spread dicts are deleted, not retained in reduced form.

- **INV-APV-41**: `APERV_PROPERTY_MAPPING` MUST contain only keys the deployed jar accepts. Dead keys
  are removed, not commented out. `llm_snap_tolerance_px` and `llm_max_tokens` are live jar keys
  (`Feature.LLM` sub-parameters) and MUST remain mapped.

- **INV-APV-43**: `tool.py` MUST NOT parse, validate or branch on `RUN_START` or any other jar echo
  output (owner decision D1). Provenance is write-only in the trace; drift auditing is post-hoc
  analysis.

- **INV-APV-59**: No source file under `modules/` SHALL state the revision, digest or version of a
  build artifact produced outside this repository, and no guard SHALL require an arm to declare one.
  The identity of such an artifact SHALL be obtained by measuring the artifact at the moment it is
  used — as `_capture_llm_provenance()` digests `ape-rv.jar` into `jar_sha256` at push time — and
  recorded in the run's provenance, never asserted in advance by a literal. A literal identity is
  unfalsifiable at rest and stale from the first rebuild: `ape-rv.jar` comes from a sibling
  repository whose build is not bit-reproducible, so the same revision yields a different digest each
  time it is built, and any pin becomes a maintenance obligation discharged by an author's memory. A
  gate that compares a measurement against such a pin therefore fails on correct redeployments and
  passes on stale ones, which is worse than no gate at all. This retires INV-APV-34, whose pairing of
  the snap tolerance to a declared jar identity was the mechanism being described.

- **INV-APV-44**: The one-time regeneration diff that proved every surviving arm's effective
  configuration unchanged under `preset + overrides` MUST NOT survive as a standing
  constant-vs-constant guard. It ran per arm against a captured baseline of all 29 pre-change
  arms, on typed values rather than property text, with the 21 retired names excluded by an
  explicit list rather than by silent absence; it was deleted at owner sign-off on 2026-08-07,
  and its baseline and executed result are archived under
  `modules/aperv-tool/docs/gh95-migration-record/`. Re-creating it under any name would recreate
  the retired INV-APV-14 — a constant validated against a frozen copy of itself.

- **INV-APV-48**: `trace_ndjson.py` SHALL be read-only and analysis-time only. It SHALL NOT write to the trace, SHALL NOT emit legacy `[APE-*]` lines, SHALL NOT be imported or invoked from `execute_tool_specific_logic()` or any other collection-path code, and SHALL NOT require a device, an emulator or `adb`.

- **INV-APV-49**: default materialization SHALL be total for the fields whose absence means a default and SHALL NOT be applied to the fields whose absence is itself information. The seven boost fields (`mop`, `mopf`, `wtg`, `navf`, `cov`, `menu`, `form`) SHALL be materialized at `0` when absent, and `out.new_state` / `out.act_changed` at `false`. `dec.patched`, `dec.cf`, `dec.cfc`, `dec.own`, `dec.mopd` and every other `dec` member added by the group-isolation jar SHALL be preserved as absent when absent, because a trace from the `eea2b1a9` jar carries none of them and a materialized default would claim the mechanism ran.

- **INV-APV-50**: A malformed record SHALL be skipped and counted in the reader's diagnostics rather than aborting the read. A record referencing an `act`, `st` or `out.target` ID that no earlier dictionary record defined is malformed by this rule; the reader SHALL NOT invent a placeholder string for it.

- **INV-APV-51**: The reader SHALL NOT fabricate an absolute clock. When `RUN_START` is absent from the trace — a truncated capture, or a pre-stage-4 file — the run-relative `t` SHALL still be reported and the epoch expansion SHALL be reported as unavailable. A base SHALL NOT be inferred from file mtime, from the logcat, or from any other source.

- **INV-APV-52**: The gzip step SHALL be non-fatal and write-only. Its failure SHALL log a WARNING and leave the uncompressed trace in place, and the task SHALL complete with the status it would otherwise have had. `task.result.trace_file` SHALL be byte-identical before and after collection completes: no step of the flow rewrites, reformats, truncates or converts it.

- **INV-APV-53**: no code path on the collection path of this module (`tools/aperv/*`) SHALL read, validate or act on the `RUN_END` record: no sentinel check, no exit-code interpretation beyond the existing debug log, no task-status change and no retry keyed on it (owner decision D5). The offline reader `trace_ndjson.py` SHALL expose it as a census record and SHALL NOT interpret it.

- **INV-APV-54**: `_align_clocks()` and the UTC-offset reconstruction SHALL NOT be deleted before a captured run is shown to contain heartbeat lines in the task's `.logcat`. This is the counterpart of `event-sink` INV-SNK-14 on the jar side: the heartbeat is filtered at the device under any tag outside the capture allowlist, so a deletion that precedes the observation trades a working mechanism for an inert one and does so silently.

- **INV-APV-55**: The frozen legacy-corpus readers SHALL NOT be migrated, adapted or deleted by this change: `scripts/cmpm_stratify.py`, `scripts/analyze_cmpv2_llm.py`, `experimento-cal/scripts/*`, `experimento-20260721/scripts/*` and `calibracao/*`. They read an archived dataset that will not be regenerated, and are not compatibility shims.

- **INV-APV-56**: When `corpus_basis` is absent from the tool configuration, `_push_properties()` SHALL omit `ape.corpusBasis` from the generated `ape.properties` entirely. It SHALL NOT emit the key with an empty, placeholder or defaulted value — the jar's contract is that the key is absent when the corpus is unstated, and a defaulted value would assert a provenance the harness does not have.

- **INV-APV-57**: No component of `modules/aperv-tool` SHALL read `RUN_START` — including `corpus_basis` — on any execution path. The property is write-only from this side, mirroring `run-spec` INV-RUN-03. Any verification of the echoed value SHALL be post-hoc analysis over a recorded trace, outside `tool.py`.

- **INV-APV-58**: the reader SHALL NOT drop data the trace carries. Every field of an `llm[]` sub-event SHALL reach the caller, every `dec` member listed in this delta's Data Contracts SHALL reach the row, and every run-level record SHALL be reachable: `MOP_DATA`, `PIPELINE`, `LLM_ACK` and `RUN_END` as reader attributes.

- **INV-APV-60**: `ApeRVTool` SHALL NOT report a run as successful on the strength of the exploration process having returned. A return that arrives materially before the requested exploration budget SHALL raise `RVToolExecutionError` naming the elapsed time and the budget. The exit code SHALL NOT be used to decide this: a non-zero exit is normal for APE-RV — it exits non-zero when it detects an application crash during exploration — so a dead emulator and a crashing application are indistinguishable by it, and the elapsed time is the one signal that separates them.

- **INV-APV-61**: `RunStart` SHALL carry every top-level member of the `RUN_START` record the jar emits, `variant` included, with `build` as a nested `(sha, time)` value; a member absent on the wire SHALL be reported absent, never defaulted.

- **INV-APV-62**: `TraceReader` SHALL accept `RUN_START.v` in `SUPPORTED_VERSIONS = {1, 2}`. Version 1 is the `eea2b1a9` jar and earlier, and version 2 is the group-isolation jar, which bumped the version because `dec.src` changed meaning. Any other declared version SHALL be surfaced in `TraceDiagnostics` and SHALL raise `SchemaVersionMismatch` in strict mode. The reader SHALL expose the version it read as `run_start.v`. A trace with no `RUN_START` reports the version as unknown (INV-APV-51 applies).

- **INV-APV-63**: The heartbeat placement rule SHALL exist once, in `clock_logcat_join.place_on_timeline(stamp, heartbeats)`, and SHALL be tag-agnostic; the tag admitted is a parameter of the line reader, not of the placement.

- **INV-APV-64**: On a cache miss `_derive_mop_artifact` SHALL read the document in streaming and SHALL keep, of each method's `targetDistances`, after taking the minimum per target, only the pairs at `d ≤ DIST_WEIGHED_MAX` and the `DIST_K` nearest by `(d, i)`. The serialized artifact SHALL be byte-identical to `serialize_canonical(derive(json.load(document)))` of the same file.

- **INV-APV-65**: every variant SHALL carry a top-level `variant` equal to its own name (`default` carries `"base"`), and `_push_properties()` SHALL write it as `ape.variant=<variant>` on the second line. The tool SHALL NOT read the echoed `RUN_START.variant` back (INV-APV-43).

- **INV-APV-66**: `static_data` SHALL be present exactly on the cells that mount STATIC or MOP — every cell except `base` — so the artifact reaches the device if and only if a group that reads it is mounted.

- **INV-APV-67**: the reader SHALL NOT rewrite, translate or reinterpret `dec.src`. Its documentation SHALL state both meanings: the executed owner under `RUN_START.v == 2`, the largest boost under `v == 1`. The version is what tells them apart, and the reader carries it without branching on it.

- **INV-APV-68**: `activity_has_mop`, on the step side and on the outcome side, SHALL be `None` when the `ACT` record carries no `mop` member. The group-isolation jar writes `ACT.mop` only when the MOP group is mounted, so in `base`, `as` and `as_llm` the fact was not computed, and `False` would claim it was. The same rule holds for `StateCoverage.mop_reach`: a `UICOV` line without `mopReach` is complete, with `mop_reach = None`.

## Requirements

### Requirement: ApeRVTool Registration (FR18, FR19)

`ApeRVTool` SHALL be registered as an external tool via rv-platform's `_register_external_tools()` function in `rv_platform/__init__.py`. `modules/rv-platform/pyproject.toml` SHALL declare `aperv-tool` in `dependencies` and as a workspace source in `[tool.uv.sources]`, as it declares `rvagent-tool` (`tools` INV-TOOL-26). Registration SHALL be idempotent: the function MUST check `registry.is_tool_registered("aperv")` before calling `registry.register_tool_class(ApeRVTool)`. If importing `aperv_tool.tools.aperv.tool` raises `ImportError`, the error SHALL be caught and logged as a warning, and the platform SHALL continue operating normally. An unexpected exception during registration SHALL be logged as an error and SHALL NOT propagate.

With the dependency declared, an `ImportError` no longer means the module was left out of the install. It means the module is present and its import failed, for example because one of its own imports broke. The guard keeps rv-platform importable in that case. The `aperv` arm is then absent from the registry. `rv-experiment` rejects it in `ExperimentConfig.validate()` before pre-processing, with `ConfigurationError("Tool 'aperv' not found in registry...")`. `rv-platform run` fails each `aperv` task in `ToolFactory.create_tool`.

#### Scenario: ApeRVTool registers on rv-platform import
- **WHEN** `import rv_platform` is executed in the workspace `.venv`
- **THEN** `ToolRegistry.get_instance().is_tool_registered("aperv")` SHALL return True
- **AND** `ToolRegistry.get_instance().get_tool_spec("aperv").name` SHALL be `"aperv"`

#### Scenario: Missing aperv-tool does not break rv-platform
- **WHEN** `import rv_platform` is executed and importing `aperv_tool.tools.aperv.tool` raises `ImportError` (the module is declared, so this is a broken import rather than a missing install)
- **THEN** rv-platform SHALL import successfully
- **AND** a warning log line SHALL be written containing `"aperv tool not available"`
- **AND** `ToolRegistry.get_instance().is_tool_registered("aperv")` SHALL return False

#### Scenario: Re-importing rv-platform does not double-register
- **WHEN** `import rv_platform` is executed twice
- **THEN** `ToolRegistry.get_instance()` SHALL contain exactly one registration for `"aperv"`

#### Scenario: rv-platform declares aperv-tool
- **WHEN** `.claude/skills/rv-analyze-dependencies/scripts/workspace_deps.py` is run from the rv-android root
- **THEN** the `rv-platform` entry SHALL list `aperv-tool` under `declared`
- **AND** its `undeclared` line SHALL be `-`

---

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
- **AND** the variant SHALL still resolve as `ape.preset=as_mop`, `ape.variant=as_mop` plus `ape.staticDataPath`
  and `ape.mopCoinLedgerMaxInteractions=2`

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

---

### Requirement: JAR Resolution (FR19)

`ApeRVTool._resolve_jar_path()` SHALL use `JarResolver.resolve_jar_path("ape-rv.jar", search_paths)` where `search_paths` is built as follows:

1. Always include `os.path.dirname(__file__)` (the module directory)
2. If `RVSEC_HOME` env var is set, append `$RVSEC_HOME/ape/target/`
3. If `TOOLS_DIR` env var is set, append `$TOOLS_DIR/aperv/`

The first existing path that contains `ape-rv.jar` wins. If no path resolves, `RVToolExecutionError` SHALL be raised with a message listing all searched paths.

#### Scenario: JAR found in module directory
- **WHEN** `ape-rv.jar` exists in `os.path.dirname(__file__)`
- **THEN** `_resolve_jar_path()` SHALL return the absolute path to that file

#### Scenario: JAR not found anywhere
- **WHEN** `ape-rv.jar` does not exist in any search path
- **THEN** `_resolve_jar_path()` SHALL raise `RVToolExecutionError`
- **AND** the error message SHALL list all searched paths

---

### Requirement: ApeRVTool Execution Flow (FR18, FR19)

`ApeRVTool.execute_tool_specific_logic(task, app)` SHALL perform the following steps in order:

1. **Extract execution parameters**: Resolve `device_serial` from `task.config.device_id` (default `"emulator-5554"`) and `timeout_seconds` from `task.config.timeout` (default 300).

2. **Push JAR**: Resolve `ape-rv.jar` via `_resolve_jar_path()` and push to `/data/local/tmp/ape-rv.jar` via `_push_file_to_device()`.

3. **Push broadcast catalog**: When the variant carries `broadcast_catalog=True` and `system-broadcast.json` exists in the module directory (`os.path.dirname(__file__)`), push it to `/data/local/tmp/system-broadcast.json`. The catalog provides typed extras for the system broadcast intents of APE-RV's component triggering, a STATIC member that the four `as*` presets mount at `componentPercentage=0.03` and that is the catalog's only reader in the jar. `base` and `mop` do not mount STATIC and push no catalog (INV-APV-10). If the file is absent, skip (APE-RV degrades gracefully).

4. **Derive and push the artifact** (every cell except `base`): When `_tool_config.get("static_data") == "static_analysis"`, locate `<task.results_dir>/<apk_name>.json`, derive `<task.results_dir>/<apk_name>.mop.json` from it, and push **only that artifact** to `/data/local/tmp/mop-artifact.json`. The source document is never modified and never pushed. A variant with no static-analysis JSON, or whose derivation fails, raises `RVToolExecutionError`.

5. **Push ape.properties**: Generate `ape.properties` as `ape.preset=<preset>` first, `ape.variant=<variant>` second, then `ape.staticDataPath=<artifact device path>` when the artifact was pushed, then one `ape.<key>=<value>` line per entry of `overrides`, translated through `APERV_PROPERTY_MAPPING`. Push to `/data/local/tmp/ape.properties`.

6. **Capture LLM backend provenance** (LLM cells only): query `GET {llm_url}/v1/models` once and record the result in the task output -- see "Per-Run LLM Backend Provenance". A failed query is encoded, never inferred from configuration, and never aborts the run (INV-APV-33).

7. **Build and execute command**: Build the `app_process` command via `_build_main_command()` and execute it, capturing stdout+stderr to `task.result.trace_file` in binary write mode. From stage 4 onward the captured stream is the NDJSON trace. **Command timeout is `timeout_seconds + 45` seconds** — widened from `+ 15`; see the grace-window rationale below.

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
- **THEN** the generated file SHALL be exactly the four lines `ape.preset=as_mop`, `ape.variant=as_mop`,
  `ape.staticDataPath=/data/local/tmp/mop-artifact.json`, `ape.mopCoinLedgerMaxInteractions=2`
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

---

### Requirement: Static Analysis File Discovery

`ApeRVTool._find_static_analysis_file(task)` SHALL locate the static analysis JSON file at `<task.results_dir>/<task.config.apk_name>.json`. This file is produced by rv-android's static analysis pipeline (GATOR/GESDA/REACH) during experiment pre-processing.

The method SHALL return the absolute path if the file exists, or `None` otherwise. It SHALL return `None` without error when `task.results_dir` or `task.config` are absent (graceful degradation for standalone execution outside rv-experiment).

#### Scenario: Static analysis file found
- **WHEN** `_find_static_analysis_file(task)` is called
- **AND** `task.results_dir` is `/results/exp1/` and `task.config.apk_name` is `com.example_1.apk`
- **AND** `/results/exp1/com.example_1.apk.json` exists
- **THEN** the method SHALL return `"/results/exp1/com.example_1.apk.json"`

#### Scenario: Static analysis file not found
- **WHEN** the JSON file does not exist in `task.results_dir`
- **THEN** `None` SHALL be returned

#### Scenario: Standalone execution without results_dir
- **WHEN** `task.results_dir` is None or absent
- **THEN** `None` SHALL be returned without error

---

### Requirement: uv Workspace Declaration

`aperv-tool/pyproject.toml` SHALL declare the package as a uv workspace member compatible with rv-android's `members = ["modules/*"]` discovery. Its only workspace dependency SHALL be `rv-android-core`, declared as a workspace source. That is where `AbstractTool`, `ToolSpec`, `Command`, `JarResolver`, the domain models and `util.analysis_document` come from. The module SHALL NOT declare `rv-tools`, which its code does not import. The undeclared lazy import of `rv_coverage` in `analysis/step_bundle.py` is deliberate and is not declared (see Purpose).

The `[project.entry-points."rv_tools.plugins"]` table SHALL NOT be used for `aperv-tool` -- registration is done explicitly in `rv-platform/__init__.py`, not via entry-point auto-discovery.

#### Scenario: Module added to workspace
- **WHEN** `aperv-tool/` exists under `modules/` in the rv-android root
- **THEN** `uv sync` SHALL include `aperv-tool` in the workspace without any change to the root `pyproject.toml`

#### Scenario: Declared and imported workspace dependencies agree
- **WHEN** `.claude/skills/rv-analyze-dependencies/scripts/workspace_deps.py` is run from the rv-android root
- **THEN** the `aperv-tool` entry SHALL show `declared: rv-android-core`
- **AND** its `unused` line SHALL be `-`
- **AND** its `undeclared` line SHALL list only `rv-coverage`

### Requirement: Seed Propagation to APE-RV (FR18, FR19)

`ApeRVTool._build_main_command()` SHALL append `-s <seed>` to the `app_process` argument vector when a
`seed` key is present in `_tool_config` (INV-APV-18). The seed reaches `_tool_config` via the tool DSL
(`aperv:<variant>@seed=<n>`) or `ToolConfig.parameters`, merged by `ToolFactory`. When no seed is
configured, the command SHALL NOT include `-s`, preserving the current default where the jar self-seeds
non-deterministically.

The `mop-fairtest` APE-RV jar already honors a passed seed: `Monkey` parses `-s SEED`
(`Monkey.java:886-887`), and when `mSeed != 0` it seeds both `Monkey.mRandom` and APE's `RandomHelper`
(`Monkey.java:731`, `RandomHelper.seed(mSeed)`, INV-EXPL-14) — so a fixed seed makes a run reproducible.
The rv-android-side gap (the command never emitting `-s`) is what this requirement closes; no jar change
is required.

#### Scenario: Seed configured is passed as -s
- **WHEN** `_build_main_command(app, "emulator-5554", 60)` is called with `_tool_config` containing `seed=42`
- **THEN** the command argument vector SHALL contain `-s` immediately followed by `"42"`
- **AND** the `-s 42` pair SHALL appear after `--ape <strategy>`

#### Scenario: No seed configured omits -s
- **WHEN** `_build_main_command(app, "emulator-5554", 60)` is called with `_tool_config` containing no `seed` key
- **THEN** the command argument vector SHALL NOT contain `-s`

#### Scenario: Seed is not written to ape.properties
- **WHEN** `_push_properties()` is called for a variant whose `_tool_config` contains `seed=42`
- **THEN** the generated properties file SHALL NOT contain a `seed` line (it is a CLI-only, Python-only key)

---

### Requirement: Per-Run LLM Backend Provenance (FR19, NFR06)

`aperv-tool` SHALL record, at the start of every run that uses an LLM, the backend actually serving that run. The record SHALL be obtained by querying the OpenAI-compatible `/v1/models` endpoint derived from the arm's `llm_url`, and SHALL be written into the task output alongside the run's other results.

The derivation SHALL resolve the emulator-only host alias `10.0.2.2` to `127.0.0.1`, because the query runs outside the emulator while `llm_url` is written for the jar that runs inside it (design D6). The resolution SHALL apply to the query alone and SHALL NOT alter the value written into `ape.properties`. The recorded `llm_backend` SHALL be the address actually queried.

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

---

### Requirement: Heartbeat Placement Is One Tag-Agnostic Function (FR11, FR13, NFR03)

`clock_logcat_join.py` SHALL expose its placement rule as `place_on_timeline(stamp, heartbeats) -> (Phase, step | None, anchor)` — the violation belongs to the step of the last heartbeat at or before it; before the first heartbeat is `PRE_EXPLORATION`, after the last is `POST_EXPLORATION`, no heartbeat at all is `UNALIGNED` — and a line reader `read_tagged_lines(logcat_path, tag) -> list[(stamp, payload)]` whose admitted tag is a parameter (INV-APV-63). The join's own behaviour, output type `RunJoin` and every scenario of *Offline Clock-to-Violation Join* SHALL be unchanged: it calls the two with `tag="RVSEC"`. `campaign-analysis`'s `step_bundle` calls them with `RVSEC-COV` and with the diagnostic base tags. The heartbeat regex, the timestamp regex and the run-filename regex SHALL NOT be duplicated into any other module; the last one moves to `run_identity.py` and is imported here (`campaign-analysis` INV-CAN-01).

#### Scenario: The join is unchanged after the extraction
- **WHEN** the existing `test_clock_logcat_join.py` suite runs after the placement and line reader are extracted
- **THEN** every test SHALL pass without modification
- **AND** `join_run` SHALL produce byte-identical `RunJoin` values over the fixtures

#### Scenario: RVSEC-COV lines are placed by the same rule
- **WHEN** `read_tagged_lines(path, "RVSEC-COV")` and `place_on_timeline` run over a logcat with heartbeats
- **THEN** a coverage line between heartbeat 7 and heartbeat 8 SHALL be placed at step 7
- **AND** `read_tagged_lines(path, "RVSEC")` SHALL NOT admit that line, and vice versa

#### Scenario: Placement exists once
- **WHEN** the tests grep `aperv_tool/analysis/` for the phrase `last heartbeat at or before`
- **THEN** the implementing loop SHALL exist only in `clock_logcat_join.py`
- **AND** `step_bundle.py` SHALL import it

### Requirement: Offline Coverage-Dump Parser at Activity Grain (FR11, NFR03, NFR06)

`aperv_tool` SHALL provide a versioned, offline, read-only parser for the coverage dump emitted by the jar — the `[APE-RV] UICOV` (per state) and `[APE-RV] UICOV-ACT` (per Activity) lines — producing per-run rows consumable by the analysis path.

The parser exists because the dump has **no automated consumer today**: a search for `UICOV` across the whole rv-android tree returns zero hits in Python, and the only historical consumption was manual. The sister change (`ape`, `telemetry-proof-llm-efficacy`, item A10) hoists the dump to the front of the teardown chain, which recovers it in 333 of the 338 runs that lose it today; without a parser that recovery yields data nothing reads.

**Activity grain is mandatory, not a preference.** The per-state `UICOV` key embeds `StateKey.toString()`, whose hash includes the JVM identity hash of a `Naming` object that overrides neither `equals` nor `hashCode`. State keys are therefore not comparable across runs: the measured Jaccard between replicas of the same `(APK, arm)` is **0.000 — mean, median and maximum**, meaning not one state line in the corpus pairs with its counterpart in the other replica. Anything the parser reports across runs, replicas or arms SHALL be derived from `UICOV-ACT`; `UICOV` lines MAY be parsed for intra-run use and SHALL NOT be aggregated across runs.

**Partial dumps are valid input.** Hoisting the emission does not make it atomic — 3 of the 462 runs that dump today are truncated mid-`UICOV-ACT`. The parser SHALL accept a truncated final line as a partial dump, retain every complete line preceding it, and mark the run as partial rather than discarding it.

**Line format.** `gap` carries one decimal place under `Locale.ROOT` and SHALL NOT be used as a computation source; `discovered` and `interacted` are integers and are the authoritative fields. `byType` is `TYPE:interacted/discovered`. Note that `mopReach` appears on the `UICOV` line and **not** on `UICOV-ACT`, so MOP reach is not reconstructible at Activity grain from the current jar; the parser SHALL report its absence rather than infer it.

**`mopReach` is present only where MOP is mounted.** The group-isolation jar writes `mopReach` on a `UICOV` line only when the MOP group is mounted, as it does with `ACT.mop` (`ape` D-B14.21, contract v3.2). `StateCoverage.mop_reach` SHALL therefore be `Optional[int]`. A `UICOV` line without `mopReach` SHALL be a complete line with `mop_reach = None`, and SHALL NOT count toward a partial dump. Partial means truncated or unparseable, and a cell that does not compute MOP reach is neither. A `UICOV` line of the `eea2b1a9` jar always carries the field and reads as before. The consumer `state_coverage_join.py` SHALL carry `None` through to `uicov_mop_reach`. Its statement that `mopReach` agrees with the activity's MOP flag holds on the cells that mount MOP, and on the other cells both facts are absent.

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

#### Scenario: A state line without mopReach is complete
- **WHEN** an `aperv:as` trace carries `[APE-RV] UICOV state=S1 discovered=12 interacted=5 byType=CLICK:5/12` with no `mopReach` field, and its dump ends normally
- **THEN** the parser SHALL emit the state row with `mop_reach = None`
- **AND** the run's dump status SHALL be complete, not partial
- **AND** a line of the same trace missing `discovered` SHALL still be counted toward a partial status

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

---

### Requirement: Derived MOP Artifact Generation and Caching (FR19, NFR04)

`ApeRVTool._derive_mop_artifact(task)` SHALL return the host path of the compact MOP artifact for the
task's APK, generating it when needed:

1. Compute the SHA-256 of the current full JSON at `<results_dir>/<apk_name>.json`, reading the file
   in chunks.
2. When `<results_dir>/<apk_name>.mop.json` exists, its `source.digest` equals `"sha256:" + <hex>`
   **and** its `formatVersion` equals `derive_mop_artifact.FORMAT_VERSION`, reuse it without
   regenerating and without parsing the full JSON.
3. Otherwise read the full JSON in streaming as UTF-8, reducing each method's `targetDistances` to the
   pairs the artifact can carry (INV-APV-64), call `derive()` + `serialize_canonical()` on the result,
   and write the artifact atomically (write-temp-then-rename in the same directory). A failed
   derivation SHALL write nothing.

The method SHALL NOT hold the file's text, nor any `targetDistances` pair that cannot reach the
artifact. A gh120 document is large — up to 9.34 GB in the Study 03 corpus — and a whole-document
parse peaked at 3.1 times the file size (gh122 task 7.7). The digest and the streaming read each read
the file on their own, and a cache hit never parses.

The reduction is exact, not an approximation. `derive()` merges distances by the minimum per target
and cuts only at emission: every pair at `d ≤ DIST_WEIGHED_MAX` for a widget or handler, the
`DIST_K` nearest by `(d, i)` for an activity (INV-DRV-10). A pair dropped by the reduction is beyond
`DIST_WEIGHED_MAX` and has at least `DIST_K` targets ahead of it in its own method; after any merge
those targets are still ahead of it, so it can be in no emitted list.

The artifact is cached next to its source so it is inspectable and diffable, and it is a pure function
of the full JSON and the generator's format (INV-APV-47, INV-DRV-05). The format is part of the cache
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

---

### Requirement: MOP Artifact Projection Contents (FR04, FR05, FR06, FR19)

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
     for `i`: 0 when the method is the target, 1–10 otherwise (gh120 `DIST_MAX = 10`); a target
     absent from its entries is unreachable. An entry that is not a pair of integers, whose index is
     outside `[0, targets)` or whose distance is negative is skipped, like any malformed entry inside
     a well-typed section. A method the producer marks reaching and gives no `targetDistances` is
     one whose every target is more than `DIST_MAX` calls away: gh120 computes reach without a depth
     bound and distances with the cut. It has flags and no distance, and the derive does not invent
     one, so a widget or handler whose reaching methods are all that far is flagged and carries no
     pair. Under `distance` scoring that is the weight the exact distance would give, since a target
     at `d ≥ 4` gives none.
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
     The app callbacks that a library dispatcher calls, and that the View stamp names in
     `rvsec.click` instead of the dispatcher (`instrumentation` INV-INS-181), are handler methods
     that fill `click` (INV-DRV-11): `onOptionsItemSelected(android.view.MenuItem)`,
     `onNavigationItemSelected(android.view.MenuItem)`, `onMenuItemClick(android.view.MenuItem)`,
     `onMenuItemSelected(android.view.MenuItem)`, `onPreferenceClick(androidx.preference.Preference)`,
     `onPreferenceTreeClick(androidx.preference.Preference)`,
     `onPreferenceChange(androidx.preference.Preference,java.lang.Object)` and
     `onClick(android.content.DialogInterface,int)`. A class that declares more than one of them,
     or one of them and `onClick(android.view.View)`, as an activity that is both a button's
     listener and the options-menu owner does, gets one `click` event by the merge rule below; the
     stamp names the class, not the method, so the record cannot be finer than the class.
     `<init>` and `<clinit>` are never handler methods. An event's flag is derived from the method's
     own `directlyReachesTarget`/`reachesTarget` on INV-DRV-01's two axes, and its pairs are the
     method's distances; two methods filling one event OR their flags and merge their pairs by the
     minimum per target. A class whose handler methods reach nothing SHALL still be listed, with
     `none` for each of its events and no `dist`: on the device a listed class states that the
     stamped handler reaches no target. The key is the class's binary name as `reachability[].className`
     writes it, which is the `Class.getName()` form gh121 stamps.
   - **Cut, order, omission** (INV-DRV-10). A widget's and a handler's pair list SHALL keep every
     target at `d ≤ 3` and drop every pair at `d ≥ 4`. These are the lists that weigh an action, and
     the jar gives no weight from `d = 4` (`ape` D18). Under the three-pair cut, 4,024 of the 21,485
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
- **AND** `handlers` SHALL have exactly four keys: `br.unb.cic.cryptoapp.cipher.CipherActivity$1` and
  `br.unb.cic.cryptoapp.generated.CryptographyActivity$$ExternalSyntheticLambda0`, each with
  `mop == {"click": "transitive"}`, the second carrying `dist == {"click": [[16,3],[17,3],[18,3]]}`
  and the first no `dist`; and `br.unb.cic.cryptoapp.MainActivity` (its
  `onOptionsItemSelected(android.view.MenuItem)`) and `br.unb.cic.cryptoapp.MainActivity$1` (its
  `onMenuItemClick(android.view.MenuItem)`), each `{"mop": {"click": "none"}}` with no `dist`,
  because those callbacks reach no target (INV-DRV-11)
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

---

#### Scenario: the handler table records the app callbacks behind library dispatchers
- **WHEN** `reachability[]` lists `com.example.app.MainActivity` with the method `<com.example.app.MainActivity: boolean onOptionsItemSelected(android.view.MenuItem)>` at distance 2 from target 0, `com.example.app.SettingsFragment$$ExternalSyntheticLambda5` with `<...: boolean onPreferenceClick(androidx.preference.Preference)>` at distance 1 from target 1, and `com.example.app.Dialogs$$ExternalSyntheticLambda3` with `<...: void onClick(android.content.DialogInterface,int)>` at distance 3 from target 0
- **THEN** `handlers["com.example.app.MainActivity"].dist` SHALL be `{"click": [[0, 2]]}`, `handlers["com.example.app.SettingsFragment$$ExternalSyntheticLambda5"].dist` SHALL be `{"click": [[1, 1]]}`, and `handlers["com.example.app.Dialogs$$ExternalSyntheticLambda3"].dist` SHALL be `{"click": [[0, 3]]}`
- **AND** none of the three records SHALL carry a `longclick` event

#### Scenario: a callback name with another parameter list is not a handler method
- **WHEN** `reachability[]` lists `com.example.app.Helper` whose only methods are `<com.example.app.Helper: boolean onOptionsItemSelected(int)>` and `<com.example.app.Helper: void onClick(android.content.DialogInterface)>`, both reaching target 0
- **THEN** `handlers` SHALL have no key `com.example.app.Helper`

#### Scenario: a class with a view listener and an options-menu callback merges both into click
- **WHEN** `com.example.app.MainActivity` declares `onClick(android.view.View)` at distances `{0: 3}` and `onOptionsItemSelected(android.view.MenuItem)` at distances `{0: 1, 2: 2}`, the first reaching no target directly and the second reaching target 0 directly
- **THEN** `handlers["com.example.app.MainActivity"]` SHALL carry `dist.click == [[0, 1], [2, 2]]`
- **AND** its `click` flag SHALL be the OR of the two methods' flags, with neither method's record overwriting the other

### Requirement: Widget MOP Flag Derivation (FR04, FR06)

The generator SHALL derive each widget's MOP flags from its listeners, per normalized `eventType`,
and OR-aggregate them across listeners (INV-DRV-01). For each listener:

1. When `handlerDirectlyReachesTarget` or `handlerReachesTarget` is non-null, the producer's values
   win: `direct` is `handlerDirectlyReachesTarget is True`, `transitive` is
   `handlerReachesTarget is True or direct`.
2. Otherwise the handler signature is looked up in the index built from `reachability[].methods[]`,
   which SHALL carry, per signature and for **every** listed method, reaching or not, the pair
   (`directlyReachesTarget`, `reachesTarget or directlyReachesTarget`). Duplicate signatures SHALL be
   merged by OR rather than by last-write, so the index does not depend on producer ordering.
3. Only when the signature is absent from `reachability[]` and the handler matches
   `^<(.+?)\$\$ExternalSyntheticLambda\d+:`, the flags SHALL be recovered from the enclosing class's
   reaching `lambda$…` methods, OR-aggregated; when that class has no reaching lambda method the
   widget SHALL NOT be flagged. A wrapper listed in `reachability[]` with both flags `false` SHALL
   keep `(false, false)`: the producer links each wrapper to its own body (`analysis`, INV-ANA-77),
   so a listed wrapper's flags are its own, and recovering it from the class would lend it the flags
   of a sibling lambda. The recovery remains for wrappers the producer does not list at all.

The two axes SHALL NOT be collapsed. `direct` retains the producer's 0-hop meaning — the handler
invokes a monitored operation in its own body — which is what `ape.mopWeightDirect` was defined to
reward, and `transitive` is the any-depth reach implied by it. A listener whose `eventType` is null
contributes to the aggregates and normally produces no wire key, since a null key is unaddressable
by the query side. It has one exception, and the exception is what keeps the projection lossless:
because the jar recomputes a widget's aggregate as the OR over the `mop` map, a widget whose *only*
flagged listeners are null-keyed would lose the flag entirely. In that case, and only that case, the
generator SHALL emit the reserved key `""` — the same key `normalizeEventType("")` produces, so it is
reachable only by a query for the empty event type and shadows no real one.

#### Scenario: producer-supplied flags take precedence
- **WHEN** a listener carries `handlerReachesTarget: true` and `handlerDirectlyReachesTarget: false`
- **AND** the handler's signature is absent from `reachability`
- **THEN** the widget's `click` entry SHALL be `transitive`, not `none`

#### Scenario: direct implies transitive
- **WHEN** the handler's method carries `directlyReachesTarget: true` and `reachesTarget: false` — the
  shape 33 methods across 16 corpus apps actually have
- **THEN** the derived flags SHALL be `direct == true` and `transitive == true`, emitted as `both`
- **AND** no widget SHALL ever be emitted with `direct` set and `transitive` unset

#### Scenario: D8 synthetic-lambda handler is recovered
- **WHEN** a widget's click listener has handler
  `<com.example.MainActivity$$ExternalSyntheticLambda0: void onClick(android.view.View)>` with no
  matching signature in `reachability`
- **AND** `com.example.MainActivity` has a method `lambda$onCreate$0` with `reachesTarget: true`
- **THEN** the widget's `click` entry SHALL be `transitive`
- **AND** `stats.recovered` SHALL count it

#### Scenario: synthetic-lambda wrapper with no reaching lambda stays unflagged
- **WHEN** the same wrapper shape occurs but `com.example.MainActivity` has no `lambda$…` method with
  `reachesTarget` or `directlyReachesTarget` true
- **THEN** the widget SHALL NOT be flagged
- **AND** `stats.syntheticLambda` SHALL count the wrapper while `stats.recovered` SHALL NOT

#### Scenario: a null event type folds into the aggregate
- **WHEN** a widget's only flagged listener carries `eventType: null`
- **THEN** the wire map SHALL carry `{"": "transitive"}`, so the jar's OR-over-the-map recompute of
  the aggregate still sees the flag
- **AND** the widget's base activity SHALL be in `mopActivities`

#### Scenario: a null event type adds no key when another event is flagged
- **WHEN** the same widget also carries a flagged `click` listener
- **THEN** the wire map SHALL carry `{"click": "transitive"}` and no `""` key, because the aggregate
  is already recoverable from the keyed entry

#### Scenario: per-event flags are independent
- **WHEN** a widget has a `click` listener reaching a monitored operation and a `long_click` listener
  reaching nothing
- **THEN** the wire map SHALL carry `{"click": "transitive", "longclick": "none"}`
- **AND** the `none` entry SHALL be emitted explicitly, because key presence is what suppresses the
  aggregate fallback on the query side

#### Scenario: a listed wrapper keeps its own flags
- **WHEN** a widget's click listener has handler
  `<com.example.MainActivity$$ExternalSyntheticLambda1: void onClick(android.view.View)>`, listed in
  `reachability` with `reachesTarget: false` and `directlyReachesTarget: false`
- **AND** `com.example.MainActivity` has `lambda$onCreate$0` with `reachesTarget: true`, the body of a
  different wrapper
- **THEN** the widget's `click` entry SHALL be `none`
- **AND** `stats.recovered` SHALL NOT count it

---

### Requirement: Widget Map Keying, Collisions and Activity Marking (FR06)

Widgets SHALL be keyed `baseActivity → shortId`, where the base activity is the window name truncated
at the first `#`. Windows sharing a base activity (an activity and its `#OptionsMenu`, for instance)
SHALL accumulate into the same map under the collision policy of INV-DRV-02.

A MOP-flagged widget SHALL add its base activity to the widget-derived MOP-activity set **before** the
empty-short-id drop is evaluated. Deriving the set from the emitted map instead would silently shrink
it, and the loss cascades into `scoreWtg`, the frontier passes, the `stateMopDensity` floor, the
OPTIONSMENU gateway's second condition and the launcher census — with a normal `status=loaded` in the
trace. The pinned corpus exercises this: 19 apps carry at least one flagged widget with an empty
`idName`, 1,263 such widgets in total.

#### Scenario: a flagged widget with an empty short id still marks its activity
- **WHEN** the only MOP-flagged widget of base activity `com.example.CryptoActivity` carries
  `idName == ""`
- **THEN** the artifact SHALL NOT contain a widget entry for it
- **AND** `stats.droppedFlaggedNoId` SHALL count it
- **AND** `mopActivities` SHALL nevertheless contain `com.example.CryptoActivity` (INV-DRV-02)

#### Scenario: collision keeps the strongest flag regardless of order
- **WHEN** two widgets in the same base activity share `shortId == "btn_ok"`, one unflagged with a
  `hint` and one flagged `direct`
- **THEN** the emitted entry SHALL be the flagged one, whichever appears first in `windows[]`

#### Scenario: equal-rank collision keeps the first occurrence
- **WHEN** two unflagged widgets share `shortId == "btn_ok"`, the first carrying `hint == "user"` and
  the second `hint == "password"`
- **THEN** the emitted entry SHALL carry `hint == "user"`

---

### Requirement: DIALOG Re-Keying and WTG Click View (FR05)

DIALOG windows SHALL be re-keyed to their host activity before the activity sets are finalized, and
the WTG view SHALL be a deduplicated, click-only projection keyed by base source activity
(INV-DRV-03). The five coupled dialog sub-rules are: the host is the source of the **first** incoming
transition whose source window has a name; merging uses the same `mopRank` collision policy as widget
keying; the dialog's widget-map key is **moved**, not copied, so counts do not inflate; a merge that
carried at least one flagged widget promotes the host into the widget-derived activity set; and the
dialog class's own entry in that set is **retained**, because WTG edges into the dialog are keyed by
it and the OPTIONSMENU gateway tests membership of the edge target.

A dialog with no incoming transition is an orphan: it keeps its own key and is counted in
`stats.orphanDialogs`. WTG edges SHALL record `widget` (the transition event's `widgetName`, empty
string when absent) and `target` (the base target activity); exact duplicate edges within a source
SHALL be removed and counted in `stats.dedupedTransitions`.

#### Scenario: flagged dialog promotes its host and moves its widgets
- **WHEN** window `android.app.AlertDialog` has one flagged widget `btn_confirm` and the first
  incoming transition comes from `com.example.MainActivity`
- **THEN** `widgets["com.example.MainActivity"]["btn_confirm"]` SHALL exist
- **AND** `widgets` SHALL have no `android.app.AlertDialog` key
- **AND** `mopActivities` SHALL contain both `com.example.MainActivity` and `android.app.AlertDialog`

#### Scenario: first incoming edge wins
- **WHEN** a DIALOG window has incoming transitions from `ActivityA` and then `ActivityB`
- **THEN** its widgets SHALL merge into `ActivityA`

#### Scenario: orphan dialog keeps its key
- **WHEN** a DIALOG window has no incoming transition
- **THEN** its widget-map key SHALL remain the dialog class
- **AND** `stats.orphanDialogs` SHALL count it

#### Scenario: WTG keeps click edges only, deduplicated, by base activity
- **WHEN** `transitions[]` carries two identical click events from window `MainActivity#OptionsMenu`
  to `CipherActivity` and one `long_click` event between the same pair
- **THEN** `wtg["MainActivity"]` SHALL contain exactly one entry targeting `CipherActivity`
- **AND** `stats.dedupedTransitions` SHALL count the removed duplicate

---

### Requirement: MOP-Activity Sets and OPTIONSMENU Records (FR04)

The generator SHALL emit both activity sets. `mopActivities` is the widget-derived set of INV-DRV-02
and INV-DRV-03. `mopActivitiesAugmented` is the A′ union of three sources: the widget-derived set,
every `components.activities[]` entry with `reachesTarget == true`, and every `reachability[]` class
with `componentType == "activity"` carrying at least one method other than its own `<init>` and
`<clinit>` with `reachesTarget` or `directlyReachesTarget` true. The constructor exclusion is new in
format 2: under gh120 every activity constructor is a boundary target (its D12) and is listed reaching
itself, so without it every activity class would enter the augmented census and the A′ arm would
treat the whole app as MOP-bearing. Both sources contribute base activity names. Both sets SHALL be emitted
in sorted order, and the augmented set SHALL be a superset of the widget-derived one.

`optionsMenus` SHALL carry one record per distinct base activity owning an `OPTIONSMENU` window, with
`hasFlaggedWidget` the OR across that activity's menu windows. The gateway *set* is not shipped: it
depends on which activity set the run selects, so the jar recomputes it from these records, the WTG
view and the selected set.

#### Scenario: A′ union draws from three distinct sources
- **WHEN** the widget-derived set is `{A}`, `components.activities[]` flags `B` with
  `reachesTarget == true`, and `reachability[]` carries class `C` with `componentType == "activity"`
  and one method with `reachesTarget == true`
- **THEN** `mopActivities` SHALL equal `["A"]`
- **AND** `mopActivitiesAugmented` SHALL equal `["A", "B", "C"]`

#### Scenario: augmented set never loses a widget-derived member
- **WHEN** an activity is in the widget-derived set and flagged by no component or reachability source
- **THEN** it SHALL still appear in `mopActivitiesAugmented`

#### Scenario: OPTIONSMENU record reflects the parsed menu widgets
- **WHEN** `MainActivity#OptionsMenu` holds one flagged widget whose `idName` is empty
- **THEN** `optionsMenus` SHALL contain `{"activity": "MainActivity", "hasFlaggedWidget": true}`
- **AND** the emitted `widgets` map SHALL contain no entry for that widget

#### Scenario: an activity reaching only through its constructor stays out of source 3
- **WHEN** `derive()` runs on the gh120 cryptoapp fixture, where `MainActivity`'s only reaching method
  is `<br.unb.cic.cryptoapp.MainActivity: void <init>()>` (boundary target 23)
- **THEN** `mopActivitiesAugmented` SHALL NOT contain `br.unb.cic.cryptoapp.MainActivity`
- **AND** on that fixture `mopActivitiesAugmented` SHALL equal `mopActivities`

---

### Requirement: Per-Activity Deep-Link URI (FR19)

Each emitted activity SHALL carry `deepLinkUri`, assembled host-side by the rule the jar applies
today: the first intent-filter that declares `android.intent.action.VIEW` **and** a non-empty scheme
list yields `scheme + "://" + host + path`, where host and path are the filter's first entries or the
empty string when absent. When no filter qualifies the field SHALL be absent, which the dispatcher
reads as "use the explicit-component intent" (INV-DRV-07). The filter structure SHALL NOT be on the
wire.

This field is not optional decoration: the MOP stagnation launcher dispatches `ACTION_VIEW` on it, so
dropping it would make activities reachable only by deep link unopenable while the trace still
reported a normal load.

#### Scenario: deep link derived from the first ACTION_VIEW filter
- **WHEN** an activity declares an intent-filter with `android.intent.action.VIEW` and
  `data.schemes == ["myapp"]`, `data.hosts == ["detail"]`, `data.paths == ["/x"]`
- **THEN** its `deepLinkUri` SHALL be `"myapp://detail/x"`

#### Scenario: ACTION_VIEW without schemes yields no URI
- **WHEN** the only `ACTION_VIEW` filter has an empty scheme list
- **THEN** `deepLinkUri` SHALL be absent

#### Scenario: schemes without ACTION_VIEW yield no URI
- **WHEN** a filter declares `data.schemes == ["myapp"]` but its actions do not include
  `android.intent.action.VIEW`
- **THEN** `deepLinkUri` SHALL be absent

#### Scenario: activity without intent filters yields no URI
- **WHEN** an activity declares no intent-filter at all
- **THEN** `deepLinkUri` SHALL be absent
- **AND** the artifact SHALL carry no `data` block, scheme list, host list or path list

#### Scenario: missing host and path default to empty
- **WHEN** the qualifying filter carries `data.schemes == ["myapp"]` with empty host and path lists
- **THEN** `deepLinkUri` SHALL be `"myapp://"`

---

### Requirement: Canonical Serialization and Provenance (NFR04)

`derive_mop_artifact.serialize_canonical(artifact)` SHALL emit canonical bytes: UTF-8, object keys
sorted lexicographically at every level, separators `,` and `:` with no whitespace, non-ASCII
characters preserved rather than escaped, and deterministic array order — source first-occurrence for
WTG edges and component lists, sorted for the activity sets and the OPTIONSMENU records, and sorted by
`(d, i)` for every distance pair list (INV-DRV-10). Running the
generator twice on the same full-JSON bytes SHALL produce byte-identical output, so the artifact's own
digest is stable and the `source.digest` chain identifies the exact static-analysis input of every run
(INV-DRV-05).

#### Scenario: byte-identical regeneration
- **WHEN** `derive()` + `serialize_canonical()` run twice on the same full JSON in separate processes
- **THEN** the two byte sequences SHALL be identical

#### Scenario: provenance digest matches the input
- **WHEN** an artifact is generated from a full JSON whose SHA-256 is `d`
- **THEN** `source.digest` SHALL equal `"sha256:" + d`
- **AND** `source.file` SHALL be the basename of that JSON

---

### Requirement: Equivalence Gate for the Parser Cutover

Before the jar's full-JSON parser is deleted, a one-shot equivalence gate SHALL demonstrate over a
designed input set — the cryptoapp fixture pair plus one synthetic full-JSON fragment per relocated
rule — that the projections served by the old parser on the full JSON and by the new parser on the
derived artifact are identical: widget flag maps including per-event entries and aggregates, widget
metadata, both activity sets, OPTIONSMENU gateway sets under both flag states, WTG views, component
and provider trigger tuples, per-activity deep-link URIs including their absent cases, and
`package`/`mainActivity`. The gate lives on the `ape` side, where both parsers are; this requirement
governs what this module owes it — the generator that produces the artifact half of every comparison,
and the synthetics being derived through that generator rather than hand-written.

The gate's oracle SHALL be the old parser reading the **raw** full JSON, not the enriched copy the
deleted compaction step used to push. The enrichment is a behaviour this change retires (see the
REMOVED requirement below), so comparing against it would prove the distortion rather than the
relocation. No synthetic authored for the gate may carry the enrichment for the same reason.

Each relocated rule SHALL have at least one input-set member that **fires** it, and the gate SHALL
fail when one does not.

**Scope decision, 2026-08-05 (owner).** This gate was specified over the pinned 345-application corpus
and that run does not occur: the APE-RV side executes once, in `gh97-rearch-ab-gate`, which gates the
merge rather than the cutover. What the corpus already established stands, because it was executed:
the batch derivation of tasks 7.1/7.2 ran over all 345 documents with no crash and no refusal, and its
per-rule exercise counts are the measured record — **19** apps carry flagged widgets dropped for an
empty short id, **10** carry recoverable D8 synthetic-lambda handlers, **165** carry DIALOG windows,
and the A′ union differs from the widget-derived set wherever component or reachability sources add an
activity. Those counts are why each of these rules is worth a synthetic and are retained as evidence
that the shapes are common in real applications; they are **not** evidence of jar-side equivalence over
those applications, which is the thing that now goes unmeasured. The gate is deleted with the old
parser once green; what survives is the per-rule unit suite of this module.

#### Scenario: equivalence over the designed input set
- **WHEN** the gate runs over the cryptoapp pair and the per-rule synthetics
- **THEN** every member SHALL compare equal on every projection listed above
- **AND** any inequality SHALL fail the gate naming the member and the first differing projection

#### Scenario: a rule fired by no member fails the gate
- **WHEN** no member of the input set fires D8 synthetic-lambda recovery
- **THEN** the gate SHALL fail
- **AND** the omission SHALL be repaired by a synthetic that fires the rule, never by lowering the
  requirement — a rule with no firing member is uncovered, whatever the rest of the set proves

### Requirement: Corpus Basis Provenance (FR18, FR19, NFR06)

`ApeRVTool` SHALL accept an optional `corpus_basis` configuration value identifying the application
list a run was drawn from, and `_push_properties()` SHALL write it to the generated `ape.properties`
as `ape.corpusBasis=<value>` when present. The value SHALL be treated as opaque provenance: the tool
validates its shape and passes it through unchanged, and SHALL NOT derive, complete or normalize it.

This exists because a run's artifacts cannot today answer which corpus it belonged to. A results
directory names one application; the list that application was drawn from lives in a campaign
directory, a compose file's bind-mount, or an operator's memory. The cost is not hypothetical — this
study has counted its analysis basis as 163, 181 and 219 applications in different documents, and
every cross-campaign analysis has had to re-derive the membership before it could compare anything.

Validation SHALL occur in `configure()`, before any device interaction, and SHALL reject any value not
matching `^[A-Za-z0-9._-]+:[0-9a-f]{64}$` with `ConfigurationError` naming the offending value. The
two-part shape is what makes the value useful: the identifier is what a human reads in a report, and
the digest is what makes two runs provably drawn from the same list rather than from two lists that
happen to share a name.

The tool SHALL NOT own the corpus list and SHALL NOT grow a filesystem dependency on a campaign's
layout in order to hash it. Correctness of the digest itself is established where the corpus lives, by
recomputing it from the list file and comparing against `RUN_START.corpus_basis` during a campaign's
pre-flight — a check against the file, not a transcription anyone has to trust.

When the value is absent the key SHALL be omitted entirely (INV-APV-56). Absence is a legitimate state
— every campaign before this requirement ran without it, and every standalone invocation still does —
and it SHALL NOT be treated as an error, a warning, or a reason to synthesize a value.

The tool SHALL NOT read the value back from `RUN_START` or from any other artifact at run time
(INV-APV-57). Confirming that the jar received and echoed what was pushed is the campaign pre-flight's
work, performed by an operator script over a recorded trace.

#### Scenario: A configured corpus basis reaches the device

- **WHEN** `configure()` receives `corpus_basis="subset40:4157faa071fae1b405730de6d3fabf3d6821e54830473e98d2c342bffcadd252"` and `_push_properties()` runs for variant `as_mop`
- **THEN** the generated `ape.properties` SHALL contain the line `ape.corpusBasis=subset40:4157faa071fae1b405730de6d3fabf3d6821e54830473e98d2c342bffcadd252`
- **AND** the value SHALL be byte-identical to what was configured, with no re-derivation, truncation or case change
- **AND** the run's `RUN_START` SHALL carry `corpus_basis` with that same value

#### Scenario: An unstated corpus produces no key at all

- **WHEN** `_push_properties()` runs for variant `base` and `corpus_basis` is absent from `_tool_config`
- **THEN** the generated `ape.properties` SHALL NOT contain any line beginning `ape.corpusBasis`
- **AND** no warning SHALL be logged and no placeholder value SHALL be substituted
- **AND** the run SHALL proceed normally, since a standalone invocation has no corpus to state

#### Scenario: A malformed basis fails before the emulator is touched

- **WHEN** `configure()` receives `corpus_basis="subset40"` — an identifier with no digest
- **THEN** it SHALL raise `ConfigurationError` naming the key and the rejected value
- **AND** the error SHALL be raised before any `adb push`, so no device is started and no partially-configured run exists

#### Scenario: A digest that does not match the list is caught by the pre-flight, not by the tool

- **WHEN** a campaign is configured with `corpus_basis="subset40:<digest>"` where `<digest>` is well-formed but was transcribed from a different list, and the pre-flight recomputes the SHA-256 of the list file
- **THEN** `ApeRVTool` SHALL have pushed the value unchanged, because shape is all it validates
- **AND** the pre-flight SHALL report the mismatch between the recomputed digest and `RUN_START.corpus_basis` and fail the gate
- **AND** no component of `modules/aperv-tool` SHALL have read `RUN_START` in the process

---

### Requirement: Run Completion Is Established, Not Assumed (FR18, NFR06)

`ApeRVTool` SHALL establish that an exploration ran for the budget it was given before reporting the
run as successful. When the exploration process returns and the elapsed time falls short of the
requested budget by more than the teardown grace already applied to the command, the tool SHALL raise
`RVToolExecutionError` naming the elapsed time and the budget, so `rv-platform` records the task as
`ERROR` and its own resume re-executes it (INV-APV-60).

**The exit code is not the discriminator, and cannot be made into one.** A non-zero exit is a normal
outcome for APE-RV — it exits non-zero when it detects an application crash during exploration — so
the same code means both "the application under test misbehaved, which is data" and "the device went
away, which is a lost run". Elapsed time separates them without ambiguity: an exploration that was
asked for 1800 s and returned at 1012 s did not do the work, whatever ended it.

**A timeout remains the normal, successful ending and is unaffected.** APE-RV is designed to explore
until stopped; the `RVToolTimeoutError` path, its trace compression and its treatment as a completed
run are unchanged. What this requirement removes is the third path — a return that is neither a
timeout nor a full budget — which previously logged success and inspected nothing.

The check SHALL read only the tool's own measurement of the exploration it launched. It SHALL NOT
open, parse or inspect the trace, the logcat or any recorded artifact: `tool.py` reads no jar output
(INV-APV-43), and admissibility judged from artifacts is a campaign gate's work, performed after the
fact over the whole results tree.

#### Scenario: A run cut short by a dead emulator fails loudly

- **WHEN** an exploration is launched with a 1800 s budget and the `adb shell` command returns after 1284 s because the emulator died mid-run
- **THEN** `ApeRVTool` SHALL raise `RVToolExecutionError` naming both 1284 s and 1800 s
- **AND** it SHALL NOT log that the execution completed successfully
- **AND** `rv-platform` SHALL record the task with state `ERROR` and a non-empty `error_message`, so the identity is not skipped on the next resume

#### Scenario: A run that reaches its budget is unaffected

- **WHEN** an exploration is launched with a 1800 s budget and APE-RV returns on its own clock at approximately 1800 s, having exited non-zero because the application under test crashed during exploration
- **THEN** the tool SHALL treat the run as successful, because the budget was consumed
- **AND** the non-zero exit SHALL NOT by itself cause a failure, since an application crash is data the run exists to collect

#### Scenario: The timeout path keeps its meaning

- **WHEN** the exploration is still running when the command's timeout expires
- **THEN** `RVToolTimeoutError` SHALL be raised exactly as before and the run SHALL be recorded as completed
- **AND** the trace SHALL be compressed on this path as it already is, with the truncated final line included

### Requirement: Arm Property Overrides Pass-Through

`APERV_PROPERTY_MAPPING` SHALL be a pass-through table and nothing more: it exists to translate a
Python override key into an `ape.*` property name, and it SHALL contain only keys the deployed jar
accepts (INV-APV-41). Behavioural validation of values, types, dependencies and combinations is the
jar's responsibility under stage-2 fail-fast resolution; the Python side SHALL perform no semantic
validation of overrides beyond the mapping-membership check.

This is a deliberate transfer of responsibility rather than a loss of one. Guards on the Python side could only
compare Python constants with Python constants, so they detected a missing mapping entry but never a value the jar
would reject, a sub-parameter whose feature was inactive, or a key the jar had stopped reading. The jar rejects all
four, at run time, with an abort naming the key — a stronger check, applied to the binary that actually runs.

At implementation time the mapping SHALL be swept against the jar's accepted-key vocabulary
(`KeyOwnership.allKeys()` plus the retired list, read from the `ape` source checkout on the branch
`isolate-guidance-groups`) and any dead entry removed. The sweep performed while authoring this change against the
key contract found two: `mop_target_pick_cap` and `least_visited_priority_tiebreak`, both retired by the jar.

#### Scenario: Dead key removed
- **WHEN** `APERV_PROPERTY_MAPPING` is inspected after this change
- **THEN** it SHALL NOT contain `mop_target_pick_cap`, `least_visited_priority_tiebreak` or `mop_weight_activity`
- **AND** a grep for `mopTargetPickCap`, `leastVisitedPriorityTiebreak` and `mopDataPath` across
  `modules/aperv-tool/src` SHALL return no hit

#### Scenario: Every mapped key is one the jar accepts
- **WHEN** each value of `APERV_PROPERTY_MAPPING` is checked against the accepted-key vocabulary of the jar
  source on the `isolate-guidance-groups` branch
- **THEN** every one SHALL be present in it
- **AND** none SHALL appear in the jar's retired-key list

#### Scenario: Live ungoverned key travels the normal path
- **WHEN** `aperv:as_mop_llm@llm_snap_tolerance_px=120` is resolved
- **THEN** `llm_snap_tolerance_px: 120` SHALL be an entry of its `overrides`
- **AND** `_push_properties()` SHALL write `ape.llmSnapTolerancePx=120`
- **AND** the variant SHALL carry no key declaring the jar it was raised for (INV-APV-59)

#### Scenario: No semantic validation is performed on override values
- **WHEN** a variant's `overrides` carries a mapped key at a value the jar will reject, such as
  `llm_url` on the `as_mop` cell, which does not mount LLM
- **THEN** `_push_properties()` SHALL write it unchanged
- **AND** the rejection SHALL come from the jar as an abort before step 1, visible in the trace

---

### Requirement: ApeRVTool Cell Variants (FR20)

`ApeRVTool` SHALL define one variant per experimental cell and nothing else. Every variant SHALL consist of a
`preset` name, a `variant` name, an `overrides` dict, and Python-only orchestration keys (INV-APV-40).

`get_variants()` SHALL return exactly these **eight** names, carrying **seven** distinct configurations: the six
cells, `default`, and one ablation variant, `mop_nolaunch`:

| Variant | preset | static_data | broadcast_catalog | overrides | Groups mounted by the preset |
|---|---|---|---|---|---|
| `default` | `base` | — | — | _(empty)_ — bound to the same object as `base` (INV-TOOL-02) | — |
| `base` | `base` | — | — | _(empty)_ | — |
| `mop` | `mop` | `"static_analysis"` | — | `mop_coin_ledger_max_interactions: 2` | MOP |
| `as` | `as` | `"static_analysis"` | `True` | _(empty)_ | ADDONS, STATIC |
| `as_mop` | `as_mop` | `"static_analysis"` | `True` | `mop_coin_ledger_max_interactions: 2` | ADDONS, STATIC, MOP |
| `as_llm` | `as_llm` | `"static_analysis"` | `True` | `llm_url` | ADDONS, STATIC, LLM |
| `as_mop_llm` | `as_mop_llm` | `"static_analysis"` | `True` | `mop_coin_ledger_max_interactions: 2`, `llm_url` | ADDONS, STATIC, MOP, LLM |
| `mop_nolaunch` | `mop` | `"static_analysis"` | — | `mop_coin_ledger_max_interactions: 2`, `activity_trigger_enabled: False` | MOP without `MOP_LAUNCHER` |

Every variant carries `strategy="sata"` and `variant` equal to its own name; `default` carries `"base"`.

**What a cell means lives in the jar.** Each preset is the union of the jar's group blocks (the `ape` design's
§ "Group blocks and cells"): ADDONS is the former `aperv` vector, STATIC is the frontier at 200 plus typed input,
MOP is E6 arm 3's MOP configuration plus `p_M = 1.0`, LLM is E6 arm 4's sampling configuration with `p_L = 0.9`.
On a cell, `overrides` SHALL carry only what the jar cannot know, the server URL, with one exception: the three
cells that mount MOP (`mop`, `as_mop`, `as_mop_llm`) carry `mop_coin_ledger_max_interactions: 2`, so the MOP coin
may take each (activity, widget) key twice instead of the jar's default once. In the `e03igg2` campaign the coin at
2 brought `mop` back to the misuse level of the earlier jar and was the only arm above `ape`; the author placed
that default on this side, and the jar's group blocks do not state the key (author's decision, 2026-10-19). A dose (`llm_percentage`,
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
- **THEN** `overrides` SHALL be exactly `{"mop_coin_ledger_max_interactions": 2, "llm_url": "http://10.0.2.2:30000/v1"}`
- **AND** `get_variants()["as_llm"]["overrides"]` SHALL be exactly `{"llm_url": "http://10.0.2.2:30000/v1"}`
- **AND** `get_variants()["mop"]["overrides"]` and `get_variants()["as_mop"]["overrides"]` SHALL each be exactly
  `{"mop_coin_ledger_max_interactions": 2}`
- **AND** the `base` and `as` cells' `overrides` SHALL be empty

#### Scenario: The MOP cells write the ledger budget

- **WHEN** `_push_properties()` runs for the `mop` cell with the artifact pushed
- **THEN** it SHALL write `ape.preset=mop`, `ape.variant=mop`, `ape.staticDataPath=/data/local/tmp/mop-artifact.json`
  and `ape.mopCoinLedgerMaxInteractions=2`, in that order
- **AND** for the `as_mop_llm` cell the line `ape.mopCoinLedgerMaxInteractions=2` SHALL come before `ape.llmUrl=…`,
  because the lines follow the order of `APERV_PROPERTY_MAPPING`

#### Scenario: The launcher ablation is the mop cell without its launcher

- **WHEN** `get_variants()["mop_nolaunch"]` is read
- **THEN** `preset` SHALL be `"mop"`, `variant` SHALL be `"mop_nolaunch"` and `strategy` SHALL be `"sata"`
- **AND** `overrides` SHALL be exactly `{"mop_coin_ledger_max_interactions": 2, "activity_trigger_enabled": False}`,
  the `mop` cell's plus one key
- **AND** every other top-level key SHALL equal the `mop` cell's
- **AND** `_push_properties()` with the artifact pushed SHALL write `ape.preset=mop`, `ape.variant=mop_nolaunch`,
  `ape.staticDataPath=/data/local/tmp/mop-artifact.json`, `ape.activityTriggerEnabled=false` and
  `ape.mopCoinLedgerMaxInteractions=2`, in that order

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
Overrides Pass-Through"). It SHALL contain only keys the deployed jar accepts (INV-APV-41). The 67
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
| `mop_weight_d1` | `ape.mopWeightD1` | `MOP` sub-parameter, read under `distance` only |
| `mop_weight_d2` | `ape.mopWeightD2` | `MOP` sub-parameter, read under `distance` only |
| `mop_weight_d3` | `ape.mopWeightD3` | `MOP` sub-parameter, read under `distance` only |
| `mop_retire_after` | `ape.mopRetireAfter` | `MOP` sub-parameter, read under `distance` only |
| `mop_launcher_dmax` | `ape.mopLauncherDmax` | `MOP` sub-parameter, read under `distance` only |
| `mop_coin_percentage` | `ape.mopCoinPercentage` | `MOP_COIN` activation (MOP); `p_M`, jar default 1.0 |
| `mop_coin_ledger_max_interactions` | `ape.mopCoinLedgerMaxInteractions` | `MOP_COIN` sub-parameter; the coin's picks per (activity, widget) key, jar default 1, values below 1 read as 1; set to 2 on the `mop`, `as_mop` and `as_mop_llm` cells |
| `llm_url` | `ape.llmUrl` | `LLM` dependency; required on both LLM cells (INV-APV-38) |
| `llm_on_new_state` | `ape.llmOnNewState` | `LLM_NEW_STATE` activation |
| `llm_on_stagnation` | `ape.llmOnStagnation` | `LLM_STAGNATION` activation |
| `llm_model` | `ape.llmModel` | `LLM` sub-parameter |
| `llm_temperature` | `ape.llmTemperature` | `LLM` sub-parameter |
| `llm_top_p` | `ape.llmTopP` | `LLM` sub-parameter |
| `llm_top_k` | `ape.llmTopK` | `LLM` sub-parameter |
| `llm_timeout_ms` | `ape.llmTimeoutMs` | `LLM` sub-parameter |
| `llm_percentage` | `ape.llmPercentage` | `LLM_COIN` activation; `p_L`, the LLM block states 0.9 |
| `llm_percentage_no_substrate` | `ape.llmPercentageNoSubstrate` | `LLM_COIN` sub-parameter; the `-1` sentinel is accepted on a plan with no LLM |
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
`llm_boundary_top_pct`). `ape.variant` and
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
- **AND** the remaining lines SHALL be `ape.mopCoinLedgerMaxInteractions=2` and `ape.llmUrl=http://10.0.2.2:30000/v1`,
  in that order

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
- **THEN** it SHALL contain exactly 67 entries
- **AND** it SHALL contain `addons`, `static`, `mop`, `llm`, `mop_coin_percentage`,
  `mop_coin_ledger_max_interactions`, `llm_gate_min_actions`,
  `llm_breaker_failures`, `llm_breaker_open_ms`, `activity_stable_restart_threshold`,
  `take_screenshot_for_every_step`, `save_gui_tree_to_xml_every_step` and `llm_boundary_top_pct`
- **AND** it SHALL NOT contain `mop_target_pick_cap`, `least_visited_priority_tiebreak`, `mop_weight_activity`,
  `step_telemetry_enabled`, `variant` or any key mapping to `ape.mopDataPath` or `ape.staticDataPath`

#### Scenario: Python-only keys are still excluded
- **WHEN** `_push_properties()` is called for `aperv:as_mop@seed=42`, whose `_tool_config` carries
  `strategy`, `static_data` and `seed`
- **THEN** the properties file SHALL contain none of those three names

#### Scenario: A dose ablation writes the dose
- **WHEN** `_push_properties()` is called for `aperv:as_mop_llm@llm_percentage=0.7` with the artifact pushed
- **THEN** the file SHALL contain `ape.llmPercentage=0.7`
- **AND** it SHALL contain no `ape.mopCoinPercentage` line, because the cell takes the MOP block's 1.0

### Requirement: NDJSON Trace Reader (FR11, FR13, NFR03, NFR06)

The module SHALL provide `modules/aperv-tool/src/aperv_tool/analysis/trace_ndjson.py`, a read-only streaming reader of the NDJSON trace, and it SHALL be the sole mechanism by which analysis code in this module consumes a stage-4 trace. It follows the shape of its sibling `analysis/coverage_dump.py`: a pure offline component with a typed row model, never in the run path.

The reader SHALL stream the file — the trace is the largest artifact a run produces, and the reader must not require it in memory — and SHALL yield one typed row per `StepRecord`, having already:

- resolved the `act` and `st` integer references, and `out.target`, against the `ACT` / `STATE` dictionary records defined earlier in the same trace;
- materialized the fields the sink omits at their documented defaults, and left the tri-state fields and every member added by the group-isolation jar absent when absent (INV-APV-49);
- re-derived `activity_has_mop` on the step side from the record's `ACT` entry, and on the outcome side via `out.target` → `STATE.act` → `ACT.mop`, since the jar records that static per-activity fact once on the dictionary entry rather than on every step;
- expanded the run-relative `t` to epoch milliseconds via `RUN_START.t0` where an absolute clock is wanted, and reported the expansion as unavailable when `RUN_START` is absent (INV-APV-51);
- attached the step's `llm[]` sub-events, in occurrence order, and its `out` section to the same row — so that the three-way join by `step=` that the legacy format required ceases to exist for every consumer;
- carried each sub-event **whole**, including the `sys` / `user` / `resp` / `tool_calls` prompt and response dumps (INV-APV-58);
- carried every `dec` member the jar writes (INV-APV-58).

**The decision record of the group-isolation jar.** The jar built from the `ape` branch `isolate-guidance-groups`
records, for each step, which mechanism owned it and why. `StepRow` SHALL carry each member under a typed field,
`None` when absent:

| Wire member | `StepRow` field | Type |
|---|---|---|
| `dec.own` | `owner` | `Ownership(intended: str, trigger: Optional[str], u_llm: Optional[float], u_mop: Optional[float], gate: Optional[str], fallback: Optional[str])` |
| `dec.cfc` | `scorer_cf` | `Mapping[str, bool]` keyed by scorer name |
| `dec.draw` | `draw` | `Tuple[int, int]` (index, total) |
| `dec.nav` | `nav` | `NavTie(point: str, component: str, alternative: bool, drew: bool)` |
| `dec.inp` | `input_source` | `str` |
| `dec.restart` | `restart_kind` | `str` |
| `dec.bmc` | `back_menu_capped` | `int` |
| `dec.strat` | `sata_path` | `str` |
| `dec.rot` | `rotation` | `int` |
| `dec.buf` | `buffer_abandoned_by` | `str` |
| `dec.trig` | `component_trigger` | `ComponentTrigger(kind: str, component_class: str)` |
| `dec.navf` | `nav_frontier` | `int`, a boost field materialized at `0` |
| `dec.mopd` | `mop_distance` | `int` |
| `dec.mops` | `mop_stamp` | `str` |
| `dec.ret` | `retired_targets` | `Tuple[int, ...]` |
| `dec.hnd` | `mop_handler` | `str` |

The reader SHALL NOT validate the enumerated values of these members against a closed list. A value it does not
know is carried as written. A new owner or SATA path added on the jar side would otherwise turn well-formed records
into malformed ones, and malformed-record counting exists for damaged lines (INV-APV-50).

**`decision_source` has two meanings, and the reader does not choose between them (INV-APV-67).** Under
`RUN_START.v == 2` (the group-isolation jar) `dec.src` is the **owner** that executed the step, one of `budget`, `restart`, `llm`,
`launcher`, `mop`, `sata`, which makes it causal. On the `eea2b1a9` jar and earlier it is the stage whose boost was
largest, under `v == 1`. That label is not causal, because every stage adds into one shared priority. The row carries
the value as written, and `run_start.v` says which meaning applies. A consumer that counts `decision_source` across traces of both jars is
counting two different things, and the documentation of `StepRow.decision_source` SHALL say so.

**`Counterfactual` and `scorer_cf` say what they remove.** `counterfactual` is the `eea2b1a9` jar's `dec.cf`. It is
the pick the agent would have made with **only the MOP boosts** zeroed, so a `changed` value is evidence about MOP
guidance and about nothing else. It is absent on the group-isolation jar, which removed `dec.cf`. `scorer_cf` is that
jar's `dec.cfc`. For each mounted scorer with a non-zero term in the candidate set, it records whether zeroing that
one scorer would have changed the pick at a roulette or least-visited site, replaying the same draw index. On the
least-visited pick the candidate set is the tie of least-visited actions, and `cfc` is written only when that tie
holds two or more actions. It answers
"did this scorer change the choice", one scorer at a time. It does not answer "did the guidance as a whole change it".

**`RunStart` carries the whole `RUN_START` record (INV-APV-61).** The jar echoes its resolved run specification into the first record so that a post-hoc audit can say which jar, which cell and which parameters produced a trace — `build.sha` exists because a stale jar once shipped, its MOP boost fired zero times across 147,153 evaluations, and nothing in 2,028 tasks' output said which jar had run. `RunStart` SHALL therefore expose `v`, `run_id`, `t0_ms`, `seed`, `agent`, `preset`, `variant`, `features`, `params`, `inert`, `corpus_basis`, `digest`, `props_digest` and `build` (as a nested value with `sha` and `time`), each reported absent — `None` — when the wire record lacks it, never defaulted; `params` remains what the jar recorded verbatim (only non-default values plus active activation keys — absence means "at the jar default for this `build.sha`"). `variant` is absent on every trace written before the group-isolation jar. No consumer in `aperv_tool` SHALL parse `RUN_START` other than through this class.

**The `v` schema gate is checked, not merely carried (INV-APV-62).** The reader implements two versions, `SUPPORTED_VERSIONS = {1, 2}`. Version 1 is the `eea2b1a9` jar and earlier, and version 2 is the group-isolation jar, which bumped `RunSpecEcho.FORMAT_VERSION` because `dec.src` changed meaning. Any other declared version SHALL be recorded in `TraceDiagnostics.schema_version_mismatch` and, when the reader is constructed with `strict=True`, SHALL raise `SchemaVersionMismatch` before any row is yielded — a cross-campaign comparison over incomparable fields fails loudly rather than quietly. The default is non-strict, so a survey over a mixed tree still yields rows and counts the mismatches. A trace whose capture began after `RUN_START` reports the version as unknown, and the reader does not infer it.

**`activity_has_mop` is absent where it was not computed (INV-APV-68).** The group-isolation jar writes `ACT.mop` only when the MOP group is mounted. An `ACT` without `mop` SHALL resolve to `activity_has_mop = None` on both sides of the row, not to `False`. A trace of the `eea2b1a9` jar always carries the member and reads as before. The artifact census `MOP_DATA` is not the same signal: it appears in every cell that loads the artifact, `as` and `as_llm` included, because it reports the load and not the MOP group.

**The run-level records are reader attributes, `RUN_END` included.** The reader SHALL expose `MOP_DATA`, `PIPELINE`,
`LLM_ACK` and `RUN_END` as attributes beside the `RUN_START` header, each the record verbatim minus `type`, and
`None` when the trace carries none. A step-row iterator has no natural place for run-level records, and this module
is the only way to reach them. `RUN_END` is now one of them. Its counters (`launches`, `gateMinActions`,
`gateBreaker`, `guardBacks`, `bufAbandoned`, `restarts`, `coinLlm`, `coinMop`, `nullRelaunches`, beside the existing `acts`,
`states`, `stampNodes`, `stampHits`, `retired` and `llm`) are the per-run census of the mechanisms the cells mount,
and an analysis of the cells needs them. Owner decision D5 stays in force where it was aimed, on the collection
path. `tool.py` reads no `RUN_END`, and the reader exposes the record without interpreting it: there is no
completeness flag, no "ended normally" property and no derived status (INV-APV-53). A trace without `RUN_END` is a
fact the analysis reports, not something the reader repairs.

The reader SHALL NOT convert between formats in either direction, SHALL NOT write to the trace, and SHALL NOT run on the collection path (INV-APV-48). A malformed record SHALL be skipped and counted rather than aborting the read (INV-APV-50): a trace truncated by a `SIGKILL` ends in a partial line by construction, and losing the whole run's analysis over its last line would be a worse failure than losing the line. `RUN_START` is not guaranteed to be line 1 — AOSP banner lines may precede it — so the reader SHALL take the first `{`-leading line as the candidate header.

**The `ape` changes are the authority for the wire format.** `rearch-04-step-ndjson-telemetry` defines the `StepRecord` schema, the dictionary encoding, the omitted-default rules and the heartbeat payload; `isolate-guidance-groups` defines the members listed above, the meaning of `dec.src` on its jar, `RUN_START.variant` and the new `RUN_END` counters. This reader conforms to them rather than restating them.

The golden fixture that exercises this requirement SHALL be `modules/aperv-tool/tests/fixtures/trace_ndjson_golden.ndjson`, a hand-written stage-4 trace from the `eea2b1a9` jar containing, at minimum: a `RUN_START` with `t0` **and all thirteen of that jar's members**; `ACT` entries with `mop:1` and `mop:0`; two `STATE` entries; a step whose `dec` carries no boost fields at all; a step carrying `patched:0`; a step carrying no `patched` member; a step with two `llm[]` entries in occurrence order; a step whose `out` resolves to a new state; a step closed with no `out` member; a step flushed with `out:{"resolved":false}`; a completed call carrying the `sys` / `user` / `resp` / `tool_calls` dumps beside one that carries none; a step carrying `mopd`, `mops` and `ret`; a `MOP_DATA` record, a `PIPELINE` record whose `candidates` include disabled entries, an `LLM_ACK` and a `RUN_END` with `counters`; a malformed line; and a truncated final line. A second fixture, `trace_ndjson_v3_header.ndjson` (renamed from `trace_ndjson_v2_header.ndjson`, since 2 is now a supported version), SHALL carry `RUN_START` with `v: 3` and one step. A third, `trace_ndjson_groups.ndjson`, SHALL be a trace of the group-isolation jar: a `RUN_START` carrying `v: 2` and `variant: "as_mop_llm"`; an `ACT` without `mop`; a step owned by each of `llm`, `mop`, `restart` and `sata`; a step carrying every member of the table above; a step carrying `dec.own` with `fb` and `g`; a step carrying `dec.own.fb:"screenshot"`; a step carrying
`dec.mops:"s"` with `dec.hnd`; and a `RUN_END` carrying the nine new counters. Every scenario below names the fixture element that exercises it, so no rule is asserted against an input that cannot reach it.

#### Scenario: Reader yields a joined step row
- **WHEN** the reader runs over the golden fixture, whose step 42 carries a `dec` with no boost fields, two `llm[]` sub-events and an `out` closed at step 43
- **THEN** it SHALL yield exactly one row for step 42
- **AND** that row SHALL carry the activity and state resolved to their dictionary strings, not their integer IDs
- **AND** it SHALL carry `mop=0`, `mop_frontier=0`, `wtg=0`, `nav_frontier=0`, `coverage=0`, `menu=0` and `form=0` as explicit zeros
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

#### Scenario: The MOP stamp members reach the row
- **WHEN** the reader runs over the golden fixture's step carrying `dec.mopd:2`, `dec.mops:"s"` and `dec.ret:[0,3]`
- **THEN** the row SHALL report `mop_distance=2`, `mop_stamp="s"` and `retired_targets=(0, 3)`
- **AND** a step carrying none of them SHALL report all three as `None`

#### Scenario: The owner record of the group-isolation jar reaches the row
- **WHEN** the reader runs over the groups fixture's step with `dec.src:"sata"` and `dec.own:{"i":"llm","trg":"coin","uL":0.42,"uM":0.17,"g":"min_actions","fb":"gate"}`
- **THEN** the row SHALL report `decision_source="sata"`
- **AND** `owner` SHALL be `Ownership(intended="llm", trigger="coin", u_llm=0.42, u_mop=0.17, gate="min_actions", fallback="gate")`

#### Scenario: Every new decision member reaches the row
- **WHEN** the reader runs over the groups fixture's step carrying `cfc`, `draw`, `nav`, `inp`, `restart`, `bmc`, `strat`, `rot`, `buf`, `trig` and `navf`
- **THEN** each SHALL reach its `StepRow` field with the type of the table above
- **AND** `nav` given as `{"x":"X3","c":"mop","alt":1,"drew":0}` SHALL become `NavTie(point="X3", component="mop", alternative=True, drew=False)`
- **AND** `trig` given as `{"k":"broadcast","c":"com.example.BootReceiver"}` SHALL become `ComponentTrigger(kind="broadcast", component_class="com.example.BootReceiver")`
- **AND** `rotation` given as `0` SHALL be `0`, not `None`

#### Scenario: An eea2b1a9 trace reports the new members as absent
- **WHEN** the reader runs over the golden fixture, which comes from the `eea2b1a9` jar
- **THEN** `owner`, `scorer_cf`, `draw`, `nav`, `input_source`, `restart_kind`, `back_menu_capped`, `sata_path`, `rotation`, `buffer_abandoned_by` and `component_trigger` SHALL be `None` on every row
- **AND** `nav_frontier` SHALL be `0`, as the other boost fields are
- **AND** `reader.run_start.variant` SHALL be `None`

#### Scenario: An unknown enumerated value is carried, not rejected
- **WHEN** a step carries `dec.strat:"lookahead"`, a value absent from the fifteen names the contract lists
- **THEN** the row SHALL report `sata_path="lookahead"`
- **AND** the record SHALL NOT be counted as malformed

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
- **AND** the schema version SHALL be reported unknown, not assumed

#### Scenario: Prompt and response dumps reach the caller
- **WHEN** the reader runs over the fixture's step-42 completed call, which carries `sys`, `user`, `resp` and `tool_calls`
- **THEN** the sub-event SHALL carry all four, with the widget list's embedded newlines intact as the jar escaped them
- **AND** the abandoned attempt beside it, written without dumps, SHALL report them as absent rather than as empty strings — an empty string would claim the model was sent an empty prompt

#### Scenario: The run-level records are reachable, RUN_END included
- **WHEN** the reader runs over the groups fixture, which carries `MOP_DATA`, `PIPELINE`, `LLM_ACK` and a `RUN_END` whose `counters` hold `launches:4`, `coinLlm:120` and `coinMop:37`
- **THEN** the four SHALL be readable as reader attributes
- **AND** `reader.run_end["counters"]["coinMop"]` SHALL be `37`
- **AND** the reader SHALL expose no property derived from `RUN_END`, such as a completeness flag (INV-APV-53)
- **AND** a trace carrying none of them SHALL report each as `None` rather than as an empty record

#### Scenario: RunStart carries every member, variant included
- **WHEN** the reader runs over the groups fixture's `RUN_START`, which carries `v, run_id, t0, seed, agent, preset, variant, features, params, inert, corpus_basis, digest, props_digest, build{sha,time}`
- **THEN** `reader.run_start` SHALL expose each of them, `build` as a nested value with `sha` and `time`
- **AND** `reader.run_start.variant` SHALL be `"as_mop_llm"`
- **AND** a `RUN_START` written without `inert` SHALL report `inert=None`, not `False`

#### Scenario: Schema version mismatch is loud in strict mode and counted otherwise
- **WHEN** the reader opens `trace_ndjson_v3_header.ndjson` with `strict=True`
- **THEN** it SHALL raise `SchemaVersionMismatch` naming `3` and the supported versions `1` and `2` before yielding any row
- **AND** with `strict=False` it SHALL yield the row and report `schema_version_mismatch=1` in diagnostics

#### Scenario: Both jar generations are read in strict mode
- **WHEN** the reader opens the golden fixture (`v: 1`) and the groups fixture (`v: 2`) with `strict=True`
- **THEN** neither SHALL raise
- **AND** `run_start.v` SHALL be `1` and `2` respectively

#### Scenario: An activity without the MOP fact reports it absent
- **WHEN** the reader runs over the groups fixture's step whose `act` refers to an `ACT` record with no `mop` member
- **THEN** the row's `activity_has_mop` SHALL be `None`, not `False`
- **AND** a golden-fixture step whose `ACT` carries `mop:0` SHALL still report `False`

#### Scenario: Reader stays off the collection path
- **WHEN** the module's tests assert the import graph of `tools/aperv/tool.py`
- **THEN** `trace_ndjson` SHALL NOT be reachable from it
- **AND** no collection-path function SHALL reference `RUN_END` (INV-APV-53)

### Requirement: Cell Configuration Matches the Jar's Cell Echo (FR20, NFR06)

Each cell's configuration on the Python side SHALL be checked against what the jar resolves for it, on two levels
that answer different questions.

**Offline, against the jar source.** A test that reads the `ape` checkout on the branch `isolate-guidance-groups`
(through `$APE_REPO`, skipped without it, like the other `tests/migration` checks) SHALL assert three things. The
jar's preset vocabulary is exactly the six cell names. Each preset is the union of the group blocks the cell
names. The `RUN_START` fixture of each cell (`src/test/resources/cells/<cell>.run_start.json`) carries
`preset` and `variant` equal to the variant's own `preset` and `variant`. This catches a renamed cell or a moved
block before any device is started.

**On the device, against the trace.** The integration smoke SHALL run each cell it covers on an instrumented APK with its
`.apk.json` beside it and compare the recorded `RUN_START` with the cell's fixture on `preset`, `variant`, `features`, `params`, `inert`
and `digest`. The comparison masks the members that differ by construction: `run_id`, `t0`, `seed`, `build` and
`props_digest`. This is the gate of the cross-repository pairing (plan §9.3). A jar and a `tool.py` from different
sides of the key change cannot pass it, because the run aborts at resolution and writes no `RUN_START`. A pair
that passes it runs what each cell claims.

**A variant whose overrides reach the plan is checked with its deltas set apart.** The fixtures describe the jar's
presets, and the jar's echo rules predict how an override moves the echo: `params` carries a non-default value and
the activation key of each active feature, and a key of an inactive feature stated at its neutral value is
reported in `inert`. `digest` is not compared for these variants, because it hashes every plan value and so differs
by construction. `preset` SHALL be equal and `variant` SHALL be the variant's name.
- `mop`, `as_mop`, `as_mop_llm`, each against its own fixture: `features` and `inert` equal the fixture's; `params`
  is the fixture's plus `ape.mopCoinLedgerMaxInteractions: 2`, the ledger budget the cell carries and the jar's
  default (1) does not.
- `mop_nolaunch`, against `cells/mop.run_start.json`, because the jar ships no preset for an ablation variant:
  `features` is the fixture's without `MOP_LAUNCHER`; `params` is the fixture's plus
  `ape.mopCoinLedgerMaxInteractions: 2` and without `ape.activityTriggerEnabled`, because an inactive feature's
  activation key is not echoed and `false` is that key's neutral value; `inert` is `["ape.activityTriggerEnabled"]`.
- `base`, `as`, `as_llm` are compared on every member, `digest` included: `as_llm`'s only override, `llm_url`,
  states the value its fixture already carries (`http://10.0.2.2:30000/v1`).
Offline, the test checks that the ablation variant names the `mop` preset and that the ledger and launcher
overrides map to keys the jar accepts.

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

#### Scenario: A MOP cell echoes its fixture plus the ledger budget
- **WHEN** the smoke runs `aperv:mop` on an instrumented APK with its `.apk.json`, with the paired jar
- **THEN** the trace's `RUN_START.preset` and `RUN_START.variant` SHALL be `"mop"`
- **AND** its `features` SHALL equal the fixture's `FUZZING`, `STATIC_DATA`, `MOP`, `WTG`, `MOP_FRONTIER`,
  `MOP_LAUNCHER`, `MOP_ACTIVITY_SOURCE`, `MOP_COIN`, with no `MENU_GATEWAY`, and its `inert` SHALL equal the
  fixture's
- **AND** its `params` SHALL equal the fixture's plus `ape.mopCoinLedgerMaxInteractions: 2`
- **AND** its `digest` SHALL NOT be compared

#### Scenario: The launcher ablation echoes its cell without the launcher
- **WHEN** the smoke runs `aperv:mop_nolaunch` on an instrumented APK with its `.apk.json`, with the paired jar
- **THEN** the trace's `RUN_START.preset` SHALL be `"mop"` and `RUN_START.variant` SHALL be `"mop_nolaunch"`
- **AND** its `features` SHALL be those of `cells/mop.run_start.json` without `MOP_LAUNCHER`
- **AND** its `params` SHALL equal the fixture's plus `ape.mopCoinLedgerMaxInteractions: 2` and without
  `ape.activityTriggerEnabled`, and its `inert` SHALL be `["ape.activityTriggerEnabled"]`
- **AND** its `RUN_END.counters.launches` and `nullRelaunches` SHALL be `0`

#### Scenario: A mismatched pair fails at resolution
- **WHEN** a jar that predates the group keys is deployed under this `tool.py` and `aperv:base` runs
- **THEN** the jar SHALL abort before step 1 on the unknown preset `base` or the unknown key `ape.variant`
- **AND** the smoke SHALL report the cell as failed, because no `RUN_START` was recorded
