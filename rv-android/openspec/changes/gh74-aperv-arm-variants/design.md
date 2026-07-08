## Context

The comparable-arm experiment (memo §3) needs each APE-RV run to be a clean, isolated treatment: original
APE (`ape_pure`), aperv-without-MOP (`sata`), and a decomposition of the MOP reach mechanism
(`sata_mop_widget` → `sata_mop_activity` → `sata_mop_act_frontier`). Today that is impossible because
`aperv` variants inherit exploration behavior from the jar's `Config` defaults. On the `mop-fairtest` jar
`frontierBoostWeight` defaults to `200` and `activityTriggerEnabled` to `true` (`Config.java:195,148`), and
neither is in `APERV_PROPERTY_MAPPING` (tool.py:74-113) — so those RV extensions are silently ON in every
arm, including the intended non-MOP baseline (memo §3 blocker).

The APE-RV re-architecture (`ape-mop-fairtest/docs/20260708_arquitetura_separacao_aperv.md`) fixes the jar
side: it introduces the `apePureMode` kill-switch and flags for the previously flag-less behaviors
(`formCompletionEnabled`, `stepTelemetryEnabled`, `modelMenuEnabled`, `leastVisitedPriorityTiebreak`,
`treeEnhancementsEnabled`, `activityBudgetEnabled`) and the reach strategies (`mopActivitySourceComponents`,
`mopFrontierWeight`, `triggerMopFirst`, `llmPercentageNoSubstrate`). This change is the rv-android
counterpart (design §6.1): complete the mapping, freeze the arm variants, and add a guard so the "arm =
explicit variant dict" contract cannot rot. It is Python-only and touches one module (`aperv-tool`).

References: proposal.md; specs/aperv/spec.md (INV-APV-13..19); the arm matrix (design §4); the frozen
`ape.*` names (design §3); `Config.java` (mop-fairtest) for the baseline default values.

## Architecture

```
 experiment DSL  aperv:<variant>[@seed=n]
        │
        ▼  ToolFactory: merge get_variants()[variant] ⊕ parameters  →  _tool_config
        │
        ├── APERV_PROPERTY_MAPPING (extended)  ──►  _push_properties()  ──►  ape.properties (device)
        │        (every ARM_DEFINING_KEYS member has an entry — INV-APV-13)      arm-defining ape.* lines
        │
        └── _build_main_command()  ──►  app_process … --ape <strategy> [-s <seed>]   (INV-APV-18)
                                                                          │
 guard pytest (tests/test_aperv_tool.py):                                 ▼
   (i)  every ARM_DEFINING_KEYS ∈ APERV_PROPERTY_MAPPING       mop-fairtest jar honors -s
   (ii) every non-exempt variant sets every ARM_DEFINING_KEYS  (Monkey -s SEED → RandomHelper.seed)
```

### Key Components

| Component | Responsibility | Change |
|-----------|---------------|--------|
| `APERV_PROPERTY_MAPPING` (tool.py:74-113) | Python key → `ape.*` name | Add the 19 arm-defining entries (8 existing-but-unmapped RV flags + 11 new) |
| `ARM_DEFINING_KEYS` (new constant, tool.py) | Single source of truth for the guard | Enumerate the 19 arm-defining Python keys |
| `_ARM_DEFINING_EXEMPT` (new constant, tool.py) | Named exemption set | The six gh43 `sata_mop_llm_<prompt>` names |
| `get_variants()` (tool.py:201-301) | Frozen variant dicts | 4 new variants; make existing explicit; `sata_mop`→alias of `sata_mop_widget` |
| `_build_main_command()` (tool.py:487-542) | Build `app_process` argv | Append `-s <seed>` when `_tool_config` has `seed` |
| `tests/test_aperv_tool.py` | Guard + per-arm assertions | Add guard tests (INV-APV-13/14) + arm-value tests |

To avoid duplicating ~19 keys across ~11 variants, the implementation SHOULD define a shared
`_BASELINE_ARM_FLAGS` dict (RV exploration ON, MOP/reach/frontier/trigger off) and a `_MOP_SUBSTRATE`
dict (mop_data + 4 weights), then spread + override per arm (e.g. `{**_BASELINE_ARM_FLAGS, "strategy":
"bfs"}`). This keeps the arms readable and the guard green without copy-paste drift (P1). `sata_mop` and
`sata_mop_widget` MUST reference one shared object so INV-APV-16 holds by construction.

## Mapping: Spec → Implementation → Test

| Requirement / INV | Implementation | Test |
|-------------------|----------------|------|
| INV-APV-13 (mapping completeness) | 19 new `APERV_PROPERTY_MAPPING` entries | `test_all_arm_defining_keys_are_mapped` |
| INV-APV-14 (variant explicitness) | `_BASELINE_ARM_FLAGS` spread into every non-exempt variant | `test_non_exempt_variants_set_all_arm_defining_keys` |
| INV-APV-15 (`ARM_DEFINING_KEYS` constant) | module-level `frozenset` | `test_arm_defining_keys_excludes_mop_data_and_strategy` |
| INV-APV-16 (`sata_mop` alias) | shared dict object | `test_sata_mop_is_alias_of_widget` |
| INV-APV-17 (gh43 exempt) | `_ARM_DEFINING_EXEMPT` named constant | `test_exempt_set_is_exactly_the_six_gh43_variants` |
| INV-APV-18 (seed → `-s`) | `_build_main_command` append | `test_seed_passed_as_dash_s`, `test_no_seed_omits_dash_s` |
| INV-APV-19 (flag policy) | INV-13 + INV-14 together | the two guard tests (executable policy) |
| Variants requirement (arm matrix) | 4 new + explicit existing | per-arm value tests (widget/activity/act_frontier/ape_pure/sata) |

## Goals / Non-Goals

**Goals:**
- Every non-exempt arm is defined entirely by its variant dict; no arm-defining flag falls back to a jar
  default. Enforced by a guard test, not discipline.
- The 4 new arms exist with the exact matrix values (design §4); `sata_mop` keeps working as an alias.
- The experiment seed reaches the jar (`-s`), closing the rv-android-side "seed ignored" gap.

**Non-Goals:**
- Any change to the jar / `Config.java` (repo APE-RV) — the sibling changes own flag semantics and
  defaults. This change only pushes properties/CLI.
- New LLM arms (round 2), and weight calibration (`mop_frontier_weight` × `frontier_boost_weight`) — done
  via DSL override in smokes, not new variants.
- Changing the DSL, the `ToolFactory` merge, or `experiment`/`tools` specs — the `@override` and merge
  semantics are unchanged and already specified (INV-EXP-*, INV-TOOL-05).

## Decisions

**D1 — `ape_pure` sets the kill-switch AND every RV flag off explicitly (belt-and-suspenders).** The jar's
`apePureMode=true` already forces RV off, so listing all offs is redundant for the jar. It is kept anyway
so (a) the guard test treats `ape_pure` uniformly (it must satisfy INV-APV-14 like any other non-exempt
arm), and (b) the arm is auditable from the pushed `ape.properties` without trusting the kill-switch to be
correct. Alternative (rely solely on `apePureMode`) rejected: it would force a special-case exemption in
the guard and make the arm's behavior invisible in the properties file.

**D2 — MOP weights are NOT in `ARM_DEFINING_KEYS`, but ARE set explicitly in MOP arms.** A null `MopData`
(no `mop_data` push) disables scoring regardless of weight, so the weights cannot contaminate a non-MOP
baseline the way `frontierBoostWeight` does (frontier boosting runs without MOP data). Putting the weights
in the guard would force every baseline arm to carry inert `mop_weight_*=…` lines. Instead the guard set is
the flags that actually change behavior unconditionally; the MOP arms still pin the weights for
auditability. This matches the issue's arm-defining enumeration.

**D3 — Exemption is an explicit named set, not a `sata_mop_llm_` prefix.** A prefix match would silently
absorb a future non-exempt `sata_mop_llm_*` arm into the exemption and defeat the guard. INV-APV-17 pins
the exact six gh43 names.

**D4 — `sata_mop` is an alias by shared object, not a copy.** Referencing one dict guarantees INV-APV-16
holds even if the widget arm is edited later; a copy would drift.

**D5 — `frozen ape.* names taken from the design doc, not from the jar.** The 11 new properties do not yet
exist on any built jar (they arrive with `rv-scoring-pipeline` / `mop-reach-strategies`). The names are
frozen in design §3 and pinned in INV-APV-13. Risk: a name mismatch would make the property inert (the jar
ignores unknown `ape.*`), so the arm would silently not steer. Mitigation: R1 below (a live cross-check
task once the sibling jar is available); until then the names are copied verbatim from the design doc.

**D6 — Seed wiring is included in this change (author decision beyond the issue's "verification-only"
framing).** The issue scoped seed as investigation and said "if the defect is in the jar, file an issue in
the APE-RV repo (the fix is not in this change)". The investigation's finding is the opposite: the
**jar is correct** on `mop-fairtest` (it parses `-s SEED` at `Monkey.java:881-882` and seeds
`RandomHelper` at `Monkey.java:731`, INV-EXPL-14), so the conditional never fires. The defect is entirely
in `aperv-tool._build_main_command`, which never emits `-s`. Because (a) it is rv-android code, (b) it is a
one-line-shaped, well-understood append, and (c) it is a hard prerequisite of the paired-by-app experiment
this whole change enables, the fix is specified here as INV-APV-18 rather than deferred. This is flagged
for reviewer confirmation. If the reviewer prefers to keep this change strictly to
mapping+variants+guard, INV-APV-18 and its requirement can move to a one-task follow-up change without
affecting the rest.

## Data Flow

1. The experiment DSL resolves a variant name (and optional `@seed=n`) into a `ToolConfig`. `ToolFactory`
   merges `get_variants()[variant]` with `parameters` (parameters win) → `_tool_config`.
2. `_push_properties()` writes one `ape.<Name>=<value>` line for each `_tool_config` key that is in
   `APERV_PROPERTY_MAPPING`. After this change that includes every arm-defining flag the variant set.
3. `_build_main_command()` builds the `app_process` argv, appending `-s <seed>` iff `_tool_config` has a
   `seed`.
4. On device, the jar's `Config` loads `ape.properties`; `Monkey` parses `-s` and seeds `mRandom` +
   `RandomHelper`. An unknown `ape.*` (name mismatch) is ignored.

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| Arm-defining flag missing from a variant | authoring drift | guard test (ii) fails at CI | add the key to the variant (or `_BASELINE_ARM_FLAGS`) |
| Arm-defining flag missing from mapping | authoring drift | guard test (i) fails at CI | add the `APERV_PROPERTY_MAPPING` entry |
| `ape.*` name mismatch vs jar | design/jar skew | jar ignores unknown property (inert) | R1 live cross-check once sibling jar built |
| Seed configured but not honored | (was) tool.py gap | INV-APV-18 emits `-s`; jar honors it | n/a — closed by this change |

## Risks / Trade-offs

- **R1 — `ape.*` name skew with the not-yet-built jar** → a mismatched property is silently inert, so an
  arm would not steer as intended and the failure is invisible in `ape.properties`. Mitigation: names
  pinned from design §3 (INV-APV-13); a Verification task cross-checks them against the sibling jar's
  `Config.java` once `rv-scoring-pipeline`/`mop-reach-strategies` land (before the experiment runs).
- **R2 — 19 explicit keys × 11 variants is verbose and drift-prone** → mitigated by the shared
  `_BASELINE_ARM_FLAGS`/`_MOP_SUBSTRATE` dicts (D-Architecture) and the guard test.
- **R3 — Reviewer disagrees with including seed wiring (D6)** → isolated in one requirement/INV and one
  command edit; removable to a follow-up without touching the mapping/variants/guard.
- **R4 — `ape_pure` explicit-offs diverge from what `apePureMode` forces** → if a future RV flag is added
  to the kill-switch but not to `ape_pure`'s explicit offs, the arm and the kill-switch could disagree.
  Mitigated: `ape_pure` is built from the same `ARM_DEFINING_KEYS` (all set to off/0), and INV-APV-19
  requires new flags to touch every non-exempt variant.

## Testing Strategy

| Layer | What | How | Count |
|-------|------|-----|-------|
| Unit (guard) | INV-APV-13/14/15/17 | iterate `ARM_DEFINING_KEYS` vs mapping; iterate non-exempt variants | ~4 |
| Unit (arm values) | matrix values for ape_pure / sata / sata_mop_widget / _activity / _act_frontier | assert specific keys per variant | ~6 |
| Unit (alias) | INV-APV-16 | `sata_mop == sata_mop_widget` | 1 |
| Unit (properties) | arm-defining flags reach `ape.properties`; seed excluded | reuse `_push_properties` capture harness | ~4 |
| Unit (command) | INV-APV-18 | `-s <seed>` present/absent | 2 |

All tests run offline (no device) via `pytest modules/aperv-tool/tests/`. No live emulator or jar needed —
the guard operates on `get_variants()` / `APERV_PROPERTY_MAPPING` dictionaries.

## Open Questions

- **R1 cross-check timing**: the live `ape.*` name verification depends on the sibling APE-RV changes being
  built. Until then the names are trusted from the design doc. Non-blocking for authoring; a Verification
  task gates it before the experiment.
- **Do `bfs`/`random` want the RV exploration extensions ON?** This change sets them to the current jar
  default (ON) to preserve today's behavior (P4). If the experiment design later wants pure-baseline
  bfs/random with RV off, that is a variant-value change (one commit), not a structural one.
