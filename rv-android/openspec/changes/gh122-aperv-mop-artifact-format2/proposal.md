GitHub Issue: #122

## Why

The compact MOP artifact that `aperv-tool` derives for APE-RV (`derive_mop_artifact.py`, format 1) carries one yes/no mark per widget, and nothing else of what the static analysis now knows. gh120 (#120) gave every app method its call-graph distance to each monitored target (`distanceTargets`, `reachability[].methods[].targetDistances`), and gh121 (#121) makes the instrumented app write the class of each widget's handler on its accessibility node. Neither reaches the device: the derive does not read the distances, and the artifact has no table that a handler class could be looked up in. The gh120 design (`:86-87`) leaves the derive to the consumer. The consumer, the `ape` change `llm-coordinate-single-base` (design D15, Part B; `ape` commit `093d6ab9`), fixed the wire contract of **format 2**, and its jar reads only format 2. This change implements that contract on the rv-android side and adds the arms that select the jar's new `distance` scoring.

## What Changes

- **BREAKING (artifact):** `derive()` emits `formatVersion: 2` and `generator: "aperv-derive/2"`. Every format-1 member stays with its meaning, and four members are added:
  - `targets`: the number of entries of `distanceTargets`;
  - a per-widget `dist` map (event → up to three `[i, d]` pairs, nearest first);
  - `activityDist` (base activity → up to three pairs);
  - `handlers` (binary class name → `{mop, dist}`), the table APE-RV reads a gh121 stamp through.

  The jar of `llm-coordinate-single-base` rejects format 1, and the current jar rejects format 2, so the two sides ship together.
- **A′ source 3 of `mopActivitiesAugmented`** no longer counts an activity class's own `<init>`/`<clinit>`. Under gh120 every activity constructor is a boundary target, so without the exclusion every activity would enter the augmented census (on the cryptoapp fixture, `MainActivity` leaves it).
- **Host cache keyed on the format.** `_cached_artifact_digest` reuses a cached `.mop.json` only when both its `source.digest` and its `formatVersion` match. Today a format-1 artifact derived before the bump would be reused and pushed, and every MOP arm of the new jar would abort on it.
- **INV-DRV-06 amended:** format 2 may carry integer target indices, integer distances and binary class names. It still carries no method signature, no call edge, and no `*Target` key other than `hasTargetMethods`.
- **Six new mapped keys:** `mop_scoring`, `mop_weight_d1`, `mop_weight_d2`, `mop_weight_d3`, `mop_retire_after` and `mop_launcher_dmax`, mapped to the jar's `ape.mopScoring`, `ape.mopWeightD1..3`, `ape.mopRetireAfter` and `ape.mopLauncherDmax`.
- **Two new arms**, both selecting `mop_scoring: "distance"`:
  - `mopd_on_llm_off`: the reference `mop_on_llm_off` plus `mop_scoring: "distance"`, the third arm of the minimal family the plan analysis proposes (no guidance, E6 mark plus ordered shortcut, distance plus ordered shortcut);
  - `mopd_on_llm_90`: Study 03's E6 arm 4 (`e6_mop_on_llm_90`: E5b's `e5b_m1_v13_A` with `llm_percentage` 0.9) key by key, plus `mop_scoring: "distance"`.
- **Spec drift fixed in passing:** the `ape.properties` mapping table lists `step_telemetry_enabled`, which the code no longer maps and the jar rejects, and omits `corpus_basis`, which the code maps.

**Not in this change:**
- the jar's reader of format 2 and the `distance` scoring (`ape`, `llm-coordinate-single-base`);
- the static analysis of the corpus with the gh120 GATOR;
- the campaign's instrumentation with `--instrumentation-variant dexlib2 --stamp-handlers`, which the Study 03 replication-package side runs.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `aperv`:
  - "MOP Artifact Projection Contents": format 2, the four new members, and the cryptoapp scenario updated to three MOP sub-activities;
  - "MOP-Activity Sets and OPTIONSMENU Records": the source-3 constructor exclusion;
  - "Derived MOP Artifact Generation and Caching": the format in the cache key;
  - "ape.properties Generation": six new mapping entries, 56 in total, and the table corrected;
  - "ApeRVTool Variants": ten names carrying nine configurations;
  - "Decisive Run Arm Set": the two distance arms and their single-factor contrasts;
  - invariants INV-DRV-06, INV-APV-05, INV-APV-42 and INV-APV-47 amended, and INV-DRV-10 added (distance pairs).

## Impact

- **Module:** `aperv-tool` only.
  - `tools/aperv/derive_mop_artifact.py`: the indices, the pair merge and the four members;
  - `tools/aperv/tool.py`: the cache check, `APERV_PROPERTY_MAPPING`, `get_variants()`;
  - tests: `tests/test_derive_mop_artifact.py`, `tests/test_aperv_tool.py`, `tests/migration/test_decisive_contrasts.py`.
- **Cross-repository:**
  - the artifact's consumer is APE-RV's `MopData` (`ape`). Format 2 and the six keys exist only in the jar built from `llm-coordinate-single-base`;
  - `tests/migration/test_mapping_sweep.py` checks every mapped key against the ape checkout's `KeyOwnership.java` (INV-APV-41), so the mapping part of this change is applied against an ape checkout that carries Part B;
  - the derive and the jar bump together, or every MOP arm aborts (INV-MOP-34 on the jar side).
- **Data:**
  - the cached `.mop.json` files of earlier runs are re-derived on first use (they are format 1);
  - a `.apk.json` written before gh120 derives to `targets: 0` with no pair, and the jar runs it without distance data. Nothing guards it: gh120 D9 left that to the corpus hand-off.
- **FRs/NFRs:**
  - FR04, FR05, FR06 (MOP data, WTG, widget map);
  - FR19 (tool configuration);
  - FR20 (variants);
  - NFR04 (deterministic artifact bytes).
