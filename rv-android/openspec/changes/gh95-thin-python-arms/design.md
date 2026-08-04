# Design: gh95-thin-python-arms

## Context

Counterpart of stage 5 of the APE-RV re-architecture (`phtcosta/ape`, change
`rearch-05-thin-python-arms`), which places roughly 95% of its work in this repository. See
`proposal.md` for the motivation. Requirements touched: **FR18**, **FR19**, **FR20**, **NFR05**.

**Verified state at HEAD `9e639074`** (re-derived by executing the module, not copied from the `ape`
artifacts, which carry three stale figures):

| Fact | Value | `ape`-side artifact says |
|---|---|---|
| Variants in `get_variants()` | 29 | 29 ✓ |
| `APERV_PROPERTY_MAPPING` pairs | **51** | 52 |
| `ARM_DEFINING_KEYS` | **17** | 18 |
| `_APE_PURE_ARM_FLAGS` | **17** | 18 |
| `LLM_ARM_KEYS` | 11 | 11 ✓ |
| `_ARM_DEFINING_EXEMPT` | 6 | 6 ✓ |
| Arms setting `mop_weight_activity` | 0 | 0 ✓ |
| Dead keys to delete from the mapping | **1** (`mop_weight_activity`) | 2 (`ape_pure_mode` too) |

`ape_pure_mode` was already removed from the mapping by `gh93-retire-ape-pure-mode` (archived
2026-08-04), so this change deletes one entry and the mapping goes 51 → 50.

**The jar side this design reads against.** `rearch-02-runspec` is archived (2026-08-04) and its
classes exist on branch `rearch` of the `ape` worktree:

- `runtime/Presets.java` — the four base vectors, sizes 18 / 22 / 25 / 29.
- `runtime/KeyOwnership.java` — 111 accepted `ape.*` keys with owner, `ValueType` and default, plus a
  retired-key table carrying a reason per key.
- `runtime/Feature.java` — activation over *effective* values (`PRESENT`/`TRUE`/`POSITIVE`/`NONZERO`),
  with neutral values that make a key of an inactive feature acceptable only at its off value.

The `ape-rv.jar` currently installed in `modules/aperv-tool/src/aperv_tool/tools/aperv/` is dated
2026-07-31 and therefore predates all of it. That matters for *running* the re-expressed arms, not for
building them: a pre-stage-2 jar treats `ape.preset` as an unknown key and ignores it, so every arm
would silently collapse to jar defaults. The deployment is recorded as a precondition (task 1.1) and
the run that proves it belongs to `gh97-rearch-ab-gate`.

**This change is offline.** It reads Java source, computes over Python dicts, and writes Python. No
emulator, no `adb`, no jar execution anywhere in it.

## Architecture

```text
BEFORE (per arm)                              AFTER (per arm)
──────────────────                            ─────────────────
{ **_BASELINE_ARM_FLAGS,   (17 keys)          { "preset": "mop",              (1 key)
  **_MOP_SUBSTRATE,        (5 keys)             "strategy": "sata",           (Python-only, CLI)
  "strategy": "sata",                           "mop_data": "static_analysis",(Python-only)
  "throttle_ms": 200,                           "overrides": { …deltas only… } }
  …per-arm deltas… }                                  │
        │                                             ▼
        ▼                                     _push_properties writes:
_push_properties expands 18–33                ape.preset=mop
ape.* lines from the 51-pair map              ape.mopDataPath=…      (when pushed)
                                              ape.<override>=<value> (deltas only)
        │                                             │
        ▼                                             ▼
jar: Config static, silent on                 jar (stage 2): Presets.resolve("mop")
unknown keys; the arm's meaning                 + overrides, fail-fast on unknown/retired
reconstructible only from tool.py               key, RUN_START echoes the effective plan
```

The jar becomes the sole authority on what a preset *means*; Python stays the sole authority on the
*experimental matrix*. They meet only through `ape.properties` (unchanged transport) and the
write-only `RUN_START` line (unchanged collection, never read back).

### Key Components

| Component | Responsibility | Input | Output |
|---|---|---|---|
| `ApeRVTool.get_variants()` | The eight arms as `preset + overrides` | — | `Dict[str, Dict[str, Any]]` (names frozen) |
| `ApeRVTool.configure()` | Validate `strategy`/`preset`/`overrides` and fold DSL keys, before device access | `Dict[str, Any]` | `None`; raises `ConfigurationError` |
| `ApeRVTool._push_properties()` | Write `ape.preset` + `ape.mopDataPath` + override lines | `self._tool_config` | `ape.properties` on device |
| `APERV_PROPERTY_MAPPING` | Override key → `ape.*` name; pass-through only | override keys | `ape.*` names (50 entries) |
| `tests/migration/capture_arm_baseline.py` | One-time capture of the 29 pre-change effective configs | live `tool.py` + jar defaults | `arm_effective_baseline.json` |
| `tests/migration/jar_tables.py` | Parse `Presets.java` / `KeyOwnership.java` from the `ape` checkout | Java source | preset vectors, key types, defaults, retired list |
| `tests/migration/test_arm_regeneration_diff.py` | The gate: regenerated effective config == baseline, per arm | baseline + re-expressed arms | pass/fail per arm |

## Mapping: Spec → Implementation → Test

| Requirement / Invariant | Implementation | Test |
|---|---|---|
| Tool Variants (MODIFIED) | `ApeRVTool.get_variants()` | `TestVariants`: eight names, `default is sata`, per-arm override dicts, 21 retirements absent |
| INV-APV-38 (LLM arms carry `llm_url`) | `get_variants()` | `test_llm_preset_arms_declare_url` |
| INV-APV-39 (DSL overrides folded, unhonourable keys raise) | `ApeRVTool.configure()` | `test_dsl_override_reaches_properties`, `test_unmapped_top_level_key_raises` |
| INV-APV-40 (arm shape) | `get_variants()` | `test_every_variant_is_preset_plus_overrides` |
| INV-APV-41 (mapping contains only accepted keys) | `APERV_PROPERTY_MAPPING` | `test_mapping_against_jar_vocabulary` (migration tier) |
| INV-APV-42 (frozen names, kinded retirements) | `get_variants()` + the retirement list | `test_variant_names_frozen`, `test_retirement_list_kinds` |
| INV-APV-43 (no echo read-back) | absence of any `RUN_START` parser | `test_no_run_start_parsing` (grep-style source assertion) |
| INV-APV-44 (regeneration diff, typed, one-time) | `tests/migration/` | `test_arm_regeneration_diff.py` (deleted after sign-off) |
| configure() Method (MODIFIED) | `ApeRVTool.configure()` | `TestConfigure`: missing preset, non-dict overrides, `bfs`/`dfs` rejected, DSL fold and its error path |
| execute flow step 5 (MODIFIED) | `_push_properties()` call site | `TestExecutionFlow` (unchanged elsewhere) |
| ape.properties Generation (MODIFIED) | `_push_properties()` | `TestPushProperties`: preset first, deltas only, lowercase bools, unmapped key raises |
| Arm Property Overrides Pass-Through (ADDED) | `APERV_PROPERTY_MAPPING` | `test_mapping_has_50_entries`, `test_mop_weight_activity_absent` |
| One-Time Arm Regeneration Migration Check (ADDED) | `tests/migration/` | itself |
| Decisive Run Arm Set (MODIFIED) | the three gh90 arms | `TestDecisiveRunArms`: contrasts asserted on `overrides` |
| Arm-Defining Flag Completeness (REMOVED) | constants + guards deleted | absence asserted by `test_retired_guards_are_gone` |
| Calibration Property Mappings (REMOVED) | framing deleted; entries kept in the table | covered by the mapping tests |

## Goals / Non-Goals

**Goals**

- Re-express the eight surviving names as `preset + explicit override deltas`, preserving every
  surviving arm's **name** and **effective configuration**.
- Retire 21 names as documented removals, each carrying its kind, and prove that the one *name
  consolidated* retirement really is preserved under its survivor.
- Keep the tool DSL's override path working, so the change does not create a silent-discard defect
  while removing one.
- Shrink `APERV_PROPERTY_MAPPING` to the keys the deployed jar accepts (51 → 50) and prove the
  remainder against the jar's own vocabulary.
- Delete the guard machinery (`ARM_DEFINING_KEYS`, `_ARM_DEFINING_EXEMPT`, `LLM_ARM_KEYS`, the
  substrate spread dicts, and the constant-vs-constant tests) with the substitutes recorded.
- Pay the gh88 debt: remove the calibration tier and the `LLM_ARM_KEYS` guard from the main `aperv`
  spec, alongside retiring the `cal_*` arms themselves.

**Non-Goals**

- **No jar changes.** Presets, fail-fast and the echo are stage-2 deliverables. If a preset is found
  missing or wrong, that is a stage-2 defect to report, not something to patch here.
- **No device interaction.** No smoke, no emulator, no `adb`. The run that proves the deployed jar
  honours `ape.preset` belongs to `gh97-rearch-ab-gate`.
- **No runtime echo validation** (owner decision D1): no `RUN_START` parser, no echo-vs-intent check,
  now or as a follow-up of this change.
- **No new arms and no re-tuning.** Byte-identical effective configurations, or an owner-approved
  divergence under a new name.
- **No changes to `experimento-cal/`.** It is a finished campaign's scaffold and a frozen-corpus
  reader (`gh94` INV-APV-55). Its `get_variants()` coupling degrades after this change; that is
  recorded in the proposal, not repaired.
- Orchestration is otherwise untouched: JAR resolution/push, MOP artifact derivation and caching, seed
  propagation (INV-APV-18), the +45 s grace, timeout-as-normal-exit, empty-trace detection, LLM
  provenance (INV-APV-33), gzip at collection, and the B3 pairing (INV-APV-34).

## Decisions

### D1: Arm shape — `preset` key plus an `overrides` sub-dict

```python
"sata_mop_act_frontier": {
    "preset": "mop",                     # jar preset name → ape.preset line
    "strategy": "sata",                  # Python-only → --ape CLI flag (unchanged)
    "mop_data": "static_analysis",       # Python-only → derive + push the MOP artifact (unchanged)
    "overrides": {                       # deltas over the preset, written as ape.* lines
        "mop_activity_source_components": True,
        "frontier_boost_weight": 200,
        "mop_frontier_weight": 200,
        "activity_trigger_enabled": True,
    },
},
```

An explicit `overrides` sub-dict rather than override keys mixed into the top level keeps the boundary
machine-checkable: everything under `overrides` is translated and written, everything at the top level
is Python orchestration. *Alternative considered*: a flat dict with `preset` inline (smaller diff to
today's shape). Rejected — the Python-only/pass-through split would again live in a constant, which is
the pattern this change retires.

### D2: The surviving set, and the override sets derived from the jar's vectors

The 29-variant surface reduces to eight names carrying seven configurations. The override contents
were not authored by hand: they were computed by expanding each arm through `APERV_PROPERTY_MAPPING`
and subtracting the preset vector parsed from `Presets.java`.

| Arm | preset | overrides |
|---|---|---|
| `default` | `aperv` | _(empty)_ — bound to the same object as `sata` |
| `sata` | `aperv` | _(empty)_ |
| `sata_mop` | `mop` | _(empty)_ |
| `sata_llm` | `llm` | `llm_url` |
| `sata_mop_llm` | `llm_mop` | `llm_url` |
| `mop_on_llm_off` | `mop` | `mop_activity_source_components=True`, `frontier_boost_weight=200`, `mop_frontier_weight=200`, `activity_trigger_enabled=True` |
| `mop_off_llm_off` | `mop` | the above minus `mop_frontier_weight`/`activity_trigger_enabled` (both at the preset's zero/false), plus the four MOP weights at `0` |
| `mop_on_llm_70` | `llm_mop` | `mop_on_llm_off`'s four, plus `llm_url`, `llm_prompt_variant="v13"`, `llm_percentage=0.7`, `llm_temperature=0`, `llm_snap_tolerance_px=150` |

`throttle_ms=200` disappears from all of them — the `aperv` preset already states
`ape.defaultGUIThrottle=200`. A delta that looks redundant is dropped only when the regeneration diff
stays empty without it.

**The 21 retirements**, in the three kinds the migration record keeps apart:

| Kind | Names | Note |
|---|---|---|
| never distinct | `ape_pure`, `bfs`, `sata_mop_widget` | no configuration is lost: `bfs` ran `sata`'s plan, `sata_mop_widget` was `sata_mop`'s object, `ape_pure`'s enumeration is what stage 2 made structural |
| name consolidated | `sata_mop_act_frontier` | byte-identical to `mop_on_llm_off`; the migration check proves the survivor reproduces its baseline |
| finished campaign | the six gh43 prompt arms, `cal_a1`…`cal_a9`, `sata_mop_activity`, `random` | recorded results unaffected; what ends is launching new runs under those names |

Two consequences worth stating rather than discovering. First, `random` leaves as an *arm* while
`"random"` stays in the `configure()` whitelist: the jar accepts `--ape random` and the strategy is
still reachable as `aperv:sata@strategy=random`, so the whitelist is not narrowed to a single value.
Second, retiring the six gh43 arms **dissolves the inherited-default hazard entirely**. Those were the
only arms that relied on a jar `Config` default the preset contradicts — every survivor sets its
arm-defining keys explicitly today, because they were all non-exempt under the guard being retired.
The archaeology that would otherwise have been needed (which default did the gh43-era jar carry?) has
no subject left, and the invariant reserving `INV-APV-39` for it is freed for D3a below.

### D3: The tool DSL's override path must be folded, not left to rot

`ToolFactory` merges DSL parameters at the **top level** of the config
(`modules/rv-tools/src/rv_tools/registry/factory.py:127`, `{**variant_config, **tool_config.parameters}`),
and that is how `aperv:sata_mop@mop_frontier_weight=400` works today: `_push_properties()` walks
`APERV_PROPERTY_MAPPING` against the top level, finds the key, writes the line. After this change
`_push_properties()` reads only `overrides`, so the same invocation would put the key somewhere nothing
reads — producing no property line, no error, and a run whose configuration silently differs from what
the operator asked for.

That is the failure class this change exists to remove, so it may not be introduced by it.
`configure()` therefore does two things (INV-APV-39):

1. moves every top-level key that has a mapping entry into `overrides`, with the DSL value winning over
   an arm's own entry for the same key — the DSL is the operator's last word, which is what makes it
   usable for smokes and ablations without declaring a variant;
2. raises `ConfigurationError` for any top-level key that is neither mapped nor one of the recognised
   orchestration keys, so a typo fails loudly instead of evaporating.

*Alternative considered*: teach `ToolFactory` to merge into `overrides` when the tool declares a
preset-shaped variant. Rejected — it puts aperv-specific knowledge into the shared factory, which every
other tool would then carry, and the fold is three lines in the one `configure()` that needs it (P1).

*Alternative considered*: accept top-level mapped keys in `_push_properties()` as well as `overrides`.
Rejected — two entry points for the same data is exactly the duplication being deleted; the fold gives
one place where the effective override set is assembled.

### D4: `_push_properties` — preset line first, then pass-through

Output contract, ordered for diffability:

```text
ape.preset=<preset>                                   # always first
ape.mopDataPath=/data/local/tmp/mop-artifact.json     # only when the artifact was pushed
ape.<mapped-override-key>=<value>                     # one line per overrides entry, mapping order
```

Bool serialization (`True` → `true`) is unchanged. An `overrides` key with no mapping entry raises
`ConfigurationError` at push time: under fail-fast the typo would abort the run on the device anyway,
so catching it on the host saves emulator minutes (the INV-APV-02 rationale). The 51-pair expansion
loop and the seven substrate spread dicts are deleted.

### D5: Deletion ledger

| Deleted | Where | Substitute |
|---|---|---|
| `mop_weight_activity → ape.mopWeightActivity` | `tool.py:110` | none — the jar lists it as retired; a file carrying it now aborts |
| `_BASELINE_ARM_FLAGS`, `_APE_PURE_ARM_FLAGS`, `_MOP_SUBSTRATE`, `_LLM_FLAGS`, `_FRONTIER_SUBSTRATE`, `_MOP_OFF_OVERRIDES`, `_CAL_LLM_COMMON` | `tool.py:252-378` | jar presets + per-arm override deltas |
| `ARM_DEFINING_KEYS` (17), `_ARM_DEFINING_EXEMPT` (6), `LLM_ARM_KEYS` (11) | `tool.py:184-246` | the guards they fed are retired (D6) |
| the INV-APV-13/14/15/17/19/26/27 guard tests, `_EXPECTED_ARM_DEFINING_MAPPING`, the cal-table and decisive-run expansion-diff pins | `tests/test_aperv_tool.py` | one-time regeneration diff (D7) + jar fail-fast + level-0 echo |
| 21 variants (`ape_pure`, `bfs`, `random`, `sata_mop_widget`, `sata_mop_activity`, `sata_mop_act_frontier`, the six gh43 prompt arms, `cal_a1`…`cal_a9`) | `tool.py:499-784` | documented retirements in the migration report, each carrying its kind; `sata_mop_act_frontier`'s configuration survives under `mop_on_llm_off` |
| `"bfs"`, `"dfs"` from `APERV_AVAILABLE_STRATEGIES` | `tool.py:85` | jar aborts on an unknown `--ape`; `configure()` rejects earlier |

`ape_pure_mode` is **not** in this ledger: `gh93` already removed it. Stating that explicitly is
deliberate, so a reader comparing against the `ape`-side design does not go looking for a deletion
that already happened.

### D6: Guard retirement — what goes, what stays

Retired: every pytest that validates a Python constant against another Python constant *about arm
definitions* — mapping completeness, variant explicitness, key-count pins, frozen name tables,
calibration plan-table pins, and the decisive-run tests that recompute contrasts by expansion.

Explicitly **not** retired: `configure()` validation (INV-APV-02), command building (INV-APV-04/18),
device-path constants (INV-APV-03), MOP artifact derivation and caching (INV-APV-45..47), LLM
provenance (INV-APV-33), the snap-tolerance/jar-digest pairing (INV-APV-34), empty-trace detection,
and the properties-writer serialization tests — restated for the D4 output contract rather than
deleted.

The load-bearing point: **there is no runtime replacement, by decision.** The substitute is (a) the
jar's fail-fast resolution, which catches at run time and with an abort the errors the guards
approximated at test time, (b) the one-time diff proving the migration changed nothing, and (c) the
standing property that every trace opens with `RUN_START` carrying the effective plan, so the arm is
reconstructible post-hoc without consulting `tool.py`. Any future echo-vs-intent check is an owner
decision on a real incident, not part of this change.

### D7: The regeneration diff compares typed effective configurations

1. **Capture, before any edit.** `capture_arm_baseline.py` computes for each of the 29 pre-change arms
   the *effective configuration*: the `ape.*` lines the current code writes, expanded over the jar's
   declared defaults into a canonical `{key: typed value}` map, plus `strategy` and `mop_data` as
   orchestration fields. Output: `arm_effective_baseline.json`, committed.
2. **Regenerate.** `test_arm_regeneration_diff.py` recomputes the same map from
   `Presets.resolve(preset) + overrides` and asserts an empty diff per arm.
3. **Type-aware comparison.** Values are compared after parsing with the key's declared `ValueType`
   from `KeyOwnership`. A textual comparison would flag `ape.llmPercentageNoSubstrate` on every arm —
   the preset writes `-1`, the declared default is `-1.0` — and bury the real signal.
4. **Retirements are listed, not diffed.** All 21 retired names live in an explicit retirement list
   the test reads, each with its kind. An arm that vanished without being on that list fails the
   check, so a silent deletion cannot pass as a retirement. For the one *name consolidated* entry the
   test also asserts that `mop_on_llm_off` regenerates `sata_mop_act_frontier`'s baseline — the
   retirement's justification is that the two configurations are identical, so it is checked rather
   than asserted.
5. **Divergence protocol.** A non-empty diff is either a re-expression bug (fix it) or an intentional
   divergence, which requires owner approval and a **new arm name**. No third option.
6. **One-time.** After the final diff and sign-off the test is deleted and the baseline plus report
   archived under `modules/aperv-tool/docs/`. Keeping it would recreate INV-APV-14 under a new number.

*Alternative considered*: compare generated `ape.properties` byte-for-byte. Impossible by construction
— the file's shape is exactly what changes; only the resolved plan is invariant.

### D8: The jar tables are parsed, not vendored

`tests/migration/jar_tables.py` reads `Presets.java` and `KeyOwnership.java` from the `ape` source
checkout (`$APE_REPO`, falling back to `$RVSEC_HOME/ape`) and extracts the four vectors, the accepted
key set, the retired key set, and each key's `ValueType` and default. It records the `ape` repo commit
it read, which goes into the migration record.

*Alternative considered*: vendor a JSON copy of the tables into `aperv-tool`. Rejected — a vendored
copy is a second source of truth for preset contents, which is the class of duplication this change
exists to delete. Parsing keeps the tables in one place and confines the coupling to migration tooling
that is deleted at sign-off. The parser is deliberately shallow (regex over `put(...)` lines) because
it has one caller and a lifetime measured in this change (P1); a failure to parse is a hard error, not
a degraded mode.

## API Design

### `ApeRVTool.get_variants() -> Dict[str, Dict[str, Any]]`

Returns exactly 8 entries. Each value has keys drawn only from `preset` (required, one of the four
jar names), `overrides` (required, dict, possibly empty), `strategy` (required), `mop_data`
(optional), `seed` (optional), `expected_jar_git_sha` / `expected_jar_sha256` (`mop_on_llm_70` only).
`variants["sata_mop"] is variants["sata_mop_widget"]` holds. No exception path.

### `ApeRVTool.configure(config: Dict[str, Any]) -> None`

*Preconditions*: `config["strategy"] in ("sata", "random")`; `config["preset"]` present and non-empty;
`config.get("overrides", {})` is a `dict`.
*Postcondition*: `self._tool_config` holds a defensive copy of `config` in which every top-level key
carrying an `APERV_PROPERTY_MAPPING` entry has been folded into `overrides` (DSL value winning), and
only the recognised orchestration keys remain at the top level.
*Errors*: `ConfigurationError` on any precondition violation, and on any top-level key that is neither
mapped nor recognised — raised before any device interaction and naming the offending key. Order of
checks: `strategy` presence → `strategy` membership → `preset` presence → `overrides` type → fold →
unrecognised top-level keys.

### `ApeRVTool._push_properties(device_serial: str, trace_file_path: str, mop_json_pushed: bool = False) -> None`

*Precondition*: `configure()` has run.
*Postcondition*: `/data/local/tmp/ape.properties` contains the D4 contract, in that order, with
lowercase bools.
*Errors*: `ConfigurationError` when an `overrides` key is absent from `APERV_PROPERTY_MAPPING`, raised
before the push; `RVToolExecutionError` when the push itself fails (unchanged).

### `tests/migration/jar_tables.py`

```python
def load_presets(ape_repo: Path) -> Dict[str, Dict[str, str]]:      # name -> {ape.key: text value}
def load_key_specs(ape_repo: Path) -> Dict[str, KeySpec]            # ape.key -> (type, default)
def load_retired_keys(ape_repo: Path) -> Dict[str, str]             # ape.key -> reason
def source_provenance(ape_repo: Path) -> Dict[str, str]             # commit, file digests
```

`KeySpec` is a small dataclass (`value_type: str`, `default: str | None`) — not a Pydantic model:
it crosses no system boundary, has one producer and one consumer, and is deleted with the migration
(P1).

### `tests/migration/capture_arm_baseline.py`

```python
def effective_config(arm: Dict[str, Any], key_specs, mop_pushed: bool) -> Dict[str, object]
def main(ape_repo: Path, out: Path) -> None      # writes arm_effective_baseline.json
```

`effective_config` returns typed values: every key the arm writes, overlaid on the jar defaults for
the keys it does not, restricted to the keys reachable through `APERV_PROPERTY_MAPPING` plus
`ape.mopDataPath`.

## Data Flow

1. Experiment YAML selects a variant → `ToolFactory` merges `{**variant, **parameters}` →
   `configure()` validates `strategy`, `preset` and `overrides`.
2. `execute_tool_specific_logic()` (flow unchanged): jar push → broadcast catalog → MOP artifact
   derivation and push (`mop_data`) → `_push_properties()` writes `ape.preset` + `ape.mopDataPath` +
   override lines → LLM provenance sidecar → main command with `--ape <strategy>` and `-s <seed>` →
   capture → empty-trace check → gzip.
3. Jar (stage 2): `Presets.resolve(name)`, overlay the explicit keys, validate totally, abort on any
   unknown/retired key or non-neutral value of an inactive feature, then echo the effective plan in
   `RUN_START`. The Python side reads **nothing** back (D6, INV-APV-43).
4. Migration only: `jar_tables` parses the `ape` checkout → `capture_arm_baseline` writes the baseline
   from the pre-change dicts → `test_arm_regeneration_diff` recomputes from preset + overrides and
   diffs. This path never touches a device and is deleted at sign-off.

## Error Handling

| Error | Source | Strategy | Recovery |
|---|---|---|---|
| `ConfigurationError` — missing/empty `preset` | `configure()` | raise before device interaction | fix the arm definition |
| `ConfigurationError` — `overrides` not a dict | `configure()` | raise before device interaction | fix the arm or the DSL override |
| `ConfigurationError` — strategy outside `["sata","random"]` | `configure()` | raise before device interaction | use a supported strategy; `bfs`/`dfs` are retired |
| `ConfigurationError` — override key not in the mapping | `_push_properties()` | raise before `adb push` | fix the key, or add the mapping entry if the jar accepts it |
| `ConfigurationError` — unrecognised top-level key (typo in a DSL override) | `configure()` fold | raise before device interaction | fix the DSL key; it is never silently discarded (INV-APV-39) |
| Unknown / retired `ape.*` key reaches the jar | jar, stage-2 resolution | run aborts before step 1, abort visible in the trace | fix the arm; nothing silent survives |
| `ape.preset=llm*` without `ape.llmUrl` | jar resolution | abort: routing gates ON over an absent mechanism | add `llm_url` to the arm's overrides (INV-APV-38) |
| Regeneration diff non-empty | migration test | the task group is blocked | fix the re-expression, or take an owner-approved divergence under a new arm name |
| `Presets.java` / `KeyOwnership.java` unparseable | `jar_tables.py` | hard error naming the file and the checkout | point `$APE_REPO` at a stage-2 checkout |

## Risks / Trade-offs

- [Silent grid drift during re-expression] → the per-group regeneration diff, the final full diff with
  owner sign-off, and frozen arm names throughout.
- [A DSL override silently vanishing because `_push_properties()` stopped reading the top level]
  → the D3 fold, with an explicit error for any top-level key that cannot be honoured. This risk was
  created by the change itself and is closed inside it.
- [Retiring 21 names removes the ability to re-run those configurations]
  → accepted deliberately: the campaigns they served have concluded, their recorded results are frozen
  artifacts unaffected by the retirement, and the one configuration still wanted
  (`sata_mop_act_frontier`) survives under `mop_on_llm_off` with the equality proved by the migration
  check rather than asserted.
- [Preset tables parsed from `ape` source drift from the deployed jar] → the migration record captures
  the `ape` commit and the source digests it read against; the check is one-time and archived. The
  standing guarantee for a *running* campaign is the jar's own fail-fast, not this tooling.
- [A pre-stage-2 jar silently ignores `ape.preset` and collapses every arm to defaults] → recorded as
  a hard precondition (task 1.1); the empirical proof that the deployed jar honours the preset is
  `gh97-rearch-ab-gate`'s, by owner decision, and this change stays offline.
- [Losing the guards weakens day-to-day defect detection] → accepted deliberately (owner D1). The jar
  now catches the same error classes at run time with an abort, which is stronger than a constant
  self-check; provenance makes any survivor auditable post-hoc.
- [`experimento-cal`'s expected-`[APE-LLM-CONFIG]` derivation degrades to an almost-empty field set]
  → accepted and recorded, not repaired: the campaign is finished and `gh94` INV-APV-55 declares those
  scripts frozen-corpus readers. Repairing them would maintain a consumer of a dataset that will not
  be regenerated.
- [gh94 and gh96 modify the same two requirements and neither is synced] → this change's MODIFIED
  blocks are written on top of theirs (execution flow over gh94's, properties over gh96's), so the
  three compose in any archive order.

## Testing Strategy

| Layer | What to test | How | Count |
|---|---|---|---|
| Unit — variants | eight names frozen, all 21 retirements absent, arm shape, `default is sata`, per-arm override dicts, INV-APV-38 | direct assertions on `get_variants()` | ~10 |
| Unit — configure | missing/empty preset, non-dict overrides, `bfs`/`dfs` rejected, valid arm accepted, DSL fold, DSL precedence, unrecognised top-level key raises | `pytest.raises(ConfigurationError)` + config inspection | ~9 |
| Unit — properties writer | preset line first, `mopDataPath` second, deltas only, lowercase bools, unmapped key raises, Python-only keys excluded | mock the push, inspect the written file | ~8 |
| Unit — mapping | 50 entries, `mop_weight_activity` absent, `llm_max_tokens`/`llm_snap_tolerance_px` present | constant inspection | ~3 |
| Migration (one-time) | per-arm typed empty diff; the 21-name retirement list honoured with kinds; the consolidated name's equality proved | `test_arm_regeneration_diff.py`, re-run after every arm-editing group, deleted at sign-off | 8 + 3 |
| Unchanged | MOP artifact derivation and caching, execution flow, provenance, clock/logcat join, coverage dump | untouched suites | — |

The full `aperv-tool` suite runs in ~14 s at HEAD (217 tests) with the CI contract flags
(`--import-mode=importlib -o "addopts="`), which every group's verification step uses.

## Open Questions

1. **Does any mapped key beyond `mop_weight_activity` become dead after stage 4?** The sweep performed
   for this design found none against the stage-2 vocabulary, but stage 4 may retire
   `ape.stepTelemetryEnabled` when telemetry becomes universal. Task 1.5 re-runs the sweep at
   implementation time against whatever the checkout then holds, which absorbs the ordering either
   way.

2. **Nothing pushes `ape.corpusBasis`.** The jar declares it as a third resolver-owned key, supplied
   by the harness and echoed unread, and the stage-2 spec carries a scenario written for the harness
   pushing it. No rv-android change claims it. It is out of this change's scope — it is a per-run
   deployment key needing a new capability (computing the corpus hash), not an arm re-expression — and
   is recorded here so it is not lost. `ape.runId` needs nothing: the jar self-generates it and the
   stage-2 spec states no deployment pushes it.
