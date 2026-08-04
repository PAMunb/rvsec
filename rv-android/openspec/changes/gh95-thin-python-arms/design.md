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
| `ApeRVTool.get_variants()` | The 27 arms as `preset + overrides` | — | `Dict[str, Dict[str, Any]]` (names frozen) |
| `ApeRVTool.configure()` | Validate `strategy`, `preset`, `overrides` before device access | `Dict[str, Any]` | `None`; raises `ConfigurationError` |
| `ApeRVTool._push_properties()` | Write `ape.preset` + `ape.mopDataPath` + override lines | `self._tool_config` | `ape.properties` on device |
| `APERV_PROPERTY_MAPPING` | Override key → `ape.*` name; pass-through only | override keys | `ape.*` names (50 entries) |
| `tests/migration/capture_arm_baseline.py` | One-time capture of the 29 pre-change effective configs | live `tool.py` + jar defaults | `arm_effective_baseline.json` |
| `tests/migration/jar_tables.py` | Parse `Presets.java` / `KeyOwnership.java` from the `ape` checkout | Java source | preset vectors, key types, defaults, retired list |
| `tests/migration/test_arm_regeneration_diff.py` | The gate: regenerated effective config == baseline, per arm | baseline + re-expressed arms | pass/fail per arm |

## Mapping: Spec → Implementation → Test

| Requirement / Invariant | Implementation | Test |
|---|---|---|
| Tool Variants (MODIFIED) | `ApeRVTool.get_variants()` | `TestVariants`: 27 names, `sata_mop is sata_mop_widget`, per-arm override dicts |
| INV-APV-38 (LLM arms carry `llm_url`) | `get_variants()` | `test_llm_preset_arms_declare_url` |
| INV-APV-39 (inherited defaults restated) | the six gh43 arms' overrides | `test_frozen_prompt_arms_restore_inherited_defaults` |
| INV-APV-40 (arm shape) | `get_variants()` | `test_every_variant_is_preset_plus_overrides` |
| INV-APV-41 (mapping contains only accepted keys) | `APERV_PROPERTY_MAPPING` | `test_mapping_against_jar_vocabulary` (migration tier) |
| INV-APV-42 (frozen names) | `get_variants()` | `test_variant_names_frozen` |
| INV-APV-43 (no echo read-back) | absence of any `RUN_START` parser | `test_no_run_start_parsing` (grep-style source assertion) |
| INV-APV-44 (regeneration diff, typed, one-time) | `tests/migration/` | `test_arm_regeneration_diff.py` (deleted after sign-off) |
| configure() Method (MODIFIED) | `ApeRVTool.configure()` | `TestConfigure`: missing preset, non-dict overrides, `bfs`/`dfs` rejected |
| execute flow step 5 (MODIFIED) | `_push_properties()` call site | `TestExecutionFlow` (unchanged elsewhere) |
| ape.properties Generation (MODIFIED) | `_push_properties()` | `TestPushProperties`: preset first, deltas only, lowercase bools, unmapped key raises |
| Arm Property Overrides Pass-Through (ADDED) | `APERV_PROPERTY_MAPPING` | `test_mapping_has_50_entries`, `test_mop_weight_activity_absent` |
| One-Time Arm Regeneration Migration Check (ADDED) | `tests/migration/` | itself |
| Decisive Run Arm Set (MODIFIED) | the three gh90 arms | `TestDecisiveRunArms`: contrasts asserted on `overrides` |
| Arm-Defining Flag Completeness (REMOVED) | constants + guards deleted | absence asserted by `test_retired_guards_are_gone` |
| Calibration Property Mappings (REMOVED) | framing deleted; entries kept in the table | covered by the mapping tests |

## Goals / Non-Goals

**Goals**

- Re-express all 27 surviving arms as `preset + explicit override deltas`, preserving every arm's
  **name** and every arm's **effective configuration**.
- Retire `ape_pure` and `bfs` as documented removals.
- Shrink `APERV_PROPERTY_MAPPING` to the keys the deployed jar accepts (51 → 50) and prove the
  remainder against the jar's own vocabulary.
- Delete the guard machinery (`ARM_DEFINING_KEYS`, `_ARM_DEFINING_EXEMPT`, `LLM_ARM_KEYS`, the
  substrate spread dicts, and the constant-vs-constant tests) with the substitutes recorded.
- Pay the gh88 debt: remove the calibration tier framing and the `LLM_ARM_KEYS` guard from the main
  `aperv` spec, while keeping the nine `cal_*` arms.

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

### D2: The override sets are derived from the jar's vectors, not authored by hand

The exact contents were computed by expanding each arm through `APERV_PROPERTY_MAPPING` and
subtracting the preset vector parsed from `Presets.java`. The result, which is the implementation
target:

| Arm | preset | # overrides |
|---|---|---|
| `default`, `sata`, `random` | `aperv` | 0 |
| `sata_mop`, `sata_mop_widget` | `mop` | 0 |
| `sata_mop_activity` | `mop` | 1 |
| `sata_llm` | `llm` | 1 (`llm_url`) |
| `sata_mop_llm` | `llm_mop` | 1 (`llm_url`) |
| `sata_mop_act_frontier`, `mop_on_llm_off` | `mop` | 4 |
| `mop_off_llm_off` | `mop` | 6 |
| the six gh43 prompt arms | `llm_mop` | 5 (3 + the two INV-APV-39 restorations) |
| `cal_a1`, `cal_a2`, `cal_a4`, `cal_a6`…`cal_a9` | `llm_mop` | 8 |
| `cal_a3` | `llm_mop` | 9 |
| `mop_on_llm_70` | `llm_mop` | 9 |
| `cal_a5` | `llm_mop` | 10 |

`throttle_ms=200` disappears from all 27 — the `aperv` preset already states
`ape.defaultGUIThrottle=200`, and every arm used that value. A delta that looks redundant is dropped
only when the regeneration diff stays empty without it.

### D3: The six frozen gh43 arms need explicit restorations, and this is the one real hazard

The six prompt arms never set the arm-defining flags; they ran on jar `Config` defaults. Two of those
defaults **disagree with the `llm_mop` preset**:

| Key | Jar default (what they ran) | `llm_mop` preset states | Consequence under `Feature` |
|---|---|---|---|
| `ape.frontierBoostWeight` | `200` | `0` | `FRONTIER` deactivated (`Rule.POSITIVE`, neutral `0`) |
| `ape.activityTriggerEnabled` | `true` | `false` | `ACTIVITY_TRIGGER` deactivated (`Rule.TRUE`) |

Re-expressing them as `preset="llm_mop"` + prompt/dose deltas would therefore change their behaviour
silently. The fix is `frontier_boost_weight=200` and `activity_trigger_enabled=True` as explicit
overrides (INV-APV-39), which restores the effective configuration and keeps the diff empty.

**This rests on an assumption the implementation must verify, not assume**: that the jar the gh43
campaign actually ran carried those same defaults. `KeyOwnership`'s defaults are asserted against the
*current* `Config` by reflection on the jar side; whether they held at gh43 time is a separate
question, answered by reading `Config.java` at the revision that campaign used. If they differ, this
is a declared divergence for the owner under INV-APV-42, not a value to pick. Task 1.6 carries it.

*Alternative considered*: introduce a fifth preset matching the frozen arms' inheritance. Rejected —
the preset vocabulary belongs to the jar, and an ablation is a named override set (proposal, and the
`ape`-side design D2).

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
| `ape_pure`, `bfs` variants | `tool.py:503,506` | documented retirements in the migration report |
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
4. **Retirements are listed, not diffed.** `ape_pure` and `bfs` live in an explicit retirement list
   the test reads. An arm that vanished without being on that list fails the check, so a silent
   deletion cannot pass as a retirement.
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

Returns exactly 27 entries. Each value has keys drawn only from `preset` (required, one of the four
jar names), `overrides` (required, dict, possibly empty), `strategy` (required), `mop_data`
(optional), `seed` (optional), `expected_jar_git_sha` / `expected_jar_sha256` (`mop_on_llm_70` only).
`variants["sata_mop"] is variants["sata_mop_widget"]` holds. No exception path.

### `ApeRVTool.configure(config: Dict[str, Any]) -> None`

*Preconditions*: `config["strategy"] in ("sata", "random")`; `config["preset"]` present and non-empty;
`config.get("overrides", {})` is a `dict`.
*Postcondition*: `self._tool_config` holds a defensive copy of `config`.
*Errors*: `ConfigurationError` on any precondition violation, raised before any device interaction and
naming the offending key. Order of checks: `strategy` presence → `strategy` membership → `preset`
presence → `overrides` type.

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
| Unknown / retired `ape.*` key reaches the jar | jar, stage-2 resolution | run aborts before step 1, abort visible in the trace | fix the arm; nothing silent survives |
| `ape.preset=llm*` without `ape.llmUrl` | jar resolution | abort: routing gates ON over an absent mechanism | add `llm_url` to the arm's overrides (INV-APV-38) |
| Regeneration diff non-empty | migration test | the task group is blocked | fix the re-expression, or take an owner-approved divergence under a new arm name |
| `Presets.java` / `KeyOwnership.java` unparseable | `jar_tables.py` | hard error naming the file and the checkout | point `$APE_REPO` at a stage-2 checkout |

## Risks / Trade-offs

- [Silent grid drift during re-expression] → the per-group regeneration diff, the final full diff with
  owner sign-off, and frozen arm names throughout.
- [The six frozen gh43 arms change behaviour through an inherited default the preset contradicts (D3)]
  → INV-APV-39 restorations, plus task 1.6 verifying the defaults against the jar revision that
  campaign ran. This is the one place where "preserve the effective configuration" required reading
  history rather than the current tree.
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
| Unit — variants | 27 names frozen, `ape_pure`/`bfs` absent, arm shape, `sata_mop is sata_mop_widget`, per-arm override dicts, INV-APV-38/39 | direct assertions on `get_variants()` | ~12 |
| Unit — configure | missing/empty preset, non-dict overrides, `bfs`/`dfs` rejected, valid arm accepted | `pytest.raises(ConfigurationError)` | ~6 |
| Unit — properties writer | preset line first, `mopDataPath` second, deltas only, lowercase bools, unmapped key raises, Python-only keys excluded | mock the push, inspect the written file | ~8 |
| Unit — mapping | 50 entries, `mop_weight_activity` absent, `llm_max_tokens`/`llm_snap_tolerance_px` present | constant inspection | ~3 |
| Migration (one-time) | per-arm typed empty diff; retirement list honoured; frozen-arm restoration load-bearing | `test_arm_regeneration_diff.py`, re-run after every arm-editing group, deleted at sign-off | 27 + 3 |
| Unchanged | MOP artifact derivation and caching, execution flow, provenance, clock/logcat join, coverage dump | untouched suites | — |

The full `aperv-tool` suite runs in ~14 s at HEAD (217 tests) with the CI contract flags
(`--import-mode=importlib -o "addopts="`), which every group's verification step uses.

## Open Questions

1. **Did the gh43-era jar carry `frontierBoostWeight=200` and `activityTriggerEnabled=true` as
   defaults?** (D3). Resolvable by reading `Config.java` at the revision that campaign ran. If it did,
   the INV-APV-39 overrides are a preservation and the diff closes empty. If it did not, the six arms
   have a declared divergence for the owner. Task 1.6; blocks group 5, nothing earlier.
2. **Does any mapped key beyond `mop_weight_activity` become dead after stage 4?** The sweep performed
   for this design found none against the stage-2 vocabulary, but stage 4 may retire
   `ape.stepTelemetryEnabled` when telemetry becomes universal. Task 1.5 re-runs the sweep at
   implementation time against whatever the checkout then holds, which absorbs the ordering either
   way.
