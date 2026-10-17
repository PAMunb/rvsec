## Why

GitHub Issue: none (author's decision, 2026-10-17). This is the sister change of the `ape` change
`isolate-guidance-groups` (APE-RV `openspec/changes/isolate-guidance-groups/`), which is the authority for the
jar side. Both changes are on branch `isolate-guidance-groups` in their repositories. They are merged only after
the mini experiment's results are good and the author decides so explicitly (D-A19). Source of the plan-level
decisions: APE-RV `docs/plans/20261017_isolamento_grupos_aperv.md` (the plan; §9 is this change). Source of the
key and telemetry contract: the `ape` change's `design.md` § API Design (contract v3.1, `ape` `558549a5`, which includes
D-B13 and D-B14).

**Label: MEASUREMENT.** The change alters what an `aperv` arm measures.

Study 03's E6 v2 could not attribute its gain to MOP guidance, because APE-RV's behaviour groups cannot be
switched on and off independently: the "unguided" arm (`mop_off_llm_off`) still consumed static-analysis and MOP
data (plan §2.1). The `ape` change mounts five groups by declaration (BASE, ADDONS, STATIC, MOP, LLM). It replaces
the jar's four presets with six **cell presets**, one per experimental cell (plan §6.2). The current `aperv-tool`
arms are built on the old presets, on per-arm override sets, and on keys the new jar retires. Kept as they are,
every run would abort at `RunSpec` resolution. Only renamed, the names would claim configurations the jar no
longer runs. The trace reader also cannot read the decision fields the new jar writes. And it describes
`decision_source` and `Counterfactual` as causal, which they are not on the `eea2b1a9` jar (plan §9.1).

## What Changes

- **BREAKING — one variant per cell** (plan P-7, D-A12): `get_variants()` returns `base`, `mop`, `as`,
  `as_mop`, `as_llm` and `as_mop_llm`. It also returns `default`, bound to the same object as `base`, because every
  registered tool must carry a `default` variant (`tools` INV-TOOL-02; author's decision, 2026-10-17). Each
  variant is the cell's jar preset plus what the jar cannot know: the server URL on the two LLM cells. What a group
  switches on lives in the jar's group blocks. Doses and other keys are ablations through the tool DSL, never new
  variants.
- **BREAKING — the ten current variants are deleted, without alias** (D-A13). The deleted names are `sata`,
  `sata_mop`, `sata_llm`, `sata_mop_llm`, `mop_on_llm_off`, `mop_off_llm_off`, `mop_on_llm_70`,
  `mopd_on_llm_off` and `mopd_on_llm_90`, and `default` is rebound to `base`. The decisive-run arm set, the
  frozen-name rule (INV-APV-42) and the MOP-off control shape (INV-APV-29, INV-APV-30) are retired with them.
  Campaigns recorded under the old names resume from their frozen image (`rvandroid:0.9.5`). The spec keeps an
  old → nearest-cell table as documentation only.
- **BREAKING — the data key is renamed** (author's decision, 2026-10-17, for the reason of `ape` D-B2): the
  orchestration key `mop_data` becomes `static_data`, and the properties line `ape.mopDataPath` becomes
  `ape.staticDataPath`. The `as` cell pushes the artifact with MOP off, so the old names would lie. The artifact
  goes to the device if and only if the cell mounts STATIC or MOP, which is every cell except `base`.
- **Broadcast catalog follows STATIC** (`ape` D-B13): component triggering becomes a STATIC member, which the four
  `as*` presets mount at 0.03. Those four variants carry `broadcast_catalog=True`, and `system-broadcast.json` is
  pushed only for them.
- **The variant name reaches the trace**: `ape.variant=<variant>` is a fixed second line of `ape.properties`.
  The jar echoes it as `RUN_START.variant`.
- **Property mapping** (P-8): `APERV_PROPERTY_MAPPING` goes from 56 to 66 entries. It gains the four group keys,
  the MOP coin dose, the three LLM gate parameters, and four existing jar keys it lacked
  (`activity_stable_restart_threshold`, `take_screenshot_for_every_step`, `save_gui_tree_to_xml_every_step`,
  `llm_boundary_top_pct`). It loses `mop_target_pick_cap` and `least_visited_priority_tiebreak`, whose jar keys
  are retired.
- **Derive**: each receiver and service intent filter keeps a reduced `data` member (`schemes`, `hosts`, `paths`,
  `pathPrefixes`, `mimeTypes`). The artifact stays `formatVersion: 2`, and the member is additive. Every component is projected,
  whatever its `reachesTarget`. The code already does this, and the spec makes it normative because the trigger
  pool no longer filters on MOP data.
- **Trace reader** (P-9): `trace_ndjson.py` surfaces the new `dec` members (`own`, `cfc`, `draw`, `nav`, `inp`,
  `restart`, `bmc`, `strat`, `rot`, `buf`, `navf`). It also surfaces `mopd`/`mops`/`ret`, which it drops today,
  `RUN_START.variant`, and the `RUN_END` record. The coverage-dump parser accepts `UICOV` lines without
  `mopReach`, which the new jar writes only when MOP is mounted. It accepts `RUN_START.v` 1 and 2, the new jar's version,
  and reports `activity_has_mop` as absent where the jar did not compute it. The docs of `decision_source` and `Counterfactual` say what each
  means on each jar.
- **`APERV_LLM_BASE_URL` works** (author's decision, 2026-10-17): the module's docs and spec promise that the
  variable redirects the LLM cells, and no code reads it. gh55 removed the read from `configure()` for layer purity
  and the entry-point read it announced was never written. `rv-experiment` now reads it, beside `RV_HUMANOID_URL`,
  and injects it as `llm_url` into the `ToolConfig.parameters` of the `as_llm` and `as_mop_llm` cells. A DSL
  `@llm_url` wins over it. No recorded run set it, so no measurement changes.
- **BREAKING (spec) — `RUN_END` in the offline reader** (author's decision, 2026-10-17): INV-APV-53 is narrowed to
  the collection path and the `RUN_END` clause of INV-APV-58 is reversed. `tool.py` still never reads `RUN_END`
  (owner decision D5). The reader exposes the record as a census, like `MOP_DATA`, without interpreting it.
- **Ordering** (plan §9.3): this change lands together with the first `ape-rv.jar` that changes the keys. A
  mismatched pair aborts at `RunSpec` resolution, which is the intended guard. A cell gate compares each cell's
  configuration with the jar's per-cell `RUN_START` fixtures.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `aperv`: the variant set (cells instead of arms) and the removal of the decisive-run arm set. The data-key
  rename. The artifact and broadcast push rules. The variant line of `ape.properties` and the 66-entry mapping. The
  intent-filter `data` member of the artifact. The trace reader's coverage of the new decision record and of
  `RUN_END`. The new cell gate.

- `campaign-analysis`: gate 1 gains an NDJSON form. The anchored `mop=` pattern is blind on every stage-4 trace,
  a pre-existing defect. The new form counts the MOP-group members of the step records and `UICOV mopReach`, and
  `MOP_DATA` and `ACT` never count. Gate 3 uses `RUN_START.variant` as attribution evidence. `screen_visits` tags
  `decision_source` counts with the trace version. `screen_visits` and `step_bundle`
  carry `activity_has_mop = None` through. The arm names in `analysis/` and `callers/rq_map.toml` (cmp162, E3)
  are labels of recorded data and stay.

- `experiment`: the entry point reads `APERV_LLM_BASE_URL` and injects it into the `aperv` LLM cells; the
  Layer-Purity audit names the new reader and its one exception to the `RV_*` naming.

`tools` is not modified: `default` survives.

## Impact

- **Module**: `modules/aperv-tool`:
  - `tools/aperv/tool.py`: variants, mapping, push rules, properties lines;
  - `tools/aperv/derive_mop_artifact.py`: the intent-filter `data` member;
  - `analysis/trace_ndjson.py`: the reader;
  - `analysis/gates.py`, `runspec.py`, `screen_visits.py`, `step_bundle.py`, `coverage_dump.py`,
    `state_coverage_join.py`: the consumers, kept faithful to the new telemetry;
  - `analysis/baseline_ape.py` and `analysis/baseline_droidbot.py`: `None` for the new `StepRow` columns;
  - the vendored `ape-rv.jar`;
  - the tests: `tests/test_aperv_tool.py`, `tests/test_trace_ndjson.py`, `tests/test_derive_mop_artifact.py`,
    `tests/migration/*`, and the trace fixtures;
  - the docs: the module's `CLAUDE.md`, `README.md` and `docs/architecture.md`.
- **Outside the module, code**: `modules/rv-experiment/src/rv_experiment/__main__.py` (the variable's read and
  injection) and `modules/rv-android-core/src/rv_android_core/constants.py` (`ENV_APERV_LLM_BASE_URL`), with a new
  `rv-experiment` test.
- **Outside the module, docs**: the current-behaviour docs that name the deleted variants (`docs/architecture/ape-rv.md`,
  `docs/architecture/rv-experiment.md`, the `rv-experiment-compare` skill examples) are updated. Compose files,
  `scripts/` and `experimento-*/` are records of finished campaigns and stay as they are.
- **Requirements**: FR19 (external tool support), FR20 (per-tool variant system), FR11 (trace parsing for
  analysis), FR04/FR06 (MOP artifact contents), NFR06 (provenance: the variant name in `RUN_START`).
- **Cross-repository**: the tasks that encode the contract are blocked by the `ape` change's wave 0 (contracts),
  and the gate and the jar refresh by its wave 2 (cell `RUN_START` fixtures, `mvn install`). `tasks.md` cites
  them.
- **Not affected**: the builtin `ape` tool, the rv-platform code and the rest of rv-experiment (nothing there
  names an `aperv` variant), the frozen legacy-corpus readers (INV-APV-55), and the artifact format version.
- **Comparability**: no run made with this tree shares a name with an E6 or earlier `aperv` run. That is the
  point of deleting the names.
