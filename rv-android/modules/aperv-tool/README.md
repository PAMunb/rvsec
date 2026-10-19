# aperv-tool

APE-RV tool wrapper for rv-platform integration.

## Overview

aperv-tool wraps the enhanced APE-RV binary (`ape-rv.jar`) as an `AbstractTool` plugin for the rv-platform task execution framework. APE-RV is an enhanced fork of the AOSP Monkey tool that performs model-based UI exploration using the Widget Table Graph (WTG) model with adaptive random testing. This module handles JAR deployment, strategy selection, properties injection, and execution lifecycle on Android emulators.

## Installation

```bash
# Install all rv-android modules (from project root)
uv sync
```

This module is part of the RV-Android uv workspace. All modules are installed in editable mode — source changes are reflected immediately.

## Quick Start

aperv-tool is used through rv-experiment or rv-platform, not directly:

```bash
# Via rv-experiment (recommended); a bare `aperv` runs the `base` cell
uv run rv-experiment run --tools aperv --apks-dir ./apks_examples --timeouts 300

# With a specific cell
uv run rv-experiment run --tools aperv:as_mop --apks-dir ./apks_examples

# Via rv-platform
uv run rv-platform run --tools aperv:as --apks-dir ./apks_examples
```

## Features

- **Strategy selection**: SATA (adaptive random) and random exploration — the two agent types the APE-RV binary implements
- **One variant per experimental cell**: each variant names a jar cell preset, which mounts a union of APE-RV's behaviour groups, so a contrast between two cells is a contrast between group sets
- **MOP-guided exploration**: the `mop`, `as_mop` and `as_mop_llm` cells bias exploration toward screens where monitored operations are reachable, using a compact artifact derived from static analysis
- **LLM-guided exploration**: the `as_llm` and `as_mop_llm` cells integrate with an OpenAI-compatible LLM endpoint for decision guidance
- **JAR deployment**: Resolves `ape-rv.jar` via priority search paths and pushes to the Android device
- **Properties injection**: Generates `ape.properties` naming the cell's jar preset, the cell's own name and its override deltas
- **Timeout-aware execution**: Treats timeout as expected exit behavior for exploration tools, and checks the converse — a run that returned early without timing out did not explore its budget, so it fails instead of reporting success. The exit code is not consulted: APE-RV exits non-zero when the application under test crashes, which is data the run exists to collect

## Variants

APE-RV mounts five behaviour groups by declaration: **BASE** (the APE algorithm), **ADDONS** (the fork's own improvements), **STATIC** (the consumers of the static GUI model), **MOP** (the consumers of the specification targets) and **LLM** (the vision-language model). A **cell** is a union of groups, and the jar ships one preset per cell, each the union of that cell's group blocks. What a group switches on lives in the jar; this module names a cell and supplies only what the jar cannot know: the server URL, the static-analysis artifact, and the variant name the jar echoes into the trace.

Eight names carry seven configurations — the six cells, `default` and the ablation `mop_nolaunch`; `default` is bound to the same object as `base`, because every registered tool must carry a `default` variant.

| Variant | Preset | Groups beside BASE | Static-analysis artifact | Broadcast catalog | Overrides |
|---------|--------|--------------------|--------------------------|-------------------|-----------|
| `default` | `base` | — | No | No | _(none)_ — same object as `base` |
| `base` | `base` | — | No | No | _(none)_ — the APE reference cell |
| `mop` | `mop` | MOP | Yes | No | `mop_coin_ledger_max_interactions: 2` |
| `as` | `as` | ADDONS, STATIC | Yes | Yes | _(none)_ |
| `as_mop` | `as_mop` | ADDONS, STATIC, MOP | Yes | Yes | `mop_coin_ledger_max_interactions: 2` |
| `as_llm` | `as_llm` | ADDONS, STATIC, LLM | Yes | Yes | `llm_url` |
| `as_mop_llm` | `as_mop_llm` | ADDONS, STATIC, MOP, LLM | Yes | Yes | `mop_coin_ledger_max_interactions: 2`, `llm_url` |
| `mop_nolaunch` | `mop` | MOP without the launcher | Yes | No | `mop_coin_ledger_max_interactions: 2`, `activity_trigger_enabled: False` — the MOP launcher and its null-tree recovery are unmounted |

The artifact goes to the device on every cell that mounts STATIC or MOP — every cell except `base` — because those are the groups that read it; `as` reads it with MOP off. The broadcast catalog goes only to the four `as*` cells, because its only reader in the jar is component triggering, a STATIC member. For a new experiment, `as` is the control without specifications, `as_mop` the guidance on the full tool, and `mop` against `base` the guidance on APE alone.

The three cells that mount MOP set `mop_coin_ledger_max_interactions` to 2, so the MOP coin may take each (activity, widget) key twice instead of the jar's default once. The jar's group blocks do not state that key; the default lives here by the author's decision, after the `e03igg2` campaign, where the coin at 2 was the only arm above APE in misuses.

A dose or any other tunable is an ablation through the tool DSL: `--tools aperv:as_mop@mop_coin_percentage=0.5`, or `aperv:as_mop_llm@llm_percentage=0.7`. An ablation that runs in the same containers as its cell needs a name instead, because the platform's resume identity (apk, tool, variant, repetition, timeout) and the result file names leave the parameters out; `mop_nolaunch` (the MOP launcher off) is that variant.

These eight are the only names. The arm names of earlier campaigns (`sata`, `sata_mop`, `sata_llm`, `sata_mop_llm`, `mop_on_llm_off`, `mop_off_llm_off`, `mop_on_llm_70`, `mopd_on_llm_off`, `mopd_on_llm_90`) have no alias in this tree, because they configured presets and keys the paired jar no longer has; resolving one fails with "Invalid variant". Campaigns recorded under them resume from the frozen image `rvandroid:0.9.5`, and their recorded results stay readable.

The cells need the `ape-rv.jar` built from the `ape` change `isolate-guidance-groups` (contract v3.3). A jar that predates the group keys aborts before step 1 on `ape.variant` and on the cell presets, which is the intended guard against a mismatched pair.

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `RVSEC_HOME` | Path to RVSEC installation (for JAR resolution fallback) | No |
| `TOOLS_DIR` | Alternative path for manual JAR placement | No |
| `APERV_LLM_BASE_URL` | LLM endpoint for the `as_llm` and `as_mop_llm` cells, for Docker or non-emulator setups. Read by the `rv-experiment` entry point, not by this module: `configure()` reads no environment. A DSL `@llm_url` wins over it; cells without the LLM group never receive it; `rv-platform run` does not read it | No |

### JAR Resolution Priority

1. Module directory (shipped with the package)
2. `$RVSEC_HOME/ape/target/` (Maven build output)
3. `$TOOLS_DIR/aperv/` (manual placement)

### Properties (ape.properties)

The generated file states the cell and nothing more. For `as_mop_llm`, whose overrides are the coin's ledger budget and the server URL, it is exactly five lines:

```properties
ape.preset=as_mop_llm                                 # always first
ape.variant=as_mop_llm                                # always second; echoed as RUN_START.variant
ape.staticDataPath=/data/local/tmp/mop-artifact.json  # only when the artifact was pushed
ape.mopCoinLedgerMaxInteractions=2                    # one line per override delta, in mapping order
ape.llmUrl=http://10.0.2.2:30000/v1                   # one line per override delta
```

Everything a preset supplies — throttle, epsilon, the group keys, MOP weights and coin, LLM model, dose and timeouts — is resolved inside the jar and is never restated here, so `as_mop` ships a four-line file, `as` a three-line one and `base` a two-line one. Override keys are translated to `ape.*` names through `APERV_PROPERTY_MAPPING` (67 entries; the full table is in [docs/architecture.md](./docs/architecture.md)); the emission walks the mapping rather than the override dict, so two runs of the same cell produce byte-identical properties. The ten top-level keys in `APERV_ORCHESTRATION_KEYS` (`preset`, `variant`, `overrides`, `strategy`, `static_data`, `broadcast_catalog`, `seed`, and the three device-addressing keys `device_port` / `device_serial` / `device_id`) are Python orchestration; `preset` and `variant` reach the device only through their fixed lines, and the rest never do. Any other unmapped key raises `ConfigurationError` before a device is touched — `mop_data` included, since the data key is `static_data`.

The jar must postdate the preset mechanism. An older build treats `ape.preset` as an unknown key and ignores it, and since the file no longer carries what the preset would have supplied, the run silently executes on jar defaults while the results directory still carries the cell's name.

An experiment can add a delta without a new variant using the tool DSL, e.g. `--tools aperv:as_mop@default_epsilon=0.1`.

### Corpus provenance

`corpus_basis` records which application list a run was drawn from, as `<corpus-id>:<sha256>` (e.g. `subset40:b60903ad…d48d4`). It is provenance the caller supplies, not a digest the tool computes: aperv-tool does not own the corpus list and does not read a campaign's filesystem layout to hash it. `configure()` validates the shape before any device interaction, the key is omitted entirely when unstated, and the jar echoes it into the trace's opening record without reading it back — so it changes no behaviour and makes a recorded run answer "which corpus?" from its own artifacts. Usually set through the DSL: `--tools aperv:as_mop@corpus_basis=subset40:<sha256>`.

## Offline analysis

`aperv_tool.analysis` is a read-only library over artifacts a run already produced — no device, no adb, and nothing in the execution path. It lives in the tool package because the thesis experiment consumes it, not only a calibration campaign.

Three of its modules are the stream readers the calibration work started from: `trace_ndjson` (native reader of the stage-4 NDJSON trace), `coverage_dump` (the jar's `UICOV` / `UICOV-ACT` dump) and `clock_logcat_join` (placing `RVSEC` violation lines on the exploration timeline). Around them sits the campaign analysis layer:

- **Layer 0** — `run_identity`, `runspec`, `tasks_record`, `loader`, `liveness`, `gates`, `corpus`, `clones`: which runs exist, which of them count, and what the denominator is
- **Layer 1** — `outcomes`, `screen_visits`: streams into labelled per-unit values under declared conventions
- **Layer 2** — `estimators/`: one estimator per module, every function returning an `Envelope`
- **Layer 3** — `step_bundle`, `state_coverage_join`, `violations`, `monitored_ops`, `static_artifact`, `baseline_ape`, `baseline_droidbot`: parsing the recorded artifacts
- **Layer 4** — `envelope`, `provenance`, `emit`: the result structure, its re-derivability, and the files it becomes
- **`callers/` + `rq_map.toml`** — the only place a research-question identifier appears

Two rules bind the whole library: it names no research question outside `callers/`, and no number leaves it without its estimand, both denominators, its conventions and its exclusions. Every knob the pre-registration is meant to decide — the margin, the corpus, the replica rule, the dedup convention, the GLM offset and reference level, the multiplicity strategy — is a required parameter with no default, and a call that omits one raises instead of choosing.

### Two jar generations in one reader

`trace_ndjson.TraceReader` reads traces with `RUN_START.v` 1 (the `eea2b1a9` jar and earlier) and 2 (the group-isolation jar of the cells), and reports the version as `run_start.v`. It does not translate between them, so the version decides what some fields mean:

- `decision_source` is the stage with the largest boost under `v == 1`, which is not causal, and the owner that executed the step (`budget`, `restart`, `llm`, `launcher`, `mop`, `sata`) under `v == 2`. Counts of it are never pooled across versions.
- The `v == 2` decision record reaches typed `StepRow` fields, each `None` when absent: `owner` (with the coin draws, the gate and the fallback), `scorer_cf`, `draw`, `nav`, `input_source`, `restart_kind`, `back_menu_capped`, `sata_path`, `rotation`, `buffer_abandoned_by`, `component_trigger`, `mop_handler` (the stamped handler, `dec.hnd`), and the boost `nav_frontier` (materialized at `0`). `mop_distance`, `mop_stamp` and `retired_targets` are read on both versions. `counterfactual` (only the MOP boosts zeroed) exists only under `v == 1`.
- `activity_has_mop` is `None` where the jar did not compute it: the `v == 2` jar writes the fact only when MOP is mounted.
- `run_start.variant` names the cell; it is `None` on `v == 1`.
- `reader.run_end` is the `RUN_END` record verbatim, a census of the run's mechanisms (`counters` with `launches`, `coinLlm`, `coinMop`, `restarts`, `nullRelaunches` and the others), beside `mop_data`, `pipeline` and `llm_ack`. The reader derives no status from it, and the collection path never reads it.

Gate 1 (clean control) has two forms. On a legacy `key=value` stream it keeps the anchored pattern `(?<![a-z_])mop=`, which cannot match an NDJSON `"mop":` member. On any NDJSON trace it uses `gates.count_mop_group_signal(reader)`, which on a `v == 2` trace counts the MOP-group members the `ape` side's own clean-control gate lists: MOP boosts, stamps and owners on the step rows, a `mop_coin` or `launcher` pick channel, an `ACT` carrying `mop`, a `UICOV` line carrying `mopReach`, and a non-zero `coinMop`, `launches`, `stampHits` or `retired` in `RUN_END`. On a `v == 1` trace it counts only steps whose `mop` or `mop_frontier` boost fired, the meaning of the legacy rule: that jar's control mounted MOP with zero weights, so the MOP pass wrote its by-products (`mopx`, `wtg`, `mopReach`, `ACT.mop`) in a clean run. `MOP_DATA` never counts: it reports that the artifact was loaded, which `as` and `as_llm` do by design. On a group-isolation campaign the controls are `aperv:base`, `aperv:as` and `aperv:as_llm`.

The end-to-end smoke runs the whole chain over two applications with no device:

```bash
# from the repository root
.venv/bin/python -m pytest modules/aperv-tool/tests/test_smoke_two_apps.py \
    modules/aperv-tool/tests/test_corrupted_fixture.py \
    --import-mode=importlib -o "addopts=" -q
```

Full narrative — the layers, the freeze-item rule, the two fixture classes, and why the activity-visit is the unit: [docs/20260815_gh103_analysis_layer.md](../../docs/20260815_gh103_analysis_layer.md).

## Dependencies

### Internal (rv-android)
- `rv-android-core` - Foundation infrastructure (AbstractTool, Command, Task, App)

aperv-tool does not depend on rv-tools: rv-platform, which depends on both, registers `ApeRVTool` in the `ToolRegistry`. `analysis/step_bundle.py` imports rv-coverage lazily for the opt-in diagnostic stream without declaring it; when rv-coverage is absent, that stream is reported as not read.

### External
- Android SDK (`adb`) - Device interaction via ADB push and shell commands
- `pandas` / `numpy` / `scipy` - the analysis layer's tidy carrier, numerics and estimator stack
- `statsmodels` - the negative-binomial GLM, imported lazily inside `analysis/estimators/count_glm.py` so the stream readers and the collection path do not pay its import cost

## Documentation

- [Architecture](./docs/architecture.md) - Detailed architecture documentation

## Testing

```bash
# From project root
uv run pytest modules/aperv-tool/tests/ -v

# With coverage
uv run pytest modules/aperv-tool/tests/ --cov=modules/aperv-tool/src --cov-report=html
```

## License

Part of the rv-android project.
