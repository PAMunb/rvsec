## Purpose

This delta turns the `aperv` arms into the six cells of the APE-RV group-isolation experiment and teaches the
trace reader the decision record the new jar writes. It is the rv-android half of a two-repository change: the
`ape` change `isolate-guidance-groups` defines the jar side (group keys, cell presets, the step's owners and the
telemetry), and this delta defines how `aperv-tool` names, configures and reads it. The key contract quoted here
is the `ape` design's § "Key contract" and § "Telemetry contract" (contract v1, 2026-10-17); a later revision of
that contract reaches this delta as a diff.

APE-RV now mounts five behaviour groups by declaration. BASE is the APE algorithm. ADDONS holds the fork's own
improvements. STATIC holds the consumers of the static GUI model. MOP holds the consumers of the specification
targets. LLM is the vision-language model. A **cell** is a union of groups. The jar ships one preset per cell, and
each preset is the union of that cell's group blocks: `base`, `mop`, `as` (ADDONS + STATIC), `as_mop`, `as_llm`
and `as_mop_llm`. What a group switches on is defined in the jar. The Python side therefore names a cell and
supplies only the deployment facts: the server URL, the static-analysis artifact, and the variant name that the
jar echoes into `RUN_START`.

The ten arms this module defined before are deleted, without alias (author decision D-A13). They were built on
presets the jar no longer has and on override sets that the new jar either rejects (`ape.mopDataPath`,
`ape.mopTargetPickCap`, `ape.leastVisitedPriorityTiebreak` are retired keys) or would run as a different
configuration, so a surviving name would describe a configuration the jar no longer runs. Campaigns recorded under
those names keep resuming from their frozen image (`rvandroid:0.9.5`), whose `tool.py` still defines them. The
only name kept is `default`, which every registered tool must carry (`tools` INV-TOOL-02). It is bound to the same
object as `base`, so `aperv` with no variant runs the APE reference cell and its trace says `variant: "base"`.

The reader change follows from the jar's new telemetry. `dec.src` now names the owner that took the step (`budget`,
`restart`, `llm`, `launcher`, `mop`, `sata`) instead of the largest boost, `dec.cf` is replaced by a per-scorer
`dec.cfc`, eleven further new `dec` members record the owner with its coins and gates, the roulette draw, the
extension points, the input origin, the restart kind, the SATA path, the display rotation, the buffer preemption,
the navigation-frontier boost and the component trigger (contract v3.2, `ape` `16b185f4`), and `RUN_END.counters` gains the per-run counts of each mechanism. The
reader surfaces all of them, plus the `mopd`/`mops`/`ret` members it drops today, and exposes `RUN_END` as a
census record. The collection path in `tool.py` still never reads `RUN_END` or `RUN_START`.

## Data Contracts

### Input
- `variant dict: Dict[str, Any]` — per cell: `preset: str` (one of `base`, `mop`, `as`, `as_mop`, `as_llm`,
  `as_mop_llm`), `variant: str` (the cell's own name), `overrides: Dict[str, Any]` (the server URL on the two LLM
  cells, otherwise empty), `strategy: "sata"`, `static_data: "static_analysis"` on every cell except `base`, and
  `broadcast_catalog: True` on the four cells that mount STATIC (source: `ApeRVTool.get_variants()`, merged with
  DSL parameters by `ToolFactory`)
- `APERV_PROPERTY_MAPPING: Dict[str, str]` — 66 entries: override key → `ape.*` property name; only keys the jar
  built from the `ape` branch `isolate-guidance-groups` accepts (source: `tool.py` module constant)
- `<ape>/src/test/resources/cells/<cell>.run_start.json` — the jar's expected `RUN_START` per cell, with `run_id`,
  `t0`, `seed`, `build` and `props_digest` masked (source: `ape` change wave 2; read by the cell gate only, never at
  run time)
- Trace records (source: the jar's `NdjsonSink` and `RunSpecEcho`):
  - `RUN_START.variant: str`, omitted when the jar received no `ape.variant`;
  - `dec.src: str` — on the group-isolation jar, one of `budget`, `restart`, `llm`, `launcher`, `mop`, `sata`; on
    the `eea2b1a9` jar and earlier, the stage whose boost was largest;
  - `dec.ch: str` — on the group-isolation jar, `mop_coin`, `budget`, `restart`, `launcher`, `llm` or one of the
    SATA channels; `short_circuit_*` is no longer written;
  - `dec.own: {"i": str, "trg"?: "new_state"|"stagnation"|"coin", "uL"?: float, "uM"?: float, "g"?:
    "min_actions"|"breaker", "fb"?: "gate"|"error"|"decline"|"no_match"|"ineligible"}` — written on every step
    record; `i` takes the owners of `dec.src`; `trg` is the LLM stage that made the step's one LLM call;
  - `dec.cfc: {<scorer>: 0|1}` over `mop`, `mopf`, `wtg`, `navf`, `cov`, `menu`, `form`;
  - `dec.draw: [int, int]`; `dec.nav: {"x": "X1"|"X3"|"X4", "c": "ape"|"mop", "alt": 0|1, "drew": 0|1}` — written
    when the point had at least two candidates; `alt` is 1 only when the MOP variant decided by its own rule
    (`ape` D-B14.8), so always 0 at X1 and on cells without MOP;
  - `dec.trig: {"k": "broadcast"|"service"|"provider", "c": str}` — the step during which component triggering
    fired, whatever its owner; `dec.comp` stays the launcher's activity-launch outcome;
  - `dec.inp: "typed"|"heuristic"|"random"|"form"|"llm"`; `dec.restart: "graph"|"state"|"activity"|"periodic"`;
  - `dec.bmc: int` (omitted when 0); `dec.strat: str` (one of the fifteen SATA path names); `dec.rot: int` in
    `-1..3`; `dec.buf: str` (an owner name);
  - `dec.navf: int` (scorer field, omitted when 0); `dec.mopd: int`; `dec.mops: "s"|"i"`; `dec.ret: [int, …]`;
  - `RUN_END: {reason, detail?, steps, t_first_step?, t_last_step?, counters: {acts, states, stampNodes,
    stampHits, retired, launches, gateMinActions, gateBreaker, guardBacks, bufAbandoned, restarts, coinLlm,
    coinMop, llm?: {…}}}`

### Output
- `ape.properties` on device — `ape.preset=<cell>` first, `ape.variant=<variant>` second,
  `ape.staticDataPath=/data/local/tmp/mop-artifact.json` third when the artifact was pushed, then one
  `ape.<key>=<value>` line per `overrides` entry in mapping order (destination: the jar's `RunSpec` resolution)
- `TraceReader.run_end: Optional[Dict[str, Any]]` — the `RUN_END` record minus `type`, verbatim; `None` when the
  trace carries none (destination: offline analysis)
- `StepRow` — gains `owner`, `scorer_cf`, `draw`, `nav`, `input_source`, `restart_kind`, `back_menu_capped`,
  `sata_path`, `rotation`, `buffer_abandoned_by`, `component_trigger`, `nav_frontier`, `mop_distance`, `mop_stamp`,
  `retired_targets` (destination: `analysis/*` consumers and the baseline frames, which write `None` for each)
- `RunStart.variant: Optional[str]` — the fourteenth member

### Side-Effects
- **[Device]**: `/data/local/tmp/mop-artifact.json` receives the derived compact artifact on every cell except
  `base`, and never the full static-analysis JSON (INV-APV-46)
- **[Device]**: `system-broadcast.json` is pushed on the four cells that mount STATIC (`as`, `as_mop`, `as_llm`,
  `as_mop_llm`), whose preset mounts `COMPONENT_TRIGGER` at `componentPercentage=0.03`, and never on `base` or `mop`
- **[Trace]**: `RUN_START.variant` is present in every trace of an `aperv` run made with this tree

### Error
- `ConfigurationError` — raised by `configure()` as before, and additionally when `variant` is absent or empty, and
  for the retired Python key `mop_data` at the top level (it is no longer an orchestration key, so the
  unhonourable-key rule of INV-APV-39 rejects it)
- Jar-side abort — a properties file that still sets `ape.mopDataPath`, `ape.mopTargetPickCap` or
  `ape.leastVisitedPriorityTiebreak` aborts before step 1 with `retired_key`; a jar that predates the group keys
  aborts on `ape.variant` and the cell presets as unknown. This is the intended guard of the cross-repository
  ordering, not a failure to handle

## Invariants

These replace, add to or retire the listed invariants of `openspec/specs/aperv/spec.md` § Invariants; the
invariant section is synchronized by hand at archive.

- **INV-APV-05** (replaced): `get_variants()` SHALL return a dict whose keys are exactly `default`, `base`, `mop`,
  `as`, `as_mop`, `as_llm` and `as_mop_llm`, with `default` bound to the same object as `base` (INV-TOOL-02).
- **INV-APV-06** (replaced): every cell except `base` SHALL set `static_data` to `"static_analysis"`. When
  `static_data == "static_analysis"`, `execute_tool_specific_logic()` SHALL locate the full static-analysis JSON,
  obtain the derived compact artifact from it (cache-or-generate), and push only that artifact. If the JSON is not
  found, or its derivation fails, the task SHALL fail before the jar is launched (INV-APV-45).
- **INV-APV-08** (replaced): `ape.properties` generation SHALL use `APERV_PROPERTY_MAPPING` to translate the
  `overrides` keys. Python-only keys (`strategy`, `static_data`, `seed`, the three device-addressing keys) have no
  mapping entry and are never written; `preset` and `variant` are written by their own fixed lines.
- **INV-APV-09** (replaced): the LLM cells (`as_llm`, `as_mop_llm`) SHALL carry `http://10.0.2.2:30000/v1` as
  their default `llm_url`; `10.0.2.2` is the Android emulator's alias for the host loopback interface. The
  `APERV_LLM_BASE_URL` environment variable SHALL replace that default when set, through the `rv-experiment` entry
  point and `ToolConfig.parameters`, never through a read in this module (INV-TOOL-20). A DSL `@llm_url` SHALL win
  over the variable. A cell without the LLM group SHALL NOT receive `llm_url` from the variable.
- **INV-APV-10** (replaced): `system-broadcast.json` SHALL be pushed when it is present in the module directory and
  the variant carries `broadcast_catalog=True`, and SHALL NOT be pushed otherwise. `broadcast_catalog` SHALL be
  `True` exactly on the cells whose preset mounts STATIC, because the catalog's only reader in the jar is
  `COMPONENT_TRIGGER`, a STATIC member (`ape` D-B13). When the catalog is absent from the module directory the jar
  degrades gracefully: component triggering proceeds without typed extras for system broadcasts.
- **INV-APV-29** (retired): the MOP-off control arm it shaped is deleted; MOP-off is the absence of the MOP group,
  stated by the cell preset.
- **INV-APV-30** (retired): the frontier is a STATIC member (`NAV_FRONTIER`) mounted by the `as*` cells; no rule
  ties it to MOP arms.
- **INV-APV-38** (replaced): every variant whose preset mounts the LLM group (`as_llm`, `as_mop_llm`) MUST carry
  `llm_url` in its `overrides`. The cell preset states `ape.llm=true` without the URL, which names a machine
  rather than a cell, so a variant without it aborts at resolution (`MISSING_DEPENDENCY`). This is a fail-fast,
  not a fallback.
- **INV-APV-42** (retired): the frozen-name rule protected the resume identity of names that this change deletes.
  Old campaigns resume from their frozen image.
- **INV-APV-45** (replaced): a variant configured with `static_data == "static_analysis"` SHALL either push a
  freshly validated derived artifact and write `ape.staticDataPath`, or fail the task before the jar is launched.
  There SHALL be no execution path in which such a variant launches the jar without `ape.staticDataPath` set.
- **INV-APV-49** (replaced): default materialization SHALL be total for the fields whose absence means a default
  and SHALL NOT be applied to the fields whose absence is itself information. The seven boost fields (`mop`,
  `mopf`, `wtg`, `navf`, `cov`, `menu`, `form`) SHALL be materialized at `0` when absent, and `out.new_state` /
  `out.act_changed` at `false`. `dec.patched`, `dec.cf`, `dec.cfc`, `dec.own`, `dec.mopd` and every other `dec`
  member added by the group-isolation jar SHALL be preserved as absent when absent, because a trace from the
  `eea2b1a9` jar carries none of them and a materialized default would claim the mechanism ran.
- **INV-APV-53** (replaced): no code path on the collection path of this module (`tools/aperv/*`) SHALL read,
  validate or act on the `RUN_END` record: no sentinel check, no exit-code interpretation beyond the existing debug
  log, no task-status change and no retry keyed on it (owner decision D5). The offline reader `trace_ndjson.py`
  SHALL expose it as a census record and SHALL NOT interpret it.
- **INV-APV-58** (replaced): the reader SHALL NOT drop data the trace carries. Every field of an `llm[]` sub-event
  SHALL reach the caller, every `dec` member listed in this delta's Data Contracts SHALL reach the row, and every
  run-level record SHALL be reachable: `MOP_DATA`, `PIPELINE`, `LLM_ACK` and `RUN_END` as reader attributes.
- **INV-APV-62** (replaced): `TraceReader` SHALL accept `RUN_START.v` in `SUPPORTED_VERSIONS = {1, 2}`. Version 1 is
  the `eea2b1a9` jar and earlier, and version 2 is the group-isolation jar, which bumped the version because
  `dec.src` changed meaning. Any other declared version SHALL be surfaced in `TraceDiagnostics` and SHALL raise
  `SchemaVersionMismatch` in strict mode. The reader SHALL expose the version it read as `run_start.v`. A trace
  with no `RUN_START` reports the version as unknown (INV-APV-51 applies).
- **INV-APV-61** (replaced): `RunStart` SHALL carry every top-level member of the `RUN_START` record the jar emits,
  `variant` included, with `build` as a nested `(sha, time)` value; a member absent on the wire SHALL be reported
  absent, never defaulted.
- **INV-APV-65** (new): every variant SHALL carry a top-level `variant` equal to its own cell name (`default`
  carries `"base"`), and `_push_properties()` SHALL write it as `ape.variant=<variant>` on the second line. The tool
  SHALL NOT read the echoed `RUN_START.variant` back (INV-APV-43).
- **INV-APV-66** (new): `static_data` SHALL be present exactly on the cells that mount STATIC or MOP — every cell
  except `base` — so the artifact reaches the device if and only if a group that reads it is mounted.
- **INV-APV-67** (new): the reader SHALL NOT rewrite, translate or reinterpret `dec.src`. Its documentation SHALL
  state both meanings: the executed owner under `RUN_START.v == 2`, the largest boost under `v == 1`. The version
  is what tells them apart, and the reader carries it without branching on it.
- **INV-APV-68** (new): `activity_has_mop`, on the step side and on the outcome side, SHALL be `None` when the
  `ACT` record carries no `mop` member. The group-isolation jar writes `ACT.mop` only when the MOP group is
  mounted, so in `base`, `as` and `as_llm` the fact was not computed, and `False` would claim it was. The same
  rule holds for `StateCoverage.mop_reach`: a `UICOV` line without `mopReach` is complete, with `mop_reach = None`.

## MODIFIED Requirements

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
- **AND** `handlers` SHALL have exactly the keys `br.unb.cic.cryptoapp.cipher.CipherActivity$1` and
  `br.unb.cic.cryptoapp.generated.CryptographyActivity$$ExternalSyntheticLambda0`, each with
  `mop == {"click": "transitive"}`; the second SHALL carry `dist == {"click": [[16,3],[17,3],[18,3]]}`
  and the first no `dist`
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

## ADDED Requirements

### Requirement: ApeRVTool Cell Variants (FR20)

`ApeRVTool` SHALL define one variant per experimental cell and nothing else. Every variant SHALL consist of a
`preset` name, a `variant` name, an `overrides` dict, and Python-only orchestration keys (INV-APV-40).

`get_variants()` SHALL return exactly these **seven** names, carrying **six** distinct configurations:

| Variant | preset | static_data | broadcast_catalog | overrides | Groups mounted by the preset |
|---|---|---|---|---|---|
| `default` | `base` | — | — | _(empty)_ — bound to the same object as `base` (INV-TOOL-02) | — |
| `base` | `base` | — | — | _(empty)_ | — |
| `mop` | `mop` | `"static_analysis"` | — | _(empty)_ | MOP |
| `as` | `as` | `"static_analysis"` | `True` | _(empty)_ | ADDONS, STATIC |
| `as_mop` | `as_mop` | `"static_analysis"` | `True` | _(empty)_ | ADDONS, STATIC, MOP |
| `as_llm` | `as_llm` | `"static_analysis"` | `True` | `llm_url` | ADDONS, STATIC, LLM |
| `as_mop_llm` | `as_mop_llm` | `"static_analysis"` | `True` | `llm_url` | ADDONS, STATIC, MOP, LLM |

Every variant carries `strategy="sata"` and `variant` equal to its own cell name; `default` carries `"base"`.

**What a cell means lives in the jar.** Each preset is the union of the jar's group blocks (the `ape` design's
§ "Group blocks and cells"): ADDONS is the former `aperv` vector, STATIC is the frontier at 200 plus typed input,
MOP is E6 arm 3's MOP configuration plus `p_M = 1.0`, LLM is E6 arm 4's sampling configuration with `p_L = 0.9`.
`overrides` SHALL carry only what the jar cannot know: the server URL. A dose (`llm_percentage`,
`mop_coin_percentage`) or any other mapped key is an ablation, expressed through the tool DSL
(`aperv:as_mop@mop_coin_percentage=0.5`), never as a new variant and never as a new preset. The preset vocabulary
belongs to the jar.

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
- **THEN** its keys SHALL be exactly `default`, `base`, `mop`, `as`, `as_mop`, `as_llm`, `as_mop_llm`
- **AND** `get_variants()["default"] is get_variants()["base"]` SHALL be true
- **AND** none of `sata`, `sata_mop`, `sata_llm`, `sata_mop_llm`, `mop_on_llm_off`, `mop_off_llm_off`,
  `mop_on_llm_70`, `mopd_on_llm_off`, `mopd_on_llm_90` SHALL be a key

#### Scenario: Each cell names its own preset and itself

- **WHEN** any variant `v` other than `default` is read from `get_variants()`
- **THEN** `v["preset"]` SHALL equal its key and `v["variant"]` SHALL equal its key
- **AND** `v["strategy"]` SHALL be `"sata"`

#### Scenario: The base cell carries no data and no overrides

- **WHEN** `get_variants()["base"]` is read
- **THEN** `preset` SHALL be `"base"`, `overrides` SHALL be empty, and no `static_data` key SHALL be present

#### Scenario: Only the LLM cells carry an override

- **WHEN** `get_variants()["as_mop_llm"]` is read
- **THEN** `overrides` SHALL be exactly `{"llm_url": "http://10.0.2.2:30000/v1"}`
- **AND** `get_variants()["as_llm"]["overrides"]` SHALL be the same dict value
- **AND** every other cell's `overrides` SHALL be empty

#### Scenario: Every cell but base carries the static data

- **WHEN** the variants `mop`, `as`, `as_mop`, `as_llm`, `as_mop_llm` are read
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
Overrides Pass-Through"). It SHALL contain only keys the deployed jar accepts (INV-APV-41). The 66
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
with `retired_key`: `mop_target_pick_cap` (`ape.mopTargetPickCap`, subsumed by the MOP coin's first-interaction
rule) and `least_visited_priority_tiebreak` (`ape.leastVisitedPriorityTiebreak`, replaced by the scorer-sum tie X1,
which equals APE with zero scorers). Twelve enter, so the table goes from 56 to 66 entries: the four group keys,
the MOP coin dose, the three LLM gate parameters, and four existing jar keys the table lacked
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
- **AND** the only remaining line SHALL be `ape.llmUrl=http://10.0.2.2:30000/v1`

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
- **THEN** it SHALL contain exactly 66 entries
- **AND** it SHALL contain `addons`, `static`, `mop`, `llm`, `mop_coin_percentage`, `llm_gate_min_actions`,
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
`gateBreaker`, `guardBacks`, `bufAbandoned`, `restarts`, `coinLlm`, `coinMop`, beside the existing `acts`,
`states`, `stampNodes`, `stampHits`, `retired` and `llm`) are the per-run census of the mechanisms the cells mount,
and an analysis of the cells needs them. Owner decision D5 stays in force where it was aimed, on the collection
path. `tool.py` reads no `RUN_END`, and the reader exposes the record without interpreting it: there is no
completeness flag, no "ended normally" property and no derived status (INV-APV-53). A trace without `RUN_END` is a
fact the analysis reports, not something the reader repairs.

The reader SHALL NOT convert between formats in either direction, SHALL NOT write to the trace, and SHALL NOT run on the collection path (INV-APV-48). A malformed record SHALL be skipped and counted rather than aborting the read (INV-APV-50): a trace truncated by a `SIGKILL` ends in a partial line by construction, and losing the whole run's analysis over its last line would be a worse failure than losing the line. `RUN_START` is not guaranteed to be line 1 — AOSP banner lines may precede it — so the reader SHALL take the first `{`-leading line as the candidate header.

**The `ape` changes are the authority for the wire format.** `rearch-04-step-ndjson-telemetry` defines the `StepRecord` schema, the dictionary encoding, the omitted-default rules and the heartbeat payload; `isolate-guidance-groups` defines the members listed above, the meaning of `dec.src` on its jar, `RUN_START.variant` and the new `RUN_END` counters. This reader conforms to them rather than restating them.

The golden fixture that exercises this requirement SHALL be `modules/aperv-tool/tests/fixtures/trace_ndjson_golden.ndjson`, a hand-written stage-4 trace from the `eea2b1a9` jar containing, at minimum: a `RUN_START` with `t0` **and all thirteen of that jar's members**; `ACT` entries with `mop:1` and `mop:0`; two `STATE` entries; a step whose `dec` carries no boost fields at all; a step carrying `patched:0`; a step carrying no `patched` member; a step with two `llm[]` entries in occurrence order; a step whose `out` resolves to a new state; a step closed with no `out` member; a step flushed with `out:{"resolved":false}`; a completed call carrying the `sys` / `user` / `resp` / `tool_calls` dumps beside one that carries none; a step carrying `mopd`, `mops` and `ret`; a `MOP_DATA` record, a `PIPELINE` record whose `candidates` include disabled entries, an `LLM_ACK` and a `RUN_END` with `counters`; a malformed line; and a truncated final line. A second fixture, `trace_ndjson_v3_header.ndjson` (renamed from `trace_ndjson_v2_header.ndjson`, since 2 is now a supported version), SHALL carry `RUN_START` with `v: 3` and one step. A third, `trace_ndjson_groups.ndjson`, SHALL be a trace of the group-isolation jar: a `RUN_START` carrying `v: 2` and `variant: "as_mop_llm"`; an `ACT` without `mop`; a step owned by each of `llm`, `mop`, `restart` and `sata`; a step carrying every member of the table above; a step carrying `dec.own` with `fb` and `g`; and a `RUN_END` carrying the eight new counters. Every scenario below names the fixture element that exercises it, so no rule is asserted against an input that cannot reach it.

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
- **WHEN** the smoke runs `aperv:mop` on an instrumented APK with its `.apk.json`, with the paired jar
- **THEN** the trace's `RUN_START.variant` SHALL be `"mop"`
- **AND** its `features` SHALL equal the fixture's `FUZZING`, `STATIC_DATA`, `MOP`, `WTG`, `MOP_FRONTIER`,
  `MOP_LAUNCHER`, `MOP_ACTIVITY_SOURCE`, `MOP_COIN`, with no `MENU_GATEWAY`
- **AND** its `digest` SHALL equal the fixture's

#### Scenario: A mismatched pair fails at resolution
- **WHEN** a jar that predates the group keys is deployed under this `tool.py` and `aperv:base` runs
- **THEN** the jar SHALL abort before step 1 on the unknown preset `base` or the unknown key `ape.variant`
- **AND** the smoke SHALL report the cell as failed, because no `RUN_START` was recorded

## REMOVED Requirements

### Requirement: ApeRVTool Variants (FR20)

**Reason**: the ten-name variant set it defined is deleted without alias (D-A13). It is replaced by "ApeRVTool Cell Variants (FR20)", which defines one variant per cell. The replacement is a new requirement rather than a modification, because every scenario of this one asserts a name or an arm that no longer exists.

**Migration**: none; the requirement named in the reason is its successor in this delta.

### Requirement: ape.properties Generation

**Reason**: the file it specified no longer has that layout. `ape.variant` is a fixed second line, `ape.mopDataPath` is now `ape.staticDataPath`, and the mapping goes from 56 to 66 entries. It is replaced by "ape.properties Composition". Its scenarios pin the deleted arms and the old line counts, so they cannot be carried over.

**Migration**: none; the requirement named in the reason is its successor in this delta.

### Requirement: Native NDJSON Trace Reader (FR11, FR13, NFR03, NFR06)

**Reason**: two of its normative clauses are reversed by the author's decision of 2026-10-17. `RUN_END` becomes a reader attribute, and `RunStart` has fourteen members. The reader also has to read a second jar generation's decision record. It is replaced by "NDJSON Trace Reader (FR11, FR13, NFR03, NFR06)", which keeps every rule this one had except the `RUN_END` exclusion.

**Migration**: none; the requirement named in the reason is its successor in this delta.

### Requirement: Decisive Run Arm Set (FR20)

**Reason**: the five arms it defined (`mop_on_llm_off`, `mop_off_llm_off`, `mop_on_llm_70`, `mopd_on_llm_off`,
`mopd_on_llm_90`) are deleted with the other variants (D-A13). Their premise is the one the group-isolation change
refutes: the control kept the static-analysis document, the frontier and the MOP-activity tie-break, so "MOP off"
was not free of static or MOP data (plan §2.1). In the cells, MOP-off is the absence of the MOP group, and the
single-factor property of each contrast is a property of the jar's group blocks, checked by "Cell Configuration
Matches the Jar's Cell Echo". INV-APV-29 and INV-APV-30 are retired with it. Deletion is complete, with no alias,
no adapter and no retained constant. `tests/migration/test_decisive_contrasts.py` is backed up to `backup/` and
deleted.

**Migration**: a campaign recorded under these names resumes from its frozen image (`rvandroid:0.9.5`). A new
experiment uses the cells: `as` is the control without specifications, `as_mop` the guidance on the full tool, and
`mop` against `base` the guidance on APE alone.
