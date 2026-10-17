<!-- Subagent dispatch plan (maximum parallelism by file ownership):

     Wave 0 (serial, one agent, short): task group 0. It fixes the only shared Python contract, the reader's
       declarations, so that the consumer front (A) and the reader front (R) never edit the same file.

     Wave 1 (parallel, seven agents, disjoint files), all against key/telemetry contract v3.2 (ape 16b185f4; design D16):
       T  tools/aperv/tool.py, tests/test_aperv_tool.py
       D  tools/aperv/derive_mop_artifact.py, tests/test_derive_mop_artifact.py           (not blocked; start first)
       R  analysis/trace_ndjson.py (bodies only), tests/test_trace_ndjson.py, tests/fixtures/trace_ndjson_*.ndjson
       A  analysis/gates.py, screen_visits.py, step_bundle.py, runspec.py, coverage_dump.py, state_coverage_join.py
          and their tests (test_gates, test_screen_visits, test_step_bundle, test_runspec, test_coverage_dump,
          test_state_coverage_join, test_baseline_*); baseline_ape.py/baseline_droidbot.py were finished in wave 0
       M  tests/migration/*
       E  modules/rv-android-core/src/rv_android_core/constants.py, modules/rv-android-core/tests/test_constants_registry.py,
          modules/rv-experiment/src/rv_experiment/__main__.py, modules/rv-experiment/tests/test_cli_aperv_llm_url.py (new)                      (APERV_LLM_BASE_URL, D14)
       W  docs: modules/aperv-tool/{CLAUDE.md,README.md,docs/architecture.md}, docs/architecture/{ape-rv,rv-experiment}.md,
          .claude/skills/rv-experiment-compare/{SKILL.md,scripts/gen_compare.py docstring}

     Wave 2 (serial, coordinator): group I. The module suite is green as a whole, and the work is re-checked against the
       contract commit of APE 3.10.
     Wave 3 (with the ape and mini-experimento sessions): group S. The jar pairing (APE 11.9) and the device smoke,
       which is the short pre-run of the mini-experimento session's comparison (APE 12.1 hands off to it).
     Wave 4 (serial): group C. Close.

     Rules for every subagent prompt: no git state commands (stash, checkout, reset, branch, switch) and no commits;
     edit only the files of the agent's front; run tests with `--import-mode=importlib -o "addopts="` from the
     worktree's .venv. The coordinator commits each front by path (`git commit -- <paths>`).
     Critical path: 0 → R/A/T (longest is R) → I → S (gated by APE 11.9/12.1) → C.
     ~38 files; seven parallel dispatches in wave 1. -->

Cross-repository dependencies (APE-RV `openspec/changes/isolate-guidance-groups/tasks.md`):

| This change | Waits for APE | APE waits for this change |
|---|---|---|
| T, R, A, M (written against contract v3.2) | 3.10 is re-checked in I.2, not waited on | — |
| E (`APERV_LLM_BASE_URL`) | — | — |
| D (derive `data` member) | — | 5.6, 10.4, 11.7 (re-derive the APE fixtures) |
| M.4 (offline cell gate) | 11.6 (`cells/<cell>.run_start.json`) | — |
| S.1 (jar into this worktree) | 11.9 (`mvn install`, `rvsec_home` = this worktree's rvsec root) | — |
| S.2–S.4 (device smoke, `RUN_START` gate) | 12.1, run as the `mini-experimento` session's short pre-run | 12.1 runs through this worktree's jar and sources |

## 0. Wave 0 — setup and the reader's declarations (serial)

- [x] 0.1 In the worktree root (`…/worktrees-aperv/isolate-guidance-groups/rv-android`), run `uv sync` and confirm `modules/aperv-tool` tests import from this worktree's `.venv`
- [x] 0.2 Baseline: `cd modules/aperv-tool && uv run pytest --import-mode=importlib -o "addopts=" -q`; record the pass/skip counts, so a later red is attributable
- [x] 0.3 Back up `modules/aperv-tool/tests/migration/test_decisive_contrasts.py` to `backup/20261017-isolate-guidance-groups/` (P3)
- [x] 0.4 In `analysis/trace_ndjson.py`, declarations only: the `Ownership`, `NavTie` and `ComponentTrigger` dataclasses; the fifteen new `StepRow` fields with `None` defaults (`nav_frontier` defaults to `0`); `activity_has_mop` / `target_activity_has_mop` as `Optional[bool]`; `RunStart.variant`; `TraceReader.run_end` property returning `None`; `SUPPORTED_VERSIONS = {1, 2}` (design § API Design). No parsing yet; the existing suite stays green
- [x] 0.5 In `analysis/baseline_ape.py` and `analysis/baseline_droidbot.py`, add `None` for the fifteen new fields to the row dicts, so `test_baseline_frames.py` parity stays green after 0.4
- [x] 0.6 Run `/rv-test-run aperv-tool`; commit wave 0 by path

## T. Variants, configuration, properties, mapping, push (`tool.py`) — wave 1

- [x] T.1 Replace `get_variants()` with "ApeRVTool Cell Variants": `default` is the same object as `base`; every cell carries `preset` = `variant` = its name and `strategy="sata"`; every cell but `base` carries `static_data="static_analysis"`; `as`, `as_mop`, `as_llm`, `as_mop_llm` carry `broadcast_catalog=True`; `as_llm` and `as_mop_llm` carry `overrides={"llm_url": "http://10.0.2.2:30000/v1"}`. Delete the ten old dicts and their comments (`tool.py:329-541`); the docstring describes the cells (P4)
- [x] T.2 `APERV_ORCHESTRATION_KEYS`: add `variant` and `broadcast_catalog`, replace `mop_data` with `static_data`; `configure()` requires a non-empty `variant` (INV-APV-65); every `mop_data` read becomes `static_data`
- [x] T.3 `APERV_PROPERTY_MAPPING`: delete `mop_target_pick_cap` and `least_visited_priority_tiebreak`; add `addons`, `static`, `mop`, `llm`, `mop_coin_percentage`, `llm_gate_min_actions`, `llm_breaker_failures`, `llm_breaker_open_ms`, `activity_stable_restart_threshold`, `take_screenshot_for_every_step`, `save_gui_tree_to_xml_every_step`, `llm_boundary_top_pct` — 66 entries, grouped and commented by owning group as in "ape.properties Composition"
- [x] T.4 `_push_properties()`: `ape.preset`, `ape.variant`, `ape.staticDataPath` (only when the artifact was pushed), then overrides; no `ape.mopDataPath` left in `src/`
- [x] T.5 `execute_tool_specific_logic()`: catalog iff `broadcast_catalog` and the file exists (INV-APV-10); artifact keyed on `static_data` (INV-APV-45); the comments at `:1313-1322` and `:1364-1368` describe the cells
- [x] T.6 Rewrite `tests/test_aperv_tool.py`: `TestVariants` for the seven names; delete `TestDecisiveRunArms` and `TestDistanceArms`; `TestConfigure` / `TestDslOverrideFold` with cell names, plus the `variant`-missing and `mop_data`-rejected scenarios; `TestPushProperties` for the fixed lines and 66 entries; `TestExecuteMopArtifactFlow` on `static_data`; new `TestBroadcastCatalogPush`; `TestCorpusBasis` on `as_mop`/`base`
- [x] T.6b The comments at `tool.py:376` and `:656-660` state the D14 mechanism: `configure()` reads no environment, `rv-experiment` injects `APERV_LLM_BASE_URL` as a top-level `llm_url` into the LLM cells, and the DSL fold moves it into `overrides`. In `tests/test_aperv_tool.py`, the two `test_env_var_*_at_l2` tests stay (L2 still ignores the variable) and the scenario "LLM URL override via environment variable" gets a test: a top-level `llm_url` beside the cell default wins and writes exactly one `ape.llmUrl`
- [x] T.7 Grep `modules/aperv-tool/src/aperv_tool/tools` for `sata_mop`, `mop_on_llm`, `mop_off_llm`, `mopd_on`, `mop_data`, `mopDataPath`, `mopTargetPickCap`, `leastVisitedPriorityTiebreak`: no hit
- [x] T.8 Run `/rv-test-run aperv-tool` (front's tests only: `tests/test_aperv_tool.py`)

## E. `APERV_LLM_BASE_URL` at the entry point (D14) — wave 1, not blocked

- [x] E.1 `rv_android_core/constants.py`: `ENV_APERV_LLM_BASE_URL = "APERV_LLM_BASE_URL"` beside `ENV_HUMANOID_URL`; `tests/test_constants_registry.py` (INV-CORE-30): the name pattern admits `APERV_LLM_BASE_URL` as its one non-`RV_*` user-facing name, beside the three installation paths (INV-EXP-41)
- [x] E.2 `rv_experiment/__main__.py`, beside the `RV_HUMANOID_URL` block (`:1369-1379`): read the variable through the constant; when non-empty, for each `ToolConfig` named `aperv` whose variant definition in `ToolRegistry` carries `overrides.llm_url` and whose `parameters` lack `llm_url`, set `parameters["llm_url"]`; the comment states the precedence DSL > variable > cell default and why non-LLM cells get nothing (INV-EXP-41). The lookup reads the registry, not a list of cell names
- [x] E.3 New `modules/rv-experiment/tests/test_cli_aperv_llm_url.py`: the five scenarios of "aperv LLM URL Resolved at the Entry Point" (LLM cells injected; `base`/`as_mop` untouched; DSL wins; unset/empty injects nothing; reader set pinned to `__main__.py`, none in `aperv-tool/src`). Exercise the resolution through the same function the CLI calls, with the registry populated by importing `rv_platform` as `__main__` does
- [x] E.4 Run `/rv-test-run rv-experiment` (the new file and `test_constants.py`) and `/rv-test-run rv-android-core` (constants tests)

## D. Derive: the intent-filter `data` member — wave 1, not blocked (start first)

- [x] D.1 `_reduce_filter_data(data)` in `derive_mop_artifact.py`: `schemes`, `hosts`, `paths`, `pathPrefixes`, `mimeTypes` via `_string_list`, empty lists omitted, `None` when all five are empty; called from `_project_component` for receivers and services (`:1494-1504`); `ports` and `pathPatterns` never emitted
- [x] D.2 Docstrings of `_project_components` / `_project_component` (`:1404-1480`): the filter carries `data`; every component is projected whatever its `reachesTarget`, because the trigger pool reads no MOP data
- [x] D.3 Tests in `tests/test_derive_mop_artifact.py`: the receiver-filter scenario (five lists kept, `ports`/`paths`-empty/`pathPatterns` absent, `data` absent when all empty, `formatVersion` 2); all components projected at `reachesTarget: false`; the cryptoapp ground truth and the streaming byte-identity tests unchanged
- [x] D.4 Run `/rv-test-run aperv-tool` (`tests/test_derive_mop_artifact.py`); the coordinator commits D first and sends the SHA to the ape session (unblocks APE 5.6, 10.4, 11.7)

## R. Trace reader bodies (`trace_ndjson.py`) — wave 1, after 0.4

- [x] R.1 Version gate on `SUPPORTED_VERSIONS`; `SchemaVersionMismatch` names the supported set; `RunStart.variant` parsed; the module docstring cites both `ape` changes as wire authorities
- [x] R.2 Parse the new members into the declared fields: `own` → `Ownership`, `nav` → `NavTie`, `trig` → `ComponentTrigger`, `cfc`, `draw`, `inp`, `restart`, `bmc`, `strat`, `rot`, `buf`; `navf` joins `_BOOST_FIELDS`; `mopd`/`mops`/`ret`; a wrongly shaped member is malformed, and unknown enum values are carried
- [x] R.3 `ACT.mop` absent → `activity_has_mop = None` on both sides (INV-APV-68; `:806-810`)
- [x] R.4 `run_end` holds the record minus `type`; delete the "RUN_END is deliberately absent" comments (`:84-89`, `:830-836`) and the docstring clause (`:57-58`)
- [x] R.5 Docstrings: `decision_source` with both meanings keyed on `run_start.v` (INV-APV-67); `Counterfactual` says it zeroes only the MOP boosts and exists under `v == 1` only; `scorer_cf` says what it answers; `wtg_source` is `v == 1` only
- [x] R.6 Fixtures: add `mopd`/`mops`/`ret` to a golden step; rename `trace_ndjson_v2_header.ndjson` → `trace_ndjson_v3_header.ndjson` (`v: 3`); write `trace_ndjson_groups.ndjson` (`v: 2`, `variant`, an `ACT` without `mop`, owners `llm`/`mop`/`restart`/`sata`, a step with every new member, `RUN_END` with the eight new counters)
- [x] R.7 Tests in `tests/test_trace_ndjson.py` for every scenario of "NDJSON Trace Reader": invert the `V2_HEADER` tests (`:484-519`) onto the v3 fixture; the cmp162 real-trace check (`:760`) asserts `v == 1`; flip `test_run_end_is_read_by_nothing_and_not_counted_as_malformed` (`:253-272`) to the census scenario; the collection-path test still forbids `RUN_END` in `tools/aperv/*`
- [x] R.8 Run `/rv-doc-code modules/aperv-tool/src/aperv_tool/analysis/trace_ndjson.py`
- [x] R.9 Run `/rv-test-run aperv-tool` (`tests/test_trace_ndjson.py`)

## A. Analysis consumers — wave 1, after 0.4 (codes against the declared fields)

- [x] A.1 `gates.py`: `count_mop_group_signal(reader)` on `v == 2` with the INV-SNK-18 member list ("Validity Gates Run Before Any Outcome"): step rows (including `pick_channel` `mop_coin`/`launcher` and a non-`None` `activity_has_mop`/`target_activity_has_mop`), `UICOV mopReach`, and a `RUN_END` with non-zero `coinMop`/`launches`/`stampHits`/`retired`; on `v == 1` only the steps with a non-zero `mop` or `mop_frontier` boost; gate 1 selects it for any NDJSON trace and keeps `count_forbidden_signal` for legacy streams; `MOP_DATA` never counts
- [x] A.2 `runspec.py`: `attribution_evidence` compares `RunStart.variant` with the manifest arm's cell; `not-run` on `v == 1`; gate 3's evidence form names `variant`
- [x] A.3 `screen_visits.py`: `decision_source_counts` carries `run_start.v`, and cross-version pooling raises (INV-CAN-21); `activity_has_mop` / `target_activity_has_mop` are `Optional[bool]` (INV-CAN-22); no `input_source` aggregate (D15)
- [x] A.4 `step_bundle.py`: the `activity_has_mop` column is null when absent
- [x] A.4b `coverage_dump.py`: `StateCoverage.mop_reach: Optional[int]`; a `UICOV` line without `mopReach` is complete (`:300`); `state_coverage_join.py` carries `None` to `uicov_mop_reach` and its module docstring (`:15-18`) scopes the agreement claim to MOP cells; gate 1 also counts `UICOV` lines carrying `mopReach` (A.1); tests in `test_coverage_dump.py` and `test_state_coverage_join.py`
- [x] A.5 Tests: `test_gates.py` (the clean and counted scenarios, the v2 `ACT`/`RUN_END` scenario, the two v1 scenarios (non-signal, fired boost only), the blind-pattern scenario, the variant attribution); `test_runspec.py` (variant pass/fail/not-run); `test_screen_visits.py` (version-tagged counts, `None` MOP fact, no `input_source_counts` field); `test_step_bundle.py` (null column); `test_baseline_frames.py` (new null columns). Build the `v == 2` rows directly from the wave-0 dataclasses, not from R's fixtures, so A does not wait for R
- [x] A.6 Run `/rv-test-run aperv-tool` (the front's test files)

## M. Migration checks against the jar source (`tests/migration/*`) — wave 1; M.4 also needs APE 11.6

- [x] M.1 `jar_tables.py`: parse the new `Presets.java` (cells composed from group blocks, design D10), against the file APE wave 0 writes; `test_jar_tables.py` pins six cells, the block unions, the new retired keys (`ape.mopDataPath`, `ape.mopTargetPickCap`, `ape.leastVisitedPriorityTiebreak`) and the vocabulary size read from `KeyOwnership.java`
- [x] M.2 `test_mapping_sweep.py` unchanged; it must pass against the `isolate-guidance-groups` checkout
- [x] M.3 Delete `tests/migration/test_decisive_contrasts.py` (backed up in 0.3); `retirements.py`, `capture_arm_baseline.py` and the gh95 migration record stay (archive tooling for recorded arms)
- [ ] M.4 New `tests/migration/test_cells.py` (offline cell gate): preset names = the six cells; `as_mop_llm` keys = union of the four blocks; each `cells/<cell>.run_start.json` has `preset`/`variant` equal to `get_variants()`'s and the expected `features` of contract v3.2 (`mop` with `MOP_LAUNCHER` and without `MENU_GATEWAY`; `COMPONENT_TRIGGER` in the four `as*`)
- [ ] M.5 Run `APE_REPO=<ape checkout on isolate-guidance-groups> /rv-test-run aperv-tool` (`tests/migration`)

## W. Documentation — wave 1 (writes from the specs, not from the code)

- [x] W.1 `modules/aperv-tool/CLAUDE.md`: Overview example, `## Variants` (cells, `default` = `base`, the deleted names, frozen image for old campaigns), Configuration Flow (`static_data`, `broadcast_catalog`, `ape.variant`, `ape.staticDataPath`), Gotchas, the reader's two jar generations; keep the frozen-corpus carve-out
- [x] W.2 `modules/aperv-tool/README.md` and `modules/aperv-tool/docs/architecture.md`: variant table, mapping table, data flow, scenarios (`aperv:as_mop`), reader fields and `run_end`, the two forms of gate 1
- [x] W.3 `docs/architecture/ape-rv.md`, `docs/architecture/rv-experiment.md` (`:101`, `:1343`), `.claude/skills/rv-experiment-compare/SKILL.md` (`:96`, `:154`) and the `scripts/gen_compare.py` docstring (`:14`, `:19`): cells in place of the deleted names
- [x] W.3b `APERV_LLM_BASE_URL` in `modules/aperv-tool/README.md:73`, `docs/architecture.md` (`:49`, `:518`, `:595`, `:709-725`) and `docs/architecture/ape-rv.md:1466`: the variable is read by `rv-experiment` and injected into the LLM cells, `configure()` reads no environment, `@llm_url` wins; `modules/rv-experiment/CLAUDE.md` names the new read beside `RV_HUMANOID_URL`
- [x] W.4 Grep the current-behaviour docs for the deleted names; historical docs, compose files, `scripts/`, `experimento-*/` and `callers/rq_map.toml` (decisive-corpus labels) stay as records

## I. Wave 2 — integration (serial, coordinator)

- [x] I.1 Run the whole module suites: `/rv-test-run aperv-tool` and `/rv-test-run rv-experiment`; fix cross-front breaks (front owners re-dispatched if needed)
- [x] I.2 When APE 3.10 sends the contract commit: diff its `design.md` § Key contract / § Telemetry contract against v3.2 (`16b185f4`); apply any difference through `/opsx:update` and the owning front; then run M.2 against that commit
- [x] I.3 Grep `modules/aperv-tool/src` for `FORMAT_VERSION`, `mop_data` (outside `TraceReader.mop_data`), `MOP_WIDGET`, `wtgsrc` in non-v1 docstrings: no stale reference

## S. Wave 3 — jar pairing and device smoke (with APE 11.9 / 12.1)

- [ ] S.1 The paired jar lands in this worktree's `modules/aperv-tool/src/aperv_tool/tools/aperv/ape-rv.jar` (APE 11.9 with `-Drvsec_home=<this worktree's rvsec root>`); record its sha256 in the report (no literal in source, INV-APV-59)
- [ ] S.2 Smoke (author's decision, 2026-10-17): the short pre-run ("smoke of the smoke") of the `mini-experimento` session's comparison, run by that session on a few instrumented APKs of the Study 03 v2 corpus (rep pack `data/raw/e6-corpus`), each with its compact `.apk.json` beside it; image `phtcosta/rvandroid:0.9.5` with the S.1 jar, `tool.py` and `derive_mop_artifact.py` bind-mounted from this worktree into `/opt/rvsec/rv-android/modules/aperv-tool/src/aperv_tool/tools/aperv/`; the mounted jar's sha256 equals the one recorded in S.1; the six cells, or the subset the author fixes; LLM through the entrypoint's socat for the LLM cells; the platform manages the emulator inside the container. The evidence of S.3/S.4 is that pre-run's results dir
- [ ] S.3 Device cell gate, run from the host with this worktree's `.venv` over the pre-run's results dir: a one-off script (scratchpad, not committed) reads each trace's `RUN_START` through `TraceReader` and compares it with `cells/<cell>.run_start.json` on `preset`, `variant`, `features`, `params`, `inert`, `digest`, masking `run_id`, `t0`, `seed`, `build`, `props_digest`; per-cell report
- [ ] S.4 On the same traces, for the cells the pre-run ran: `v == 2`; gate 1 (`count_mop_group_signal`) is 0 on `base`, `as`, `as_llm` and positive on the three MOP cells; the catalog was pushed only on the four `as*` cells; no malformed record from the new members; zero step records without `dec` (`ape` INV-SEL-05: every record carries `src`, `ch`, `own`); the teardown overrun per run; no UICOV `mopReach` on `base`/`as`/`as_llm` (`ape` D-B14.21)
- [ ] S.5 Report the smoke to the author, to the ape session and to the `mini-experimento` session before group C

## C. Wave 4 — close (serial)

- [ ] C.1 Run `/rv-qa-lint-fix aperv-tool` and `/rv-qa-lint-fix rv-experiment`
- [ ] C.2 Run `/rv-verify aperv-tool` and `/rv-verify rv-experiment`
- [ ] C.3 Invoke `/rv-code-reviewer` via Skill tool
- [ ] C.4 Run `/rv-docs-sync aperv-tool` and `/rv-docs-sync rv-experiment`
- [ ] C.5 At archive, synchronize by hand the § Invariants and § Data Contracts of `aperv` (INV-APV-05, -06, -08, -10, -38, -45, -49, -53, -58, -61, -62 and -09 replaced; -29, -30, -42 retired; -65 to -68 new), of `campaign-analysis` (INV-CAN-07 replaced; -21, -22 new) and of `experiment` (INV-EXP-41 new)
- [ ] C.6 No push and no merge into `modules` without the author's explicit word (D-A19); commits only by path
