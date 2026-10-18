# aperv-tool - CLAUDE.md

## Overview

rv-platform plugin that wraps the APE-RV binary (`ape-rv.jar`) as an `AbstractTool`. Manages JAR deployment, `ape.properties` injection, and command execution on the Android emulator via `app_process`. (APE-RV internals live in the `ape` repository, a sibling of `rvsec/` — `../../ape` from the rv-android root — which has its own CLAUDE.md.)

```bash
uv run rv-experiment run --tools aperv:as_mop --specification-set jca_android   # ADDONS + STATIC + MOP cell
```

(uv sync / editable install, pytest, and the general `rv-experiment run` form are documented in the top-level module CLAUDE.md.)

## Files

| File | Purpose |
|------|---------|
| `src/aperv_tool/tools/aperv/tool.py` | `ApeRVTool`: JAR resolution, device push, MOP artifact derivation + digest cache, `ape.properties` generation, command building, execution |
| `src/aperv_tool/tools/aperv/derive_mop_artifact.py` | **Single authority** for the MOP substrate's parse-time semantics (gh96). `derive(document) -> dict` + `serialize_canonical(artifact) -> bytes`, both pure |
| `src/aperv_tool/analysis/trace_ndjson.py` | `TraceReader`, the streaming reader of the NDJSON trace. Resolves the `ACT`/`STATE` dictionaries, materializes omitted defaults, re-derives `activity_has_mop` on both sides, expands the run-relative clock through `RUN_START.t0`, checks `RUN_START.v` against `SUPPORTED_VERSIONS = {1, 2}` (any other version is counted, or raises `SchemaVersionMismatch` in strict mode, INV-APV-62), and yields one `StepRow` per step with `dec`/`llm[]`/`out` joined. Exposes `RUN_START` as `run_start` (with `variant`) and `MOP_DATA`, `PIPELINE`, `LLM_ACK` and `RUN_END` as verbatim attributes. Read-only; never in the run path |
| `src/aperv_tool/analysis/coverage_dump.py` | Offline parser of the jar's `UICOV` / `UICOV-ACT` coverage dump (gh90 O3). Never in the run path. Reads only the `UICOV` lines, which the NDJSON trace format leaves unchanged |
| `src/aperv_tool/analysis/clock_logcat_join.py` | Offline placement of a run's `RVSEC` violation lines on its exploration timeline (gh90 A9). Both series come out of the same logcat: a violation belongs to the step of the last `ApeRvHb` heartbeat at or before it, so the two stamps carry identical unknowns (no year, no zone) that cancel in the difference. `trace_ndjson.py` supplies what the logcat cannot — the matched step's activity and abstract state, and `RUN_START.t0` as the only absolute clock. Holds no clock reconstruction of any kind. Owns `read_tagged_lines`, the shared reader of one logcat tag — matching is exact, so a request for `RVSEC` never returns an `RVSEC-COV` line — which returns a `TaggedLines` list subclass whose `.skipped` counts lines that carried the tag and whose threadtime shape did not parse. Holds **no payload parser**: it imports `violations.parse_payload` (lazily, because `violations` imports this module) so the seven-field decomposition exists once and cannot drift. Never in the run path |
| `src/aperv_tool/analysis/violations.py` | The violation stream at a declared grain, and the sole parser of the payload. `parse_payload` decomposes the seven comma fields and then reads the **v1 message envelope** the `jca_android` monitors write into the seventh (`v=1 code=… ev=… obj=… val=… exp=… msg=…`), exposing `code`/`event`/`obj`/`val`/`exp`/`msg` as fields instead of leaving them inside free text. `envelope_status` separates `absent` (a pre-change message — a legitimate shape, not a defect) from `malformed` and `truncated` (logcat cuts a payload at 4068 bytes with no marker, so an unclosed quote is the only evidence the record is half a record). `ERRORS_CSV_HEADER` restates rv-platform's 13-column consolidated CSV so a header change fails loudly here rather than going missing three layers up; `read_errors_csv` returns `CsvDiagnostics`, which counts `unique_msg_unparsed` and `unique_msg_disagrees` — `unique_msg` carries a second, independent copy of the attribution, so the reader counts a contradiction rather than silently preferring one side. The envelope grammar is restated here rather than imported from `rv_coverage`: that module is not a declared dependency, and a Layer-3 reader that needed the platform installed to read a recorded artifact would not be a reader of recorded artifacts |
| `src/aperv_tool/analysis/` (campaign layer) | The offline campaign analysis, in five layers plus `callers/`. **Layer 0** `run_identity` (single seat of the identity regex, the arm table and the frame columns), `runspec`, `tasks_record`, `loader`, `liveness` (sole owner of the per-run verdict), `gates`, `corpus`, `clones`; **Layer 1** `outcomes`, `screen_visits`; **Layer 2** `estimators/`; **Layer 3** `step_bundle`, `state_coverage_join`, `violations`, `monitored_ops`, `static_artifact`, `baseline_ape`, `baseline_droidbot`; **Layer 4** `envelope`, `provenance`, `emit`. Read-only, offline, never in the run path. Narrative: `docs/20260815_gh103_analysis_layer.md` (rv-android root) |
| `src/aperv_tool/analysis/callers/` | **The only place a research-question identifier may appear** (INV-CAN-22). `rq_map.toml` maps an entry id to a builder, an estimator and its parameters; `basis.py` carries the corpus and the upstream attrition into the envelope; `coverage.py` reports entries with no working caller, distinguishing "no caller declared" from "declared caller does not resolve". An entry whose knobs the author has not frozen is written with them **absent** — it loads, reports as wired, and raises `FreezeItemUnset` if run. That is intended; do not make it runnable by supplying a plausible value |
| `src/aperv_tool/tools/aperv/ape-rv.jar` | APE-RV binary (gitignored); pushed to `/data/local/tmp/ape-rv.jar` |
| `src/aperv_tool/tools/aperv/system-broadcast.json` | System broadcast intent catalog for component triggering; pushed only on the four `as*` cells (`broadcast_catalog`) |
| `tests/test_aperv_tool.py` | Tool spec, variants, configure validation, JAR search paths, command building, empty-trace detection, trace compression, the completion check (`TestCompletionIsEstablished`), properties generation, artifact derivation/caching (including the streaming miss path and the refusal of a truncated or non-UTF-8 source), the `.mop.json` audit, the frozen-corpus carve-out |
| `tests/test_derive_mop_artifact.py` | One named test per relocated derivation rule, plus the cryptoapp ground truth |
| `tests/test_trace_ndjson.py` | Reader semantics against `tests/fixtures/trace_ndjson_golden.ndjson` (the `eea2b1a9` jar, `v: 1`), `trace_ndjson_groups.ndjson` (the group-isolation jar, `v: 2`) and `trace_ndjson_v3_header.ndjson` (an unsupported version) |
| `tests/test_coverage_dump.py` | `UICOV` / `UICOV-ACT` parsing |
| `tests/test_clock_logcat_join.py` | Heartbeat placement, including both routes to `UNALIGNED`. The extraction cases (`read_tagged_lines`, payload parsing) live in `tests/test_clock_logcat_join_extraction.py` |
| `tests/test_smoke_two_apps.py` | The whole chain — loader → gates → corpus → a catalogue-driven caller → emit — over the two applications the fixture manifest names, with no device. Asserts no result: two applications are below the estimator's power floor by construction, and what is pinned is that the envelope says so |
| `tests/test_corrupted_fixture.py` | A temp copy of those two applications with a trace truncated to 864 bytes, a `summary.csv` removed and a `tasks.json` record stripped of its identity; asserts each defect reaches the envelope by identity and reason and that the denominator shrinks visibly. Copies first, then re-hashes every pinned file to prove the campaign tree was untouched |
| `tests/fixtures/cmp162_manifest.json` | FIXTURE-REAL pin: path + sha256 per file read, plus the measured facts every gated test asserts against. **The campaign tree is not in this repository**; a test over it either runs against the pinned bytes or skips naming what is absent, never quietly passes |
| `tests/migration/` | The checks against the jar source: the retirement list, the pinned jar tables (the six cells and their group-block unions, INV-APV-41), the mapping sweep, and the offline cell gate `test_cells.py`, which compares each cell with the jar's `cells/<cell>.run_start.json` fixture. Requires `$APE_REPO` (`$RVSEC_HOME/ape` is tried but rarely carries the sources); **skips without it** — the skip reason names the command — so a green run here is not evidence the tier executed |
| `docs/gh95-migration-record/` | The archived one-time evidence: `arm_effective_baseline.json` (29 pre-change arms) and the record of the empty regeneration diff. That diff is one-time by rule (INV-APV-44) and must not become a standing constant-vs-constant test. `tests/migration/capture_arm_baseline.py` still produces the baseline and writes here |
| `tests/fixtures/cryptoapp.apk.json` | Ground-truth static-analysis JSON, a byte copy of the full-mode (`fullOutput=true`) baseline `modules/rv-static-analysis/tests/resources/cryptoapp.apk.json` (provenance in `tests/fixtures/README.md`). Refresh by copying, never by editing |
| `docs/architecture.md` | Architecture notes |

Dependencies: workspace `rv-android-core` (AbstractTool, ToolSpec, Command, JarResolver, domain models, `util.analysis_document` for the streaming read and the source digest of the MOP artifact), the only declared workspace dependency — rv-platform registers the tool into rv-tools' `ToolRegistry`, so this module does not import rv-tools; external `pandas`, `numpy`, `scipy` and `statsmodels`, declared for the analysis layer alone — the tool path needs none of them, and `statsmodels` is imported lazily inside `analysis/estimators/count_glm.py`. Two sibling imports are deliberately undeclared: `analysis/step_bundle.py` imports `rv_coverage`'s `DiagnosticEventParser` lazily and degrades to "not read" without it, and `test_compact_document_derives_the_same_artifact` imports `rv_static_analysis.compact`, which only the shared workspace `.venv` provides.

## Variants

A variant is **one experimental cell**: a jar cell preset, the cell's own name, and the deployment facts the jar cannot know. APE-RV mounts five behaviour groups by declaration — BASE (the APE algorithm), ADDONS (the fork's own improvements), STATIC (the consumers of the static GUI model), MOP (the consumers of the specification targets) and LLM (the vision-language model). A cell is a union of groups, and `Presets.java` ships one preset per cell, built as the union of that cell's group blocks. The jar owns what a group switches on; this module names a cell and supplies the server URL, the static-analysis artifact and the variant name the jar echoes into `RUN_START.variant`. The Python side never restates what a group mounts and never branches on a preset name.

`get_variants()` returns **9 names carrying 8 configurations**: the six cells, `default` and the ablations `mop_k2` and `mop_nolaunch`. `default` is bound to the same object as `base`, because every registered tool must carry a `default` variant (INV-TOOL-02); a bare `aperv` runs the APE reference cell and its trace says `variant: "base"`. Every variant carries `strategy="sata"` and `variant` equal to its own name. `configure()` accepts `sata` and `random` as strategies — `bfs`/`dfs` were never agent types and are rejected before the device.

| Variant | Groups the preset mounts beside BASE | static_data | broadcast_catalog | overrides |
|---------|--------------------------------------|-------------|-------------------|-----------|
| `default` / `base` | — | — | — | _(empty)_ |
| `mop` | MOP | `static_analysis` | — | _(empty)_ |
| `as` | ADDONS, STATIC | `static_analysis` | `True` | _(empty)_ |
| `as_mop` | ADDONS, STATIC, MOP | `static_analysis` | `True` | _(empty)_ |
| `as_llm` | ADDONS, STATIC, LLM | `static_analysis` | `True` | `llm_url` |
| `as_mop_llm` | ADDONS, STATIC, MOP, LLM | `static_analysis` | `True` | `llm_url` |
| `mop_k2` (preset `mop`) | MOP | `static_analysis` | — | `mop_coin_ledger_max_interactions: 2` |
| `mop_nolaunch` (preset `mop`) | MOP without `MOP_LAUNCHER` | `static_analysis` | — | `activity_trigger_enabled: False` |

Why each orchestration key sits where it does:

- **`static_data` follows STATIC or MOP** (INV-APV-66). Every cell except `base` reads the derived artifact: `mop` reads it with ADDONS and STATIC off, `as` reads it with MOP off. That is why the key and the jar property are named after the static data and not after MOP.
- **`broadcast_catalog` follows STATIC** (INV-APV-10). The catalog's only reader in the jar is component triggering, a STATIC member that the four `as*` presets mount at `componentPercentage=0.03`. The flag is stated on the variant rather than inferred from the preset name, because the Python side does not know what a preset mounts.
- **`llm_url` is the only override.** The LLM presets state `ape.llm=true` without the URL, since a URL names a machine rather than a cell, so an LLM cell without it aborts at resolution (`MISSING_DEPENDENCY`, INV-APV-38). The default is `http://10.0.2.2:30000/v1`, the emulator's alias for host loopback.

A dose (`llm_percentage`, `mop_coin_percentage`) or any other mapped key is an **ablation expressed through the tool DSL** (`aperv:as_mop@mop_coin_percentage=0.5`), never a new preset: the preset vocabulary belongs to the jar. The exception is an ablation that runs in the same containers as its cell. The platform's resume identity is (apk, tool, variant, repetition, timeout) and the result file names use the same fields, so `aperv:mop` and `aperv:mop@...` there would be one task; such an ablation is a named variant on the cell's preset. There are two, both on the `mop` cell: `mop_k2`, with the MOP coin allowed two picks per (activity, widget) key, and `mop_nolaunch`, with the launcher unmounted (`ape.activityTriggerEnabled=false`, its neutral value, so the launcher stage and the null-tree recovery it owns leave the plan). The cell gate checks each against the `mop` fixture with the digest not compared: `mop_k2` adds one `params` entry; `mop_nolaunch` drops `MOP_LAUNCHER` from `features` and moves `ape.activityTriggerEnabled` from `params` to `inert`. For a new experiment, `as` is the control without specifications, `as_mop` the guidance on the full tool, and `mop` against `base` the guidance on APE alone.

**Only these nine names exist.** The arm names of the earlier campaigns (`sata`, `sata_mop`, `sata_llm`, `sata_mop_llm`, `mop_on_llm_off`, `mop_off_llm_off`, `mop_on_llm_70`, `mopd_on_llm_off`, `mopd_on_llm_90`) are not defined here and have no alias: they configured presets and keys that the paired jar no longer has, so a surviving name would claim a configuration that no longer runs. Resolving one fails in `ToolFactory` with "Invalid variant". Campaigns recorded under those names resume from their frozen image, `rvandroid:0.9.5`, whose `tool.py` still defines them; their recorded results are unaffected, and the arm labels in `analysis/callers/rq_map.toml` stay because they name recorded data. The spec's old → nearest-cell table (`openspec/specs/aperv/spec.md`, "Deleted variants") is documentation only, not an equivalence: every cell differs from every old arm at least in the MOP coin, the owner order of the step and the X1–X4 defaults. The earlier retirements, with their reasons, are listed in `tests/migration/retirements.py`.

**No variant names the binary it runs against** (INV-APV-59). The jar is built in a sibling
repository whose build is not bit-reproducible, so a digest pinned in a variant would fail correct
redeployments and pass stale ones. Which jar ran is recorded by measurement instead:
`_capture_llm_provenance()` digests the jar it is about to push into the run's `jar_sha256`.
`expected_jar_git_sha` / `expected_jar_sha256` are neither mapped nor in `APERV_ORCHESTRATION_KEYS`,
so `configure()` rejects them from experiment YAML or the tool DSL. Which build is installed is a
deployment decision, stated in the deployment, not in `tool.py`.

**There is no Python-side configuration guard.** The jar validates the plan: an unknown key, a retired key, or a non-neutral value of an inactive feature aborts the run before step 1. `tool.py` never parses `RUN_START` or any other jar output (INV-APV-43), and it does not read the echoed `RUN_START.variant` back (INV-APV-65); checking that a run executed its cell is post-hoc analysis of the trace (the cell gate in `tests/migration/test_cells.py`, and the device smoke).

## Configuration Flow

1. `configure(config)` validates before any device interaction (INV-APV-02): `strategy` in `APERV_AVAILABLE_STRATEGIES`, a non-empty `preset` and a non-empty `variant` (INV-APV-65), `overrides` a dict; folds tool-DSL keys that have a mapping entry into `overrides` (the DSL value wins); rejects unrecognised top-level keys and unmapped overrides (INV-APV-39) — `mop_data` among them, since the key is `static_data` and an experiment YAML that still names the old one must fail rather than run a cell without its data; checks the `corpus_basis` shape. `configure()` reads no environment variable (INV-TOOL-20).
2. `execute_tool_specific_logic(task, app)`:
   - Resolves `ape-rv.jar` through `JarResolver` by priority: module dir > `$RVSEC_HOME/ape/target/` > `$TOOLS_DIR/aperv/`.
   - Pushes JAR to `/data/local/tmp/ape-rv.jar`.
   - Pushes `system-broadcast.json` to `/data/local/tmp/` when the variant carries `broadcast_catalog=True` and the file exists in the module directory; `base` and `mop` never receive it. An absent file is skipped, and component triggering then runs without typed extras for system broadcasts.
   - When `static_data == "static_analysis"` (every cell but `base`): derives `<results_dir>/<apk_name>.mop.json` from the full static-analysis JSON (cache hit when the recorded `source.digest` and `formatVersion` both match, otherwise derive + atomic write) and pushes **only that artifact** to `/data/local/tmp/mop-artifact.json`. The source at `<results_dir>/<apk_name>.json` is never modified and never pushed. A cell with no static-analysis JSON, or whose derivation fails, raises `RVToolExecutionError` (INV-APV-45) — it does not degrade to a run that carries the cell's name without its data.
   - Generates + pushes `ape.properties`: `ape.preset=<preset>` first, `ape.variant=<variant>` second, `ape.staticDataPath=/data/local/tmp/mop-artifact.json` when the artifact was pushed, then one `ape.<key>=<value>` per override in mapping order (bools as `true`/`false`). For `as_mop` the file is exactly those three fixed lines; for `base` it is the first two.
   - LLM cells only (discriminated by `llm_url` in `overrides`, not by preset name): `_capture_llm_provenance()` writes a `<run>.provenance.json` sidecar recording the backend that serves the run and the sha256 of the jar about to be pushed. Non-fatal — a failed query or write costs the record, never the run (INV-APV-33).
   - Runs `adb shell CLASSPATH=... app_process`.
   - `_gzip_trace()` writes `<run>.trace.ndjson.gz` beside the trace. On **every** exit path, because timeout is the majority path, not the exception. Write-only (the trace stays byte-identical, INV-APV-52), inspects nothing (INV-APV-53), non-fatal.
   - Establishes completion (INV-APV-60): a non-timeout return whose elapsed time is below `task.config.timeout - APERV_TEARDOWN_GRACE_S` raises `RVToolExecutionError`. Compression runs first, so a truncated run keeps the artifacts that are the evidence of what truncated it.

`APERV_PROPERTY_MAPPING` translates Python config keys → Java `ape.properties` keys (67 entries): the four group keys (`addons`, `static`, `mop`, `llm`), the MOP coin dose and its ledger budget (`mop_coin_ledger_max_interactions`), the LLM gate parameters, and the member keys of each group, commented by owning group. Keys not in the mapping are the ten in `APERV_ORCHESTRATION_KEYS` — `preset`, `variant`, `overrides`, `strategy`, `static_data`, `broadcast_catalog`, `seed`, and the three device-addressing keys rv-experiment injects whenever `--device-port` is set — and are Python-only; `preset` and `variant` reach the file only through their own fixed lines. `ape.variant` and `ape.staticDataPath` are not mapping entries, so the DSL cannot set or relabel either. Any other top-level key raises `ConfigurationError` before a device is touched.

**`corpus_basis` is provenance, not configuration.** Mapped to `ape.corpusBasis`, set by no variant, supplied per campaign through the DSL (`@corpus_basis=<corpus-id>:<sha256>`). It names the application list a run was drawn from; the jar echoes it into the trace's opening record and reads it nowhere, so it changes no behaviour. `configure()` validates only the shape against `CORPUS_BASIS_PATTERN` (`<corpus-id>:<sha256>`) — this module does not own the corpus list and must not grow a filesystem dependency on a campaign's layout to hash it, so whether the digest matches the list is verified where the list lives. The check runs after the DSL fold, covering both a variant's `overrides` and an `@corpus_basis=…` parameter. Unstated ⇒ the key is omitted entirely.

## Key Design Decisions

- **Working dir `/system/bin`**: APE-RV needs system-level resource resolution; `/data/local/tmp/` causes `ClassNotFoundException` on some API levels.
- **Shared `process_pattern`** `com.android.commands.monkey`: shared with the builtin `ape` tool — the two must not run concurrently on the same device.
- **Timeout as expected exit**: exploration runs to the time limit; `RVCommandTimeoutError` → `RVToolTimeoutError` (completed run, not failure).
- **Non-zero exit is normal**: APE-RV exits non-zero when it detects app crashes during exploration.
- **…and therefore the exit code cannot be the authority on whether a run happened** (INV-APV-60). A dead emulator and an application crash are indistinguishable by it: both come back non-zero, and the crash is data the campaign collects. **Elapsed time is the discriminator, and the rule is structural** — the exploration is budget-bound by construction, so a non-timeout return more than `APERV_TEARDOWN_GRACE_S` (45 s) short of the budget did not explore its budget and raises `RVToolExecutionError` instead of reporting success. The timeout path is untouched: a timeout is the normal, successful ending, not the exception. Raising makes rv-platform store the task as `ERROR`, which its ordinary resume re-executes; without the check a truncated run would be stored `COMPLETED` with a null `error_message`.
- **LLM URL**: the two LLM cells carry `llm_url=http://10.0.2.2:30000/v1` (the emulator's alias for host loopback) in `overrides`. Docker and physical-device setups need another address, and there are two ways to give it, with a fixed precedence: a tool-DSL `@llm_url=...` > the `APERV_LLM_BASE_URL` environment variable > the cell's default. `configure()` reads no environment (INV-TOOL-20, INV-APV-09). The variable is read only by the `rv-experiment` entry point (`rv_experiment/__main__.py`, beside `RV_HUMANOID_URL`), which sets `parameters["llm_url"]` on every parsed `aperv` `ToolConfig` whose variant definition in `ToolRegistry` carries `overrides.llm_url` and whose parameters do not already set it. `ToolFactory` merges that top-level key and `configure()`'s DSL fold moves it into `overrides`, so this module gains no code path for it. The cells without the LLM group never receive the URL, because it would write an `ape.llmUrl` line for a group they do not mount. `rv-platform run` does not read the variable; there, only `@llm_url` changes the address.

## Two trace formats are parsed in this repository, on purpose

The `.trace` is NDJSON — one `StepRecord` per exploration step — and
`analysis/trace_ndjson.py` is the only
way code in this module reads one. There is deliberately **no converter** in
either direction: reconstructing the retired `[APE-STEP]` / `[APE-OUTCOME]` /
`[APE-LLM-TEL]` `key=value` family over the primary artifact would make the file
everyone opens a derived reconstruction, and would re-import the unescaped
line-breaking defect the jar's new serializer exists to remove.

So a legacy `[APE-*]` parser still lives in this tree, and that is **not** a P3
violation. The scripts below read the archived corpus behind the 2026-07-24
calibration report and the decisive run — a dataset that is finished and will not
be regenerated. They are not compatibility shims keeping a superseded
implementation alive for new data; they are the readers of frozen data. P3
governs superseded *implementation*, not analysis code over a closed dataset.

Carved out by INV-APV-55, not to be migrated, adapted or deleted:

- `scripts/cmpm_stratify.py`
- `scripts/analyze_cmpv2_llm.py`
- `experimento-cal/scripts/*`
- `experimento-20260721/scripts/*`
- `calibracao/*`

**The operational test, when it is unclear which side a reader belongs on:**
`clock_logcat_join.py` migrated because it must read *new* traces; these never
will. Should the archived corpus ever be regenerated against a stage-4 jar, the
carve-out expires with it and these scripts migrate or die then — not before.
`TestFrozenCorpusCarveOut` in `tests/test_aperv_tool.py` asserts both halves:
that none of them imports the new reader, and that they still parse the legacy
family (so the carve-out is protecting something rather than nothing).

`analysis/coverage_dump.py` is outside that split for a different reason: it reads
only the `[APE-RV] UICOV` / `UICOV-ACT` dump, which stage 4 does not modify, and
it reads it from a stage-4 trace as from an earlier one. The one field that varies
is `mopReach`: the group-isolation jar writes it on a `UICOV` line only when the
MOP group is mounted, so a line without it is complete, with `mop_reach = None`,
and does not make the dump partial (INV-APV-68).

**Two routes to `UNALIGNED`, both of which look like a bug and are not.**
`clock_logcat_join.py` places a violation against the heartbeat series in the
run's logcat, so a run whose logcat carries no `ApeRvHb` line has nothing to
place against and every violation in it comes back `UNALIGNED`. That is the
case for a run recorded before stage 4 — its jar emitted no heartbeat, and its
legacy-format trace additionally reports zero steps through the NDJSON reader —
and equally for a stage-4 run whose capture allowlist omitted the tag or that
died before its first step. Either way the run stays in the report with its
denominator, since the violation series comes from the logcat and is unaffected,
and no format sniffer or fallback branch is to be added.

## The NDJSON reader reads two jar generations

`TraceReader` accepts `RUN_START.v` 1 and 2 (`SUPPORTED_VERSIONS`), and exposes
the version it read as `run_start.v`. Version 1 is the `eea2b1a9` jar and
earlier. Version 2 is the jar built
from the `ape` change `isolate-guidance-groups` (contract v3.3, `ape` `345006e3`),
which bumped the version because `dec.src` changed meaning. The reader carries both
vocabularies without translating one into the other, so a consumer must know which
one it holds:

- **`decision_source` (`dec.src`) means two things** (INV-APV-67). Under `v == 2`
  it is the owner that executed the step — `budget`, `restart`, `llm`, `launcher`,
  `mop` or `sata` — and is causal. Under `v == 1` it is the stage whose boost was
  largest, which is not causal, because every stage adds into one shared priority.
  Counting it across traces of both versions counts two different things;
  `screen_visits` reports its counts beside the version and refuses to pool them
  (INV-CAN-21).
- **The decision record of `v == 2`** reaches typed `StepRow` fields, `None` when
  absent: `owner` (`dec.own`, an `Ownership` with the intended owner, the LLM
  stage that made the step's one call, the coin draws `u_llm`/`u_mop`, the gate and
  the fallback), `scorer_cf` (`dec.cfc`), `draw`, `nav` (a `NavTie`), `input_source`
  (`dec.inp`), `restart_kind`, `back_menu_capped`, `sata_path` (`dec.strat`),
  `rotation`, `buffer_abandoned_by`, `component_trigger` (`dec.trig`, a
  `ComponentTrigger`), plus `nav_frontier` (`dec.navf`, a boost field materialized
  at `0`). `mop_handler` (`dec.hnd`, the stamped handler, written only when `mops` is `s`)
  is `v == 2` only. `mop_distance`, `mop_stamp` and `retired_targets` (`dec.mopd`, `mops`,
  `ret`) are read on both versions. A `v == 1` trace carries none of the `v == 2`
  members, and a default would claim a mechanism ran, so they stay `None`
  (INV-APV-49). Enumerated values are carried as written, never checked against a
  closed list.
- **`counterfactual` and `wtg_source` exist only under `v == 1`.** `counterfactual`
  is that jar's `dec.cf`: the pick with **only the MOP boosts** zeroed, so it is
  evidence about MOP guidance and nothing else. `scorer_cf` is its `v == 2`
  successor, answering "did this one scorer change the pick", one scorer at a time.
- **`activity_has_mop` is tri-state** (INV-APV-68). The `v == 2` jar writes
  `ACT.mop` only with MOP mounted, so on `base`, `as` and `as_llm` the fact was not
  computed and reads `None`, not `False`. Consumers carry `None` through
  (INV-CAN-22).
- **`RUN_START.variant`** names the cell (`RunStart.variant`); it is `None` on every
  `v == 1` trace.
- **`RUN_END` is a census attribute.** `reader.run_end` is the record minus `type`,
  verbatim — `reason`, `steps` and `counters`, which on `v == 2` add `launches`,
  `gateMinActions`, `gateBreaker`, `guardBacks`, `bufAbandoned`, `restarts`,
  `coinLlm`, `coinMop` and `nullRelaunches` — beside `mop_data` (the jar's `MOP_DATA` load census), `pipeline` and `llm_ack`. The reader
  derives nothing from it: no completeness flag, no status (INV-APV-53). The
  collection path in `tools/aperv/*` still never reads `RUN_END`.

Gate 1 (clean control) has two forms for the same reason. The anchored pattern
`(?<![a-z_])mop=` is kept for the legacy `key=value` streams and is blind on NDJSON,
whose member is `"mop":`. Over any NDJSON trace the gate uses
`count_mop_group_signal(reader)`, which reads the trace through `TraceReader`. On
`v == 2` it counts the members of the `ape` side's clean-control list (INV-SNK-18). On
`v == 1` it counts only steps whose `mop` or `mop_frontier` boost fired: that jar's
control mounted MOP with zero weights, so `mopx`, `wtg`, `mopReach` and `ACT.mop`
appear in a clean run. `MOP_DATA` never counts, because it reports an artifact load,
which the STATIC cells do by design.

## Gotchas

- `ape-rv.jar` is gitignored. The Docker image builds it at image-build time (`docker/rvandroid/Dockerfile` clones `https://github.com/phtcosta/ape.git`, `mvn package`, copies `target/ape-rv.jar` into the module dir = priority-1 path). A host run needs `mvn install -Drvsec_home=<rvsec root>` in the `ape` repository (its install step copies the jar to the priority-1 path), or `_resolve_jar_path()` raises `RVToolExecutionError`.
- **The jar and `tool.py` are a pair.** The cells need the jar built from the `ape` change `isolate-guidance-groups` (key and telemetry contract v3.3, `ape` `345006e3`), which knows the six cell presets, the group keys, `ape.variant` and `ape.staticDataPath`. A mismatched pair aborts before step 1, and that is the intended guard of the cross-repository ordering: a jar that predates the group keys rejects `ape.variant` and the cell presets as unknown, and the paired jar rejects `ape.mopDataPath`, `ape.mopTargetPickCap` and `ape.leastVisitedPriorityTiebreak` as `retired_key`. Such a run writes no `RUN_START`. The Docker image builds `ape`'s default branch, so an image pairs with this tree only when that branch carries the group keys. Old campaigns run from `rvandroid:0.9.5`, whose image carries both halves of the earlier pair.
- **The jar must postdate stage 2 of the APE-RV re-architecture, or every cell silently collapses to jar defaults.** Cells are `preset + overrides`, so the properties file leads with `ape.preset=<name>` and carries only the deltas. A jar built before `rearch-02-runspec` has no `Presets`/`KeyOwnership` resolution: it treats `ape.preset` as an unknown key and ignores it, and the keys the preset would have supplied are simply absent from the file — so the run executes on `Config` defaults while the results directory still carries the cell's name. This is a deployment precondition, not something the tool can detect: nothing is read back from the jar (INV-APV-43). Identify a jar by unzipping it and running `strings -a classes.dex`: a stage-4 build carries `ApeRvHb`, `NdjsonSink` and `RUN_START`, and no `APE-STEP`; a format-2 build also carries `mopScoring`. **Do not identify it by its `build.sha` stamp**: `git-commit-id-maven-plugin` cannot read a worktree HEAD, so a jar built from a worktree is stamped with the `ape` master commit instead of the commit it was built from.
- **The derive emits artifact format 2, which only an `ape` jar from commit `61642793` onward reads.** Each side rejects the other's format (`version-mismatch`), so a format-1 jar aborts every cell that reads the artifact — every cell but `base` — at load. The intent filters of receivers and services carry a reduced `data` member (`schemes`, `hosts`, `paths`, `pathPrefixes`, `mimeTypes`; `ports` and `pathPatterns` are never emitted), which component triggering needs to build an intent the platform actually delivers. The member is additive: the format stays 2, empty lists are omitted, and `data` is omitted when all five are empty, so the artifact of an application without data filters is unchanged. Every component is projected whatever its `reachesTarget`, because the trigger pool reads no MOP data. Before running a cell on the host, check that the jar in this module directory is the paired build (above).
- `APERV_TEARDOWN_GRACE_S` (45 s) is stated once and read from opposite sides by the two users that must agree on it: `_build_main_command()` adds it to the command timeout, so APE-RV can flush its WTG model and emit the coverage dump before the process is killed, and the completion check subtracts it from the budget to get the floor. The value is a hypothesis about censored teardown durations, not a measurement; the evidence behind it is in the comment of `_build_main_command()`. Changing it moves both uses.
- Empty (0-byte) trace file = silent startup crash; logged as a warning, not an error (coverage may still come from logcat).
- Static-analysis JSON for every cell but `base` must exist at `<task.results_dir>/<apk_name>.json`. If it is missing, the task **fails** rather than running without its STATIC or MOP data under the cell's name, which would be indistinguishable from a real run of that cell in the results directory.
- The device receives the derived projection, never the producer's JSON, so the jar does not parse the call graph: a call-graph-heavy app loads in `as_mop` as it does in `as`, which keeps the comparison between cells fair per app.
- **Widget flags carry the producer's two axes**: `direct` = 0-hop, `transitive` = any depth, `direct` implying `transitive`, and the D8 synthetic-lambda recovery (an unlisted `X$$ExternalSyntheticLambdaN` handler recovered from `X`'s `lambda$…` methods) applies to both. **Runs before and after gh96 are not substrate-comparable**; no campaign may mix runs across that cut.
- The artifact is device input only. No module outside `aperv-tool` may read a `*.mop.json` (INV-ANA-53) — it is a lossy projection and a metric computed over it would answer a different question under the same name. `TestMopArtifactAudit` enforces this.
- **The violation message is a parsed contract, and that breaks anything regexing its free text.** The `jca_android` monitors write a `v=1` envelope into the seventh comma field, and `violations.parse_payload` reads it into named fields. A consumer that pattern-matched the message body gets a different string. `data/gh104/consumer_matrix.md` (rv-android root) names every reader of `message`, `unique_msg` or `errors.csv` with its verdict — migrated, or frozen with the reason — closed by a grep over `modules/`, `scripts/`, the experiments and `audit/`, so every hit that is code has a row. Add a row there before adding a reader.
- **`shape_bad` and the two envelope counters are not interchangeable.** A line that failed the seven-field split is `shape_bad` and keeps the whole payload in `message`; a line that split cleanly and then declared a `v=1` envelope it did not honour is `envelope_malformed`, with the seven fields still populated. `envelope_truncated` is neither defect — it is logcat's 4068-byte cut, and the record is genuinely half a record. `step_bundle.BundleDiagnostics.violations` carries all three onto the bundle, because a step whose lines were discarded upstream is otherwise indistinguishable from a step that produced no violation: the per-tag counters account only for lines the reader returned.
- Cache freshness is the SHA-256 recorded in `source.digest` together with the artifact's `formatVersion`, not mtime: mtime does not survive a copy, a resume or a container boundary. The format is in the key because after a format bump an old-format artifact still matches its source's digest, and the jar reads one format only (INV-APV-47). A corrupt or unreadable cached artifact is a miss, not a failure. The digest is streamed (`digest_of_file`, imported from `rv_android_core.util.analysis_document`, the same digest the parsed-copy cache of `rv-static-analysis` keys on), so a hit never parses the source: a static-analysis JSON can reach several gigabytes. A miss reads the source in streaming too (`read_analysis_document` with `PairPolicy.reduce(DIST_WEIGHED_MAX, DIST_K)`, INV-APV-64): each method's `targetDistances` is folded into per-target minima and only the pairs at `d <= DIST_WEIGHED_MAX` and the `DIST_K` nearest survive, which is exact for `derive()` because it merges by the minimum and cuts only at emission, so the artifact is byte-identical to a whole-document derivation. A whole-document `json.load` peaks at about 3.1 times the file size. GATOR's default compact output (pairs already reduced, `distancePairs` marker) derives the same artifact as the full document of the same analysis apart from the `source` object (INV-ANA-89, `test_compact_document_derives_the_same_artifact`). The read is strict: a document whose root object never closes (a producer killed mid-write, or bytes that are not UTF-8) raises `RVToolExecutionError`, unlike the static-analysis parser, which keeps the complete sections. Changing either cut (`DIST_WEIGHED_MAX`, `DIST_K` in `derive_mop_artifact.py`) changes what the reduction must keep, and GATOR's compact writer (`TargetDistances`, Java) and the offline converter (`COMPACT_WEIGHED_MAX`/`COMPACT_K` in `rv_static_analysis/compact.py`) must move with them; a parity test in `rv-static-analysis` pins the three (INV-ANA-88).
