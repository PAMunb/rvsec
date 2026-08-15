# Specification: ApeRV Tool

## Purpose

`aperv-tool` is an rv-platform external tool module that wraps the APE-RV binary (`ape-rv.jar`) for integration into the rv-android experiment framework. APE-RV is an enhanced fork of APE (Ape Explores Apps, ICSE 2019), a model-based Android UI exploration tool that uses adaptive random testing with a Widget Table Graph model. The enhanced version adds AndroidX ViewPager support, systematic OptionsMenu exploration (`MODEL_MENU` action), optional MOP-guided action scoring from static analysis data, optional LLM-guided action selection via an SGLang server, and probabilistic component triggering for Services and BroadcastReceivers.

The tool runs on the Android device using the `app_process` execution model. The JAR is pushed to `/data/local/tmp/ape-rv.jar` via ADB, and execution is launched via `adb shell CLASSPATH=... /system/bin/app_process /system/bin com.android.commands.monkey.Monkey`. This execution model is necessary because APE requires internal Android APIs (`android.app.UiAutomationConnection`, `android.hardware.display.DisplayManagerGlobal`) that are inaccessible from the host via `adb shell monkey`.

The module is an optional uv workspace member, auto-discovered by `members = ["modules/*"]` in the root `pyproject.toml`. If not installed, rv-platform's `_register_external_tools()` catches the `ImportError` and logs a warning, allowing the platform to function normally with other tools.

Coverage metrics (method calls, MOP violations) are collected by the rv-android Python infrastructure via logcat `RVSEC-COV` tags -- the same pipeline used by all other tools. No special output parsing is required.

### APE-RV Java Capabilities

The `ape-rv.jar` binary supports several capabilities that `aperv-tool` configures via `ape.properties`:

1. **MOP-Guided Scoring**: When `ape.mopDataPath` points to the derived compact MOP artifact on the device, APE-RV reads the widget-to-MOP mappings it already carries and applies priority boosts (+500 direct, +300 transitive, +100 activity-level) to actions whose handlers reach monitored operations. This biases exploration toward code paths under runtime verification. The device receives only that artifact and never the full static-analysis JSON (INV-APV-46): the derivation the jar used to perform at load time — per-widget MOP flags, the two MOP-activity sets, the OPTIONSMENU gateway inputs, the click-only WTG view and the component trigger surface — happens host-side, so the call-graph section that dominates the file never crosses to the device and no on-device parse footprint guard can abort a MOP arm at 0 steps while the baseline explores normally.

2. **LLM-Guided Action Selection**: When `ape.llmUrl` points to an SGLang server, APE-RV captures screenshots and consults a vision-language model (Qwen3-VL) at two decision points: (a) first visit to a new state (`llmOnNewState`), and (b) stagnation midpoint (`llmOnStagnation`). A probabilistic mode (`llmPercentage`) routes a configurable fraction of steps through the LLM. A circuit breaker (3 failures, 60s recovery) protects the exploration loop from cascading LLM failures. All LLM failures fall back to SATA transparently.

3. **Component Triggering**: When MOP data includes a `components{}` section with receivers and services, APE-RV probabilistically fires broadcast intents and starts services during exploration. A `system-broadcast.json` catalog provides typed extras for known system broadcast actions.

4. **Prompt Variants**: The `llm_prompt_variant` property selects which prompt template APE-RV uses for LLM calls (e.g., `ape_current`, `ape_reasoning`, `compact_v1`, `v13`, `v17`, `visual_only`), enabling controlled prompt ablation experiments.

### Relationship with Other Domains

- **rv-platform**: Consumes `ApeRVTool` via `ToolFactory.create_tool()` in `ToolExecutionComponent`. Registration via `_register_external_tools()`.
- **rv-experiment**: Orchestrates experiments using `aperv` tool variants. APK instrumentation and static analysis happen in pre-processing; `aperv-tool` receives the instrumented APK already installed on the emulator.
- **rv-static-analysis**: Produces the full static-analysis JSON that MOP variants derive from. It maps activities to widgets with MOP reachability flags and includes component data for triggering, and it remains the host-side source of truth: `aperv-tool` reads it, never writes to it, and projects it into the compact artifact the device receives. It also stays the sole input to offline metrics, which read the full document rather than the projection (`analysis` INV-ANA-53, INV-ANA-54).
- **rv-tools**: Provides `AbstractTool` base class, `ToolSpec`, `ToolRegistry`, and `ToolFactory` infrastructure.
- **builtin ape tool**: Shares `process_pattern` (`com.android.commands.monkey`). The two tools must not run concurrently on the same device.

## Data Contracts

### Input

- `task.config.device_id: str` -- ADB device serial (default `"emulator-5554"`)
- `task.config.timeout: int` -- exploration duration in seconds (default 300)
- `task.result.trace_file: str` -- path where stdout/stderr from APE-RV is written
- `task.results_dir: str` -- directory containing static analysis JSON (for MOP variants)
- `task.config.apk_name: str` -- APK filename used to locate the static analysis JSON
- `app.package_name: str` -- Android package name passed to APE's `-p` flag
- `self._tool_config: Dict[str, Any]` -- resolved variant configuration from `configure()`
- `variant dict: Dict[str, Any]` -- per arm: `preset: str` (one of `aperv`, `mop`, `llm`, `llm_mop`), `overrides: Dict[str, Any]` (deltas over the preset, possibly empty), plus the Python-only orchestration keys `strategy` and `mop_data` (source: `ApeRVTool.get_variants()`, merged with experiment parameters by `ToolFactory`). No arm declares the revision or the digest of an `ape-rv.jar` build (INV-APV-59)
- `tool_config.parameters: Dict[str, Any]` -- tool-DSL overrides (`aperv:<variant>@key=value`), merged **at the top level** over the variant dict by `ToolFactory` (`registry/factory.py:127`) and folded into `overrides` by `configure()` (INV-APV-39)
- `APERV_PROPERTY_MAPPING: Dict[str, str]` -- override key → `ape.*` property name; contains only keys the deployed jar accepts (source: `tool.py` module constant)
- preset vectors and the accepted-key vocabulary -- read from the `ape` source checkout (`runtime/Presets.java`, `runtime/KeyOwnership.java`) by the migration tooling only; not a runtime dependency of `aperv-tool`
- `ape-rv.jar` -- Dalvik JAR resolved at execution time via priority search
- `system-broadcast.json` -- optional broadcast catalog file shipped alongside the tool module
- `<task.results_dir>/<task.config.apk_name>.json` -- static-analysis document produced by `rvsec-analysis-client.jar`. Sections consumed by the handler-reach enrichment: `windows[].widgets[].listeners[].handler` (handler signatures) and `reachability[].methods[]` (`signature`, `reachable`, `reachesTarget`, `directlyReachesTarget`)
- `llm_url: str` -- OpenAI-compatible base URL already held by the tool configuration; the source of the `/v1/models` provenance query (LLM arms)
- `corpus_basis: str` -- optional key identifying the application list a run was drawn from, supplied through the same configuration path as any other mapped key and resting at `self._tool_config["overrides"]["corpus_basis"]`, which is where validation reads it. The nesting is not incidental: `configure()` folds every `APERV_PROPERTY_MAPPING` key from the top level of the configuration into `overrides` before validating anything, so an arm that declares the basis in its own `overrides` dict and a campaign that supplies it as an `@corpus_basis=…` DSL parameter arrive at the same place, and one rule covers both. Format `<corpus-id>:<sha256>`, where `<corpus-id>` is a short human-readable identifier of the list (e.g. `subset40`) and `<sha256>` is the lowercase hexadecimal SHA-256 of the list file's bytes
- Recorded run artifacts for the offline join and the coverage-dump parser: per-run trace files carrying the step clock and the `[APE-RV] UICOV`/`UICOV-ACT` dump lines, and the logcat lines matching `RVSEC:`

### Output

- `task.result.trace_file` -- populated with APE-RV stdout+stderr (binary write mode)
- `ape.properties` on device -- `ape.preset=<name>` first, `ape.mopDataPath=<artifact>` when the derived MOP artifact was pushed, then one `ape.<key>=<value>` line per `overrides` entry (destination: `/data/local/tmp/ape.properties`, consumed by the jar's key resolution)
- Task output provenance fields: `llm_backend`, `llm_model`, `llm_sampling` -- recorded per run (LLM arms)
- Join report (A9): per-run rows correlating step clock positions with `RVSEC:` violation timestamps
- Per-run coverage rows at Activity grain from the offline coverage-dump parser, each carrying an explicit dump status (complete, partial, or absent)
- `ape.corpusBasis=<corpus-id>:<sha256>` -- one line appended to the generated `ape.properties`, pushed to `/data/local/tmp/ape.properties`. Consumed by the jar's resolver, echoed into `RUN_START.corpus_basis`, and read by no runtime component on either side

### Side-Effects

- **[Device]**: `ape-rv.jar` pushed to `/data/local/tmp/ape-rv.jar`
- **[Device]**: `system-broadcast.json` pushed to `/data/local/tmp/system-broadcast.json` (if file exists in module directory)
- **[Device]**: `/data/local/tmp/mop-artifact.json` receives the derived compact MOP artifact -- MOP variants only. One pushed file per MOP-arm run, and never the full static-analysis JSON (INV-APV-46)
- **[Host filesystem]**: one cached `<task.results_dir>/<task.config.apk_name>.mop.json` per (apk, full-JSON digest), written atomically in canonical bytes and regenerated transparently when missing or stale
- **[Filesystem]**: `<task.results_dir>/<task.config.apk_name>.json` is read and never written
- **[Device]**: `ape.properties` pushed to `/data/local/tmp/ape.properties` (when `_tool_config` is non-empty); the pushed file gains one `ape.corpusBasis` line when a corpus basis is configured, and no other device state changes
- **[Trace]**: `RUN_START.corpus_basis` becomes present in every trace of a run configured with a corpus basis
- **[Logcat]**: APE-RV writes `RVSEC-COV` log lines during execution (read by rv-android coverage infrastructure)
- **[Network]**: LLM variants send HTTP requests from the emulator to the SGLang server (via `10.0.2.2` loopback or overridden URL)
- **[Network]**: one `GET /v1/models` per LLM-arm run at preflight time (backend provenance)
- **[Filesystem]**: the offline join utility and the coverage-dump parser read recorded artifacts and write their reports; they never write into `results/` trees they did not create

### Error

- `ConfigurationError` -- raised by `configure()` when `strategy` is absent or outside `["sata", "random"]`, when `preset` is absent or empty, when `overrides` is not a dict, when a top-level key is neither mapped nor a recognised orchestration key (INV-APV-39), when an `overrides` key has no `APERV_PROPERTY_MAPPING` entry, and when `corpus_basis` is present but does not match `^[A-Za-z0-9._-]+:[0-9a-f]{64}$`. All are raised before any device interaction, so a malformed value costs no emulator time and produces no partially-configured run
- Jar-side abort -- an unknown key, a retired key, an invalid type, or a non-neutral value of an inactive feature aborts the run before step 1; visible in the trace, never silent
- `RVToolExecutionError` -- raised when `ape-rv.jar` cannot be found in any search path, when an ADB push fails, when a MOP arm has no full JSON or its derivation fails, or when the exploration returns materially short of its budget (INV-APV-60). Non-MOP arms are unaffected by the MOP cases
- `DerivationError` -- raised by `derive()` when the document is structurally unusable (`complete` absent or false, missing `package`, a section of the wrong type). No partial artifact is produced; the caller re-raises it as `RVToolExecutionError`
- `RVToolTimeoutError` -- raised when execution exceeds `task.config.timeout + 45` seconds (expected normal exit for exploration tools)
- `SystemExit(2)` -- the offline clock-to-violation join utility on usage error (missing or unreadable run directory)
- Provenance query failures are non-fatal: the run proceeds and the provenance fields record the failure rather than a fabricated value (INV-APV-33)

## Invariants

- **INV-APV-01**: `ApeRVTool` SHALL locate `ape-rv.jar` using `JarResolver` with search paths in priority order: (a) `os.path.dirname(__file__)` -- module directory populated by `mvn install`, (b) `$RVSEC_HOME/ape/target/` -- development Maven build, (c) `$TOOLS_DIR/aperv/` -- manual placement. First match wins. If no path resolves, a `RVToolExecutionError` SHALL be raised listing all searched paths.

- **INV-APV-02**: `ApeRVTool.configure()` SHALL validate that the `strategy` key exists in `config` and its value is one of `["sata", "random", "bfs", "dfs"]`. An absent or invalid strategy SHALL raise `ConfigurationError` before any device interaction.

- **INV-APV-03**: `ApeRVTool` SHALL use device path `/data/local/tmp/ape-rv.jar` (not `/data/local/tmp/ape.jar`) to avoid collision with the builtin `ape` tool's device artifact.

- **INV-APV-04**: The `app_process` working directory SHALL be `/system/bin` (not `/data/local/tmp/`). The enhanced APE binary references system-level resources relative to its working directory during startup; using `/data/local/tmp/` causes startup failures. This intentionally diverges from the builtin `ape` tool, which uses `/data/local/tmp/` as working directory.

- **INV-APV-05**: `get_variants()` SHALL return a dict whose keys are exactly `default`,
  `sata`, `sata_mop`, `sata_llm`, `sata_mop_llm`, `mop_on_llm_off`, `mop_off_llm_off` and
  `mop_on_llm_70`, with `default` bound to the same object as `sata` (INV-TOOL-02). The pre-change
  minimum set named `bfs`, `random` and the six `sata_mop_llm_<prompt>` variants, all of which this
  change retires; the invariant is restated rather than exempted, because a minimum-set rule that
  lists retired names is false, not merely outdated.

- **INV-APV-06**: The `sata_mop` variant SHALL set `mop_data` to `"static_analysis"`. When `mop_data == "static_analysis"`, `execute_tool_specific_logic()` SHALL locate the full static-analysis JSON, obtain the derived compact artifact from it (cache-or-generate), and push **only that artifact** to the device. If the JSON is not found, or its derivation fails, the task SHALL fail before the jar is launched (INV-APV-45): there is no graceful-degradation path, because a MOP arm that runs without MOP data is a mislabelled run rather than a degraded one.

- **INV-APV-07**: `ApeRVTool.TOOL_SPEC.process_pattern` SHALL be `"com.android.commands.monkey"`. This is the same value used by the builtin `ape` tool. `AbstractTool.kill_related_processes()` uses this pattern to terminate device-side processes after execution. As a consequence, `ape` and `aperv` MUST NOT run concurrently on the same device -- each cleanup would terminate the other's process. Experiments using `aperv` SHALL NOT include the builtin `ape` tool in the same run.

- **INV-APV-08**: `ape.properties` generation SHALL use `APERV_PROPERTY_MAPPING` to translate Python config keys to Java property names. Only keys present in both `_tool_config` and `APERV_PROPERTY_MAPPING` are written. Python-only keys (`strategy`, `mop_data`) have no mapping entry and are excluded automatically.

- **INV-APV-09**: LLM variants SHALL use `http://10.0.2.2:30000/v1` as the default `llm_url`. The `10.0.2.2` address is the Android emulator's alias for the host loopback interface. The `APERV_LLM_BASE_URL` environment variable SHALL override this value in `configure()` when set, allowing Docker or non-emulator setups to specify a different endpoint.

- **INV-APV-10**: The `system-broadcast.json` catalog file SHALL be pushed to the device when present in the module directory (`os.path.dirname(__file__)`). When absent, APE-RV degrades gracefully (component triggering proceeds without typed extras for system broadcasts).

- **INV-APV-11**: Timeout is ALWAYS controlled by `task.config.timeout` (set by rv-platform). The `running_minutes` passed to APE is derived from `max(1, task.config.timeout // 60)`. Variants MUST NOT hardcode a timeout.

- **INV-APV-12**: Non-zero exit codes from APE-RV SHALL NOT be treated as failures. APE-RV exits with non-zero codes when it detects app crashes during exploration (e.g., exit code 211). Coverage is collected via logcat regardless. Only `RVCommandTimeoutError` is re-raised as `RVToolTimeoutError`.


- **INV-APV-18**: When a `seed` is present in `_tool_config`, `_build_main_command` MUST append `-s <seed>`
  to the `app_process` argument vector (after `--ape <strategy>`). When no seed is configured, the command
  MUST NOT include `-s` (preserving the current non-deterministic default). The seed value is passed
  verbatim as a string. The `mop-fairtest` jar honors this seed (it parses `-s SEED` and seeds both
  `Monkey.mRandom` and APE's `RandomHelper`, INV-EXPL-14); this invariant closes the rv-android-side gap
  that previously dropped the seed.


- **INV-APV-29**: The MOP-off control arm SHALL set `mop_data` to a **present and loadable** document, SHALL set `mop_weight_direct`, `mop_weight_transitive`, `mop_weight_open_menu`, `mop_weight_wtg`, and `mop_frontier_weight` all to `0`, and SHALL set `activity_trigger_enabled=false`. It SHALL NOT achieve MOP-off by omitting `mop_data` or by pointing `ape.mopDataPath` at a missing file — the first disables the generic WTG and frontier passes as collateral, the second aborts the run.

- **INV-APV-30**: Every arm of the decisive run SHALL use the frontier substrate (`sata_mop_act_frontier` lineage). No arm SHALL abandon the frontier mechanism, including the control arm — the control removes MOP guidance, not navigation.

- **INV-APV-33**: Backend provenance SHALL be obtained from a live `/v1/models` query performed at the start of each run, never from static configuration. When the query fails, the provenance fields SHALL record the failure explicitly; the run SHALL NOT be aborted and a value SHALL NOT be inferred from configuration.


- **INV-APV-35**: The clock↔logcat join SHALL be an offline, read-only computation over recorded artifacts. It SHALL NOT read logcat from a running device, SHALL NOT require an emulator, and SHALL NOT modify any artifact it reads.

- **INV-APV-36**: Any coverage figure aggregated across runs, replicas or arms SHALL be derived from `UICOV-ACT` (Activity grain). `UICOV` state keys SHALL NOT be used as a cross-run join key — they embed a JVM identity hash whose measured cross-replica pairing rate is zero (Jaccard 0.000 at mean, median and maximum).

- **INV-APV-37**: The coverage-dump parser SHALL report every run in its input with an explicit dump status — complete, partial, or absent — and SHALL NOT omit a run for lacking a dump. Any coverage rate it produces SHALL carry the denominator it was computed over, so that a figure computed on the runs that dumped is never mistaken for a figure over all runs.

Numbering note: `INV-APV-38` through `INV-APV-44` are deliberately left free for `gh95-thin-python-arms`,
which the sibling `ape` change already references by number.

- **INV-APV-45**: An arm configured with `mop_data == "static_analysis"` SHALL either push a
  freshly-validated derived artifact and write `ape.mopDataPath`, or fail the task before the jar is
  launched. There SHALL be no execution path in which such an arm launches the jar without
  `ape.mopDataPath` set.
- **INV-APV-46**: The device SHALL only ever receive the derived compact artifact. No code path SHALL
  push the full static-analysis JSON, under any cache state or failure mode.
- **INV-APV-47**: Cache freshness SHALL be digest-based: a cached `<apk_name>.mop.json` is reused only
  when its recorded `source.digest` equals the SHA-256 of the current full JSON. Cache state SHALL
  NOT change what the device receives for a given full JSON.
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
- **INV-DRV-06**: The artifact SHALL contain no call-graph data — no `reachability` section, no
  method signatures, no raw `windows`/`transitions`/`listeners` — and no `*Target` key other than
  `hasTargetMethods` on receivers and services. That single exception is deliberate: it is the
  boolean the `targetMethods` signature list compacts to, its name is fixed by the jointly defined
  wire format, and the jar reads it by that name. Stating the rule without the exception made it
  unsatisfiable by the very schema this delta specifies, and left it enforceable only against
  documents that happen to declare no receiver or service — which is why the cryptoapp fixture never
  caught it. The full JSON SHALL remain unmodified on the host.
- **INV-DRV-07**: Each emitted activity SHALL carry `deepLinkUri` derived by the rule the jar applies
  today; the intent-filter structure itself SHALL NOT be on the wire.

- **INV-APV-38**: Every arm whose `preset` is `llm` or `llm_mop` MUST carry `llm_url` in its
  `overrides`. The preset deliberately omits the server URL because it names a machine rather than an
  arm, while still stating the LLM routing gates ON, so an arm that inherits the preset without
  supplying the URL activates routing over an absent mechanism and aborts at resolution. This is a
  fail-fast, not a fallback.
- **INV-APV-39**: `configure()` MUST fold every top-level config key that has an
  `APERV_PROPERTY_MAPPING` entry into `overrides`, and MUST raise `ConfigurationError` for any
  top-level key that is neither mapped nor one of the recognised orchestration keys (`preset`,
  `overrides`, `strategy`, `mop_data`, `seed`, `device_port`, `device_serial`,
  `device_id`). The three device keys are addressing rather than
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
- **INV-APV-42**: The eight surviving variant names are frozen. The variant string is the
  resume-identity key and the consolidation column key; re-expression MUST NOT rename a surviving
  arm, and an owner-approved intentional divergence in effective configuration MUST be introduced as
  a new declared arm name, never as a silent edit. The 21 retired names MUST be recorded in the
  migration arm report as documented retirements — never as regeneration diffs and never as silent
  absences — and each MUST carry its kind: *never distinct*, *name consolidated* (naming the arm the
  configuration survives under), or *finished campaign*. A retirement whose configuration survives
  elsewhere and one whose configuration ends are different facts, and a report that merges them
  misstates what the migration did.
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

- **INV-APV-49**: Default materialization SHALL be total for the fields whose absence means a default, and SHALL NOT be applied to the fields whose absence is itself information. The six boost fields (`mop`, `mopf`, `wtg`, `cov`, `menu`, `form`) SHALL be materialized at `0` when absent, and `out.new_state` / `out.act_changed` at `false`. `dec.patched` and `dec.cf` SHALL be preserved as absent when absent — defaulting `patched` to `0` would make "no resolved target" indistinguishable from "natively clickable node", which is a tri-state the jar emits explicitly for that reason.

- **INV-APV-50**: A malformed record SHALL be skipped and counted in the reader's diagnostics rather than aborting the read. A record referencing an `act`, `st` or `out.target` ID that no earlier dictionary record defined is malformed by this rule; the reader SHALL NOT invent a placeholder string for it.

- **INV-APV-51**: The reader SHALL NOT fabricate an absolute clock. When `RUN_START` is absent from the trace — a truncated capture, or a pre-stage-4 file — the run-relative `t` SHALL still be reported and the epoch expansion SHALL be reported as unavailable. A base SHALL NOT be inferred from file mtime, from the logcat, or from any other source.

- **INV-APV-52**: The gzip step SHALL be non-fatal and write-only. Its failure SHALL log a WARNING and leave the uncompressed trace in place, and the task SHALL complete with the status it would otherwise have had. `task.result.trace_file` SHALL be byte-identical before and after collection completes: no step of the flow rewrites, reformats, truncates or converts it.

- **INV-APV-53**: No code path in this module SHALL read, validate or act on the `RUN_END` record. There SHALL be no sentinel check, no exit-code interpretation beyond the existing debug log, no task-status change and no retry logic keyed on it (owner decision D5 on the jar side). Truncated-run identification remains post-hoc analysis over trace and logcat timestamps.

- **INV-APV-54**: `_align_clocks()` and the UTC-offset reconstruction SHALL NOT be deleted before a captured run is shown to contain heartbeat lines in the task's `.logcat`. This is the counterpart of `event-sink` INV-SNK-14 on the jar side: the heartbeat is filtered at the device under any tag outside the capture allowlist, so a deletion that precedes the observation trades a working mechanism for an inert one and does so silently.

- **INV-APV-55**: The frozen legacy-corpus readers SHALL NOT be migrated, adapted or deleted by this change: `scripts/cmpm_stratify.py`, `scripts/analyze_cmpv2_llm.py`, `experimento-cal/scripts/*`, `experimento-20260721/scripts/*` and `calibracao/*`. They read an archived dataset that will not be regenerated, and are not compatibility shims.

- **INV-APV-56**: When `corpus_basis` is absent from the tool configuration, `_push_properties()` SHALL omit `ape.corpusBasis` from the generated `ape.properties` entirely. It SHALL NOT emit the key with an empty, placeholder or defaulted value — the jar's contract is that the key is absent when the corpus is unstated, and a defaulted value would assert a provenance the harness does not have.

- **INV-APV-57**: No component of `modules/aperv-tool` SHALL read `RUN_START` — including `corpus_basis` — on any execution path. The property is write-only from this side, mirroring `run-spec` INV-RUN-03. Any verification of the echoed value SHALL be post-hoc analysis over a recorded trace, outside `tool.py`.

- **INV-APV-58**: The reader SHALL NOT drop data the trace carries. Every field of an `llm[]` sub-event SHALL reach the caller, prompt and response dumps included, and every run-level record SHALL be reachable — `MOP_DATA`, `PIPELINE` and `LLM_ACK` as reader attributes. `RUN_END` is the sole exception and is governed by INV-APV-53. Because this module is the *sole* mechanism for consuming a stage-4 trace, a field it declines to surface is a field no conformant analysis can read: the omission is not a defer, it is a deletion at the boundary.

- **INV-APV-60**: `ApeRVTool` SHALL NOT report a run as successful on the strength of the exploration process having returned. A return that arrives materially before the requested exploration budget SHALL raise `RVToolExecutionError` naming the elapsed time and the budget. The exit code SHALL NOT be used to decide this: a non-zero exit is normal for APE-RV — it exits non-zero when it detects an application crash during exploration — so a dead emulator and a crashing application are indistinguishable by it, and the elapsed time is the one signal that separates them.

- **INV-APV-61**: `RunStart` SHALL carry every top-level member of the `RUN_START` record the jar emits, with `build` as a nested `(sha, time)` value; a member absent on the wire SHALL be reported absent, never defaulted. No consumer in `aperv_tool` SHALL parse `RUN_START` other than through `TraceReader`.
- **INV-APV-62**: `TraceReader` SHALL check `RUN_START.v` against the format version it was written for; a mismatch SHALL be surfaced in `TraceDiagnostics` and SHALL raise `SchemaVersionMismatch` when the reader is opened in strict mode. A trace with no `RUN_START` reports the version as unknown (INV-APV-51 applies).
- **INV-APV-63**: The heartbeat placement rule SHALL exist once, in `clock_logcat_join.place_on_timeline(stamp, heartbeats)`, and SHALL be tag-agnostic; the tag admitted is a parameter of the line reader, not of the placement.

## Requirements
### Requirement: ApeRVTool Registration (FR18, FR19)

`ApeRVTool` SHALL be registered as an external tool via rv-platform's `_register_external_tools()` function in `rv_platform/__init__.py`. Registration SHALL be idempotent: the function MUST check `registry.is_tool_registered("aperv")` before calling `registry.register_tool_class(ApeRVTool)`. If `aperv-tool` is not installed, the resulting `ImportError` SHALL be caught and logged as a warning; the platform SHALL continue operating normally. An unexpected exception during registration SHALL be logged as an error and SHALL NOT propagate.

#### Scenario: ApeRVTool registers on rv-platform import
- **WHEN** `import rv_platform` is executed and `aperv-tool` is installed
- **THEN** `ToolRegistry.get_instance().is_tool_registered("aperv")` SHALL return True
- **AND** `ToolRegistry.get_instance().get_tool_spec("aperv").name` SHALL be `"aperv"`

#### Scenario: Missing aperv-tool does not break rv-platform
- **WHEN** `import rv_platform` is executed and `aperv-tool` is NOT installed
- **THEN** rv-platform SHALL import successfully
- **AND** a warning log line SHALL be written containing `"aperv tool not available"`
- **AND** `ToolRegistry.get_instance().is_tool_registered("aperv")` SHALL return False

#### Scenario: Re-importing rv-platform does not double-register
- **WHEN** `import rv_platform` is executed twice
- **THEN** `ToolRegistry.get_instance()` SHALL contain exactly one registration for `"aperv"`

---

### Requirement: ApeRVTool Variants (FR20)

`ApeRVTool` SHALL define named variants as `preset + overrides`. Every variant SHALL consist of a
`preset` name, an `overrides` dict, and Python-only orchestration keys (INV-APV-40).

`get_variants()` SHALL return exactly these **eight** frozen names, carrying **seven** distinct
configurations:

| Variant | preset | mop_data | overrides |
|---|---|---|---|
| `default` | `aperv` | — | _(empty)_ — bound to the same object as `sata` (INV-TOOL-02) |
| `sata` | `aperv` | — | _(empty)_ |
| `sata_mop` | `mop` | `"static_analysis"` | _(empty)_ |
| `sata_llm` | `llm` | — | `llm_url` |
| `sata_mop_llm` | `llm_mop` | `"static_analysis"` | `llm_url` |
| `mop_on_llm_off` | `mop` | `"static_analysis"` | the four reach-package keys |
| `mop_off_llm_off` | `mop` | `"static_analysis"` | the MOP-off set (see "Decisive Run Arm Set") |
| `mop_on_llm_70` | `llm_mop` | `"static_analysis"` | the reach package plus the LLM dose |

Four of the seven configurations are one-to-one with the jar's presets and carry nothing but the
deployment-specific server URL where an LLM is involved. The remaining three are the E3 decisive
run's arms: a reference on the reach package, its MOP-off control, and its LLM arm.

**Arm shape.** An arm's `preset` names one of the four jar-resident vectors; the jar, not Python,
defines what it contains. `overrides` carries only the deltas that distinguish this arm from its
preset — an arm identical to its preset carries an empty dict. Python-only keys stay at the top level
and are never written to `ape.properties`: `strategy` (the `--ape` CLI flag), `mop_data`
(`"static_analysis"` triggers the derived-artifact push, unchanged), `seed`, and the two B3
jar-provenance declarations. The explicit `overrides` sub-dict rather than a flat dict is what keeps
the boundary machine-checkable: everything under `overrides` is translated and written, everything at
the top level is orchestration.

Every LLM-preset arm SHALL carry `llm_url` in its overrides (INV-APV-38) — the preset omits the
deployment-specific server URL while stating the routing gates ON, so its absence aborts resolution.
`throttle_ms` SHALL NOT appear in any arm: the `aperv` preset already states
`ape.defaultGUIThrottle=200`, which every arm used. Ablations SHALL be expressed as named override
sets, never as new presets: the preset vocabulary belongs to the jar.

`sata_mop` is the frozen-corpus name and SHALL NOT be renamed or folded away: 4,096
`aperv:sata_mop.trace` artifacts and 1,066 files under `results/` carry that exact token, so a rename
would orphan every one of those runs from resume and every one of those rows from consolidation. This
is a data-identity constraint, not backward compatibility (INV-APV-42).

#### Retired variants

Twenty-one names are retired. Retiring a name is a decision about the experimental matrix — Python's
authority — and touches no jar mechanism: every key those arms set remains in the mapping, and every
feature they activated remains implemented.

| Retired | Kind | Disposition |
|---|---|---|
| `ape_pure` | never distinct | purity is structural in the jar; `ape.apePureMode` is a retired key that aborts resolution. The comparison with original APE stays anchored on the frozen phase-2 data |
| `bfs` | never distinct | never an agent type; always carried `sata`'s effective configuration |
| `sata_mop_widget` | never distinct | one object under two names; `sata_mop` is the surviving name |
| `sata_mop_act_frontier` | name consolidated | byte-identical to `mop_on_llm_off`; the configuration survives under that name |
| `sata_mop_activity` | finished campaign | an intermediate step of the reach decomposition, superseded by the reach package |
| `random` | finished campaign | the `random` strategy stays in the `configure()` whitelist and remains reachable as `aperv:sata@strategy=random`; what ends is the named arm |
| the six `sata_mop_llm_<prompt>` arms | finished campaign | the gh43 prompt ablation concluded; recorded results are unaffected |
| the nine `cal_a1`…`cal_a9` arms | finished campaign | the Phase-A calibration campaign concluded (VERIFY `ADMISSIBLE`, 2026-07-24) and phases B and C were superseded by the decisive run's pre-registration freeze |

Retirement removes the ability to launch new runs under a name. It does not invalidate recorded
results: those are frozen artifacts, read by frozen-corpus analysis scripts that this change does not
touch.

Every surviving arm's effective configuration after re-expression SHALL be identical to its
pre-change effective configuration (INV-APV-44); any intentional divergence requires owner approval
and a new arm name (INV-APV-42).

#### Scenario: Preset-identity arm carries nothing

- **WHEN** `get_variants()["sata_mop"]` is read
- **THEN** `preset` SHALL be `"mop"` and `overrides` SHALL be empty
- **AND** `mop_data` SHALL be `"static_analysis"` at the top level
- **AND** the same emptiness SHALL hold for `sata` and `default` against the `aperv` preset

#### Scenario: LLM arm carries the server URL and nothing else

- **WHEN** `get_variants()["sata_mop_llm"]` is read
- **THEN** `preset` SHALL be `"llm_mop"` and `overrides` SHALL be exactly
  `{"llm_url": "http://10.0.2.2:30000/v1"}`
- **AND** every variant whose preset is `llm` or `llm_mop` SHALL likewise carry `llm_url`
  (INV-APV-38)

#### Scenario: The reach package survives under the reference arm

- **WHEN** `get_variants()["mop_on_llm_off"]` is read
- **THEN** `preset` SHALL be `"mop"` and `overrides` SHALL contain exactly
  `mop_activity_source_components=True`, `frontier_boost_weight=200`, `mop_frontier_weight=200`,
  `activity_trigger_enabled=True`
- **AND** no MOP weight key SHALL appear, because the `mop` preset already states
  `ape.mopWeightDirect=500`, `ape.mopWeightTransitive=300`, `ape.mopWeightOpenMenu=250` and
  `ape.mopWeightWtg=200`
- **AND** its effective configuration SHALL equal the baseline entry captured for the retired
  `sata_mop_act_frontier`

#### Scenario: The frozen corpus name keeps resolving

- **WHEN** `get_variants()` is read
- **THEN** `"sata_mop"` SHALL be present
- **AND** a resume over an existing `aperv:sata_mop` result directory SHALL still match its arm
- **AND** `"sata_mop_widget"` SHALL NOT be a key, so there is no alias left to keep in lockstep

#### Scenario: Retired variants are absent

- **WHEN** `get_variants()` is read after this change
- **THEN** the mapping SHALL have exactly eight keys
- **AND** none of `ape_pure`, `bfs`, `random`, `sata_mop_widget`, `sata_mop_activity`,
  `sata_mop_act_frontier`, the six `sata_mop_llm_<prompt>` names or `cal_a1`…`cal_a9` SHALL be among
  them
- **AND** the module SHALL contain no `_APE_PURE_ARM_FLAGS` constant
- **AND** all 21 SHALL appear in the migration arm report as documented retirements carrying their
  kind, not as diffs

#### Scenario: No arm carries a property expansion

- **WHEN** any variant returned by `get_variants()` is inspected
- **THEN** its top-level keys SHALL be drawn only from `preset`, `overrides`, `strategy`, `mop_data`
  and `seed`
- **AND** no variant SHALL carry `expected_jar_git_sha` or `expected_jar_sha256` (INV-APV-59)
- **AND** the module SHALL contain none of `_BASELINE_ARM_FLAGS`, `_MOP_SUBSTRATE`, `_LLM_FLAGS`,
  `_FRONTIER_SUBSTRATE`, `_MOP_OFF_OVERRIDES` or `_CAL_LLM_COMMON`
- **AND** no variant SHALL contain a `throttle_ms` key

---

### Requirement: ApeRVTool Configuration (FR19)

`ApeRVTool.configure(config)` SHALL store the resolved variant configuration in `self._tool_config`
after validation. It SHALL validate that `config["strategy"]` is one of `["sata", "random"]`, that
`config["preset"]` is present and non-empty, and that `config.get("overrides", {})` is a dict. If any
check fails, it SHALL raise `ConfigurationError` before any device interaction.

**Tool-DSL overrides SHALL be folded into `overrides`** (INV-APV-39). `ToolFactory` merges
`{**variant_config, **tool_config.parameters}` (`modules/rv-tools/src/rv_tools/registry/factory.py:127`),
so a DSL override written as `aperv:sata_mop@frontier_boost_weight=200` arrives as a **top-level** key,
while `_push_properties()` reads only `overrides`. `configure()` SHALL therefore move every top-level
key that has an `APERV_PROPERTY_MAPPING` entry into `overrides`, where a DSL value takes precedence
over an arm's own entry for the same key — the DSL is the operator's last word, which is what makes it
useful for smokes and ablations without declaring a variant.

Any remaining top-level key that is neither mapped nor one of `preset`, `overrides`, `strategy`,
`mop_data`, `seed`, `device_port`, `device_serial`,
`device_id` SHALL raise `ConfigurationError` naming it. `expected_jar_git_sha` and
`expected_jar_sha256` are not on that list and SHALL therefore be rejected like any other
unhonourable key, which is what stops the retired declaration from being reintroduced through
experiment YAML (INV-APV-59). Without both halves of this rule a DSL
override would be discarded in silence: no property line, no error, and a run executing a
configuration nobody asked for — the exact failure mode this change exists to remove, reintroduced
on the operator's path. A key that cannot be honoured fails loudly.

The three device keys are the platform's own injection, not an operator's: `ExecutionController`
adds `device_port`, `device_serial` and `device_id` to every tool's parameters whenever
`--device-port` is set, so every containerized and parallel run carries them. They address a device
rather than configure the jar — `execute_tool_specific_logic()` takes the serial from
`task.config.device_id` — so `configure()` SHALL accept and ignore them, and they SHALL never reach
`ape.properties`.

**Unmappable `overrides` keys SHALL be rejected in `configure()`**, not at push time. `_push_properties()`
runs after the jar, the broadcast catalog and the derived MOP artifact have been pushed, so a check
living there would already have cost three pushes and a derivation. Validating in `configure()` puts
one rule over both sources of an override key — an arm's own dict and the DSL keys just folded into
it — and is what makes "before any `adb push`" true as written.

The whitelist SHALL shrink from the pre-change `["sata", "random", "bfs", "dfs"]` — the deletion stage
2 delegated to this change. `bfs` and `dfs` are not agent types: `ApeAgent.createAgent` recognises
`sata`, `random` and `replay` and nothing else, so before stage 2 they ran `SataAgent` silently and
after it they abort on the device. Accepting them Python-side would let a run pass local validation
only to fail on the emulator, which is precisely the silent-degradation class the re-architecture
exists to remove. `replay` is legal in the jar but SHALL NOT be accepted here: it requires
`--ape-replay <log>`, which this tool never passes.

When the `APERV_LLM_BASE_URL` environment variable is set and `llm_url` is present in the config, the
environment variable value SHALL override the config value. This allows operators to redirect LLM
traffic without modifying variant definitions.

#### Scenario: Valid preset arm configured
- **WHEN** `configure({"strategy": "sata", "preset": "mop", "overrides": {}})` is called
- **THEN** `self._tool_config["preset"]` SHALL equal `"mop"`
- **AND** no exception SHALL be raised

#### Scenario: Missing preset raises ConfigurationError
- **WHEN** `configure({"strategy": "sata"})` is called
- **THEN** `ConfigurationError` SHALL be raised naming the missing `preset` key

#### Scenario: Invalid strategy raises ConfigurationError
- **WHEN** `configure({"strategy": "unknown", "preset": "aperv"})` is called
- **THEN** `ConfigurationError` SHALL be raised with a message listing valid strategies

#### Scenario: Retired strategy rejected before the device
- **WHEN** `configure({"strategy": "bfs", "preset": "aperv"})` or
  `configure({"strategy": "dfs", "preset": "aperv"})` is called
- **THEN** `ConfigurationError` SHALL be raised before any device interaction
- **AND** the run SHALL NOT reach the jar, where an unknown `--ape` value aborts

#### Scenario: Non-dict overrides rejected
- **WHEN** `configure({"strategy": "sata", "preset": "mop", "overrides": ["frontier_boost_weight"]})`
  is called
- **THEN** `ConfigurationError` SHALL be raised naming the `overrides` key

#### Scenario: DSL override reaches the properties file
- **WHEN** `aperv:sata_mop@frontier_boost_weight=200` is resolved and `configure()` runs
- **THEN** `self._tool_config["overrides"]["frontier_boost_weight"]` SHALL equal `200`
- **AND** `_push_properties()` SHALL write `ape.frontierBoostWeight=200`
- **AND** no top-level `frontier_boost_weight` key SHALL remain in `_tool_config`

#### Scenario: DSL override wins over the arm's own value
- **WHEN** `aperv:mop_on_llm_off@mop_frontier_weight=400` is resolved, and the arm's `overrides`
  already carries `mop_frontier_weight=200`
- **THEN** the folded value SHALL be `400`
- **AND** exactly one `ape.mopFrontierWeight` line SHALL be written

#### Scenario: The platform's device addressing is accepted and never written

- **WHEN** a containerized run resolves `aperv:sata_mop` with `--device-port 5554`, so
  `ExecutionController` has injected `device_port=5554`, `device_serial="emulator-5554"` and
  `device_id="emulator-5554"` at the top level
- **THEN** `configure()` SHALL accept the configuration without raising
- **AND** the generated `ape.properties` SHALL contain no line naming any of the three keys and no
  occurrence of the port value
- **AND** the arm SHALL still resolve as `ape.preset=mop` plus `ape.mopDataPath`

#### Scenario: Unhonourable top-level key fails loudly
- **WHEN** `aperv:sata_mop@frontier_bost_weight=200` is resolved (a typo absent from
  `APERV_PROPERTY_MAPPING`)
- **THEN** `ConfigurationError` SHALL be raised naming the key
- **AND** the key SHALL NOT be silently dropped, which would run the arm unchanged under an operator's
  belief that it had been overridden

#### Scenario: LLM URL override via environment variable
- **WHEN** `configure({"strategy": "sata", "preset": "llm", "overrides": {"llm_url": "http://10.0.2.2:30000/v1"}})` is called
- **AND** the `APERV_LLM_BASE_URL` environment variable is set to `"http://192.168.1.100:30000/v1"`
- **THEN** the effective `llm_url` SHALL be `"http://192.168.1.100:30000/v1"`

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

3. **Push broadcast catalog**: If `system-broadcast.json` exists in the module directory (`os.path.dirname(__file__)`), push it to `/data/local/tmp/system-broadcast.json`. This catalog provides typed extras for system broadcast intents used by APE-RV's component triggering. If the file is absent, skip (APE-RV degrades gracefully).

4. **Derive and push the MOP artifact** (MOP variants only): When `_tool_config.get("mop_data") == "static_analysis"`, locate `<task.results_dir>/<apk_name>.json`, derive `<task.results_dir>/<apk_name>.mop.json` from it, and push **only that artifact** to `/data/local/tmp/mop-artifact.json`. The source document is never modified and never pushed. A MOP arm with no static-analysis JSON, or whose derivation fails, raises `RVToolExecutionError`.

5. **Push ape.properties**: Generate `ape.properties` as `ape.preset=<preset>` first, then `ape.mopDataPath=<artifact device path>` when the MOP artifact was pushed, then one `ape.<key>=<value>` line per entry of `overrides`, translated through `APERV_PROPERTY_MAPPING`. Push to `/data/local/tmp/ape.properties`. The full property expansion of the pre-change mapping loop SHALL NOT be performed.

6. **Capture LLM backend provenance** (LLM arms only): query `GET {llm_url}/v1/models` once and record the result in the task output -- see "Per-Run LLM Backend Provenance". A failed query is encoded, never inferred from configuration, and never aborts the run (INV-APV-33).

7. **Build and execute command**: Build the `app_process` command via `_build_main_command()` and execute it, capturing stdout+stderr to `task.result.trace_file` in binary write mode. From stage 4 onward the captured stream is the NDJSON trace. **Command timeout is `timeout_seconds + 45` seconds** — widened from `+ 15`; see the grace-window rationale below.

8. **Handle timeout**: If `RVCommandTimeoutError` is raised, log it as the expected exit path for an exploration tool, run the collection step 10 below on the trace captured up to the kill, and only then re-raise as `RVToolTimeoutError`. Collection MUST NOT be skipped on the timeout path — timeout is how a normal exploration run ends, so skipping it there would exempt the majority of runs from collection. The `RVToolTimeoutError` contract SHALL be stated as `task.config.timeout + 45` seconds wherever it is documented.

9. **Check empty trace**: Call `_check_empty_trace()` and log a warning if the trace file is empty. This step is unchanged — a 0-byte NDJSON trace is still 0 bytes.

10. **Gzip at collection**: Compress the raw capture to `<trace>.ndjson.gz` next to the trace file. On failure, log a WARNING and continue.

Step 10 SHALL NOT inspect, validate or act on the trace's content: no `RUN_START` or `RUN_END` presence check, no exit-code interpretation beyond the existing debug log, no task-status change (INV-APV-53). `task.result.trace_file` SHALL remain the raw capture, byte-for-byte, after collection completes — no step of this flow rewrites, reformats or truncates it, and no NDJSON→legacy conversion step exists anywhere in the tool (INV-APV-52).

The tool SHALL NOT read back, parse or validate any jar output, `RUN_START` included (INV-APV-43, owner decision D1). The effective plan the jar resolved is echoed write-only into the trace; reconstructing which arm ran a task is post-hoc analysis, not a runtime check.

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

#### Scenario: Properties file carries preset plus deltas only
- **WHEN** step 5 runs for `mop_on_llm_off` with the MOP artifact pushed
- **THEN** the generated file SHALL begin with `ape.preset=mop`
- **AND** SHALL contain `ape.mopDataPath=/data/local/tmp/mop-artifact.json`
- **AND** SHALL contain exactly the four override lines `ape.mopActivitySourceComponents=true`,
  `ape.frontierBoostWeight=200`, `ape.mopFrontierWeight=200`, `ape.activityTriggerEnabled=true`
- **AND** SHALL contain no other `ape.*` line

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
  resolved plan
- **THEN** the tool SHALL NOT have parsed, validated or branched on it (INV-APV-43)

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

### Requirement: ape.properties Generation

`ApeRVTool._push_properties()` SHALL generate an `ape.properties` file and push it to
`/data/local/tmp/ape.properties` on the device. The file SHALL be composed in a fixed order so that
two runs of the same arm produce byte-identical output:

```text
ape.preset=<preset>                                   # always first
ape.mopDataPath=/data/local/tmp/mop-artifact.json     # only when the artifact was pushed
ape.<mapped-override-key>=<value>                     # one line per overrides entry, mapping order
```

Only the entries of `_tool_config["overrides"]` are translated and written. Python-only keys
(`preset` itself apart from the first line, `strategy`, `mop_data`, `seed`, and the three
device-addressing keys) have no mapping entry and never reach
the file. Python bools SHALL be serialized lowercase (`True` → `true`). An `overrides` key with no
`APERV_PROPERTY_MAPPING` entry SHALL raise `ConfigurationError` **in `configure()`**, which is what
makes the rejection precede every `adb push` of the run rather than only the properties push: under
fail-fast a misspelled key would abort on the device anyway, and catching it on the host saves the
emulator time (same rationale as INV-APV-02).

`APERV_PROPERTY_MAPPING` is a pass-through translation table and nothing more (see "Arm Property
Overrides Pass-Through"). It SHALL contain only keys the deployed jar accepts (INV-APV-41). The 50
entries are:

| Python Key | Java Property | Notes |
|------------|--------------|-------|
| `throttle_ms` | `ape.defaultGUIThrottle` | in every preset; an override only when an arm deviates |
| `default_epsilon` | `ape.defaultEpsilon` | exploration |
| `graph_stable_restart_threshold` | `ape.graphStableRestartThreshold` | exploration |
| `state_stable_restart_threshold` | `ape.stateStableRestartThreshold` | exploration |
| `fuzzing_rate` | `ape.fuzzingRate` | `FUZZING` sub-parameter |
| `do_fuzzing` | `ape.doFuzzing` | `FUZZING` activation |
| `throttle_for_activity_transition` | `ape.throttleForActivityTransition` | exploration |
| `max_extra_priority_aliased_actions` | `ape.maxExtraPriorityAliasedActions` | exploration |
| `max_states_per_activity` | `ape.maxStatesPerActivity` | exploration |
| `trivial_activity_rank_threshold` | `ape.trivialActivityRankThreshold` | exploration |
| `do_back_to_trivial_activity` | `ape.doBackToTrivialActivity` | exploration |
| `back_menu_pick_cap` | `ape.backMenuPickCap` | exploration |
| `max_idle_timeout_ms` | `ape.maxIdleTimeoutMs` | arm-neutral tuning knob |
| `foreign_activity_guard` | `ape.foreignActivityGuard` | `FOREIGN_ACTIVITY_GUARD` |
| `tree_package_guard` | `ape.treePackageGuard` | `TREE_PACKAGE_GUARD` |
| `dynamic_epsilon` | `ape.dynamicEpsilon` | `DYNAMIC_EPSILON` |
| `heuristic_input` | `ape.heuristicInput` | `HEURISTIC_INPUT` |
| `fuzz_input_typed` | `ape.fuzzInputTyped` | `TYPED_FUZZ` |
| `form_completion_enabled` | `ape.formCompletionEnabled` | `FORM_COMPLETION` |
| `step_telemetry_enabled` | `ape.stepTelemetryEnabled` | `STEP_TELEMETRY` |
| `model_menu_enabled` | `ape.modelMenuEnabled` | `MODEL_MENU` |
| `least_visited_priority_tiebreak` | `ape.leastVisitedPriorityTiebreak` | `LEAST_VISITED_TIEBREAK` |
| `tree_enhancements_enabled` | `ape.treeEnhancementsEnabled` | `TREE_ENHANCEMENTS` |
| `activity_budget_enabled` | `ape.activityBudgetEnabled` | `ACTIVITY_BUDGET` |
| `mop_weight_direct` | `ape.mopWeightDirect` | `MOP` sub-parameter |
| `mop_weight_transitive` | `ape.mopWeightTransitive` | `MOP` sub-parameter |
| `mop_weight_open_menu` | `ape.mopWeightOpenMenu` | `MENU_GATEWAY` activation |
| `mop_weight_wtg` | `ape.mopWeightWtg` | `WTG` activation |
| `mop_activity_source_components` | `ape.mopActivitySourceComponents` | `MOP_ACTIVITY_SOURCE` |
| `mop_frontier_weight` | `ape.mopFrontierWeight` | `MOP_FRONTIER` activation |
| `frontier_boost_weight` | `ape.frontierBoostWeight` | `FRONTIER` activation |
| `activity_trigger_enabled` | `ape.activityTriggerEnabled` | `ACTIVITY_TRIGGER` activation |
| `activity_trigger_stagnation_step` | `ape.activityTriggerStagnationStep` | `ACTIVITY_TRIGGER` sub-parameter |
| `activity_trigger_max_per_run` | `ape.activityTriggerMaxPerRun` | `ACTIVITY_TRIGGER` sub-parameter |
| `component_percentage` | `ape.componentPercentage` | `COMPONENT_TRIGGER` activation |
| `mop_target_pick_cap` | `ape.mopTargetPickCap` | `MOP` sub-parameter |
| `coverage_boost_weight` | `ape.coverageBoostWeight` | `COVERAGE_BOOST` activation |
| `llm_url` | `ape.llmUrl` | `LLM` activation; required on every LLM-preset arm (INV-APV-38) |
| `llm_on_new_state` | `ape.llmOnNewState` | `LLM_NEW_STATE` activation |
| `llm_on_stagnation` | `ape.llmOnStagnation` | `LLM_STAGNATION` activation |
| `llm_model` | `ape.llmModel` | `LLM` sub-parameter |
| `llm_temperature` | `ape.llmTemperature` | `LLM` sub-parameter |
| `llm_top_p` | `ape.llmTopP` | `LLM` sub-parameter |
| `llm_top_k` | `ape.llmTopK` | `LLM` sub-parameter |
| `llm_timeout_ms` | `ape.llmTimeoutMs` | `LLM` sub-parameter |
| `llm_percentage` | `ape.llmPercentage` | `LLM_RANDOM` activation |
| `llm_percentage_no_substrate` | `ape.llmPercentageNoSubstrate` | `LLM_RANDOM` sub-parameter; the `-1` sentinel is accepted on a plan with no LLM |
| `llm_prompt_variant` | `ape.llmPromptVariant` | `LLM` sub-parameter |
| `llm_max_tokens` | `ape.llmMaxTokens` | `LLM` sub-parameter |
| `llm_snap_tolerance_px` | `ape.llmSnapTolerancePx` | `LLM` sub-parameter; set by `mop_on_llm_70` alone |

`mop_weight_activity → ape.mopWeightActivity` is deleted: the jar's `KeyOwnership` table lists
`ape.mopWeightActivity` as retired ("dead since mop-fairtest: the weight it named was deleted from
the scorer"), so a properties file carrying it now aborts the run rather than being ignored. No arm
set it.

A key the jar does not recognise is no longer inert. Under stage-2 resolution an unknown key, a
retired key, or a non-neutral value of an inactive feature aborts before step 1 — which is what makes
the mapping's contents a correctness property rather than a tidiness one.

#### Scenario: Preset line comes first
- **WHEN** `_push_properties()` is called for `sata_mop_llm` with the MOP artifact pushed
- **THEN** the first line SHALL be `ape.preset=llm_mop`
- **AND** the second SHALL be `ape.mopDataPath=/data/local/tmp/mop-artifact.json`
- **AND** the only remaining line SHALL be `ape.llmUrl=http://10.0.2.2:30000/v1`

#### Scenario: Empty-override arm writes two lines
- **WHEN** `_push_properties()` is called for `sata_mop` with the MOP artifact pushed
- **THEN** the file SHALL contain exactly `ape.preset=mop` and the `ape.mopDataPath` line
- **AND** no `ape.mopWeight*` line SHALL appear, because those values come from the preset

#### Scenario: Baseline arm writes one line
- **WHEN** `_push_properties()` is called for the `sata` variant
- **THEN** the file SHALL contain exactly `ape.preset=aperv`
- **AND** it SHALL NOT contain `ape.mopDataPath`, `ape.frontierBoostWeight` or `ape.dynamicEpsilon`

#### Scenario: Bools are serialized lowercase
- **WHEN** `_push_properties()` is called for `mop_on_llm_off`
- **THEN** the file SHALL contain `ape.activityTriggerEnabled=true`, not `True`
- **AND** it SHALL contain `ape.mopActivitySourceComponents=true`

#### Scenario: Unmapped override key aborts before push
- **WHEN** an arm's `overrides` contains `frontier_bost_weight` (a typo absent from
  `APERV_PROPERTY_MAPPING`)
- **THEN** `ConfigurationError` SHALL be raised naming the key
- **AND** no `adb push` SHALL have been issued

#### Scenario: Retired jar key is not in the mapping
- **WHEN** `APERV_PROPERTY_MAPPING` is inspected after this change
- **THEN** it SHALL NOT contain `mop_weight_activity`
- **AND** it SHALL contain exactly 50 entries
- **AND** it SHALL still contain `llm_max_tokens` and `llm_snap_tolerance_px`, which are live
  `Feature.LLM` sub-parameters

#### Scenario: Python-only keys are still excluded
- **WHEN** `_push_properties()` is called for `mop_on_llm_70`, whose `_tool_config` carries
  `strategy`, `mop_data` and `seed`
- **THEN** the properties file SHALL contain none of those three names
- **AND** it SHALL contain `ape.llmSnapTolerancePx=150`, which is an ordinary override

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

`aperv-tool/pyproject.toml` SHALL declare the package as a uv workspace member compatible with rv-android's `members = ["modules/*"]` discovery. It SHALL declare dependencies on `rv-android-core` and `rv-tools` as workspace sources.

The `[project.entry-points."rv_tools.plugins"]` table SHALL NOT be used for `aperv-tool` -- registration is done explicitly in `rv-platform/__init__.py`, not via entry-point auto-discovery.

#### Scenario: Module added to workspace
- **WHEN** `aperv-tool/` exists under `modules/` in the rv-android root
- **THEN** `uv sync` SHALL include `aperv-tool` in the workspace without any change to the root `pyproject.toml`

---


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

### Requirement: Decisive Run Arm Set (FR20)

`aperv-tool` SHALL define the three arms of the E3 decisive run as named variants, so that each arm's
identity comes from its preset and override dict and never from an undeclared inheritance. The three
arms SHALL be:

1. **`mop_on_llm_off`** — reference: MOP guidance on, LLM off. The shared baseline of both contrasts.
2. **`mop_off_llm_off`** — control: MOP guidance off, LLM off. Isolates the effect of MOP guidance
   (the study's central hypothesis).
3. **`mop_on_llm_70`** — LLM arm: MOP guidance on, LLM on at `llm_percentage=0.7`. Isolates the effect
   of adding the LLM.

The variant names are normative, not cosmetic: the variant string is the resume identity key and the
consolidation column key, so a rename silently splits a campaign's results.

`mop_on_llm_off` absorbs the retired `sata_mop_act_frontier`: the two carried byte-identical effective
configurations — the ANC2 anchor under two names — so the reference arm is not a newly invented
baseline but the configuration that won the cmpma multi-arm comparison, under the name the decisive
run recorded. With `sata_mop_act_frontier` retired, these three are the only arms in the module that
carry a non-trivial override set; the other four are one-to-one with the jar's presets.

All three SHALL carry `mop_data="static_analysis"` and the frontier substrate (INV-APV-30) — the
control removes MOP guidance, not navigation. Expressed as preset + overrides:

| Arm | preset | overrides |
|---|---|---|
| `mop_on_llm_off` | `mop` | `mop_activity_source_components=True`, `frontier_boost_weight=200`, `mop_frontier_weight=200`, `activity_trigger_enabled=True` |
| `mop_off_llm_off` | `mop` | `mop_activity_source_components=True`, `frontier_boost_weight=200`, `mop_weight_direct=0`, `mop_weight_transitive=0`, `mop_weight_open_menu=0`, `mop_weight_wtg=0` |
| `mop_on_llm_70` | `llm_mop` | the reference's four, plus `llm_url`, `llm_prompt_variant="v13"`, `llm_percentage=0.7`, `llm_temperature=0`, `llm_snap_tolerance_px=150` |

The control's shape is fixed by INV-APV-29 and is now expressed jointly by the preset and the
overrides: `mop_data` present and loadable (top-level), all four MOP weights zeroed and
`mop_frontier_weight` at the preset's `0` (so `WTG`, `MENU_GATEWAY` and `MOP_FRONTIER` are inactive at
their neutral values), and `activity_trigger_enabled` at the preset's `false`. `frontier_boost_weight`
stays at `200` deliberately, keeping `FRONTIER` active. The alternatives are worse and were rejected
for reasons that have not changed: pointing `ape.mopDataPath` at a missing file aborts the run, and
omitting `mop_data` kills the generic WTG and frontier passes as collateral, turning the contrast into
"full substrate versus almost none".

Single-factor remains a property of the **effective plan**, and the override dicts now make it
readable directly. Reference minus control is exactly the five MOP weight keys plus
`activity_trigger_enabled`; reference minus LLM arm is exactly the LLM keys, with no exemption. The
two B3 jar declarations that used to be that exemption are gone (INV-APV-59), so the diff no longer
needs an argument about why an extra pair of keys is harmless — the arms differ in the LLM keys and
in nothing else.

#### Scenario: Control arm keeps the frontier alive while MOP guidance is off
- **WHEN** `get_variants()["mop_off_llm_off"]` is resolved
- **THEN** `mop_data` SHALL equal `"static_analysis"`
- **AND** `overrides` SHALL contain `mop_weight_direct=0`, `mop_weight_transitive=0`,
  `mop_weight_open_menu=0`, `mop_weight_wtg=0`
- **AND** `overrides` SHALL contain `frontier_boost_weight=200`, so generic WTG and frontier
  navigation stay enabled (INV-APV-30)
- **AND** `mop_frontier_weight` and `activity_trigger_enabled` SHALL be absent from `overrides`,
  taking the `mop` preset's `0` and `false`

#### Scenario: Control arm never omits the static analysis document
- **WHEN** the guard test inspects the control arm's variant dictionary
- **THEN** `mop_data` SHALL be present at the top level
- **AND** the test SHALL fail naming INV-APV-29 if it is absent, because an absent document disables
  `WtgPass` and `FrontierPass` as collateral damage

#### Scenario: Reference and control differ only in MOP keys
- **WHEN** the effective configurations of `mop_on_llm_off` and `mop_off_llm_off` are diffed
- **THEN** the differing keys SHALL be exactly `ape.mopWeightDirect`, `ape.mopWeightTransitive`,
  `ape.mopWeightOpenMenu`, `ape.mopWeightWtg`, `ape.mopFrontierWeight` and
  `ape.activityTriggerEnabled`
- **AND** every other key SHALL be identical, so the contrast is single-factor

#### Scenario: Reference and LLM arm differ only in LLM keys
- **WHEN** the effective configurations of `mop_on_llm_off` and `mop_on_llm_70` are diffed
- **THEN** every differing key SHALL be an `ape.llm*` key
- **AND** the two arms' top-level keys SHALL be identical, neither carrying a jar declaration
  (INV-APV-59)
- **AND** no MOP weight, frontier or exploration key SHALL differ

#### Scenario: Source components flag is explicit in all three arms
- **WHEN** the three decisive-run arms are iterated
- **THEN** each SHALL carry `mop_activity_source_components=True` in its `overrides`
- **AND** none SHALL rely on the `mop` preset's `false`


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


### Requirement: Native NDJSON Trace Reader (FR11, FR13, NFR03, NFR06)

The module SHALL provide `modules/aperv-tool/src/aperv_tool/analysis/trace_ndjson.py`, a read-only streaming reader of the NDJSON trace, and it SHALL be the sole mechanism by which analysis code in this module consumes a stage-4 trace. It follows the shape of its sibling `analysis/coverage_dump.py`: a pure offline component with a typed row model, never in the run path.

The reader SHALL stream the file — the trace is the largest artifact a run produces, and the reader must not require it in memory — and SHALL yield one typed row per `StepRecord`, having already:

- resolved the `act` and `st` integer references, and `out.target`, against the `ACT` / `STATE` dictionary records defined earlier in the same trace;
- materialized the fields the sink omits at their documented defaults, and left the tri-state fields absent (INV-APV-49);
- re-derived `activity_has_mop` on the step side from the record's `ACT` entry, and on the outcome side via `out.target` → `STATE.act` → `ACT.mop`, since the jar records that static per-activity fact once on the dictionary entry rather than on every step;
- expanded the run-relative `t` to epoch milliseconds via `RUN_START.t0` where an absolute clock is wanted, and reported the expansion as unavailable when `RUN_START` is absent (INV-APV-51);
- attached the step's `llm[]` sub-events, in occurrence order, and its `out` section to the same row — so that the three-way join by `step=` that the legacy format required ceases to exist for every consumer;
- carried each sub-event **whole**, including the `sys` / `user` / `resp` / `tool_calls` prompt and response dumps (INV-APV-58).

**`RunStart` carries the whole `RUN_START` record (INV-APV-61).** The jar echoes its resolved run specification into the first record so that a post-hoc audit can say which jar, which arm and which parameters produced a trace — `build.sha` exists because a stale jar once shipped, its MOP boost fired zero times across 147,153 evaluations, and nothing in 2,028 tasks' output said which jar had run. A reader that drops ten of those thirteen members reproduces that blindness one layer up. `RunStart` SHALL therefore expose `v`, `run_id`, `t0_ms`, `seed`, `agent`, `preset`, `features`, `params`, `inert`, `corpus_basis`, `digest`, `props_digest` and `build` (as a nested value with `sha` and `time`), each reported absent — `None` — when the wire record lacks it, never defaulted; `params` remains what the jar recorded verbatim (only non-default values plus active activation keys — absence means "at the jar default for this `build.sha`"). No consumer in `aperv_tool` SHALL parse `RUN_START` other than through this class; the workaround parser in `rvsec-calibracao/scripts/check_run_start.py` loses its reason to exist.

**The `v` schema gate is checked, not merely carried (INV-APV-62).** The reader SHALL compare `RUN_START.v` to the format version it implements (`FORMAT_VERSION = 1`); a mismatch SHALL be recorded in `TraceDiagnostics.schema_version_mismatch` and, when the reader is constructed with `strict=True`, SHALL raise `SchemaVersionMismatch` before any row is yielded — a cross-campaign comparison over incomparable fields fails loudly rather than quietly. The default is non-strict, so a survey over a mixed tree still yields rows and counts the mismatches. A trace whose capture began after `RUN_START` reports the version as unknown, and the reader does not infer it.

The reader SHALL additionally expose the run-level records as attributes beside the `RUN_START` header — `MOP_DATA`, `PIPELINE` and `LLM_ACK` — since a step-row iterator has no natural place for them and this module is the sole way to reach them. `RUN_END` SHALL NOT be exposed, and the asymmetry is deliberate rather than an omission: INV-APV-53 makes it write-only, and an accessor is the first step toward the `if not run_end: ...` that owner decision D5 refuses. The other three are load and assembly census, not a termination signal.

**Both clauses reverse an earlier reading of this requirement, and the reversal is recorded rather than quietly applied.** The first implementation surfaced neither, on the defensible ground that the dumps are the bulk of the record and nothing in this module read them. What that reasoning missed is that the jar writes them by default and the jar's own throughput gate (`event-sink` INV-SNK-13) prices their escaping, so the run pays their full cost either way — and that the analysis which did read them is real rather than hypothetical: `calibracao/decompose_nomatch.py` pairs each response with the call that produced it to decompose `no_match` causes, and that pairing was the gate of a change decision. It stays on the legacy format under INV-APV-55, so its successor over new traces has to get `resp` from here. The same argument applies to the census: `MOP_DATA.wtgEdges` and `PIPELINE.candidates` are the two quantities the jar-side change added — one because `transitions` had been misread as the frontier gate for months, the other because "the arm turned this off" and "this application's data could not support it" were otherwise the same evidence across 25 of 40 applications — and writing them into a trace no reader surfaces would reproduce that defect one layer up. If the dumps are ever judged too expensive, the lever is the jar's `llmPromptDump` flag, not a silent drop here.

The reader SHALL NOT convert between formats in either direction, SHALL NOT write to the trace, and SHALL NOT run on the collection path (INV-APV-48). A malformed record SHALL be skipped and counted rather than aborting the read (INV-APV-50): a trace truncated by a `SIGKILL` ends in a partial line by construction, and losing the whole run's analysis over its last line would be a worse failure than losing the line. `RUN_START` is not guaranteed to be line 1 — AOSP banner lines may precede it — so the reader SHALL take the first `{`-leading line as the candidate header.

**The `ape` change `rearch-04-step-ndjson-telemetry` is the authority for the wire format.** Its `event-sink` spec defines the `StepRecord` schema, the dictionary encoding, the omitted-default rules and the heartbeat payload; its `run-spec` spec defines the `RUN_START` echo; its design carries the legacy-field → new-schema mapping table. The format is defined jointly and cut once, and this reader conforms to it rather than restating it.

The golden fixture that exercises this requirement SHALL be `modules/aperv-tool/tests/fixtures/trace_ndjson_golden.ndjson`, a hand-written stage-4 trace containing, at minimum: a `RUN_START` with `t0` **and all thirteen members**; `ACT` entries with `mop:1` and `mop:0`; two `STATE` entries; a step whose `dec` carries no boost fields at all; a step carrying `patched:0`; a step carrying no `patched` member; a step with two `llm[]` entries in occurrence order; a step whose `out` resolves to a new state; a step closed with no `out` member; a step flushed with `out:{"resolved":false}`; a completed call carrying the `sys` / `user` / `resp` / `tool_calls` dumps beside one that carries none; a `MOP_DATA` record, a `PIPELINE` record whose `candidates` include disabled entries, and an `LLM_ACK`; a malformed line; and a truncated final line. A second fixture, `trace_ndjson_v2_header.ndjson`, SHALL carry `RUN_START` with `v: 2` and one step. Every scenario below names the fixture element that exercises it, so no rule is asserted against an input that cannot reach it.

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
- **AND** the schema version SHALL be reported unknown, not assumed

#### Scenario: Prompt and response dumps reach the caller
- **WHEN** the reader runs over the fixture's step-42 completed call, which carries `sys`, `user`, `resp` and `tool_calls`
- **THEN** the sub-event SHALL carry all four, with the widget list's embedded newlines intact as the jar escaped them
- **AND** the abandoned attempt beside it, written without dumps, SHALL report them as absent rather than as empty strings — an empty string would claim the model was sent an empty prompt

#### Scenario: The run-level census is reachable and RUN_END is not
- **WHEN** the reader runs over a trace carrying `MOP_DATA`, `PIPELINE`, `LLM_ACK` and `RUN_END`
- **THEN** the first three SHALL be readable as reader attributes, so `wtgEdges` and the candidate census need no second parser
- **AND** the reader SHALL expose no `RUN_END` accessor at all (INV-APV-53)
- **AND** a trace carrying none of them SHALL report each as absent rather than as an empty record

#### Scenario: RunStart carries all thirteen members
- **WHEN** the reader runs over the golden fixture's `RUN_START`, which carries `v, run_id, t0, seed, agent, preset, features, params, inert, corpus_basis, digest, props_digest, build{sha,time}`
- **THEN** `reader.run_start` SHALL expose each of them, `build` as a nested value with `sha` and `time`
- **AND** on cmp162's 972 `aperv` traces every member SHALL be present, and the test over the fixture manifest SHALL assert it
- **AND** a `RUN_START` written without `inert` SHALL report `inert=None`, not `False`

#### Scenario: Schema version mismatch is loud in strict mode and counted otherwise
- **WHEN** the reader opens `trace_ndjson_v2_header.ndjson` with `strict=True`
- **THEN** it SHALL raise `SchemaVersionMismatch` naming `2` and `1` before yielding any row
- **AND** with `strict=False` it SHALL yield the row and report `schema_version_mismatch=1` in diagnostics

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

---

### Requirement: Derived MOP Artifact Generation and Caching (FR19, NFR04)

`ApeRVTool._derive_mop_artifact(task)` SHALL return the host path of the compact MOP artifact for the
task's APK, generating it when needed:

1. Compute the SHA-256 of the current full JSON at `<results_dir>/<apk_name>.json`.
2. When `<results_dir>/<apk_name>.mop.json` exists and its `source.digest` equals `"sha256:" + <hex>`,
   reuse it without regenerating.
3. Otherwise call `derive()` + `serialize_canonical()` and write the artifact atomically
   (write-temp-then-rename in the same directory). A failed derivation SHALL write nothing.

The artifact is cached next to its source so it is inspectable and diffable, and it is a pure function
of the full JSON (INV-APV-47, INV-DRV-05). This method replaces `_compact_static_analysis_json`,
which is deleted together with its fallback-to-source push: there is no longer any condition under
which the full JSON reaches the device (INV-APV-46).

#### Scenario: cache hit skips derivation
- **WHEN** `<results_dir>/com.example_1.apk.mop.json` exists carrying
  `source.digest == "sha256:ab12…"` and the SHA-256 of `com.example_1.apk.json` is `ab12…`
- **THEN** `_derive_mop_artifact(task)` SHALL return that path
- **AND** `derive()` SHALL NOT be called

#### Scenario: stale cache regenerates
- **WHEN** the cached artifact records `source.digest == "sha256:ab12…"` but the current full JSON
  hashes to `cd34…`
- **THEN** the artifact SHALL be regenerated and overwritten
- **AND** the pushed bytes SHALL equal a fresh derivation of the current full JSON

#### Scenario: failed derivation leaves no artifact behind
- **WHEN** `derive()` raises `DerivationError` because the document carries `complete: false`
- **THEN** no `<apk_name>.mop.json` SHALL exist afterwards, and any partially written temporary file
  SHALL be removed
- **AND** `RVToolExecutionError` SHALL be raised carrying the derivation error

---

### Requirement: MOP Artifact Projection Contents (FR04, FR05, FR06, FR19)

`derive_mop_artifact.derive(document)` SHALL produce a `formatVersion: 1` artifact containing exactly
the projection the explorer consumes:

1. **Scalars**: `package` and `mainActivity` copied verbatim from the full JSON.
2. **Provenance**: `source.digest` (`"sha256:" + hex` of the full-JSON bytes), `source.file`
   (basename) and `source.generator` (generator identifier and version).
3. **Widgets** (`widgets.<baseActivity>.<shortId>`): a per-normalized-eventType `mop` map with values
   `none|direct|transitive|both`, plus the consumed metadata fields `inputType`, `hint`, `prompt`,
   `spinnerMode`, `contentDescription`, `tooltipText` and `entries`, each emitted only when non-empty.
   A widget SHALL be emitted only when it is MOP-flagged OR carries at least one metadata field. The
   keys `id`, `type`, `text` and the raw `listeners` array SHALL NOT be emitted. Map keys SHALL be
   pre-normalized (lowercased, `_` and `-` removed), matching the query-side normalization.
4. **Activity sets**: `mopActivities` (widget-derived, per INV-DRV-02 and the dialog promotion of
   INV-DRV-03) and `mopActivitiesAugmented` (the A′ union), both always emitted so the on-device
   `mopActivitySourceComponents` flag keeps selecting between them at run time.
5. **OPTIONSMENU records**: `optionsMenus: [{activity, hasFlaggedWidget}]`, where `hasFlaggedWidget`
   is true when any widget of that menu window is MOP-flagged — tested over the window's parsed
   widgets, before the empty-id drop, for the same reason INV-DRV-02 states.
6. **WTG**: `wtg.<sourceBaseActivity> = [{widget, target}]` per INV-DRV-03. `widgetClass` SHALL NOT be
   emitted.
7. **Components**: `activities[]` (`className`, `isMain`, `permission`, `reachesMop`,
   `deepLinkUri`), `receivers[]`/`services[]` (adding `intentFilters` with `actions` and `categories`
   only, plus the boolean `hasTargetMethods`), `providers[]` (adding `authorities`). `reachesMop` is
   the wire rename of `reachesTarget`. The intent-filter `data` block, `readPermission`,
   `writePermission`, the `targetMethods` signature list and `exported` SHALL NOT be emitted.
   `exported` is on that list because no consumer reads it and none may: the jar's activity launcher
   is required to ignore export status (the dispatch runs from uid 2000 and opens non-exported
   activities), so keeping the field on the wire would ship a value whose only possible use is
   forbidden.
8. **Stats**: `windows`, `widgetsTotal`, `flagged`, `droppedFlaggedNoId`, `orphanDialogs`,
   `handlersUnmatched`, `syntheticLambda`, `recovered`, `wtgEdges`, `dedupedTransitions`.
   `widgetsTotal` and `flagged` SHALL count the widget map after the dialog merge and before the
   emission filter of item 3, so they remain the numbers the jar's load record reported.

Derivation preconditions: `document["complete"] is True` and a non-null `package`; otherwise
`DerivationError`. A truncated analysis SHALL never yield an artifact — the completeness sentinel
becomes a generation precondition instead of a device-side check.

#### Scenario: cryptoapp derivation matches the known ground truth
- **WHEN** `derive()` runs on `cryptoapp.apk.gh60-fresh.json`
- **THEN** `mopActivities` SHALL equal
  `{MessageDigestActivity, CipherActivity, CryptographyActivity}` (base names).
  `CryptographyActivity` enters through the D8 recovery: the exact join drops its
  `CryptographyActivity$$ExternalSyntheticLambda0:onClick` wrapper handler and the reaching
  `lambda$setupExecuteButton$0` body restores it. The jar asserts the same three flagged widgets
  when it parses this fixture raw, which is this change's oracle (design D11)
- **AND** `optionsMenus` SHALL contain the `MainActivity` record, and `wtg` SHALL carry the click
  edges from `MainActivity` to both MOP sub-activities
- **AND** `components.activities` SHALL have 4 entries and `components.providers` 1 entry with
  `authorities == "br.unb.cic.cryptoapp.androidx-startup"`, every component `reachesMop == false`
- **AND** `stats.windows` SHALL be 5, `stats.flagged` 3 and `stats.recovered` 1

#### Scenario: incomplete full JSON refuses to derive
- **WHEN** `derive()` runs on a document whose `complete` key is absent or `false`
- **THEN** `DerivationError` SHALL be raised
- **AND** no artifact SHALL be produced

#### Scenario: no Target vocabulary and no call graph on the wire
- **WHEN** an artifact is generated from a document declaring receivers and services
- **THEN** the only key matching `*Target*` anywhere in it SHALL be `hasTargetMethods`
- **AND** it SHALL contain no `reachability`, `windows`, `transitions` or `listeners` section
  (INV-DRV-06)
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

---

### Requirement: Widget MOP Flag Derivation (FR04, FR06)

The generator SHALL derive each widget's MOP flags from its listeners, per normalized `eventType`,
and OR-aggregate them across listeners (INV-DRV-01). For each listener:

1. When `handlerDirectlyReachesTarget` or `handlerReachesTarget` is non-null, the producer's values
   win: `direct` is `handlerDirectlyReachesTarget is True`, `transitive` is
   `handlerReachesTarget is True or direct`.
2. Otherwise the handler signature is looked up in the index built from `reachability[].methods[]`,
   which SHALL carry, per signature, the pair (`directlyReachesTarget`, `reachesTarget or
   directlyReachesTarget`). Duplicate signatures SHALL be merged by OR rather than by last-write, so
   the index does not depend on producer ordering.
3. When the exact lookup misses and the handler matches `^<(.+?)\$\$ExternalSyntheticLambda\d+:`, the
   flags SHALL be recovered from the enclosing class's reaching `lambda$…` methods, OR-aggregated;
   when that class has no reaching lambda method the widget SHALL NOT be flagged.

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
with `componentType == "activity"` carrying at least one method with `reachesTarget` or
`directlyReachesTarget` true. Both sources contribute base activity names. Both sets SHALL be emitted
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
WTG edges and component lists, sorted for the activity sets and the OPTIONSMENU records. Running the
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

- **WHEN** `configure()` receives `corpus_basis="subset40:4157faa071fae1b405730de6d3fabf3d6821e54830473e98d2c342bffcadd252"` and `_push_properties()` runs for variant `mop_on_llm_off`
- **THEN** the generated `ape.properties` SHALL contain the line `ape.corpusBasis=subset40:4157faa071fae1b405730de6d3fabf3d6821e54830473e98d2c342bffcadd252`
- **AND** the value SHALL be byte-identical to what was configured, with no re-derivation, truncation or case change
- **AND** the run's `RUN_START` SHALL carry `corpus_basis` with that same value

#### Scenario: An unstated corpus produces no key at all

- **WHEN** `_push_properties()` runs for variant `sata` and `corpus_basis` is absent from `_tool_config`
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

This is a deliberate transfer of responsibility rather than a loss of one. The pre-change guards
could only compare Python constants with Python constants, so they detected a missing mapping entry
but never a value the jar would reject, a sub-parameter whose feature was inactive, or a key the jar
had stopped reading. The jar now rejects all four, at run time, with an abort naming the key — a
stronger check than the one being retired, applied to the binary that actually runs.

At implementation time the mapping SHALL be swept against the jar's accepted-key vocabulary
(`KeyOwnership.allKeys()` plus the retired list, read from the `ape` source checkout) and any dead
entry removed. The sweep performed while authoring this change found exactly one:
`mop_weight_activity`. The remaining 50 entries are all accepted keys.

`llm_snap_tolerance_px` SHALL remain mapped and reach the jar only as an explicit override of the arm
that sets it (`mop_on_llm_70`), subject to the jar's own feature-dependency validation. It SHALL
carry no Python-side pairing with a declared jar identity: INV-APV-34 is retired by INV-APV-59, and
the arm's `overrides` entry stands on its own like every other.

#### Scenario: Dead key removed
- **WHEN** `APERV_PROPERTY_MAPPING` is inspected after this change
- **THEN** it SHALL NOT contain `mop_weight_activity`
- **AND** a grep for `mopWeightActivity` across `modules/aperv-tool/src` SHALL return no hit

#### Scenario: Every mapped key is one the jar accepts
- **WHEN** each value of `APERV_PROPERTY_MAPPING` is checked against the jar's accepted-key
  vocabulary
- **THEN** every one SHALL be present in it
- **AND** none SHALL appear in the jar's retired-key list

#### Scenario: Live ungoverned key travels the normal path
- **WHEN** `get_variants()["mop_on_llm_70"]` is read
- **THEN** `llm_snap_tolerance_px: 150` SHALL be an entry of its `overrides`
- **AND** `_push_properties()` SHALL write `ape.llmSnapTolerancePx=150` for that arm
- **AND** the arm SHALL carry no key declaring the jar it was raised for (INV-APV-59)

#### Scenario: No semantic validation is performed on override values
- **WHEN** an arm's `overrides` carries a mapped key at a value the jar will reject
- **THEN** `_push_properties()` SHALL write it unchanged
- **AND** the rejection SHALL come from the jar as an abort before step 1, visible in the trace

---

---
