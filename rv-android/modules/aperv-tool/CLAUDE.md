# aperv-tool - CLAUDE.md

## Overview

rv-platform plugin that wraps the APE-RV binary (`ape-rv.jar`) as an `AbstractTool`. Manages JAR deployment, `ape.properties` injection, and command execution on the Android emulator via `app_process`. (APE-RV internals live in the sibling `../ape` repo, which has its own CLAUDE.md.)

```bash
uv run rv-experiment run --tools aperv:sata_mop --specification-set jca   # MOP-guided run
```

(uv sync / editable install, pytest, and the general `rv-experiment run` form are documented in the top-level module CLAUDE.md.)

## Files

| File | Purpose |
|------|---------|
| `src/aperv_tool/tools/aperv/tool.py` | `ApeRVTool`: JAR resolution, device push, MOP artifact derivation + digest cache, `ape.properties` generation, command building, execution |
| `src/aperv_tool/tools/aperv/derive_mop_artifact.py` | **Single authority** for the MOP substrate's parse-time semantics (gh96). `derive(document) -> dict` + `serialize_canonical(artifact) -> bytes`, both pure |
| `src/aperv_tool/analysis/trace_ndjson.py` | Native streaming reader of the stage-4 NDJSON trace (gh94). Resolves the `ACT`/`STATE` dictionaries, materializes omitted defaults, re-derives `activity_has_mop` on both sides, expands the run-relative clock through `RUN_START.t0`, and yields one row per step with `dec`/`llm[]`/`out` joined. Read-only; never in the run path |
| `src/aperv_tool/analysis/coverage_dump.py` | Offline parser of the jar's `UICOV` / `UICOV-ACT` coverage dump (gh90 O3). Never in the run path. **Unaffected by stage 4**: it reads only the `UICOV` lines, which the NDJSON change does not touch |
| `src/aperv_tool/analysis/clock_logcat_join.py` | Offline join of a run's step clock against its `RVSEC` violation lines (gh90 A9), reading steps through `trace_ndjson.py`. Never in the run path |
| `src/aperv_tool/tools/aperv/ape-rv.jar` | APE-RV binary (gitignored); pushed to `/data/local/tmp/ape-rv.jar` |
| `src/aperv_tool/tools/aperv/system-broadcast.json` | System broadcast intent catalog for component triggering |
| `tests/test_aperv_tool.py` | Tool spec, variants, configure validation, JAR search paths, command building, empty-trace detection, properties generation, artifact derivation/caching, the `.mop.json` audit |
| `tests/test_derive_mop_artifact.py` | One named test per relocated derivation rule, plus the cryptoapp ground truth |
| `tests/fixtures/cryptoapp.apk.json` | Ground-truth static-analysis JSON (provenance in `tests/fixtures/README.md`) |
| `docs/architecture.md` | Architecture notes |

Dependencies: internal `rv-android-core` (AbstractTool, ToolSpec, Command, JarResolver, domain models); external `rv-tools` (plugin registration).

## Variants

An arm is a **jar preset name plus a dict of override deltas** — nothing else. `Presets.java` holds the four campaign vectors (`aperv`, `mop`, `llm`, `llm_mop`, selected by `ape.preset`), so the jar owns what a preset means and this module owns the experimental matrix: which arms exist, what their frozen names are, and how each differs from its preset.

`get_variants()` returns **8 names carrying 7 configurations**. Four are one-to-one with the presets and carry nothing but the deployment-specific server URL where an LLM is involved; three are the E3 decisive run's arms; `default` is bound to the same object as `sata`. `configure()` accepts `sata` and `random` as strategies — `bfs`/`dfs` were never agent types and are rejected before the device.

| Variant | preset | mop_data | overrides | Notes |
|---------|--------|----------|-----------|-------|
| `default` / `sata` | `aperv` | — | _(empty)_ | Adaptive random baseline (`default` aliases `sata`, same object) |
| `sata_mop` | `mop` | yes | _(empty)_ | MOP-guided. **The frozen-corpus name**: 4,096 `aperv:sata_mop.trace` artifacts and 1,066 files under `results/` carry that token, so it must not move (INV-APV-42) |
| `sata_llm` | `llm` | — | `llm_url` | LLM guidance via SGLang |
| `sata_mop_llm` | `llm_mop` | yes | `llm_url` | MOP + LLM combined |
| `mop_on_llm_off` | `mop` | yes | the four reach-package keys | gh90 decisive-run **reference**; absorbs the retired `sata_mop_act_frontier`, whose effective configuration was byte-identical (the ANC2 anchor) |
| `mop_off_llm_off` | `mop` | yes | reach package minus the frontier weight/trigger, plus the four MOP weights at `0` | gh90 decisive-run **control**. MOP-off means `mop_data` present + the scoring weights zeroed, never an omitted document (INV-APV-29); `frontier_boost_weight` stays at 200 so navigation survives (INV-APV-30). Reference ↔ control = RQ-C1 |
| `mop_on_llm_70` | `llm_mop` | yes | the reference's four, plus the LLM dose (v13, 70%, temperature 0) and `llm_snap_tolerance_px=150` | gh90 decisive-run **LLM arm**. Reference ↔ this = RQ-C3 |

`throttle_ms` appears in no arm: the `aperv` preset already states `ape.defaultGUIThrottle=200`, which every arm used. Ablations are named override sets, never new presets — the preset vocabulary belongs to the jar.

**Twenty-one names were retired** by gh95, in three kinds: *never distinct* (`ape_pure`, `bfs`, `sata_mop_widget` — no configuration was lost, since `bfs` always carried `sata`'s plan and `sata_mop_widget` was `sata_mop`'s own object), *name consolidated* (`sata_mop_act_frontier`, surviving as `mop_on_llm_off`), and *finished campaign* (the six gh43 prompt arms, `cal_a1`…`cal_a9`, `sata_mop_activity`, `random`). Retirement ends the ability to launch new runs under a name; recorded results are frozen artifacts and are unaffected. The full list with reasons is `tests/migration/retirements.py`.

**No arm names the binary it runs against** (INV-APV-59). `mop_on_llm_70` used to declare
`expected_jar_git_sha` and `expected_jar_sha256` — the revision and digest of one `ape-rv.jar` build,
as literals — with a guard pairing them to `llm_snap_tolerance_px=150` and a smoke gate comparing the
digest against the jar actually pushed. The jar is built in a sibling repository whose build is not
bit-reproducible, so the same revision produces a different digest on every build: the gate failed on
correct redeployments (the stage-4 jar among them) and passed on stale ones, and a rebuild there
became an edit of a Python constant here. Which jar ran is still recorded, by measurement:
`_capture_llm_provenance()` digests the jar it is about to push into the run's `jar_sha256`. Both
names are also out of `APERV_ORCHESTRATION_KEYS`, so `configure()` rejects them — the declaration
cannot return through experiment YAML or the tool DSL. Which build is installed is a deployment
decision, stated in the deployment, not in `tool.py`.

**There is no arm-explicitness guard any more.** `ARM_DEFINING_KEYS`, `_ARM_DEFINING_EXEMPT` and `LLM_ARM_KEYS` validated Python constants against other Python constants, which was the best available check while the jar had no contract. Stage 2 gave it one: an unknown key, a retired key, or a non-neutral value of an inactive feature aborts the run before step 1. Per owner decision D1 nothing replaces the guards at runtime — `tool.py` never parses `RUN_START` or any other jar output (INV-APV-43), and drift auditing stays post-hoc analysis of the trace.

## Configuration Flow

1. `configure(config)` validates strategy eagerly (catches typos before device interaction).
2. `execute_tool_specific_logic(task, app)`:
   - Resolves `ape-rv.jar` by priority: module dir > `$RVSEC_HOME/ape/target/` > `$TOOLS_DIR/aperv/`.
   - Pushes JAR to `/data/local/tmp/ape-rv.jar`; `system-broadcast.json` to `/data/local/tmp/` (optional).
   - MOP variants: derives `<results_dir>/<apk_name>.mop.json` from the full static-analysis JSON (cache hit when the recorded `source.digest` matches, otherwise derive + atomic write) and pushes **only that artifact** to `/data/local/tmp/mop-artifact.json`. The source at `<results_dir>/<apk_name>.json` is never modified and never pushed. A MOP arm with no static-analysis JSON, or whose derivation fails, raises `RVToolExecutionError` — it does not degrade to a MOP-labelled SATA run.
   - Generates + pushes `ape.properties`, then runs `adb shell CLASSPATH=... app_process`.

`APERV_PROPERTY_MAPPING` translates Python config keys → Java `ape.properties` keys. Keys not in the mapping (e.g. `strategy`, `mop_data`) are Python-only and never written to properties.

## Key Design Decisions

- **Working dir `/system/bin`**: APE-RV needs system-level resource resolution; `/data/local/tmp/` causes `ClassNotFoundException` on some API levels.
- **Shared `process_pattern`** `com.android.commands.monkey`: shared with the builtin `ape` tool — the two must not run concurrently on the same device.
- **Timeout as expected exit**: exploration runs to the time limit; `RVCommandTimeoutError` → `RVToolTimeoutError` (completed run, not failure).
- **Non-zero exit is normal**: APE-RV exits non-zero when it detects app crashes during exploration.
- **LLM URL override**: `APERV_LLM_BASE_URL` overrides `llm_url` for Docker/non-emulator setups (emulator uses `10.0.2.2` host loopback).

## Two trace formats are parsed in this repository, on purpose

From stage 4 of the APE-RV re-architecture the `.trace` is NDJSON — one
`StepRecord` per exploration step — and `analysis/trace_ndjson.py` is the only
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

**A consequence worth stating, because it looks like a bug and is not.** Every
trace recorded before stage 4 is legacy format, so `clock_logcat_join.py` now
reports zero steps for those runs and their violations come back `UNALIGNED`.
The runs stay in the report with their denominators — the violation series comes
from the logcat, which stage 4 does not change — and no format sniffer or
fallback branch is to be added.

## Gotchas

- `ape-rv.jar` is gitignored. The Docker image builds it at image-build time (`docker/rvandroid/Dockerfile` clones `https://github.com/phtcosta/ape.git`, `mvn package`, copies `target/ape-rv.jar` into the module dir = priority-1 path). Standalone runs must build/place it manually, or `_resolve_jar_path()` raises `RVToolExecutionError`.
- **The jar must postdate stage 2 of the APE-RV re-architecture, or every arm silently collapses to jar defaults.** Arms are `preset + overrides`, so the properties file leads with `ape.preset=<name>` and carries only the deltas. A jar built before `rearch-02-runspec` has no `Presets`/`KeyOwnership` resolution: it treats `ape.preset` as an unknown key and ignores it, and the keys the preset would have supplied are simply absent from the file — so the run executes on `Config` defaults while the results directory still carries the arm's name. The jar installed in this module is dated 2026-07-31 and predates it; rebuild from branch `rearch` before any campaign runs these arms. This is a deployment precondition, not something the tool can detect: nothing is read back from the jar (INV-APV-43).
- The `+45s` grace on the command timeout lets APE-RV flush its WTG model and emit the coverage dump before the process is killed. The value is a hypothesis about censored teardown durations, not a measurement: among iter0 runs whose teardown completed, the overrun reaches 12,991 ms with 32 runs stacked against the previous 15 s ceiling and none beyond it.
- Empty (0-byte) trace file = silent startup crash; logged as a warning, not an error (coverage may still come from logcat).
- Static-analysis JSON for MOP variants must exist at `<task.results_dir>/<apk_name>.json`. If it is missing, the task **fails** — a MOP arm that cannot arm used to warn and run as pure SATA under a MOP label, which is indistinguishable from a real MOP arm in the results directory.
- The device receives the derived projection, not the producer's JSON. That is what removed the jar's whole-file parse of the call graph and, with it, the ~32 MB footprint reject that made call-graph-heavy apps abort with 0 steps in MOP arms while the `sata` baseline explored normally — a per-app fairness gap rather than a crash.
- **The widget-flag semantics changed with gh96 (retired `INV-APV-32`).** The deleted compaction step wrote `handlerReachesTarget = handlerDirectlyReachesTarget = reachesTarget(handler)` onto every listener, which made the jar take its producer-precedence branch on every widget: `directMop` became a synonym of the any-depth bit, so every flagged widget scored at `ape.mopWeightDirect`, and the D8 synthetic-lambda recovery — which lives only in the other branch — never ran in production. The generator restores the producer's two axes (`direct` = 0-hop, `transitive` = any depth, `direct` implying `transitive`) and applies the recovery to both. Measured over the pinned 345-app corpus: flagged widgets rise 3,733 → 4,965 (the recovery reaching 10 apps, 1,232 widgets), and every previously flagged widget moves from the direct tier to the transitive tier uniformly. **Runs before and after gh96 are not substrate-comparable**; no campaign may mix arms across the cut.
- The artifact is device input only. No module outside `aperv-tool` may read a `*.mop.json` (INV-ANA-53) — it is a lossy projection and a metric computed over it would answer a different question under the same name. `TestMopArtifactAudit` enforces this.
- Cache freshness is the SHA-256 recorded in `source.digest`, not mtime: mtime does not survive a copy, a resume or a container boundary. A corrupt or unreadable cached artifact is a miss, not a failure.
