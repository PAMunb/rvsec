## Why

GitHub Issue: #74.

The APE-RV re-architecture (design: `ape-mop-fairtest/docs/20260708_arquitetura_separacao_aperv.md`,
derived from investigation `docs/20260708_investigacao_formas_guiar_mop.md`) separates the original APE
from the RV extensions behind explicit flags, with an `apePureMode` kill-switch. For the comparable-arm
experiment (ape-pure / aperv±MOP / aperv+LLM±MOP), the rv-android side must be able to build a **clean
baseline per arm** — today it cannot.

`get_variants()` (`modules/aperv-tool/src/aperv_tool/tools/aperv/tool.py:201-301`) sets only 2-3 keys per
variant and **inherits the rest from the jar's `Config` defaults**. On the `mop-fairtest` jar,
`frontierBoostWeight` defaults to `200` and `activityTriggerEnabled` defaults to `true`
(`Config.java:195,148`), and **neither key is in `APERV_PROPERTY_MAPPING`** (tool.py:74-113) — so those two
RV behaviors are silently ON in **every** arm, including the intended non-MOP baseline. This confound
blocks the experiment (memo §3). There is also no `ape_pure` arm and no `sata_mop_widget` /
`sata_mop_activity` / `sata_mop_act_frontier` decomposition.

## What Changes

- **Complete `APERV_PROPERTY_MAPPING`** — add every arm-defining flag missing today. Existing RV flags
  not yet mapped: `frontier_boost_weight`, `activity_trigger_enabled`, `sibling_state_penalty`,
  `back_menu_pick_cap`, `foreign_activity_guard`, `tree_package_guard`, `dynamic_epsilon`,
  `heuristic_input`, `fuzz_input_typed`. New flags fixed by the sibling changes `rv-scoring-pipeline` /
  `mop-reach-strategies` (repo APE-RV, branch `mop-fairtest`): `ape_pure_mode`, `form_completion_enabled`,
  `step_telemetry_enabled`, `model_menu_enabled`, `least_visited_priority_tiebreak`,
  `tree_enhancements_enabled`, `activity_budget_enabled`, `mop_activity_source_components`,
  `mop_frontier_weight`, `trigger_mop_first`, `llm_percentage_no_substrate`.

- **Four new frozen variants** — `ape_pure` (`ape_pure_mode=true`, no `mop_data`), `sata_mop_widget`
  (current widget mechanism, the MOP control), `sata_mop_activity` (isolates strategy A′ via
  `mop_activity_source_components=true`), `sata_mop_act_frontier` (reach package: A′+B+E-min). Every new
  variant sets the **complete, explicit** set of arm-defining keys — never inheriting a jar default.

- **Existing variants made explicit** — `default`/`sata` (the aperv-without-MOP baseline: RV exploration
  ON, MOP off, `frontier_boost_weight=0`, `activity_trigger_enabled=false`), `bfs`, `random`, `sata_llm`,
  `sata_mop_llm` gain the full explicit arm-defining set. `sata_mop` becomes a documented **alias** of
  `sata_mop_widget` (identical dict — does not break existing YAMLs). The six `sata_mop_llm_<prompt>`
  variants from gh43 are **frozen exactly as they are** (historical reproducibility) and are **exempt**
  from the explicitness policy.

- **Guard pytest** — (i) every non-exempt variant sets every arm-defining key explicitly; (ii) every
  arm-defining key has an `APERV_PROPERTY_MAPPING` entry. The arm-defining list is a testable module
  constant (`ARM_DEFINING_KEYS`), the single source of truth.

- **Seed propagation** — the paired-by-app design requires the same seed per arm. Investigation
  (this change) confirms the `mop-fairtest` **jar already honors the seed**: `Monkey` parses `-s SEED`
  (`Monkey.java:881-882`) and seeds both `mRandom` and APE's `RandomHelper` with it
  (`Monkey.java:731`, INV-EXPL-14). The defect is on the **rv-android side**: `_build_main_command`
  (tool.py:487-542) never emits `-s <seed>`, so `mSeed` stays `0` → non-deterministic
  (`Monkey.java:670-671`). This change wires a configured `seed` into the command. (Author decision — see
  design Decision D6; the issue framed seed as verification-only, but the finding is that the gap is
  in-repo, not in the jar.)

- **Policy** — a new APE-RV arm-defining flag MUST land its `APERV_PROPERTY_MAPPING` entry **and** its
  per-variant coverage in the same commit (enforced by the guard tests).

**Non-goals**: jar/`Config.java` changes (repo APE-RV — the sibling changes own the flag semantics); new
LLM arms (round 2); weight calibration (`mop_frontier_weight` × `frontier_boost_weight` smoke).

## Capabilities

### New Capabilities
<!-- None. This change modifies the existing aperv capability; it introduces no new spec domain. -->

### Modified Capabilities
- `aperv`: the "ApeRVTool Variants (FR20)" requirement (variant set + arm-defining explicitness),
  the "ape.properties Generation" requirement (`APERV_PROPERTY_MAPPING` completeness), plus two ADDED
  requirements — "Arm-Defining Flag Completeness" (guard pytest + `ARM_DEFINING_KEYS` + flag policy) and
  "Seed Propagation to APE-RV" (`-s <seed>` wiring). New invariants INV-APV-13..19.

<!-- experiment/tools are NOT modified: the variant explicitness is entirely within aperv's get_variants();
     the DSL @override merge (parameters override variant values) and the ToolFactory merge are unchanged,
     already covered by INV-EXP-* / INV-TOOL-05. No delta needed there. -->

## Impact

- **Modules / repos**: `modules/aperv-tool` only (Python) — `tool.py` (`APERV_PROPERTY_MAPPING`,
  `get_variants`, `_build_main_command`) and `modules/aperv-tool/tests/test_aperv_tool.py` (guard tests).
  No changes to `rv-experiment`, `rv-platform`, or `rv-tools`. No jar rebuild.
- **Dependency (soft)**: the `ape.*` property names for the 11 new flags are fixed by the APE-RV changes
  `rv-scoring-pipeline` and `mop-reach-strategies` (branch `mop-fairtest`). The mapping can be authored in
  parallel once those names are frozen; the design records the frozen names. A mismatch would surface as
  an inert (ignored) `ape.property` on the device — safe, but the calibration/experiment would silently
  not steer, so the names are pinned here from the design doc §3.
- **Requirements**: FR18/FR19/FR20 (aperv tool invocation, configuration, variants). Relates to
  INV-TOOL-02 (`default` variant), INV-APV-05 (variant set), INV-APV-08 (mapping).
- **Downstream (out of scope)**: the large paired experiment, weight calibration smokes, and round-2 LLM
  arms consume these variants but are separate work.
