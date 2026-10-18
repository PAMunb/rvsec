## Context

The `ape` change `isolate-guidance-groups` changes the contract between APE-RV and this module in four ways at
once (its `design.md` § API Design, contract v3.2, committed in `ape` `16b185f4`, with D-B13 and D-B14; see D16):

- The keys. There are four group keys and one data root. `ape.mopDataPath` is renamed `ape.staticDataPath`.
  Three keys are retired. Four member keys are new. `ape.variant` is echoed as `RUN_START.variant`.
- The presets. The six cell presets `base`, `mop`, `as`, `as_mop`, `as_llm`, `as_mop_llm` replace `aperv`, `mop`,
  `llm` and `llm_mop`.
- The artifact. Component triggering becomes a STATIC member, and it needs each intent filter's `data`.
- The telemetry. `dec.src` becomes the step's owner, twelve `dec` members are new (`own`, `cfc`, `draw`, `nav`,
  `inp`, `restart`, `bmc`, `strat`, `rot`, `buf`, the scorer field `navf`, and `trig`), `dec.cf` and `dec.wtgsrc`
  are removed, and eight `RUN_END` counters are new.

The current module state, read for this design:

- **Variants**: `get_variants()` (`modules/aperv-tool/src/aperv_tool/tools/aperv/tool.py:329-541`) defines ten
  names. They carry nine configurations. `default` and `sata` share one object (`:355-365`).
- **Validation**: `configure()` (`tool.py:543-660`) validates the strategy, the preset and the shape of
  `overrides`. It folds mapped top-level DSL keys into `overrides` (`:608-610`), rejects unknown top-level keys
  against `APERV_ORCHESTRATION_KEYS` (`:127-138`, `:615-621`), and rejects unmapped override keys
  (`:630-635`).
- **Mapping**: `APERV_PROPERTY_MAPPING` (`tool.py:143-231`) has 56 entries.
- **Push sequence**: `execute_tool_specific_logic` (`tool.py:1259`) does the following, in order:
  - pushes the jar (`:1294-1297`);
  - pushes `system-broadcast.json` whenever the file exists (`:1302-1311`);
  - derives and pushes the artifact when `mop_data == "static_analysis"` (`:1324-1342`);
  - pushes `ape.properties` (`_push_properties`, `:912-970`): `ape.preset` first, then `ape.mopDataPath`, then the
    overrides in mapping order.
- **Variant name**: no `ape.*` property and no CLI argument carries it.
- **Derive**: `_project_components` (`derive_mop_artifact.py:1404-1444`) projects every component entry. It does
  not filter on `reachesTarget`, which it renames `reachesMop` (`:1486`). Each receiver and service intent filter
  is reduced to `actions` and `categories` (`:1497-1503`). The producer's `data` block has seven lists (`schemes`,
  `hosts`, `ports`, `paths`, `pathPrefixes`, `pathPatterns`, `mimeTypes`). Only the activities' `deepLinkUri`
  reads it (`:1363-1394`).
- **Reader**: `trace_ndjson.py` parses `RUN_START` into a 13-member `RunStart` (`:167-233`). It parses each step
  in `_build_step_row` (`:947-1034`):
  - it reads `dec.a`, `src`, `ch`, `pri`, six boosts, `wtgsrc`, `mopx`, `patched`, `cf` and `comp`;
  - it drops `mopd`, `mops` and `ret`, which the jar writes (`StepRecord.java:279-296`);
  - it skips `RUN_END` by design (`:84-89`, `:830-836`);
  - it describes `decision_source` as "the pipeline stage that selected the action" (`:417`);
  - it describes `Counterfactual` as evidence "that the guidance changed anything" (`:359-366`), without saying
    that it zeroes only the MOP boosts.
- **Reader consumers**: `clock_logcat_join`, `step_bundle`, `screen_visits`, `state_coverage_join`, `runspec`, and
  the two baseline parsers. The baseline parsers derive their column list from `fields(StepRow)`
  (`baseline_ape.py:82-84`) and write every field explicitly (`baseline_ape.py:304-330`, `baseline_droidbot.py`
  ~`:200-230`).
- **Migration checks**: the `tests/migration` package (skipped without `$APE_REPO`) parses the jar's `Presets.java`
  and `KeyOwnership.java` from the `ape` checkout. It pins four presets at sizes 17/21/24/28
  (`test_jar_tables.py:38`), sweeps the mapping against the jar's vocabulary (`test_mapping_sweep.py`), and checks
  the decisive arms' single-factor contrasts (`test_decisive_contrasts.py`).
- **The jar**: `ape-rv.jar` is absent from this worktree. It is gitignored (`tools/aperv/.gitignore:3`) and put
  there by `mvn install -Drvsec_home=…` in the `ape` repository.
- **Variant-name references outside the module**: none in production code. `rv-platform`'s registration does not
  name a variant, and `ToolFactory` resolves `default` when no variant is given
  (`rv-tools/.../registry/factory.py:112-120`).

Requirements: FR19, FR20, FR11, FR04/FR06, NFR06 (`docs/PRD.md`).

## Architecture

```
            ape repo (branch isolate-guidance-groups)                 rv-android (this change)
  ┌───────────────────────────────────────────────┐      ┌──────────────────────────────────────────────┐
  │ Presets.java: base mop as as_mop as_llm as_mop_llm ◄──┤ get_variants(): preset = variant = cell       │
  │ KeyOwnership: group keys, staticDataPath,    ◄─────────┤ APERV_PROPERTY_MAPPING (66)                   │
  │   variant, retired keys                      │      │ _push_properties():                            │
  │                                              │      │   ape.preset / ape.variant / ape.staticDataPath│
  │ StaticArtifactLoader ◄── mop-artifact.json ◄───────────┤ derive_mop_artifact: + intentFilters[].data   │
  │ COMPONENT_TRIGGER ◄──── system-broadcast.json ◄────────┤ push iff broadcast_catalog                     │
  │ NdjsonSink / RunSpecEcho ──── trace ──────────────────►│ TraceReader: owner, cfc, …, run_end, variant  │
  │ src/test/resources/cells/<cell>.run_start.json ───────►│ cell gate (tests/migration + smoke)           │
  └───────────────────────────────────────────────┘      └──────────────────────────────────────────────┘
```

### Key Components

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| `ApeRVTool.get_variants()` | The eight names, seven configurations (six cells, `default`, `mop_k2`) | — | `Dict[str, dict]` |
| `ApeRVTool.configure()` | Validate, fold DSL keys, reject `mop_data` and unknown keys | merged variant config | `self._tool_config` |
| `ApeRVTool._push_properties()` | Write the fixed lines, then the overrides | `_tool_config`, artifact flag | `/data/local/tmp/ape.properties` |
| `ApeRVTool.execute_tool_specific_logic()` | Push the catalog iff `broadcast_catalog`, the artifact iff `static_data` | task, app | trace file |
| `derive_mop_artifact._project_component()` | Add the reduced `data` member to each filter | component entry | wire projection |
| `trace_ndjson.TraceReader` | New `StepRow` fields, `RunStart.variant`, `run_end` | NDJSON trace | `StepRow`s, attributes |
| `baseline_ape` / `baseline_droidbot` row builders | Write `None` for each new column | baseline stream | tidy frame rows |
| `tests/migration/test_cells.py` (new) | Offline cell gate against the jar source and fixtures | `$APE_REPO` | pass / fail |
| `gates.count_mop_group_signal()` (new) | Gate 1 over NDJSON: on `v == 2` the INV-SNK-18 list (step members, `ACT.mop`, `UICOV mopReach`, MOP counters of `RUN_END`); on `v == 1` the fired MOP boosts | `TraceReader`, `coverage_dump` rows | count |
| `runspec.attribution_evidence()` | Adds the `variant` check (`not-run` on `v == 1`) | `RunStart`, manifest arm | verdicts |
| `screen_visits` / `step_bundle` | Version-tagged source counts, tri-state MOP fact | `StepRow`s | visits, frames |
| `coverage_dump._parse_state_line()` | `mop_reach` optional; absence is not partial | `UICOV` payload | `StateCoverage` |
| `rv-experiment` `__main__` tool-config resolution | Inject `APERV_LLM_BASE_URL` as `llm_url` into the `aperv` LLM cells' `ToolConfig.parameters` | environment, `ToolRegistry` variants, parsed `ToolConfig`s | `ToolConfig.parameters` |

## Mapping: Spec → Implementation → Test

| Requirement / invariant | Implementation | Test |
|---|---|---|
| ApeRVTool Cell Variants; INV-APV-05, -38, -40, -65, -66 | `tool.py` `get_variants()` | `test_aperv_tool.py::TestVariants` (rewritten) |
| ApeRVTool Configuration; INV-APV-39 | `tool.py` `configure()`, `APERV_ORCHESTRATION_KEYS` | `TestConfigure`, `TestDslOverrideFold` |
| ApeRVTool Execution Flow; INV-APV-06, -10, -45 | `tool.py` `execute_tool_specific_logic()` | `TestExecuteMopArtifactFlow`, new `TestBroadcastCatalogPush` |
| ape.properties Composition; INV-APV-08, -41 | `tool.py` `_push_properties()`, `APERV_PROPERTY_MAPPING` | `TestPushProperties`, `TestPropertyMapping` |
| Arm Property Overrides Pass-Through | mapping sweep | `tests/migration/test_mapping_sweep.py` |
| MOP Artifact Projection Contents (item 7) | `derive_mop_artifact._project_component()` | `test_derive_mop_artifact.py` (two new scenarios) |
| Derived MOP Artifact Generation and Caching | unchanged code | existing tests, scenario renamed only |
| Corpus Basis Provenance | unchanged code | `TestCorpusBasis` (variant names in fixtures) |
| NDJSON Trace Reader; INV-APV-49, -53, -58, -61, -67 | `trace_ndjson.py` | `test_trace_ndjson.py` + new `trace_ndjson_groups.ndjson` |
| Cell Configuration Matches the Jar's Cell Echo | `tests/migration/test_cells.py`; smoke comparison script | the test itself; smoke report |
| Validity Gates Run Before Any Outcome; INV-CAN-07 | `gates.py` `count_mop_group_signal`, gate 1 selection; `runspec.py` variant check | `test_gates.py`, `test_runspec.py` |
| Analysis Consumers Follow the Trace Version; INV-CAN-21, -22 | `screen_visits.py`, `step_bundle.py`, `runspec.py`, baselines | `test_screen_visits.py`, `test_step_bundle.py`, `test_baseline_frames.py` |
| Offline Coverage-Dump Parser at Activity Grain | `coverage_dump.py`, `state_coverage_join.py` | `test_coverage_dump.py`, `test_state_coverage_join.py` |
| ApeRVTool Configuration (LLM URL scenario); INV-APV-09; experiment "aperv LLM URL Resolved at the Entry Point", Layer-Purity Audit | `rv-experiment/__main__.py`, `rv_android_core.constants.ENV_APERV_LLM_BASE_URL` | new `rv-experiment/tests/test_cli_aperv_llm_url.py`; `rv-android-core/tests/test_constants_registry.py` (name rule, INV-CORE-30); `test_aperv_tool.py` (L2 still ignores the variable) |
| Decisive Run Arm Set (removed) | delete `tests/migration/test_decisive_contrasts.py` | `TestDecisiveRunArms`, `TestDistanceArms` deleted |

## Goals / Non-Goals

**Goals:**
- Make `aperv-tool` drive the six cells of the `ape` change exactly, with no Python restatement of what a group
  mounts.
- Read every decision member the new jar writes, without losing anything the `eea2b1a9` traces carry.
- Make a mismatched jar/tool pair fail loudly, and give the smoke a cell-by-cell check.

**Non-Goals:**
- Any change to rv-platform or rv-tools. `default` survives, so INV-TOOL-02 holds. The one change outside
  `aperv-tool` is the `APERV_LLM_BASE_URL` read in `rv-experiment`, its constant in `rv-android-core` and that
  constant's admission in the core name test (D14).
- Migrating finished-campaign files: compose files, `scripts/`, `experimento-*/`, `tests/migration/retirements.py`
  and the gh95 migration record. They describe recorded runs.
- Changing what the analysis modules compute. `screen_visits` keeps counting `decision_source`. Its meaning per
  jar is documented in the reader, not re-derived there. It does not count `input_source` (D15).
- The mini experiment. It belongs to the replication package, under its own track.

## Decisions

**D1 — `default` is the same object as `base`** (author, 2026-10-17). Every registered tool must carry `default`
(INV-TOOL-02), and `ToolFactory` resolves a bare `aperv` to it. The binding follows the precedent of
`default`/`sata`. A bare `aperv` runs the APE reference cell, and its trace says `variant: "base"`, so nothing
is hidden.
- Alternative: an exception in INV-TOOL-02. Rejected by the author, because it touches `rv-tools` for one tool.

**D2 — `static_data` replaces `mop_data`** (author, 2026-10-17). This is the reason of `ape` D-B2 applied to the
Python key. The value stays `"static_analysis"`. The old key is removed from `APERV_ORCHESTRATION_KEYS`, so a YAML
or DSL that still names it fails in `configure()` (P3, no alias). `TraceReader.mop_data` is a different thing:
the accessor of the jar's `MOP_DATA` record. It keeps its name, because the jar keeps the record's name.

**D3 — `variant` is a top-level orchestration key, written as a fixed line.** `ToolFactory` passes only the
variant's config to `configure()`, not its name (`factory.py:127`), so the name has to live in the config. A
mapped override would let any DSL parameter relabel a run. A fixed line keeps the echo honest, with the cell name
declared next to the preset, and costs one key.
- Alternative: derive it from `preset`. Rejected, because the two are equal today by construction, and the jar
  keeps them separate on purpose (the variant is outside the digest).

**D4 — `broadcast_catalog` is a top-level orchestration key on the four `as*` cells.** The catalog's only reader
is `COMPONENT_TRIGGER`, which is a STATIC member (`ape` D-B13). The Python side does not know what a preset mounts,
and it must not branch on preset names. The flag states, on the variant, the one deployment fact the push needs.
- Alternative: push whenever the artifact is pushed. Rejected, because the `mop` cell would receive a catalog
  that nothing reads.
- Alternative: push iff `component_percentage > 0` in `overrides`. Rejected, because the dose comes from the
  preset, so no cell carries it.

**D5 — The reduced `data` member keeps five lists** (contract v3.2, `ape` D-B14). They are `schemes`, `hosts`,
`paths`, `pathPrefixes` and `mimeTypes`. The jar builds one intent from the first scheme, host and MIME type of the
filter that supplied the action, with `paths[0]`, or `pathPrefixes[0]` when there is no path. `ports` and
`pathPatterns` would be wire bytes that nothing reads, and a pattern is not a literal path. Empty lists are
omitted, and `data` is omitted when all five are empty, which keeps the artifacts of applications without data
filters byte-identical to today's.

**D6 — New `StepRow` fields are typed, absent when absent.** Each member gets a field named for its function
(`owner`, `sata_path`, `rotation`, …), not its wire key. `own` and `nav` become two small frozen dataclasses,
`Ownership` and `NavTie`. The others are scalars, tuples or a mapping. `navf` joins the boost fields and is
materialized at 0. All the others stay `None` when absent, because an `eea2b1a9` trace carries none of them, and a
default would claim that a mechanism ran (INV-APV-49). Enumerated values are carried as written, not validated
against a closed set.
- Alternative: one `decision: Mapping` holding the raw `dec`. Rejected, because consumers would re-parse the wire
  format, which is what the reader exists to prevent.

**D7 — `counterfactual` and `wtg_source` stay.** They carry the `eea2b1a9` jar's `dec.cf` and `dec.wtgsrc`. The
reader still reads those traces, and INV-APV-58 forbids dropping what a trace carries. On the new jar they are
`None`. Their docstrings say which jar writes them.

**D8 — `run_end` is a verbatim attribute** (author, 2026-10-17). It is shaped like `mop_data`, `pipeline` and
`llm_ack`: the record minus `type`, or `None`. The reader derives no property from it. `tool.py` still never reads
it, and the collection-path test that forbids it stays.

**D9 — The cell gate has two levels.** Offline: `tests/migration/test_cells.py` reads the `ape` checkout's
`Presets.java` and `src/test/resources/cells/*.run_start.json` through `$APE_REPO`, and asserts the preset names,
the block unions, and each fixture's `preset`/`variant` against `get_variants()`. On the device: the smoke, the short pre-run of a comparison
mini-experiment on instrumented corpus APKs, compares each recorded `RUN_START` with its fixture through `TraceReader`, masking
`run_id`, `t0`, `seed`, `build` and `props_digest`. Neither level runs in `tool.py` (INV-APV-43).

**D11 — The reader accepts versions 1 and 2, and `activity_has_mop` becomes tri-state** (contract v3.2).
`RunSpecEcho.FORMAT_VERSION` moves to 2 on the group-isolation jar because `dec.src` changes meaning.
`FORMAT_VERSION = 1` becomes `SUPPORTED_VERSIONS = {1, 2}`. Strict mode keeps rejecting any other version, and
`trace_ndjson_v2_header.ndjson` becomes `trace_ndjson_v3_header.ndjson`. The jar writes `ACT.mop` only with MOP
mounted, so `_absorb_typed_record` stores `record.get("mop")` and resolves a missing value to `None` instead of
`bool(0)` (`trace_ndjson.py:806-810`). `StepRow.activity_has_mop` and `StepOutcome.target_activity_has_mop`
become `Optional[bool]`. Their consumers (`screen_visits`, `step_bundle`) carry the value through, and a consumer
that tests truthiness treats `None` as not-MOP, which is what it does with `False` today.

**D12 — Gate 1 has two forms, selected by the trace's format.** The anchored pattern `(?<![a-z_])mop=`
(`gates.py:83`) was written for the `key=value` lines, and it matches no NDJSON `"mop":` member, so on every
stage-4 trace it counted zero. Rather than a second regex over JSON text, the NDJSON form reads the trace through
`TraceReader` (one parser, INV-APV-48). On a `v == 2` trace it applies the `ape` side's own clean-control list,
INV-SNK-18 (author's decision, 2026-10-17). Over the `StepRow`s it counts a row carrying a MOP scorer, a MOP stamp member, `own.uM`, a
MOP key of `cfc`, `nav.c == "mop"`, a `pick_channel` of `mop_coin` or `launcher`, or an owner `mop` or `launcher`.
It also counts a row whose `activity_has_mop` or `target_activity_has_mop` is not `None`, a `UICOV` line carrying
`mopReach`, and a `RUN_END` whose `coinMop`, `launches`, `stampHits` or `retired` counter is non-zero. The
group-isolation jar writes each of these only with MOP mounted (D-B14.9, D-B14.21). On a `v == 1` trace the list is
the legacy one (author's decision, 2026-10-17): a step counts when its `mop` or `mop_frontier` boost is non-zero,
and nothing else counts. That jar's control mounted MOP with the weights zeroed, so the MOP pass wrote its
by-products in a clean run; a recorded cmp162 control of 73 steps carries `mopx` on all 73, a non-zero `wtg` on
1 and `mopReach` on every `UICOV` line, and no MOP boost. The full list gives it 80, the legacy one 0. `MOP_DATA`
never counts, because it reports the artifact load, which the STATIC
cells do by design. Which arms are controls stays a caller parameter.
- Alternative: an unanchored JSON-key regex. Rejected, because it would match `MOP_DATA` and the `v == 1` `ACT.mop`
  and need its own anchoring rules, which is the defect class INV-CAN-07 exists for.
- Alternative: leave `ACT` and `RUN_END` out, as the first version of this design did. Rejected by the author: on
  the new jar both are written only by the MOP group, and the `ape` gate counts them.

**D13 — `mop_reach` is optional** (contract v3.2, `ape` D-B14.21). The new jar writes `mopReach` only with MOP mounted. Today
`coverage_dump.py:300` subscripts it, so every `UICOV` line of `base`, `as` and `as_llm` would parse as incomplete
and every dump would read `PARTIAL`. The field becomes `Optional[int]`, and only a missing required field or a
truncation makes a line incomplete.

**D14 — `APERV_LLM_BASE_URL` is read at the entry point** (author's decision, 2026-10-17). The variable is
documented in the module's README, architecture doc and spec, and no code reads it. gh41 read it in `configure()`;
gh55 removed that read for layer purity (INV-TOOL-20) and stated that L5 would propagate it, and no L5 read was
ever written. No compose file, script or campaign sets it, so no recorded run depended on it. The read moves to
where `RV_HUMANOID_URL` is already read (`rv-experiment/__main__.py`, INV-EXP-30): for each parsed `ToolConfig`
named `aperv` whose variant, looked up in `ToolRegistry`, carries `overrides.llm_url`, and whose DSL parameters do
not set `llm_url`, `parameters["llm_url"]` is set to the variable's value. `configure()`'s existing DSL fold
(INV-APV-39) then moves it into `overrides`, so `aperv-tool` gains no code path. Precedence: DSL `@llm_url` >
variable > the cell's default, the CLI > env > default order of INV-EXP-32 with the DSL in the CLI's place. Cells
without the LLM group never receive `llm_url`, because a URL there would write an `ape.llmUrl` line for a group
that is not mounted. The name stays `APERV_LLM_BASE_URL`, the one the docs advertise, although the entry-point
rule speaks of `RV_*` variables; the experiment delta names it as that rule's one exception (author's decision).
The core registry's name test (`rv-android-core/tests/test_constants_registry.py`, INV-CORE-30) pins every `ENV_*`
value to `RV_*` or one of the three installation paths, so its pattern admits `APERV_LLM_BASE_URL` as the same one
exception, and nothing wider.
`rv-platform run` does not read it, as it does not read `RV_HUMANOID_URL`.
- Alternative: read it in `configure()`. Rejected: INV-TOOL-20 and the lint forbid environment reads in
  `aperv-tool`.
- Alternative: delete the variable from the docs and keep only `@llm_url`. Rejected by the author.

**D15 — `screen_visits` does not count the input origin** (author's decision, 2026-10-17). `dec.inp` folds two
facts into one value: why the field was filled (`llm` when an LLM decision landed on an input widget, `form` in a
form-completion context) and which generator wrote the text (`typed`, `heuristic`, `random`), with `llm` > `form`
> the generator. The LLM never writes the text (`ApeAgent.checkInput`). A per-visit count would hide the generator
on the form and LLM fills, which is where typed input matters most. The reader keeps `StepRow.input_source` per
step, and a caller that needs it reads the rows.

**D16 — The change follows contract v3.2** (author, 2026-10-17). The `ape` verification of 2026-10-17
(`16b185f4`) revised the telemetry over v3.1 and left the keys and the group blocks unchanged, so fronts T, E and
D are untouched. On this side it means:
- `features` names `MOP_LAUNCHER` where v3.1 named `ACTIVITY_TRIGGER` (key `ape.activityTriggerEnabled` unchanged);
  the cell gate expects the new name.
- `dec.trig` is new: `{"k": "broadcast"|"service"|"provider", "c": "<class>"}`, written on the step during which
  component triggering fired, whatever the owner. It is a side effect, never an owner. The reader carries it as
  `StepRow.component_trigger`. `dec.comp` stays the launcher's activity-launch outcome.
- `dec.ch` drops `short_circuit_*` and gains `mop_coin`, `budget` and `restart`; `launcher`, `llm` and
  `sata_other` stay. The reader carries the value as written in `pick_channel`.
- `dec.nav.alt` is 1 only when the MOP variant decided by its own rule (D-B14.8), so it is 0 on every cell without
  MOP and always 0 at X1. `dec.nav` is written only when the point had at least two candidates.
- A step makes at most one LLM call, and `own.trg` names the stage that made it. `own.i` also takes the guard
  owners `budget` and `restart`. `own.fb` never takes `coin`: a lost coin claims nothing.
- Every step record carries `src`, `ch` and `own` (`ape` INV-SEL-05), which closes the question of a record
  without `dec`.

Contract v3.3 (the `ape` amendment after the `e03igg` comparison, 2026-10-18) adds four things on this side and
leaves the group blocks, the cells and the meaning of `dec.mopx` unchanged:
- one `MOP_COIN` key, `ape.mopCoinLedgerMaxInteractions` (int, jar default 1, values below 1 read as 1): how many
  times the MOP coin may take one (activity, widget) key. No group block sets it. The mapping gains it as
  `mop_coin_ledger_max_interactions`, and the retired `ape.mopTargetPickCap` now names it as its replacement;
- `dec.hnd`, the binary class name of the handler stamp behind the weight, written exactly when `dec.mops` is
  `"s"`. It is a MOP member, so INV-SNK-18 lists it, the reader carries it as `StepRow.mop_handler`, and gate 1
  counts it on `v == 2`;
- the value `screenshot` of `dec.own.fb`, for an LLM step whose screenshot could not be captured. The reader
  carries enumerated values as written, so only its documentation changes;
- the counter `RUN_END.counters.nullRelaunches`, written in every cell and 0 without `MOP_LAUNCHER`. The reader
  exposes `RUN_END` verbatim, so nothing parses it; gate 1 does not count it, because INV-SNK-18 does not list it.

The digest of the three MOP fixtures changes with v3.3 even at k = 1, because it hashes every plan value,
defaults included. The fixtures are regenerated on the `ape` side and the migration tier is re-run against them.

**D17 — `mop_k2` is a named ablation variant** (author's decision, 2026-10-18). The `e03igg` round contrasts
`mop_k2` with `mop`: the same cell, with the MOP coin allowed two picks per (activity, widget) key instead of
one. The DSL form `aperv:mop@mop_coin_ledger_max_interactions=2` cannot run beside `aperv:mop` in one campaign,
because the platform's resume identity is `(apk, tool, variant, repetition, timeout)` without the parameters
(`rv-platform/platform.py:319-327`), and the result file names use the same fields. The second arm would be
skipped as already completed or would overwrite the first. So the ablation gets its own name. It is the `mop`
cell's dict with `variant="mop_k2"` and `overrides={"mop_coin_ledger_max_interactions": 2}`, and nothing else.
The preset stays `mop`, because the jar ships no `mop_k2` preset and the preset vocabulary belongs to the jar. The
cell gate checks it against `cells/mop.run_start.json` with `variant` and the one `params` entry set apart and
the digest not compared, the same scheme as the smoke's `as_mop_llm@llm_gate_min_actions=0` run.
- Alternative: keep the DSL and run the two arms in separate containers or campaigns. Rejected: the round runs
  both arms in the same containers, which is what the named variant allows.
- Alternative: make the platform's resume identity include the parameters. Rejected: it touches `rv-platform`
  for one contrast, and it would change the identity of every recorded campaign.
- Alternative: a fixture of its own on the `ape` side. Rejected by the author: a fixture per ablation leaves the
  six-cell design.

**D10 — `test_jar_tables.py` re-pins the presets.** The parser in `jar_tables.py` reads `Presets.java` with
regular expressions. The new file composes cells from group blocks, so the parser has to read that composition, or
the test resolves each cell through the jar's own preset table if `Presets.java` exposes one. Either way, the
pinned sizes change from four presets to six cells. The exact parse is settled against the file the `ape` wave 0
writes, not guessed here.

## API Design

### Variants (`tool.py`)

```python
LLM_URL_DEFAULT = "http://10.0.2.2:30000/v1"

def get_variants(cls) -> Dict[str, Dict[str, Any]]:
    base = {"preset": "base", "variant": "base", "strategy": "sata", "overrides": {}}
    def cell(name, *, llm=False):
        return {
            "preset": name, "variant": name, "strategy": "sata",
            "static_data": "static_analysis",
            **({"broadcast_catalog": True} if name.startswith("as") else {}),
            "overrides": {"llm_url": LLM_URL_DEFAULT} if llm else {},
        }
    return {"default": base, "base": base, "mop": cell("mop"), "as": cell("as"), "as_mop": cell("as_mop"),
            "as_llm": cell("as_llm", llm=True), "as_mop_llm": cell("as_mop_llm", llm=True),
            "mop_k2": {**cell("mop"), "variant": "mop_k2",
                       "overrides": {"mop_coin_ledger_max_interactions": 2}}}
```

The sketch shows the shape, not the final code: the implementation may spell the six dicts out if that reads
better (P1). `broadcast_catalog` is set per cell in the final code, not derived from a name prefix.

`APERV_ORCHESTRATION_KEYS` = `preset`, `variant`, `overrides`, `strategy`, `static_data`, `broadcast_catalog`,
`seed`, `device_port`, `device_serial`, `device_id`.

### `_push_properties()`

Lines, in order: `ape.preset=<preset>`, `ape.variant=<variant>`, `ape.staticDataPath=<DEVICE_ARTIFACT_PATH>`
(only when the artifact was pushed), then one line per `overrides` entry in `APERV_PROPERTY_MAPPING` order, with
bools lowercased. `DEVICE_ARTIFACT_PATH` stays `/data/local/tmp/mop-artifact.json`.

### `_project_component()` (derive)

```python
def _reduce_filter_data(data: Any) -> dict | None:
    """schemes/hosts/paths/pathPrefixes/mimeTypes as string lists, empty lists omitted; None when all are empty."""
```

Each receiver and service filter becomes `{"actions": […], "categories": […], "data"?: {schemes?, hosts?, paths?,
pathPrefixes?, mimeTypes?}}`.

### Reader types (`trace_ndjson.py`)

```python
@dataclass(frozen=True)
class Ownership:
    intended: str                 # own.i: budget | restart | llm | launcher | mop | sata
    trigger: Optional[str]        # own.trg: the LLM stage that made the step's one call: new_state | stagnation | coin
    u_llm: Optional[float]        # own.uL, only when LLM is mounted
    u_mop: Optional[float]        # own.uM, only when MOP is mounted
    gate: Optional[str]           # own.g: min_actions | breaker
    fallback: Optional[str]       # own.fb: gate | screenshot | error | decline | no_match | ineligible

@dataclass(frozen=True)
class NavTie:
    point: str                    # nav.x: X1 | X3 | X4
    component: str                # nav.c: ape | mop
    alternative: bool             # nav.alt: the MOP variant decided by its own rule (D-B14.8)
    drew: bool                    # nav.drew

@dataclass(frozen=True)
class ComponentTrigger:
    kind: str                     # trig.k: broadcast | service | provider
    component_class: str          # trig.c
```

New `StepRow` fields (sixteen): `owner: Optional[Ownership]`, `scorer_cf: Optional[Mapping[str, bool]]`,
`draw: Optional[Tuple[int, int]]`, `nav: Optional[NavTie]`, `input_source: Optional[str]`,
`restart_kind: Optional[str]`, `back_menu_capped: Optional[int]`, `sata_path: Optional[str]`,
`rotation: Optional[int]`, `buffer_abandoned_by: Optional[str]`, `component_trigger: Optional[ComponentTrigger]`,
`nav_frontier: int = 0`, `mop_distance: Optional[int]`, `mop_stamp: Optional[str]`,
`retired_targets: Optional[Tuple[int, ...]]`, `mop_handler: Optional[str]`.
`RunStart.variant: Optional[str]`. `TraceReader.run_end -> Optional[Dict[str, Any]]`.

A wrongly shaped member (for example, `own` that is not an object, or `draw` that is not a pair) makes the record
malformed, as a wrongly shaped `cf` does today (`trace_ndjson.py:988-995`). An unknown enumerated value does not.

## Data Flow

1. `ToolFactory` merges the variant dict with the DSL parameters. `configure()` validates them, folds the mapped
   keys into `overrides`, and stores `_tool_config`.
2. `execute_tool_specific_logic()` pushes the jar. It pushes the catalog if `broadcast_catalog` is set. It derives
   and pushes the artifact if `static_data` is set; the derive now carries `intentFilters[].data`. Then it writes
   the properties: preset, variant, staticDataPath, overrides.
3. The jar resolves the cell, echoes `RUN_START` with `variant`, and writes the step records with the owner
   record.
4. Offline, `TraceReader` yields `StepRow`s with the new fields and exposes `run_start.variant` and `run_end`. The
   baseline frames carry the same columns, filled with `None`.

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| `ConfigurationError` naming `variant` | `configure()`, variant config without it | fail before any push | declare `variant` |
| `ConfigurationError` naming `mop_data` | old YAML / DSL | fail before any push | rename to `static_data` |
| `RVToolExecutionError` | data cell without `<apk>.apk.json`, or a derive failure | fail the task (INV-APV-45) | run static analysis first |
| jar abort `retired_key` / unknown key | old `tool.py` with the new jar, or the reverse | visible in the trace before step 1 | deploy the paired jar (§9.3) |
| malformed record | wrongly shaped new `dec` member | skip and count (INV-APV-50) | — |

## Risks / Trade-offs

- [The jar is absent from the worktree, and the paired jar exists only after the `ape` wave 2] → every
  device-facing task is blocked on it. The unit tests do not need the jar. The migration tests need only the `ape`
  checkout.
- [Adding `StepRow` fields changes the baseline frame columns] → the baseline parsers derive the column list from
  `fields(StepRow)`, and `test_baseline_frames.py` asserts parity, so a missing `None` fails a test, not an
  analysis.
- [`decision_source` counts mix meanings across jars] → documented on the field (INV-APV-67). `RUN_START.v` (1 or
  2) separates the jars.
- [The cell gate depends on the `ape` fixtures' masking] → the masked members are listed in the requirement. A
  fixture that changes masking breaks the gate visibly.
- [The deleted names still appear in finished-campaign compose files] → those files are records. Running one with
  this tree fails in `ToolFactory` with "Invalid variant", which is the intended outcome.

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Unit | variants, configure, properties lines, mapping, broadcast push | `test_aperv_tool.py` with mocked adb | ~35 changed or new |
| Unit | derive `data` member, all components projected | `test_derive_mop_artifact.py` | 3 new |
| Unit | reader: new fields, eea2b1a9 absence, `run_end`, `variant`, unknown enum | `test_trace_ndjson.py` + `trace_ndjson_groups.ndjson` | ~10 new or changed |
| Unit | baseline frames carry the new columns as `None` | `test_baseline_frames.py` | existing parity test |
| Migration | presets = cells, block unions, fixtures vs variants, mapping sweep | `tests/migration/*` with `$APE_REPO` | ~8 |
| Smoke | cells run by the mini-experiment pre-run, `RUN_START` vs fixture | container `rv-experiment run` with the jar and `aperv_tool` sources bind-mounted, the platform manages the emulator; gates run from the host | a few APKs × cells |

The smoke runs before lint, verification and review.

## Open Questions

- **The device file name `mop-artifact.json`** (not decided): the jar reads the path from `ape.staticDataPath`,
  so the name is cosmetic. Renaming it would touch `derive_mop_artifact.DEVICE_ARTIFACT_PATH` and the `ape`
  fixtures for no behavioural gain. It is left as is.
