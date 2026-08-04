# Proposal: Experiment Arms Become Preset + Overrides

**GitHub Issue**: #95
**Track**: Full SDD
**Counterpart of**: `phtcosta/ape` change `rearch-05-thin-python-arms` (stage 5 of 7 of the APE-RV
re-architecture). This repository holds roughly 95% of that stage.

## Why

What an experiment arm *means* lives in Python. `tool.py` hardcodes 29 variant dictionaries expanded
through a 51-pair `APERV_PROPERTY_MAPPING` into 18–33 `ape.properties` lines per arm, guarded by
pytest suites that validate Python constants against other Python constants (the
INV-APV-13/14/15/17/19/26/27 family). The jar had no contract to check any of it against: an unknown
key was inert, a missing key fell back to a `Config` default, and a Python↔Java divergence was
silent. The re-architecture calls this split-brain V20.

Stage 2 of the re-architecture ended that asymmetry on the jar side. `Presets.java` now holds the
four campaign arms as base key vectors (`aperv`, `mop`, `llm`, `llm_mop`, selected by `ape.preset`),
`KeyOwnership.java` declares every accepted `ape.*` key with its type and default, and resolution is
total and fail-fast — an unknown key, a retired key, or a non-neutral value of an inactive feature
aborts the run before step 1. With the presets resident in the jar, the Python side stops duplicating
them: **an arm becomes a preset name plus an explicit dict of override deltas.**

The jar becomes the sole authority on what a preset means. Python remains the sole authority on the
experimental matrix — which arms exist, their frozen names, and their deltas.

## What Changes

- **BREAKING**: the 29-variant surface is reduced to **eight names carrying seven distinct
  configurations**, all re-expressed as `preset + overrides`. The per-arm flag vectors and the
  substrate spread dicts (`_BASELINE_ARM_FLAGS`, `_APE_PURE_ARM_FLAGS`, `_MOP_SUBSTRATE`,
  `_LLM_FLAGS`, `_FRONTIER_SUBSTRATE`, `_MOP_OFF_OVERRIDES`, `_CAL_LLM_COMMON`) are **deleted, not
  deprecated** (P3). Four survivors are one-to-one with the jar's presets and carry nothing but the
  server URL where an LLM is involved — `sata` (`aperv`), `sata_mop` (`mop`), `sata_llm` (`llm`),
  `sata_mop_llm` (`llm_mop`) — `default` is bound to `sata`, and the three E3 decisive-run arms carry
  the reach package and its single-factor contrasts. `throttle_ms=200` disappears from all of them:
  the `aperv` preset already states `ape.defaultGUIThrottle=200`.

- **BREAKING**: 21 names are retired, in three kinds the migration record keeps apart. *Never
  distinct*: `ape_pure` (no structural-purity preset exists — `ape.apePureMode` is a retired key
  whose abort message reads *"purity is structural: a feature absent from the plan does not exist"*,
  and owner decision D3 descopes the stock-APE mode), `bfs` (never an agent type —
  `ApeAgent.createAgent` accepts only `sata`, `random` and `replay`, so it always carried `sata`'s
  configuration), and `sata_mop_widget` (one object under two names). *Name consolidated*:
  `sata_mop_act_frontier`, whose effective configuration is byte-identical to `mop_on_llm_off` and
  survives under that name. *Finished campaign*: the six gh43 prompt arms, the nine `cal_a1`…`cal_a9`
  calibration arms, `sata_mop_activity` and `random`. Retirement ends the ability to launch new runs
  under a name; it does not touch recorded results, which are frozen artifacts.

- `_push_properties()` writes `ape.preset=<name>` first, then `ape.mopDataPath` when the derived MOP
  artifact was pushed, then one line per `overrides` entry. The full 51-pair expansion loop is
  deleted. An override key absent from `APERV_PROPERTY_MAPPING` raises `ConfigurationError` before
  any device push.

- The strategy whitelist shrinks from `["sata", "random", "bfs", "dfs"]` to `["sata", "random"]` —
  the deletion stage 2 delegated to this stage. Accepting `bfs`/`dfs` Python-side would let a run
  pass local validation and abort on the device, which is the silent-degradation class stage 2
  exists to remove.

- **One dead key is deleted, not two.** `mop_weight_activity → ape.mopWeightActivity` is retired in
  the jar's `KeyOwnership` table. The `ape` change also lists `ape_pure_mode`, but `gh93` already
  removed it from this repository — the mapping goes 51 → 50 pairs. A sweep of the remaining 50
  against the jar's 111-key accepted vocabulary found **no further dead entry**;
  `llm_snap_tolerance_px` and `llm_max_tokens` are live jar keys and stay mapped.

- **INV-APV-14 is retired** with the dicts it audited, along with `ARM_DEFINING_KEYS`,
  `_ARM_DEFINING_EXEMPT` and `LLM_ARM_KEYS` and the guard tests they feed. The substitute is
  recorded, not assumed: (a) jar-side fail-fast resolution, which catches at run time — with an
  abort — the errors the guards approximated at test time, and (b) the one-time regeneration diff
  proving the migration preserved the calibrated grid. Per owner decision D1 **no runtime
  echo-vs-intent validation is added anywhere**: `tool.py` never parses `RUN_START`, and drift
  auditing stays post-hoc analysis of the trace.

- **Debt inherited from gh88's archive is paid here.** Syncing `gh88-cal-llm-control` (archived
  2026-08-03 at 47/58) pushed the `cal_*` arm tier and the `LLM_ARM_KEYS` explicitness guard into the
  main `aperv` spec. The guard dies with the per-arm dicts and the tier dies with the arms, so this
  change removes both from the spec as well as from `tool.py`.

- **A defect on the operator's path is closed in the same change that would create it.** The tool DSL
  (`aperv:<variant>@key=value`) delivers overrides at the top level of the config —
  `ToolFactory` merges `{**variant_config, **tool_config.parameters}` — while the new
  `_push_properties()` reads only `overrides`. Left alone, a DSL override would be discarded in
  silence: no property line, no error, and a run executing a configuration nobody asked for.
  `configure()` therefore folds mapped top-level keys into `overrides` and raises on any top-level key
  it cannot honour.

- **The gate is the regeneration diff**, and it is one-time by construction. For each surviving arm,
  the effective configuration produced by `preset + overrides` must equal the one produced by today's
  dicts. The 21 retired names appear through an explicit retirement list carrying each one's kind,
  never as silent absences; for `sata_mop_act_frontier` the check additionally proves that
  `mop_on_llm_off` reproduces its baseline, which is the whole justification for consolidating it.
  After owner sign-off the test is deleted and the baseline archived — keeping it alive would
  recreate INV-APV-14 under another name.

- **This change is entirely offline.** No emulator, no device, no jar execution. The preset vectors
  and the accepted-key vocabulary are read from the `ape` source checkout; the diff is a host-side
  computation. The one execution that proves the deployed jar honours `ape.preset` belongs to
  `gh97-rearch-ab-gate`, which is already the empirical gate with a rebuilt jar.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `aperv`: arm definitions restated as preset + overrides over eight names, with 21 retirements;
  `configure()` validation extended with the DSL fold and its whitelist shrunk; the
  properties-generation contract replaced by preset + pass-through; the arm-explicitness requirement
  and the calibration-mapping requirement removed with their substitutes recorded; the regeneration
  migration check added. Invariants INV-APV-05 and INV-APV-42 are amended; INV-APV-16 and INV-APV-17
  are retired with the arms they governed.

## Impact

**Modules**: `modules/aperv-tool` only — `src/aperv_tool/tools/aperv/tool.py` (variant dicts,
`APERV_PROPERTY_MAPPING`, `APERV_AVAILABLE_STRATEGIES`, `_push_properties`, `configure`),
`tests/test_aperv_tool.py` (guard-test retirement and restatement), `CLAUDE.md` and
`docs/architecture.md`. Requirements touched: **FR18**, **FR19**, **FR20**; **NFR05** (the
calibration-mapping requirement being removed).

**No `experiment` delta.** The issue lists `domain:experiment` with the qualifier *"if the CLI names
change"*. They do not: no arm name is added or renamed, and neither `modules/rv-experiment` nor
`modules/rv-platform` references any variant name — the tool DSL resolves them through
`get_variants()`. Creating an empty delta to satisfy the label would document nothing.

**No `calibration-control` delta.** `experimento-cal/scripts/*` resolves arms through
`get_variants()`, so with `cal_a1`…`cal_a9` retired it can no longer resolve them at all. This is
recorded rather than repaired: the calibration campaign is
finished (its journal's last calibration entry is 2026-07-24, followed only by the decisive run's
`FREEZE-PREREGISTRO` of 2026-08-01), and `gh94` already declares `experimento-cal/scripts/*` a
frozen-corpus reader that SHALL NOT be migrated, adapted or deleted (INV-APV-55). Adapting the
scaffold here would contradict that carve-out and maintain a consumer of a dataset that will not be
regenerated.

**Cross-change coordination — three open changes modify the same two requirements.** `gh96` modifies
both `ApeRVTool Execution Flow (FR18, FR19)` and `ape.properties Generation`; `gh94` modifies
`ApeRVTool Execution Flow` again, already composed over `gh96`'s text. Neither is synced into
`openspec/specs/` yet. A MODIFIED block replaces the whole requirement at archive time, so whichever
change archives last silently drops the others' content unless its block already contains it. This
change therefore writes its MODIFIED blocks **on top of the existing ones**: the execution-flow block
is `gh94`'s version with only step 5 changed, and the properties block is `gh96`'s version with the
mapping table and output contract rewritten. The three then compose in any archive order.

**Depends on**: stage 2 of the `ape` re-architecture (`rearch-02-runspec`, archived 2026-08-04) for
`Presets.java`, `KeyOwnership.java` and fail-fast resolution. Those exist on branch `rearch`; the
`ape-rv.jar` currently deployed in `modules/aperv-tool` predates them, so it must be rebuilt from
that branch before any campaign runs the re-expressed arms. A pre-stage-2 jar ignores `ape.preset`
as an unknown key and every arm silently collapses to jar defaults — which is why the deployment is
recorded as a precondition rather than left implicit.

**Comparability**: arm names are frozen throughout (the variant string is the resume-identity key and
the consolidation column key). Any intentional divergence in effective configuration requires owner
approval and a new arm name, never a silent edit.

**Satisfies** task 8.5a of the `ape`-side `rearch-05-thin-python-arms`, which reserves this
repository's counterpart to its own OpenSpec workflow rather than editing `openspec/specs/` by hand.
