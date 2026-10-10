# aperv-tool - CLAUDE.md

## Overview

rv-platform plugin that wraps the APE-RV binary (`ape-rv.jar`) as an `AbstractTool`. Manages JAR deployment, `ape.properties` injection, and command execution on the Android emulator via `app_process`. (APE-RV internals live in the `ape` repository, a sibling of `rvsec/` — `../../ape` from the rv-android root — which has its own CLAUDE.md.)

```bash
uv run rv-experiment run --tools aperv:sata_mop --specification-set jca_android   # MOP-guided run
```

(uv sync / editable install, pytest, and the general `rv-experiment run` form are documented in the top-level module CLAUDE.md.)

## Files

| File | Purpose |
|------|---------|
| `src/aperv_tool/tools/aperv/tool.py` | `ApeRVTool`: JAR resolution, device push, MOP artifact derivation + digest cache, `ape.properties` generation, command building, execution |
| `src/aperv_tool/tools/aperv/derive_mop_artifact.py` | **Single authority** for the MOP substrate's parse-time semantics (gh96). `derive(document) -> dict` + `serialize_canonical(artifact) -> bytes`, both pure |
| `src/aperv_tool/analysis/trace_ndjson.py` | `TraceReader`, the streaming reader of the NDJSON trace. Resolves the `ACT`/`STATE` dictionaries, materializes omitted defaults, re-derives `activity_has_mop` on both sides, expands the run-relative clock through `RUN_START.t0`, checks `RUN_START.v` against `FORMAT_VERSION` (counted, or `SchemaVersionMismatch` in strict mode, INV-APV-62), and yields one `StepRow` per step with `dec`/`llm[]`/`out` joined. Read-only; never in the run path |
| `src/aperv_tool/analysis/coverage_dump.py` | Offline parser of the jar's `UICOV` / `UICOV-ACT` coverage dump (gh90 O3). Never in the run path. Reads only the `UICOV` lines, which the NDJSON trace format leaves unchanged |
| `src/aperv_tool/analysis/clock_logcat_join.py` | Offline placement of a run's `RVSEC` violation lines on its exploration timeline (gh90 A9). Both series come out of the same logcat: a violation belongs to the step of the last `ApeRvHb` heartbeat at or before it, so the two stamps carry identical unknowns (no year, no zone) that cancel in the difference. `trace_ndjson.py` supplies what the logcat cannot — the matched step's activity and abstract state, and `RUN_START.t0` as the only absolute clock. Holds no clock reconstruction of any kind. Owns `read_tagged_lines`, the shared reader of one logcat tag — matching is exact, so a request for `RVSEC` never returns an `RVSEC-COV` line — which returns a `TaggedLines` list subclass whose `.skipped` counts lines that carried the tag and whose threadtime shape did not parse. Holds **no payload parser**: it imports `violations.parse_payload` (lazily, because `violations` imports this module) so the seven-field decomposition exists once and cannot drift. Never in the run path |
| `src/aperv_tool/analysis/violations.py` | The violation stream at a declared grain, and the sole parser of the payload. `parse_payload` decomposes the seven comma fields and then reads the **v1 message envelope** the `jca_android` monitors write into the seventh (`v=1 code=… ev=… obj=… val=… exp=… msg=…`), exposing `code`/`event`/`obj`/`val`/`exp`/`msg` as fields instead of leaving them inside free text. `envelope_status` separates `absent` (a pre-change message — a legitimate shape, not a defect) from `malformed` and `truncated` (logcat cuts a payload at 4068 bytes with no marker, so an unclosed quote is the only evidence the record is half a record). `ERRORS_CSV_HEADER` restates rv-platform's 13-column consolidated CSV so a header change fails loudly here rather than going missing three layers up; `read_errors_csv` returns `CsvDiagnostics`, which counts `unique_msg_unparsed` and `unique_msg_disagrees` — `unique_msg` carries a second, independent copy of the attribution, so the reader counts a contradiction rather than silently preferring one side. The envelope grammar is restated here rather than imported from `rv_coverage`: that module is not a declared dependency, and a Layer-3 reader that needed the platform installed to read a recorded artifact would not be a reader of recorded artifacts |
| `src/aperv_tool/analysis/` (campaign layer) | The offline campaign analysis, in five layers plus `callers/`. **Layer 0** `run_identity` (single seat of the identity regex, the arm table and the frame columns), `runspec`, `tasks_record`, `loader`, `liveness` (sole owner of the per-run verdict), `gates`, `corpus`, `clones`; **Layer 1** `outcomes`, `screen_visits`; **Layer 2** `estimators/`; **Layer 3** `step_bundle`, `state_coverage_join`, `violations`, `monitored_ops`, `static_artifact`, `baseline_ape`, `baseline_droidbot`; **Layer 4** `envelope`, `provenance`, `emit`. Read-only, offline, never in the run path. Narrative: `docs/20260815_gh103_analysis_layer.md` (rv-android root) |
| `src/aperv_tool/analysis/callers/` | **The only place a research-question identifier may appear** (INV-CAN-22). `rq_map.toml` maps an entry id to a builder, an estimator and its parameters; `basis.py` carries the corpus and the upstream attrition into the envelope; `coverage.py` reports entries with no working caller, distinguishing "no caller declared" from "declared caller does not resolve". An entry whose knobs the author has not frozen is written with them **absent** — it loads, reports as wired, and raises `FreezeItemUnset` if run. That is intended; do not make it runnable by supplying a plausible value |
| `src/aperv_tool/tools/aperv/ape-rv.jar` | APE-RV binary (gitignored); pushed to `/data/local/tmp/ape-rv.jar` |
| `src/aperv_tool/tools/aperv/system-broadcast.json` | System broadcast intent catalog for component triggering |
| `tests/test_aperv_tool.py` | Tool spec, variants, configure validation, JAR search paths, command building, empty-trace detection, trace compression, the completion check (`TestCompletionIsEstablished`), properties generation, artifact derivation/caching (including the streaming miss path and the refusal of a truncated or non-UTF-8 source), the `.mop.json` audit, the frozen-corpus carve-out |
| `tests/test_derive_mop_artifact.py` | One named test per relocated derivation rule, plus the cryptoapp ground truth |
| `tests/test_trace_ndjson.py` | Reader semantics against `tests/fixtures/trace_ndjson_golden.ndjson` |
| `tests/test_coverage_dump.py` | `UICOV` / `UICOV-ACT` parsing |
| `tests/test_clock_logcat_join.py` | Heartbeat placement, including both routes to `UNALIGNED`. The extraction cases (`read_tagged_lines`, payload parsing) live in `tests/test_clock_logcat_join_extraction.py` |
| `tests/test_smoke_two_apps.py` | The whole chain — loader → gates → corpus → a catalogue-driven caller → emit — over the two applications the fixture manifest names, with no device. Asserts no result: two applications are below the estimator's power floor by construction, and what is pinned is that the envelope says so |
| `tests/test_corrupted_fixture.py` | A temp copy of those two applications with a trace truncated to 864 bytes, a `summary.csv` removed and a `tasks.json` record stripped of its identity; asserts each defect reaches the envelope by identity and reason and that the denominator shrinks visibly. Copies first, then re-hashes every pinned file to prove the campaign tree was untouched |
| `tests/fixtures/cmp162_manifest.json` | FIXTURE-REAL pin: path + sha256 per file read, plus the measured facts every gated test asserts against. **The campaign tree is not in this repository**; a test over it either runs against the pinned bytes or skips naming what is absent, never quietly passes |
| `tests/migration/` | The standing part of the preset migration: the retirement list, the pinned jar tables (INV-APV-41), the mapping sweep and the decisive-run contrasts. Requires `$APE_REPO` (`$RVSEC_HOME/ape` is tried but rarely carries the sources); **skips without it** — the skip reason names the command — so a green run here is not evidence the tier executed |
| `docs/gh95-migration-record/` | The archived one-time evidence: `arm_effective_baseline.json` (29 pre-change arms) and the record of the empty regeneration diff. That diff is one-time by rule (INV-APV-44) and must not become a standing constant-vs-constant test. `tests/migration/capture_arm_baseline.py` still produces the baseline and writes here |
| `tests/fixtures/cryptoapp.apk.json` | Ground-truth static-analysis JSON, a byte copy of the full-mode (`fullOutput=true`) baseline `modules/rv-static-analysis/tests/resources/cryptoapp.apk.json` (provenance in `tests/fixtures/README.md`). Refresh by copying, never by editing |
| `docs/architecture.md` | Architecture notes |

Dependencies: workspace `rv-android-core` (AbstractTool, ToolSpec, Command, JarResolver, domain models, `util.analysis_document` for the streaming read and the source digest of the MOP artifact), the only declared workspace dependency — rv-platform registers the tool into rv-tools' `ToolRegistry`, so this module does not import rv-tools; external `pandas`, `numpy`, `scipy` and `statsmodels`, declared for the analysis layer alone — the tool path needs none of them, and `statsmodels` is imported lazily inside `analysis/estimators/count_glm.py`. Two sibling imports are deliberately undeclared: `analysis/step_bundle.py` imports `rv_coverage`'s `DiagnosticEventParser` lazily and degrades to "not read" without it, and `test_compact_document_derives_the_same_artifact` imports `rv_static_analysis.compact`, which only the shared workspace `.venv` provides.

## Variants

An arm is a **jar preset name plus a dict of override deltas** — nothing else. `Presets.java` holds the four campaign vectors (`aperv`, `mop`, `llm`, `llm_mop`, selected by `ape.preset`), so the jar owns what a preset means and this module owns the experimental matrix: which arms exist, what their frozen names are, and how each differs from its preset.

`get_variants()` returns **10 names carrying 9 configurations**. Four are one-to-one with the presets and carry nothing but the deployment-specific server URL where an LLM is involved; three are the E3 decisive run's arms; two select the jar's distance MOP scoring (gh122); `default` is bound to the same object as `sata`. `configure()` accepts `sata` and `random` as strategies — `bfs`/`dfs` were never agent types and are rejected before the device.

| Variant | preset | mop_data | overrides | Notes |
|---------|--------|----------|-----------|-------|
| `default` / `sata` | `aperv` | — | _(empty)_ | Adaptive random baseline (`default` aliases `sata`, same object) |
| `sata_mop` | `mop` | yes | _(empty)_ | MOP-guided. **The frozen-corpus name**: recorded traces and results files carry the `aperv:sata_mop` token as their resume and consolidation identity, so it must not move (INV-APV-42) |
| `sata_llm` | `llm` | — | `llm_url` | LLM guidance via SGLang |
| `sata_mop_llm` | `llm_mop` | yes | `llm_url` | MOP + LLM combined |
| `mop_on_llm_off` | `mop` | yes | the four reach-package keys | gh90 decisive-run **reference**; absorbs the retired `sata_mop_act_frontier`, whose effective configuration was byte-identical (the ANC2 anchor) |
| `mop_off_llm_off` | `mop` | yes | reach package minus the frontier weight/trigger, plus the four MOP weights at `0` | gh90 decisive-run **control**. MOP-off means `mop_data` present + the scoring weights zeroed, never an omitted document (INV-APV-29); `frontier_boost_weight` stays at 200 so navigation survives (INV-APV-30). Reference ↔ control = RQ-C1 |
| `mop_on_llm_70` | `llm_mop` | yes | the reference's four, plus the LLM dose (v13, 70%, temperature 0) and `llm_snap_tolerance_px=150` | gh90 decisive-run **LLM arm**. Reference ↔ this = RQ-C3 |
| `mopd_on_llm_off` | `mop` | yes | the reference's four, plus `mop_scoring="distance"` | gh122 **distance arm**: reference ↔ this isolates the distance scoring. Takes the jar's distance defaults (500/400/300, 3, 6) |
| `mopd_on_llm_90` | `llm_mop` | yes | the reference's four, the LLM keys written out one by one (v13, 0.9, temperature 0, snap 150, `Qwen/Qwen3-VL-4B-Instruct-FP8`, `top_p` 1.0, `top_k` -1), plus `mop_scoring="distance"` | gh122 **distance LLM arm**; differs from `mopd_on_llm_off` only in `llm_*` keys. Its flag-mode twin is defined outside rv-android |

`throttle_ms` appears in no arm: the `aperv` preset already states `ape.defaultGUIThrottle=200`, which every arm used. Ablations are named override sets, never new presets — the preset vocabulary belongs to the jar.

**Twenty-one names are retired**, in three kinds: *never distinct* (`ape_pure`, `bfs`, `sata_mop_widget` — `bfs` carried `sata`'s plan and `sata_mop_widget` was `sata_mop`'s own object), *name consolidated* (`sata_mop_act_frontier`, surviving as `mop_on_llm_off`), and *finished campaign* (the six `sata_mop_llm_*` prompt arms, `cal_a1`…`cal_a9`, `sata_mop_activity`, `random`). A retired name cannot launch new runs; recorded results are frozen artifacts and are unaffected. The full list with reasons is `tests/migration/retirements.py`.

**No arm names the binary it runs against** (INV-APV-59). The jar is built in a sibling
repository whose build is not bit-reproducible, so a digest pinned in an arm would fail correct
redeployments and pass stale ones. Which jar ran is recorded by measurement instead:
`_capture_llm_provenance()` digests the jar it is about to push into the run's `jar_sha256`.
`expected_jar_git_sha` / `expected_jar_sha256` are neither mapped nor in `APERV_ORCHESTRATION_KEYS`,
so `configure()` rejects them from experiment YAML or the tool DSL. Which build is installed is a
deployment decision, stated in the deployment, not in `tool.py`.

**There is no Python-side arm-explicitness guard.** The jar validates the plan: an unknown key, a retired key, or a non-neutral value of an inactive feature aborts the run before step 1. `tool.py` never parses `RUN_START` or any other jar output (INV-APV-43); drift auditing is post-hoc analysis of the trace.

## Configuration Flow

1. `configure(config)` validates before any device interaction (INV-APV-02): `strategy` in `APERV_AVAILABLE_STRATEGIES`, a non-empty `preset`, `overrides` a dict; folds tool-DSL keys that have a mapping entry into `overrides` (the DSL value wins); rejects unrecognised top-level keys and unmapped overrides (INV-APV-39); checks the `corpus_basis` shape.
2. `execute_tool_specific_logic(task, app)`:
   - Resolves `ape-rv.jar` through `JarResolver` by priority: module dir > `$RVSEC_HOME/ape/target/` > `$TOOLS_DIR/aperv/`.
   - Pushes JAR to `/data/local/tmp/ape-rv.jar`; `system-broadcast.json` to `/data/local/tmp/` (optional).
   - MOP variants: derives `<results_dir>/<apk_name>.mop.json` from the full static-analysis JSON (cache hit when the recorded `source.digest` and `formatVersion` both match, otherwise derive + atomic write) and pushes **only that artifact** to `/data/local/tmp/mop-artifact.json`. The source at `<results_dir>/<apk_name>.json` is never modified and never pushed. A MOP arm with no static-analysis JSON, or whose derivation fails, raises `RVToolExecutionError` — it does not degrade to a MOP-labelled SATA run.
   - Generates + pushes `ape.properties`: `ape.preset=<preset>` first, `ape.mopDataPath=/data/local/tmp/mop-artifact.json` when the artifact was pushed, then one `ape.<key>=<value>` per override in mapping order (bools as `true`/`false`).
   - LLM arms only (discriminated by `llm_url` in `overrides`, not by preset name): `_capture_llm_provenance()` writes a `<run>.provenance.json` sidecar recording the backend that serves the run and the sha256 of the jar about to be pushed. Non-fatal — a failed query or write costs the record, never the run (INV-APV-33).
   - Runs `adb shell CLASSPATH=... app_process`.
   - `_gzip_trace()` writes `<run>.trace.ndjson.gz` beside the trace. On **every** exit path, because timeout is the majority path, not the exception. Write-only (the trace stays byte-identical, INV-APV-52), inspects nothing (INV-APV-53), non-fatal.
   - Establishes completion (INV-APV-60): a non-timeout return whose elapsed time is below `task.config.timeout - APERV_TEARDOWN_GRACE_S` raises `RVToolExecutionError`. Compression runs first, so a truncated run keeps the artifacts that are the evidence of what truncated it.

`APERV_PROPERTY_MAPPING` translates Python config keys → Java `ape.properties` keys (56 entries). Keys not in the mapping are the eight in `APERV_ORCHESTRATION_KEYS` — `preset`, `overrides`, `strategy`, `mop_data`, `seed`, and the three device-addressing keys rv-experiment injects whenever `--device-port` is set — and are Python-only. Any other top-level key raises `ConfigurationError` before a device is touched.

**`corpus_basis` is provenance, not configuration.** Mapped to `ape.corpusBasis`, set by no arm, supplied per campaign through the DSL (`@corpus_basis=<corpus-id>:<sha256>`). It names the application list a run was drawn from; the jar echoes it into the trace's opening record and reads it nowhere, so it changes no behaviour. `configure()` validates only the shape against `CORPUS_BASIS_PATTERN` (`<corpus-id>:<sha256>`) — this module does not own the corpus list and must not grow a filesystem dependency on a campaign's layout to hash it, so whether the digest matches the list is verified where the list lives. The check runs after the DSL fold, covering both an arm's `overrides` and an `@corpus_basis=…` parameter. Unstated ⇒ the key is omitted entirely.

## Key Design Decisions

- **Working dir `/system/bin`**: APE-RV needs system-level resource resolution; `/data/local/tmp/` causes `ClassNotFoundException` on some API levels.
- **Shared `process_pattern`** `com.android.commands.monkey`: shared with the builtin `ape` tool — the two must not run concurrently on the same device.
- **Timeout as expected exit**: exploration runs to the time limit; `RVCommandTimeoutError` → `RVToolTimeoutError` (completed run, not failure).
- **Non-zero exit is normal**: APE-RV exits non-zero when it detects app crashes during exploration.
- **…and therefore the exit code cannot be the authority on whether a run happened** (INV-APV-60). A dead emulator and an application crash are indistinguishable by it: both come back non-zero, and the crash is data the campaign collects. **Elapsed time is the discriminator, and the rule is structural** — the exploration is budget-bound by construction, so a non-timeout return more than `APERV_TEARDOWN_GRACE_S` (45 s) short of the budget did not explore its budget and raises `RVToolExecutionError` instead of reporting success. The timeout path is untouched: a timeout is the normal, successful ending, not the exception. Raising makes rv-platform store the task as `ERROR`, which its ordinary resume re-executes; without the check a truncated run would be stored `COMPLETED` with a null `error_message`.
- **LLM URL**: the LLM arms carry `llm_url=http://10.0.2.2:30000/v1` (the emulator's alias for host loopback) in `overrides`; a deployment changes it through the tool DSL (`@llm_url=...`), which `configure()` folds into `overrides`. No component reads an environment variable for it: `APERV_LLM_BASE_URL`, named in comments at `tool.py:376` and `tool.py:659`, is read by nothing, and the tests assert `configure()` ignores it.

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

`analysis/coverage_dump.py` is untouched for a different reason: it reads only
the `[APE-RV] UICOV` / `UICOV-ACT` dump, which stage 4 does not modify, and it
keeps reading it unchanged from a stage-4 trace.

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

## Gotchas

- `ape-rv.jar` is gitignored. The Docker image builds it at image-build time (`docker/rvandroid/Dockerfile` clones `https://github.com/phtcosta/ape.git`, `mvn package`, copies `target/ape-rv.jar` into the module dir = priority-1 path). A host run needs `mvn install -Drvsec_home=<rvsec root>` in the `ape` repository (its install step copies the jar to the priority-1 path), or `_resolve_jar_path()` raises `RVToolExecutionError`.
- **The jar must postdate stage 2 of the APE-RV re-architecture, or every arm silently collapses to jar defaults.** Arms are `preset + overrides`, so the properties file leads with `ape.preset=<name>` and carries only the deltas. A jar built before `rearch-02-runspec` has no `Presets`/`KeyOwnership` resolution: it treats `ape.preset` as an unknown key and ignores it, and the keys the preset would have supplied are simply absent from the file — so the run executes on `Config` defaults while the results directory still carries the arm's name. This is a deployment precondition, not something the tool can detect: nothing is read back from the jar (INV-APV-43). Identify a jar by unzipping it and running `strings -a classes.dex`: a stage-4 build carries `ApeRvHb`, `NdjsonSink` and `RUN_START`, and no `APE-STEP`; a format-2 build also carries `mopScoring`. **Do not identify it by its `build.sha` stamp**: `git-commit-id-maven-plugin` cannot read a worktree HEAD, so a jar built from a worktree is stamped with the `ape` master commit instead of the commit it was built from.
- **The derive emits artifact format 2, which only an `ape` jar from commit `61642793` onward reads** (on `ape` master). Each side rejects the other's format (`version-mismatch`), so a format-1 jar aborts every MOP arm at load, and the two `mopd_*` arms also need that jar for `ape.mopScoring`. The Docker image builds `ape`'s default branch, so it ships a format-2 jar. The `ape-rv.jar` currently placed in this module directory is a stage-4, format-1 build (no `mopScoring`): rebuild and place a current one before running a MOP arm on the host.
- `APERV_TEARDOWN_GRACE_S` (45 s) is stated once and read from opposite sides by the two users that must agree on it: `_build_main_command()` adds it to the command timeout, so APE-RV can flush its WTG model and emit the coverage dump before the process is killed, and the completion check subtracts it from the budget to get the floor. The value is a hypothesis about censored teardown durations, not a measurement; the evidence behind it is in the comment of `_build_main_command()`. Changing it moves both uses.
- Empty (0-byte) trace file = silent startup crash; logged as a warning, not an error (coverage may still come from logcat).
- Static-analysis JSON for MOP variants must exist at `<task.results_dir>/<apk_name>.json`. If it is missing, the task **fails** rather than running as pure SATA under a MOP label, which would be indistinguishable from a real MOP arm in the results directory.
- The device receives the derived projection, never the producer's JSON, so the jar does not parse the call graph: a call-graph-heavy app loads in a MOP arm as it does in the `sata` baseline, which keeps the MOP-vs-baseline comparison fair per app.
- **Widget flags carry the producer's two axes**: `direct` = 0-hop, `transitive` = any depth, `direct` implying `transitive`, and the D8 synthetic-lambda recovery (an unlisted `X$$ExternalSyntheticLambdaN` handler recovered from `X`'s `lambda$…` methods) applies to both. **Runs before and after gh96 are not substrate-comparable**; no campaign may mix arms across that cut.
- The artifact is device input only. No module outside `aperv-tool` may read a `*.mop.json` (INV-ANA-53) — it is a lossy projection and a metric computed over it would answer a different question under the same name. `TestMopArtifactAudit` enforces this.
- **The violation message is a parsed contract, and that breaks anything regexing its free text.** The `jca_android` monitors write a `v=1` envelope into the seventh comma field, and `violations.parse_payload` reads it into named fields. A consumer that pattern-matched the message body gets a different string. `data/gh104/consumer_matrix.md` (rv-android root) names every reader of `message`, `unique_msg` or `errors.csv` with its verdict — migrated, or frozen with the reason — closed by a grep over `modules/`, `scripts/`, the experiments and `audit/`, so every hit that is code has a row. Add a row there before adding a reader.
- **`shape_bad` and the two envelope counters are not interchangeable.** A line that failed the seven-field split is `shape_bad` and keeps the whole payload in `message`; a line that split cleanly and then declared a `v=1` envelope it did not honour is `envelope_malformed`, with the seven fields still populated. `envelope_truncated` is neither defect — it is logcat's 4068-byte cut, and the record is genuinely half a record. `step_bundle.BundleDiagnostics.violations` carries all three onto the bundle, because a step whose lines were discarded upstream is otherwise indistinguishable from a step that produced no violation: the per-tag counters account only for lines the reader returned.
- Cache freshness is the SHA-256 recorded in `source.digest` together with the artifact's `formatVersion`, not mtime: mtime does not survive a copy, a resume or a container boundary. The format is in the key because after a format bump an old-format artifact still matches its source's digest, and the jar reads one format only (INV-APV-47). A corrupt or unreadable cached artifact is a miss, not a failure. The digest is streamed (`digest_of_file`, imported from `rv_android_core.util.analysis_document`, the same digest the parsed-copy cache of `rv-static-analysis` keys on), so a hit never parses the source: a static-analysis JSON can reach several gigabytes. A miss reads the source in streaming too (`read_analysis_document` with `PairPolicy.reduce(DIST_WEIGHED_MAX, DIST_K)`, INV-APV-64): each method's `targetDistances` is folded into per-target minima and only the pairs at `d <= DIST_WEIGHED_MAX` and the `DIST_K` nearest survive, which is exact for `derive()` because it merges by the minimum and cuts only at emission, so the artifact is byte-identical to a whole-document derivation. A whole-document `json.load` peaks at about 3.1 times the file size. GATOR's default compact output (pairs already reduced, `distancePairs` marker) derives the same artifact as the full document of the same analysis apart from the `source` object (INV-ANA-89, `test_compact_document_derives_the_same_artifact`). The read is strict: a document whose root object never closes (a producer killed mid-write, or bytes that are not UTF-8) raises `RVToolExecutionError`, unlike the static-analysis parser, which keeps the complete sections. Changing either cut (`DIST_WEIGHED_MAX`, `DIST_K` in `derive_mop_artifact.py`) changes what the reduction must keep, and GATOR's compact writer (`TargetDistances`, Java) and the offline converter (`COMPACT_WEIGHED_MAX`/`COMPACT_K` in `rv_static_analysis/compact.py`) must move with them; a parity test in `rv-static-analysis` pins the three (INV-ANA-88).
