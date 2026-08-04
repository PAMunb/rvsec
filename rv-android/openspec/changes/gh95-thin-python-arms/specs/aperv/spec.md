# aperv Delta Specification — Arms as Preset + Overrides

## Purpose

This delta changes what an experiment arm *is* on the Python side of APE-RV. Until now an arm was a
dictionary of 18–33 configuration keys that `_push_properties()` expanded into as many
`ape.properties` lines, and the guarantee that the arm meant what it said came from pytest suites
comparing Python constants against other Python constants. Those guards were the best available
mechanism while the jar had no contract: an `ape.*` key it did not recognise was inert, a key the
arm omitted silently took a `Config` default, and a divergence between the two sides produced no
signal at all. The re-architecture calls that split-brain V20.

Stage 2 of the re-architecture replaced the jar's side of it. `Presets.java` holds the four campaign
arms as base key vectors — `aperv`, `mop`, `llm`, `llm_mop`, selected by `ape.preset` —
`KeyOwnership.java` declares every accepted `ape.*` key with its owner, type and default, and
`Feature.java` decides activation over effective values so that a feature absent from the plan has
no constructed mechanism. Resolution is total and fail-fast: an unknown key, a retired key, or a
non-neutral value belonging to an inactive feature aborts the run before step 1. The property the
Python guards approximated is now enforced at run time by the binary that actually runs, and
enforced more strongly, because an abort is louder than a passing test about a constant.

What this delta does, therefore, is stop duplicating the presets. **An arm becomes a preset name plus
an explicit dict of override deltas**, and the two authorities separate cleanly: the jar owns what a
preset means, Python owns the experimental matrix — which arms exist, what their frozen names are,
and how each differs from its preset. The shrink is not cosmetic. Measured against the jar's actual
vectors, `default`, `sata`, `random`, `sata_mop` and `sata_mop_widget` carry **no** overrides at all;
`sata_mop_activity`, `sata_llm` and `sata_mop_llm` carry exactly one; the widest arm carries ten. The
single-factor contrasts of the decisive run become readable at the definition site instead of being
recomputed by a test that expands both dictionaries.

Two arms do not survive the move, and both retirements are removals of things that were never
distinct rather than deletions of experimental conditions. `ape_pure` existed to enumerate every RV
flag at its off value, because the jar exposed no switch that forced the extensions off; after stage
2 purity is structural — a plan without a feature has no feature — and `ape.apePureMode` is a retired
key whose abort message says exactly that. `bfs` was never an agent type: `ApeAgent.createAgent`
accepts `sata`, `random` and `replay`, and every other value fell through silently to `SataAgent`, so
the `bfs` arm always carried the same effective configuration as `sata` and differed only in a string
the jar ignored. Both appear in the migration record as documented retirements, never as
regeneration differences.

The guard machinery retires with the dicts it audited, and this delta records what replaces it rather
than leaving the question open. `ARM_DEFINING_KEYS`, `_ARM_DEFINING_EXEMPT` and `LLM_ARM_KEYS` are
explicitness obligations that only made sense while the per-arm dictionaries were authoritative:
there is no expansion left to keep complete, and a missing or misspelled key now aborts the run in
the jar instead of passing silently. Their substitute is (a) the jar's fail-fast resolution at run
time and (b) a **one-time** regeneration diff proving the migration preserved the calibrated grid.
Per owner decision D1 there is deliberately **no runtime replacement**: `tool.py` never parses
`RUN_START` or any other jar output, and drift auditing stays post-hoc analysis of the trace. Keeping
the diff alive after sign-off would recreate the retired invariant under a new number, so the delta
states its own deletion as part of the requirement.

Everything else the plugin does is untouched by this change: JAR resolution and push, the derived MOP
artifact and its digest cache, seed propagation, the +45 s command grace, timeout-as-normal-exit,
empty-trace detection, LLM backend provenance, the gzip-at-collection step, and the B3
snap-tolerance/jar-digest pairing. This change is also entirely offline — it neither requires nor
performs any device interaction.

## Data Contracts

### Input

- `variant dict: Dict[str, Any]` — per arm: `preset: str` (one of `aperv`, `mop`, `llm`, `llm_mop`),
  `overrides: Dict[str, Any]` (deltas over the preset, possibly empty), plus Python-only
  orchestration keys `strategy`, `mop_data`, and — for `mop_on_llm_70` — `expected_jar_git_sha` /
  `expected_jar_sha256` (source: `ApeRVTool.get_variants()`, merged with experiment parameters by
  `ToolFactory`)
- `APERV_PROPERTY_MAPPING: Dict[str, str]` — override key → `ape.*` property name; reduced to the
  keys the deployed jar accepts (source: `tool.py` module constant)
- `tests/migration/arm_effective_baseline.json` — the pre-change effective configuration of all 29
  arms, captured before any arm is edited (source: the one-time capture script)
- preset vectors and the accepted-key vocabulary — read from the `ape` source checkout
  (`runtime/Presets.java`, `runtime/KeyOwnership.java`) by the migration tooling only; not a runtime
  dependency of `aperv-tool`

### Output

- `ape.properties` on device — `ape.preset=<name>` first, `ape.mopDataPath=<artifact>` when the
  derived MOP artifact was pushed, then one `ape.<key>=<value>` line per `overrides` entry
  (destination: `/data/local/tmp/ape.properties`, consumed by the stage-2 jar's resolution)
- migration record — the final per-arm diff report plus the baseline JSON, archived under
  `modules/aperv-tool/docs/` after owner sign-off (destination: post-hoc audit trail)

### Side-Effects

- **[Device]**: unchanged push flow — jar, broadcast catalog, derived MOP artifact, properties file
- **[Jar]**: an unknown key, a retired key, an invalid type, or a non-neutral value of an inactive
  feature aborts the run before step 1; the effective plan is echoed write-only in `RUN_START`

### Error

- `ConfigurationError` — raised by `configure()` when `strategy` is absent or outside
  `["sata", "random"]`, when `preset` is absent or empty, or when `overrides` is not a dict; raised by
  `_push_properties()` when an `overrides` key has no `APERV_PROPERTY_MAPPING` entry. All are raised
  before any device interaction.
- Jar-side abort — any key or combination the jar rejects; visible in the trace, never silent

## Invariants

- **INV-APV-38**: Every arm whose `preset` is `llm` or `llm_mop` MUST carry `llm_url` in its
  `overrides`. The preset deliberately omits the server URL because it names a machine rather than an
  arm, while still stating the LLM routing gates ON, so an arm that inherits the preset without
  supplying the URL activates routing over an absent mechanism and aborts at resolution. This is a
  fail-fast, not a fallback.

- **INV-APV-39**: An arm that inherited a jar `Config` default which its preset restates at a
  different value MUST carry that inherited value as an explicit override. Re-expression preserves
  effective configurations (INV-APV-44); an arm silently adopting a preset value in place of the
  default it actually ran with is a behavioural change disguised as a refactor. The six frozen gh43
  prompt arms are the known instance: they never set `frontier_boost_weight` or
  `activity_trigger_enabled` and therefore ran at the jar defaults `200` and `true`, whereas the
  `llm_mop` preset states `0` and `false`, which under the stage-2 `Feature` model deactivates
  `FRONTIER` and `ACTIVITY_TRIGGER` outright.

- **INV-APV-40**: Every variant returned by `get_variants()` MUST consist of a `preset` name, an
  `overrides` dict (possibly empty), and Python-only orchestration keys. No variant may carry a full
  property expansion; the substrate spread dicts are deleted, not retained in reduced form.

- **INV-APV-41**: `APERV_PROPERTY_MAPPING` MUST contain only keys the deployed jar accepts. Dead keys
  are removed, not commented out. `llm_snap_tolerance_px` and `llm_max_tokens` are live jar keys
  (`Feature.LLM` sub-parameters) and MUST remain mapped.

- **INV-APV-42**: The 27 surviving variant names are frozen. The variant string is the resume-identity
  key and the consolidation column key; re-expression MUST NOT rename any arm. An owner-approved
  intentional divergence in effective configuration MUST be introduced as a new declared arm name,
  never as a silent edit. The two retired names (`ape_pure`, `bfs`) are the only removals and MUST be
  recorded as documented retirements in the migration arm report rather than appearing as
  regeneration diffs.

- **INV-APV-43**: `tool.py` MUST NOT parse, validate or branch on `RUN_START` or any other jar echo
  output (owner decision D1). Provenance is write-only in the trace; drift auditing is post-hoc
  analysis.

- **INV-APV-44**: During the migration, every **surviving** arm's regenerated effective configuration
  MUST diff empty against `arm_effective_baseline.json`. The comparison MUST be made on typed values
  using each key's declared `ValueType`, not on property text — the `aperv` preset writes
  `ape.llmPercentageNoSubstrate=-1` where the declared default is `-1.0`, and a textual comparison
  would fail every arm on formatting alone. The baseline covers all 29 pre-change arms; the two
  retired names are excluded by an explicit retirement list the test reads, never by silent absence.
  The check is **one-time**: after owner sign-off the test is deleted and the record archived. It MUST
  NOT survive as a standing constant-vs-constant guard.

## MODIFIED Requirements

### Requirement: ApeRVTool Variants (FR20)

`ApeRVTool` SHALL define named variants organized in four tiers: base variants, MOP-arm variants, LLM
variants (including the frozen prompt-experiment arms), and calibration arm variants. Every variant
SHALL consist of a `preset` name, an `overrides` dict, and Python-only orchestration keys
(INV-APV-40). The `"default"` variant SHALL use strategy `"sata"` (INV-TOOL-02).

`get_variants()` SHALL return exactly these **27** frozen names: `default`, `sata`, `random`,
`sata_mop_widget`, `sata_mop`, `sata_mop_activity`, `sata_mop_act_frontier`, `sata_llm`,
`sata_mop_llm`, the six gh43 prompt arms (`sata_mop_llm_ape_current`, `sata_mop_llm_ape_reasoning`,
`sata_mop_llm_compact_v1`, `sata_mop_llm_v13`, `sata_mop_llm_v17`, `sata_mop_llm_visual_only`), the
nine calibration arms (`cal_a1`…`cal_a9`), and the three decisive-run arms (`mop_on_llm_off`,
`mop_off_llm_off`, `mop_on_llm_70`).

**Arm shape.** An arm's `preset` names one of the four jar-resident vectors; the jar, not Python,
defines what it contains. `overrides` carries only the deltas that distinguish this arm from its
preset — an arm identical to its preset carries an empty dict. Python-only keys stay at the top level
and are never written to `ape.properties`: `strategy` (the `--ape` CLI flag), `mop_data`
(`"static_analysis"` triggers the derived-artifact push, unchanged), `seed`, and the two B3
jar-provenance declarations. The explicit `overrides` sub-dict rather than a flat dict is what keeps
the boundary machine-checkable: everything under `overrides` is translated and written, everything
at the top level is orchestration.

**Preset assignment.** `default`/`sata`/`random` → `aperv`. `sata_mop_widget`/`sata_mop`/
`sata_mop_activity`/`sata_mop_act_frontier`/`mop_on_llm_off`/`mop_off_llm_off` → `mop`. `sata_llm` →
`llm`. All remaining LLM arms → `llm_mop`. Ablations SHALL be expressed as named override sets, never
as new presets: the preset vocabulary belongs to the jar.

Every LLM-preset arm SHALL carry `llm_url` in its overrides (INV-APV-38) — the preset omits the
deployment-specific server URL while stating the routing gates ON, so its absence aborts resolution.
`throttle_ms` SHALL NOT appear in any arm: the `aperv` preset already states
`ape.defaultGUIThrottle=200`, which every arm used.

#### Base Variants

| Variant | preset | strategy | mop_data | overrides |
|---|---|---|---|---|
| `default` | `aperv` | `"sata"` | — | _(empty)_ — alias of `sata` |
| `sata` | `aperv` | `"sata"` | — | _(empty)_ |
| `random` | `aperv` | `"random"` | — | _(empty)_ |

The `aperv` preset is the RV-exploration baseline made explicit: the twelve exploration gates on, the
`llm_percentage_no_substrate` sentinel at `-1`, and MOP/reach/frontier off. The three base arms differ
from each other only in the `--ape` strategy, which is a command-line value and not part of any preset.

#### MOP-Arm Variants

All MOP arms set `mop_data="static_analysis"` at the top level, which is what makes the jar's `MOP`
feature active — the four MOP scoring weights come from the `mop` preset.

| Variant | preset | overrides |
|---|---|---|
| `sata_mop_widget` | `mop` | _(empty)_ — the MOP control arm |
| `sata_mop` | `mop` | — bound to the same object as `sata_mop_widget` (INV-APV-16) — |
| `sata_mop_activity` | `mop` | `mop_activity_source_components=True` |
| `sata_mop_act_frontier` | `mop` | `mop_activity_source_components=True`, `frontier_boost_weight=200`, `mop_frontier_weight=200`, `activity_trigger_enabled=True` |

`sata_mop` and `sata_mop_widget` SHALL remain bound to the same object, and `sata_mop` is the
**primary** of the pair. This is a data-identity constraint, not backward compatibility: 4,096
`aperv:sata_mop.trace` artifacts and 1,066 files under `results/` carry that exact token, while
`sata_mop_widget` has produced none, so renaming `sata_mop` would orphan every one of those runs from
resume and every one of those rows from consolidation. Nothing in the tool adapts to an old shape;
the pair costs one dict binding.

#### LLM Variants

| Variant | preset | mop_data | overrides |
|---|---|---|---|
| `sata_llm` | `llm` | — | `llm_url` |
| `sata_mop_llm` | `llm_mop` | `"static_analysis"` | `llm_url` |

The LLM sampling block (`llm_on_new_state`, `llm_on_stagnation`, `llm_model`, `llm_temperature`,
`llm_top_p`, `llm_top_k`, `llm_timeout_ms`) lives in the `llm` and `llm_mop` presets at exactly the
values these two arms used, so each reduces to the server URL.

#### Prompt Experiment Variants (gh43 — effective configuration frozen)

The six prompt-ablation arms SHALL be re-expressed like every other arm. Freezing protects their
**effective configuration**, not their source shape, and the `_ARM_DEFINING_EXEMPT` machinery is
deleted with the guard it exempted from. Each carries `preset="llm_mop"`, `mop_data="static_analysis"`
and overrides `llm_url`, `llm_percentage=0.7`, `llm_prompt_variant=<variant>`.

These six arms additionally carry `frontier_boost_weight=200` and `activity_trigger_enabled=True` as
explicit overrides (INV-APV-39). They never set either key and therefore ran at the jar defaults
`200`/`true`, while the `llm_mop` preset states `0`/`false`; under the stage-2 `Feature` model those
preset values deactivate `FRONTIER` and `ACTIVITY_TRIGGER` entirely. Restoring them as overrides is
what keeps the arms' effective configuration unchanged. The inherited values SHALL be verified against
the jar the gh43 campaign actually ran before the overrides are accepted as a preservation; a
divergence there is a declared divergence for the owner (INV-APV-42), not a value to assume.

| Variant | llm_prompt_variant |
|---|---|
| `sata_mop_llm_ape_current` | `ape_current` |
| `sata_mop_llm_ape_reasoning` | `ape_reasoning` |
| `sata_mop_llm_compact_v1` | `compact_v1` |
| `sata_mop_llm_v13` | `v13` |
| `sata_mop_llm_v17` | `v17` |
| `sata_mop_llm_visual_only` | `visual_only` |

#### Calibration Arm Variants (cal_*)

The nine arms of the Phase-A calibration table (`docs/20260721_plano_calibracao_llm.md` §6, rev. 3.2)
SHALL each carry `preset="llm_mop"`, `mop_data="static_analysis"`, and the frontier reach package as
overrides (`mop_activity_source_components=True`, `frontier_boost_weight=200`,
`mop_frontier_weight=200`, `activity_trigger_enabled=True`) plus `llm_url` and their per-arm LLM
deltas. The frontier substrate is the configuration that won the cmpma multi-arm comparison (cov_mop
37.75% vs ≤35%, Friedman+Holm): whenever the router does not delegate a step — and on every
`no_match` fallback — the arm explores in frontier mode. `sata_mop_act_frontier` without LLM keys is
exactly the ANC2 anchor arm, so the paired difference `cal_* − ANC2` isolates the LLM contribution on
the same algorithmic base.

Keys absent from an arm's overrides take the preset value, which is what makes the table below the
whole story: an empty cell is not an omission but a statement that the arm uses the shared value
(`llm_temperature=0.3`, `llm_top_p=0.6`, `llm_top_k=50`, both routing triggers `true`).

| Variant | Hypothesis | LLM overrides beyond `llm_url` |
|---|---|---|
| `cal_a1` | control | `llm_prompt_variant=v13`, `llm_percentage=0.7`, `llm_temperature=0` |
| `cal_a2` | H1 | `llm_prompt_variant=v13`, `llm_percentage=0.3`, `llm_temperature=0` |
| `cal_a3` | H1 (stagnation-only) | `llm_prompt_variant=v13`, `llm_percentage=0`, `llm_temperature=0`, `llm_on_new_state=False` |
| `cal_a4` | H1 (both triggers) | `llm_prompt_variant=v13`, `llm_percentage=0`, `llm_temperature=0` |
| `cal_a5` | H3 (vendor bundle) | `llm_prompt_variant=v13`, `llm_percentage=0.3`, `llm_temperature=0.7`, `llm_top_p=0.8`, `llm_top_k=20` |
| `cal_a6` | H3 (temperature isolated) | `llm_prompt_variant=v13`, `llm_percentage=0.3`, `llm_temperature=0.7` |
| `cal_a7` | H3 (AutoDroid point) | `llm_prompt_variant=v13`, `llm_percentage=0.3`, `llm_temperature=0.25` |
| `cal_a8` | H2 (short extreme) | `llm_prompt_variant=visual_only`, `llm_percentage=0.3`, `llm_temperature=0` |
| `cal_a9` | H2 (long extreme) | `llm_prompt_variant=v17`, `llm_percentage=0.3`, `llm_temperature=0` |

Every arm's effective configuration after re-expression SHALL be identical to its pre-change effective
configuration (INV-APV-44); any intentional divergence requires owner approval and a new arm name
(INV-APV-42).

#### Scenario: MOP arm as preset plus deltas

- **WHEN** `get_variants()["sata_mop_act_frontier"]` is read
- **THEN** `preset` SHALL be `"mop"` and `mop_data` SHALL be `"static_analysis"`
- **AND** `overrides` SHALL contain exactly `mop_activity_source_components=True`,
  `frontier_boost_weight=200`, `mop_frontier_weight=200`, `activity_trigger_enabled=True`
- **AND** no MOP weight key SHALL appear, because the `mop` preset already states
  `ape.mopWeightDirect=500`, `ape.mopWeightTransitive=300`, `ape.mopWeightOpenMenu=250` and
  `ape.mopWeightWtg=200`

#### Scenario: Arm identical to its preset

- **WHEN** `get_variants()["sata_mop_widget"]` is read
- **THEN** `preset` SHALL be `"mop"` and `overrides` SHALL be empty
- **AND** the same SHALL hold for `default`, `sata` and `random` against the `aperv` preset

#### Scenario: LLM arm carries the server URL

- **WHEN** `get_variants()["sata_mop_llm"]` is read
- **THEN** `preset` SHALL be `"llm_mop"` and `overrides` SHALL be exactly
  `{"llm_url": "http://10.0.2.2:30000/v1"}`
- **AND** every variant whose preset is `llm` or `llm_mop` SHALL likewise carry `llm_url`
  (INV-APV-38)

#### Scenario: Frozen prompt arm keeps the defaults it inherited

- **WHEN** `get_variants()["sata_mop_llm_v13"]` is read
- **THEN** `overrides` SHALL contain `frontier_boost_weight=200` and `activity_trigger_enabled=True`
- **AND** it SHALL contain `llm_percentage=0.7`, `llm_prompt_variant="v13"` and `llm_url`
- **AND** the module SHALL contain no `_ARM_DEFINING_EXEMPT` constant

#### Scenario: Calibration arm states only what it varies

- **WHEN** `get_variants()["cal_a6"]` and `get_variants()["cal_a5"]` are compared
- **THEN** both SHALL carry `preset="llm_mop"` and the same four frontier overrides
- **AND** the difference SHALL be exactly `llm_top_p` and `llm_top_k`: present in `cal_a5` at `0.8`
  and `20`, absent from `cal_a6` because it uses the preset's `0.6` and `50`
- **AND** both SHALL carry `llm_temperature=0.7` and `llm_percentage=0.3`

#### Scenario: The frozen arm name keeps resolving

- **WHEN** `get_variants()` is read
- **THEN** `variants["sata_mop"]` SHALL be present and SHALL be the same object as
  `variants["sata_mop_widget"]`
- **AND** a resume over an existing `aperv:sata_mop` result directory SHALL still match its arm

#### Scenario: Retired variants are absent

- **WHEN** `get_variants()` is read after this change
- **THEN** the mapping SHALL have exactly 27 keys
- **AND** `"ape_pure"` and `"bfs"` SHALL NOT be among them
- **AND** the module SHALL contain no `_APE_PURE_ARM_FLAGS` constant — purity is structural in the
  jar, and `ape.apePureMode` is a retired key that aborts resolution
- **AND** both names SHALL appear in the migration arm report as documented removals, not as diffs

#### Scenario: No arm carries a property expansion

- **WHEN** any variant returned by `get_variants()` is inspected
- **THEN** its top-level keys SHALL be drawn only from `preset`, `overrides`, `strategy`, `mop_data`,
  `seed`, `expected_jar_git_sha` and `expected_jar_sha256`
- **AND** the module SHALL contain none of `_BASELINE_ARM_FLAGS`, `_MOP_SUBSTRATE`, `_LLM_FLAGS`,
  `_FRONTIER_SUBSTRATE`, `_MOP_OFF_OVERRIDES` or `_CAL_LLM_COMMON`
- **AND** no variant SHALL contain a `throttle_ms` key

---

### Requirement: ApeRVTool Configuration (FR19)

`ApeRVTool.configure(config)` SHALL store the resolved variant configuration in `self._tool_config`
after validation. It SHALL validate that `config["strategy"]` is one of `["sata", "random"]`, that
`config["preset"]` is present and non-empty, and that `config.get("overrides", {})` is a dict. If any
check fails, it SHALL raise `ConfigurationError` before any device interaction.

The whitelist SHALL shrink from the pre-change `["sata", "random", "bfs", "dfs"]` — the deletion stage
2 delegated to this change. `bfs` and `dfs` are not agent types: `ApeAgent.createAgent` recognises
`sata`, `random` and `replay` and nothing else, so before stage 2 they ran `SataAgent` silently and
after it they abort on the device. Accepting them Python-side would let a run pass local validation
only to fail on the emulator, which is precisely the silent-degradation class the re-architecture
exists to remove. `replay` is legal in the jar but SHALL NOT be accepted here: it requires
`--ape-replay <log>`, which this tool never passes.

When the `APERV_LLM_BASE_URL` environment variable is set and `llm_url` is present in the config, the
environment variable value SHALL override the config value. This allows operators to redirect LLM
traffic without modifying variant definitions.

#### Scenario: Valid preset arm configured
- **WHEN** `configure({"strategy": "sata", "preset": "mop", "overrides": {}})` is called
- **THEN** `self._tool_config["preset"]` SHALL equal `"mop"`
- **AND** no exception SHALL be raised

#### Scenario: Missing preset raises ConfigurationError
- **WHEN** `configure({"strategy": "sata"})` is called
- **THEN** `ConfigurationError` SHALL be raised naming the missing `preset` key

#### Scenario: Invalid strategy raises ConfigurationError
- **WHEN** `configure({"strategy": "unknown", "preset": "aperv"})` is called
- **THEN** `ConfigurationError` SHALL be raised with a message listing valid strategies

#### Scenario: Retired strategy rejected before the device
- **WHEN** `configure({"strategy": "bfs", "preset": "aperv"})` or
  `configure({"strategy": "dfs", "preset": "aperv"})` is called
- **THEN** `ConfigurationError` SHALL be raised before any device interaction
- **AND** the run SHALL NOT reach the jar, where an unknown `--ape` value aborts

#### Scenario: Non-dict overrides rejected
- **WHEN** `configure({"strategy": "sata", "preset": "mop", "overrides": ["frontier_boost_weight"]})`
  is called
- **THEN** `ConfigurationError` SHALL be raised naming the `overrides` key

#### Scenario: LLM URL override via environment variable
- **WHEN** `configure({"strategy": "sata", "preset": "llm", "overrides": {"llm_url": "http://10.0.2.2:30000/v1"}})` is called
- **AND** the `APERV_LLM_BASE_URL` environment variable is set to `"http://192.168.1.100:30000/v1"`
- **THEN** the effective `llm_url` SHALL be `"http://192.168.1.100:30000/v1"`

---

### Requirement: ApeRVTool Execution Flow (FR18, FR19)

`ApeRVTool.execute_tool_specific_logic(task, app)` SHALL perform the following steps in order:

1. **Extract execution parameters**: Resolve `device_serial` from `task.config.device_id` (default `"emulator-5554"`) and `timeout_seconds` from `task.config.timeout` (default 300).

2. **Push JAR**: Resolve `ape-rv.jar` via `_resolve_jar_path()` and push to `/data/local/tmp/ape-rv.jar` via `_push_file_to_device()`.

3. **Push broadcast catalog**: If `system-broadcast.json` exists in the module directory (`os.path.dirname(__file__)`), push it to `/data/local/tmp/system-broadcast.json`. This catalog provides typed extras for system broadcast intents used by APE-RV's component triggering. If the file is absent, skip (APE-RV degrades gracefully).

4. **Derive and push the MOP artifact** (MOP variants only): When `_tool_config.get("mop_data") == "static_analysis"`, locate `<task.results_dir>/<apk_name>.json`, derive `<task.results_dir>/<apk_name>.mop.json` from it, and push **only that artifact** to `/data/local/tmp/mop-artifact.json`. The source document is never modified and never pushed. A MOP arm with no static-analysis JSON, or whose derivation fails, raises `RVToolExecutionError`.

5. **Push ape.properties**: Generate `ape.properties` as `ape.preset=<preset>` first, then `ape.mopDataPath=<artifact device path>` when the MOP artifact was pushed, then one `ape.<key>=<value>` line per entry of `overrides`, translated through `APERV_PROPERTY_MAPPING`. Push to `/data/local/tmp/ape.properties`. The full property expansion of the pre-change mapping loop SHALL NOT be performed.

6. **Capture LLM backend provenance** (LLM arms only): query `GET {llm_url}/v1/models` once and record the result in the task output -- see "Per-Run LLM Backend Provenance". A failed query is encoded, never inferred from configuration, and never aborts the run (INV-APV-33).

7. **Build and execute command**: Build the `app_process` command via `_build_main_command()` and execute it, capturing stdout+stderr to `task.result.trace_file` in binary write mode. From stage 4 onward the captured stream is the NDJSON trace. **Command timeout is `timeout_seconds + 45` seconds** — widened from `+ 15`; see the grace-window rationale below.

8. **Handle timeout**: If `RVCommandTimeoutError` is raised, log it as the expected exit path for an exploration tool, run the collection step 10 below on the trace captured up to the kill, and only then re-raise as `RVToolTimeoutError`. Collection MUST NOT be skipped on the timeout path — timeout is how a normal exploration run ends, so skipping it there would exempt the majority of runs from collection. The `RVToolTimeoutError` contract SHALL be stated as `task.config.timeout + 45` seconds wherever it is documented.

9. **Check empty trace**: Call `_check_empty_trace()` and log a warning if the trace file is empty. This step is unchanged — a 0-byte NDJSON trace is still 0 bytes.

10. **Gzip at collection**: Compress the raw capture to `<trace>.ndjson.gz` next to the trace file. On failure, log a WARNING and continue.

Step 10 SHALL NOT inspect, validate or act on the trace's content: no `RUN_START` or `RUN_END` presence check, no exit-code interpretation beyond the existing debug log, no task-status change (INV-APV-53). `task.result.trace_file` SHALL remain the raw capture, byte-for-byte, after collection completes — no step of this flow rewrites, reformats or truncates it, and no NDJSON→legacy conversion step exists anywhere in the tool (INV-APV-52).

The tool SHALL NOT read back, parse or validate any jar output, `RUN_START` included (INV-APV-43, owner decision D1). The effective plan the jar resolved is echoed write-only into the trace; reconstructing which arm ran a task is post-hoc analysis, not a runtime check.

No health-check step is required (APE has no `--health-check` flag).

**Capture grace window: why 45 s.** The window exists so the agent's teardown can finish writing before the harness kills the capture. The 15 s it replaces is where the losses concentrate: among runs whose teardown completed, the overrun beyond the exploration budget reaches **12,991 ms** with 32 runs stacked against that ceiling and none beyond it — the signature of a hard wall rather than a natural distribution. Runs that lose the dump end inside the model serialization step, before the dump would have run.

This is recorded as a **hypothesis, not a measurement**. The true teardown duration of the runs that were cut is unobservable — that is what censoring means — so the widened window cannot be credited with a predicted recovery rate in advance. It is complementary to, not redundant with, the jar-side reordering (`ape` design D9): the reordering moves the dump ahead of the expensive write, this gives the chain room to finish. The smoke SHALL report the observed teardown durations under the new window so the assumption is checked rather than carried.

The `app_process` invocation SHALL use:
```
adb -s <serial> shell CLASSPATH=/data/local/tmp/ape-rv.jar /system/bin/app_process /system/bin
  com.android.commands.monkey.Monkey -p <package_name>
  --running-minutes <max(1, timeout_seconds // 60)>
  --ape <strategy>
  [-s <seed>]
```

The trailing `-s <seed>` is appended only when a seed is configured (INV-APV-18).

#### Scenario: Successful APE-RV execution with sata variant
- **WHEN** `execute_tool_specific_logic(task, app)` is called with `strategy="sata"`, timeout=60
- **THEN** `ape-rv.jar` SHALL be pushed to `/data/local/tmp/ape-rv.jar`
- **AND** the adb command SHALL include `--running-minutes 1` and `--ape sata`
- **AND** stdout+stderr SHALL be written to `task.result.trace_file`
- **AND** no MOP artifact SHALL be pushed to the device

#### Scenario: Properties file carries preset plus deltas only
- **WHEN** step 5 runs for `sata_mop_act_frontier` with the MOP artifact pushed
- **THEN** the generated file SHALL begin with `ape.preset=mop`
- **AND** SHALL contain `ape.mopDataPath=/data/local/tmp/mop-artifact.json`
- **AND** SHALL contain exactly the four override lines `ape.mopActivitySourceComponents=true`,
  `ape.frontierBoostWeight=200`, `ape.mopFrontierWeight=200`, `ape.activityTriggerEnabled=true`
- **AND** SHALL contain no other `ape.*` line

#### Scenario: Collection leaves the NDJSON trace intact
- **WHEN** a run completes and `task.result.trace_file` holds 1,603 NDJSON records
- **THEN** after step 10 the file SHALL still hold exactly those 1,603 records, byte-for-byte
- **AND** `<trace>.ndjson.gz` SHALL decompress to the identical byte sequence
- **AND** no `[APE-STEP]`, `[APE-OUTCOME]` or `[APE-LLM-TEL]` line SHALL have been written anywhere by the tool

#### Scenario: Gzip failure is non-fatal and changes no status
- **WHEN** compression raises (for example, no space left on the results volume)
- **THEN** a WARNING SHALL be logged naming the trace path
- **AND** the uncompressed trace SHALL remain at `task.result.trace_file`
- **AND** the task SHALL complete with the same status it would have had otherwise

#### Scenario: Timeout during exploration still collects
- **WHEN** the exploration runs past `task.config.timeout + 45` seconds and `RVCommandTimeoutError` is raised
- **THEN** step 10 SHALL run on the trace captured up to the kill
- **AND** only then SHALL `RVToolTimeoutError` be re-raised
- **AND** the trace SHALL retain the records written before the kill, including a truncated final line if the kill landed mid-write

#### Scenario: No exit contract
- **WHEN** a trace ends without a `RUN_END` record because the process was killed before teardown
- **THEN** the tool SHALL NOT detect, log or act on its absence
- **AND** the task status SHALL be identical to that of a run whose trace ends with `RUN_END`

#### Scenario: No echo read-back
- **WHEN** the run completes and the trace's first record is the jar's `RUN_START` echo of the
  resolved plan
- **THEN** the tool SHALL NOT have parsed, validated or branched on it (INV-APV-43)

#### Scenario: Broadcast catalog pushed when present
- **WHEN** `system-broadcast.json` exists in the module directory
- **THEN** it SHALL be pushed to `/data/local/tmp/system-broadcast.json`
- **AND** APE-RV SHALL use it for component triggering with typed extras

#### Scenario: Broadcast catalog absent
- **WHEN** `system-broadcast.json` does not exist in the module directory
- **THEN** no broadcast catalog SHALL be pushed
- **AND** execution SHALL continue normally (APE-RV component triggering degrades gracefully)

#### Scenario: Execution timeout
- **WHEN** APE-RV runs for longer than `timeout_seconds + 45` seconds
- **THEN** `RVToolTimeoutError` SHALL be raised and logged
- **AND** the timeout SHALL be re-raised to the caller after collection has run

#### Scenario: Non-zero exit code from APE-RV
- **WHEN** APE-RV exits with a non-zero exit code (e.g., 211)
- **THEN** execution SHALL NOT raise an error
- **AND** a debug log SHALL be emitted noting the exit code is normal when app crashes are detected

#### Scenario: Empty trace file
- **WHEN** APE-RV execution completes but writes nothing to stdout
- **THEN** a warning log line SHALL contain `"aperv produced empty trace file"`

#### Scenario: Timeout budget includes the widened grace window
- **WHEN** a task is dispatched with an exploration timeout of `T` seconds
- **THEN** the `adb` command SHALL be given `T + 45` seconds before termination
- **AND** `RVToolTimeoutError` SHALL be raised only after `T + 45` seconds, not `T + 15`

#### Scenario: Smoke reports what the window actually cost
- **WHEN** the integration smoke completes
- **THEN** the observed teardown overrun SHALL be reported per run
- **AND** a run whose overrun still reaches the new ceiling SHALL be flagged as evidence the hypothesis was insufficient

#### Scenario: Provenance query does not delay the run
- **WHEN** the `/v1/models` query at step 6 fails or times out
- **THEN** the flow SHALL proceed to step 7
- **AND** the provenance fields SHALL record the failure (INV-APV-33)

---

### Requirement: ape.properties Generation

`ApeRVTool._push_properties()` SHALL generate an `ape.properties` file and push it to
`/data/local/tmp/ape.properties` on the device. The file SHALL be composed in a fixed order so that
two runs of the same arm produce byte-identical output:

```text
ape.preset=<preset>                                   # always first
ape.mopDataPath=/data/local/tmp/mop-artifact.json     # only when the artifact was pushed
ape.<mapped-override-key>=<value>                     # one line per overrides entry, mapping order
```

Only the entries of `_tool_config["overrides"]` are translated and written. Python-only keys
(`preset` itself apart from the first line, `strategy`, `mop_data`, `seed`, `expected_jar_git_sha`,
`expected_jar_sha256`) have no mapping entry and never reach the file. Python bools SHALL be
serialized lowercase (`True` → `true`). An `overrides` key with no `APERV_PROPERTY_MAPPING` entry
SHALL raise `ConfigurationError` before any `adb push`: under fail-fast a misspelled key would abort
the run on the device anyway, and catching it on the host saves emulator time (same rationale as
INV-APV-02).

`APERV_PROPERTY_MAPPING` is a pass-through translation table and nothing more (see "Arm Property
Overrides Pass-Through"). It SHALL contain only keys the deployed jar accepts (INV-APV-41). The 50
entries are:

| Python Key | Java Property | Notes |
|------------|--------------|-------|
| `throttle_ms` | `ape.defaultGUIThrottle` | in every preset; an override only when an arm deviates |
| `default_epsilon` | `ape.defaultEpsilon` | exploration |
| `graph_stable_restart_threshold` | `ape.graphStableRestartThreshold` | exploration |
| `state_stable_restart_threshold` | `ape.stateStableRestartThreshold` | exploration |
| `fuzzing_rate` | `ape.fuzzingRate` | `FUZZING` sub-parameter |
| `do_fuzzing` | `ape.doFuzzing` | `FUZZING` activation |
| `throttle_for_activity_transition` | `ape.throttleForActivityTransition` | exploration |
| `max_extra_priority_aliased_actions` | `ape.maxExtraPriorityAliasedActions` | exploration |
| `max_states_per_activity` | `ape.maxStatesPerActivity` | exploration |
| `trivial_activity_rank_threshold` | `ape.trivialActivityRankThreshold` | exploration |
| `do_back_to_trivial_activity` | `ape.doBackToTrivialActivity` | exploration |
| `back_menu_pick_cap` | `ape.backMenuPickCap` | exploration |
| `max_idle_timeout_ms` | `ape.maxIdleTimeoutMs` | arm-neutral tuning knob |
| `foreign_activity_guard` | `ape.foreignActivityGuard` | `FOREIGN_ACTIVITY_GUARD` |
| `tree_package_guard` | `ape.treePackageGuard` | `TREE_PACKAGE_GUARD` |
| `dynamic_epsilon` | `ape.dynamicEpsilon` | `DYNAMIC_EPSILON` |
| `heuristic_input` | `ape.heuristicInput` | `HEURISTIC_INPUT` |
| `fuzz_input_typed` | `ape.fuzzInputTyped` | `TYPED_FUZZ` |
| `form_completion_enabled` | `ape.formCompletionEnabled` | `FORM_COMPLETION` |
| `step_telemetry_enabled` | `ape.stepTelemetryEnabled` | `STEP_TELEMETRY` |
| `model_menu_enabled` | `ape.modelMenuEnabled` | `MODEL_MENU` |
| `least_visited_priority_tiebreak` | `ape.leastVisitedPriorityTiebreak` | `LEAST_VISITED_TIEBREAK` |
| `tree_enhancements_enabled` | `ape.treeEnhancementsEnabled` | `TREE_ENHANCEMENTS` |
| `activity_budget_enabled` | `ape.activityBudgetEnabled` | `ACTIVITY_BUDGET` |
| `mop_weight_direct` | `ape.mopWeightDirect` | `MOP` sub-parameter |
| `mop_weight_transitive` | `ape.mopWeightTransitive` | `MOP` sub-parameter |
| `mop_weight_open_menu` | `ape.mopWeightOpenMenu` | `MENU_GATEWAY` activation |
| `mop_weight_wtg` | `ape.mopWeightWtg` | `WTG` activation |
| `mop_activity_source_components` | `ape.mopActivitySourceComponents` | `MOP_ACTIVITY_SOURCE` |
| `mop_frontier_weight` | `ape.mopFrontierWeight` | `MOP_FRONTIER` activation |
| `frontier_boost_weight` | `ape.frontierBoostWeight` | `FRONTIER` activation |
| `activity_trigger_enabled` | `ape.activityTriggerEnabled` | `ACTIVITY_TRIGGER` activation |
| `activity_trigger_stagnation_step` | `ape.activityTriggerStagnationStep` | `ACTIVITY_TRIGGER` sub-parameter |
| `activity_trigger_max_per_run` | `ape.activityTriggerMaxPerRun` | `ACTIVITY_TRIGGER` sub-parameter |
| `component_percentage` | `ape.componentPercentage` | `COMPONENT_TRIGGER` activation |
| `mop_target_pick_cap` | `ape.mopTargetPickCap` | `MOP` sub-parameter |
| `coverage_boost_weight` | `ape.coverageBoostWeight` | `COVERAGE_BOOST` activation |
| `llm_url` | `ape.llmUrl` | `LLM` activation; required on every LLM-preset arm (INV-APV-38) |
| `llm_on_new_state` | `ape.llmOnNewState` | `LLM_NEW_STATE` activation |
| `llm_on_stagnation` | `ape.llmOnStagnation` | `LLM_STAGNATION` activation |
| `llm_model` | `ape.llmModel` | `LLM` sub-parameter |
| `llm_temperature` | `ape.llmTemperature` | `LLM` sub-parameter |
| `llm_top_p` | `ape.llmTopP` | `LLM` sub-parameter |
| `llm_top_k` | `ape.llmTopK` | `LLM` sub-parameter |
| `llm_timeout_ms` | `ape.llmTimeoutMs` | `LLM` sub-parameter |
| `llm_percentage` | `ape.llmPercentage` | `LLM_RANDOM` activation |
| `llm_percentage_no_substrate` | `ape.llmPercentageNoSubstrate` | `LLM_RANDOM` sub-parameter; the `-1` sentinel is accepted on a plan with no LLM |
| `llm_prompt_variant` | `ape.llmPromptVariant` | `LLM` sub-parameter |
| `llm_max_tokens` | `ape.llmMaxTokens` | `LLM` sub-parameter |
| `llm_snap_tolerance_px` | `ape.llmSnapTolerancePx` | `LLM` sub-parameter; paired with the jar digests (INV-APV-34) |

`mop_weight_activity → ape.mopWeightActivity` is deleted: the jar's `KeyOwnership` table lists
`ape.mopWeightActivity` as retired ("dead since mop-fairtest: the weight it named was deleted from
the scorer"), so a properties file carrying it now aborts the run rather than being ignored. No arm
set it.

A key the jar does not recognise is no longer inert. Under stage-2 resolution an unknown key, a
retired key, or a non-neutral value of an inactive feature aborts before step 1 — which is what makes
the mapping's contents a correctness property rather than a tidiness one.

#### Scenario: Preset line comes first
- **WHEN** `_push_properties()` is called for `sata_mop_llm` with the MOP artifact pushed
- **THEN** the first line SHALL be `ape.preset=llm_mop`
- **AND** the second SHALL be `ape.mopDataPath=/data/local/tmp/mop-artifact.json`
- **AND** the only remaining line SHALL be `ape.llmUrl=http://10.0.2.2:30000/v1`

#### Scenario: Empty-override arm writes two lines
- **WHEN** `_push_properties()` is called for `sata_mop_widget` with the MOP artifact pushed
- **THEN** the file SHALL contain exactly `ape.preset=mop` and the `ape.mopDataPath` line
- **AND** no `ape.mopWeight*` line SHALL appear, because those values come from the preset

#### Scenario: Baseline arm writes one line
- **WHEN** `_push_properties()` is called for the `sata` variant
- **THEN** the file SHALL contain exactly `ape.preset=aperv`
- **AND** it SHALL NOT contain `ape.mopDataPath`, `ape.frontierBoostWeight` or `ape.dynamicEpsilon`

#### Scenario: Bools are serialized lowercase
- **WHEN** `_push_properties()` is called for `sata_mop_act_frontier`
- **THEN** the file SHALL contain `ape.activityTriggerEnabled=true`, not `True`
- **AND** it SHALL contain `ape.mopActivitySourceComponents=true`

#### Scenario: Unmapped override key aborts before push
- **WHEN** an arm's `overrides` contains `frontier_bost_weight` (a typo absent from
  `APERV_PROPERTY_MAPPING`)
- **THEN** `ConfigurationError` SHALL be raised naming the key
- **AND** no `adb push` SHALL have been issued

#### Scenario: Retired jar key is not in the mapping
- **WHEN** `APERV_PROPERTY_MAPPING` is inspected after this change
- **THEN** it SHALL NOT contain `mop_weight_activity`
- **AND** it SHALL contain exactly 50 entries
- **AND** it SHALL still contain `llm_max_tokens` and `llm_snap_tolerance_px`, which are live
  `Feature.LLM` sub-parameters

#### Scenario: Python-only keys are still excluded
- **WHEN** `_push_properties()` is called for `mop_on_llm_70`, whose `_tool_config` carries
  `strategy`, `mop_data`, `seed`, `expected_jar_git_sha` and `expected_jar_sha256`
- **THEN** the properties file SHALL contain none of those five names
- **AND** it SHALL contain `ape.llmSnapTolerancePx=150`, which is an ordinary override

---

### Requirement: Decisive Run Arm Set (FR20)

`aperv-tool` SHALL define the three arms of the E3 decisive run as named variants, so that each arm's
identity comes from its preset and override dict and never from an undeclared inheritance. The three
arms SHALL be:

1. **`mop_on_llm_off`** — reference: MOP guidance on, LLM off. The shared baseline of both contrasts.
2. **`mop_off_llm_off`** — control: MOP guidance off, LLM off. Isolates the effect of MOP guidance
   (the study's central hypothesis).
3. **`mop_on_llm_70`** — LLM arm: MOP guidance on, LLM on at `llm_percentage=0.7`. Isolates the effect
   of adding the LLM.

The variant names are normative, not cosmetic: the variant string is the resume identity key and the
consolidation column key, so a rename silently splits a campaign's results.

All three SHALL carry `mop_data="static_analysis"` and the frontier substrate (INV-APV-30) — the
control removes MOP guidance, not navigation. Expressed as preset + overrides:

| Arm | preset | overrides |
|---|---|---|
| `mop_on_llm_off` | `mop` | `mop_activity_source_components=True`, `frontier_boost_weight=200`, `mop_frontier_weight=200`, `activity_trigger_enabled=True` |
| `mop_off_llm_off` | `mop` | `mop_activity_source_components=True`, `frontier_boost_weight=200`, `mop_weight_direct=0`, `mop_weight_transitive=0`, `mop_weight_open_menu=0`, `mop_weight_wtg=0` |
| `mop_on_llm_70` | `llm_mop` | the reference's four, plus `llm_url`, `llm_prompt_variant="v13"`, `llm_percentage=0.7`, `llm_temperature=0`, `llm_snap_tolerance_px=150` |

The control's shape is fixed by INV-APV-29 and is now expressed jointly by the preset and the
overrides: `mop_data` present and loadable (top-level), all four MOP weights zeroed and
`mop_frontier_weight` at the preset's `0` (so `WTG`, `MENU_GATEWAY` and `MOP_FRONTIER` are inactive at
their neutral values), and `activity_trigger_enabled` at the preset's `false`. `frontier_boost_weight`
stays at `200` deliberately, keeping `FRONTIER` active. The alternatives are worse and were rejected
for reasons that have not changed: pointing `ape.mopDataPath` at a missing file aborts the run, and
omitting `mop_data` kills the generic WTG and frontier passes as collateral, turning the contrast into
"full substrate versus almost none".

Single-factor remains a property of the **effective plan**, and the override dicts now make it
readable directly. Reference minus control is exactly the five MOP weight keys plus
`activity_trigger_enabled`; reference minus LLM arm is exactly the LLM keys. The two B3 declarations
(`expected_jar_git_sha`, `expected_jar_sha256`) are the one exemption from that diff, and they are safe
because they are **inert by construction**: neither is in `APERV_PROPERTY_MAPPING`, so neither is
written to `ape.properties` and neither can reach the jar. The test that keeps them out of the mapping
is what licenses the exemption.

#### Scenario: Control arm keeps the frontier alive while MOP guidance is off
- **WHEN** `get_variants()["mop_off_llm_off"]` is resolved
- **THEN** `mop_data` SHALL equal `"static_analysis"`
- **AND** `overrides` SHALL contain `mop_weight_direct=0`, `mop_weight_transitive=0`,
  `mop_weight_open_menu=0`, `mop_weight_wtg=0`
- **AND** `overrides` SHALL contain `frontier_boost_weight=200`, so generic WTG and frontier
  navigation stay enabled (INV-APV-30)
- **AND** `mop_frontier_weight` and `activity_trigger_enabled` SHALL be absent from `overrides`,
  taking the `mop` preset's `0` and `false`

#### Scenario: Control arm never omits the static analysis document
- **WHEN** the guard test inspects the control arm's variant dictionary
- **THEN** `mop_data` SHALL be present at the top level
- **AND** the test SHALL fail naming INV-APV-29 if it is absent, because an absent document disables
  `WtgPass` and `FrontierPass` as collateral damage

#### Scenario: Reference and control differ only in MOP keys
- **WHEN** the effective configurations of `mop_on_llm_off` and `mop_off_llm_off` are diffed
- **THEN** the differing keys SHALL be exactly `ape.mopWeightDirect`, `ape.mopWeightTransitive`,
  `ape.mopWeightOpenMenu`, `ape.mopWeightWtg`, `ape.mopFrontierWeight` and
  `ape.activityTriggerEnabled`
- **AND** every other key SHALL be identical, so the contrast is single-factor

#### Scenario: Reference and LLM arm differ only in LLM keys
- **WHEN** the effective configurations of `mop_on_llm_off` and `mop_on_llm_70` are diffed
- **THEN** every differing key SHALL be an `ape.llm*` key
- **AND** the same test SHALL assert that neither `expected_jar_git_sha` nor `expected_jar_sha256` is
  present in `APERV_PROPERTY_MAPPING`, since that absence is what makes the exemption safe rather
  than a hole in the contrast
- **AND** no MOP weight, frontier or exploration key SHALL differ

#### Scenario: Source components flag is explicit in all three arms
- **WHEN** the three decisive-run arms are iterated
- **THEN** each SHALL carry `mop_activity_source_components=True` in its `overrides`
- **AND** none SHALL rely on the `mop` preset's `false`

## ADDED Requirements

### Requirement: Arm Property Overrides Pass-Through

`APERV_PROPERTY_MAPPING` SHALL be a pass-through table and nothing more: it exists to translate a
Python override key into an `ape.*` property name, and it SHALL contain only keys the deployed jar
accepts (INV-APV-41). Behavioural validation of values, types, dependencies and combinations is the
jar's responsibility under stage-2 fail-fast resolution; the Python side SHALL perform no semantic
validation of overrides beyond the mapping-membership check.

This is a deliberate transfer of responsibility rather than a loss of one. The pre-change guards
could only compare Python constants with Python constants, so they detected a missing mapping entry
but never a value the jar would reject, a sub-parameter whose feature was inactive, or a key the jar
had stopped reading. The jar now rejects all four, at run time, with an abort naming the key — a
stronger check than the one being retired, applied to the binary that actually runs.

At implementation time the mapping SHALL be swept against the jar's accepted-key vocabulary
(`KeyOwnership.allKeys()` plus the retired list, read from the `ape` source checkout) and any dead
entry removed. The sweep performed while authoring this change found exactly one:
`mop_weight_activity`. The remaining 50 entries are all accepted keys.

`llm_snap_tolerance_px` SHALL remain mapped and reach the jar only as an explicit override of the arm
that sets it (`mop_on_llm_70`), subject to the jar's own feature-dependency validation. Its Python-side
pairing with the declared jar digests (INV-APV-34) is retained unchanged: that gate compares a
declaration against a digest computed from the installed binary at run start, which is provenance
verification, not a constant-vs-constant arm guard, and it is therefore not part of what this change
retires.

#### Scenario: Dead key removed
- **WHEN** `APERV_PROPERTY_MAPPING` is inspected after this change
- **THEN** it SHALL NOT contain `mop_weight_activity`
- **AND** a grep for `mopWeightActivity` across `modules/aperv-tool/src` SHALL return no hit

#### Scenario: Every mapped key is one the jar accepts
- **WHEN** each value of `APERV_PROPERTY_MAPPING` is checked against the jar's accepted-key
  vocabulary
- **THEN** every one SHALL be present in it
- **AND** none SHALL appear in the jar's retired-key list

#### Scenario: Live ungoverned key travels the normal path
- **WHEN** `get_variants()["mop_on_llm_70"]` is read
- **THEN** `llm_snap_tolerance_px: 150` SHALL be an entry of its `overrides`
- **AND** `_push_properties()` SHALL write `ape.llmSnapTolerancePx=150` for that arm
- **AND** `expected_jar_git_sha` and `expected_jar_sha256` SHALL remain Python-only and SHALL NOT
  reach `ape.properties`

#### Scenario: No semantic validation is performed on override values
- **WHEN** an arm's `overrides` carries a mapped key at a value the jar will reject
- **THEN** `_push_properties()` SHALL write it unchanged
- **AND** the rejection SHALL come from the jar as an abort before step 1, visible in the trace

---

### Requirement: One-Time Arm Regeneration Migration Check

Before any arm is edited, a capture script SHALL record each of the 29 pre-change arms' **effective
configuration** — the canonical `{ape.key: typed value}` map obtained by expanding the properties the
current code writes over the jar's declared defaults — into a committed baseline file
(`modules/aperv-tool/tests/migration/arm_effective_baseline.json`). During the migration, a pytest
(`tests/migration/test_arm_regeneration_diff.py`) SHALL recompute each re-expressed arm's effective
configuration from `preset vector + overrides` and assert an empty diff against the baseline, per arm
(INV-APV-44).

The comparison SHALL be typed, using each key's declared `ValueType` from the jar's ownership table.
A textual comparison would report `ape.llmPercentageNoSubstrate` as changed on every arm — the preset
writes `-1` where the declared default is `-1.0` — and would drown the real signal in formatting
noise.

The two retired names (`ape_pure`, `bfs`) SHALL be carried in an explicit retirement list that the
test reads. They are reported as documented retirements and excluded from the diff, so a retirement
can never be mistaken for a regeneration failure, nor a silent deletion for a retirement. Preset
vectors, the accepted-key table and the defaults are parsed from the `ape` source checkout **for this
purpose only**: the migration tooling is not a runtime dependency of `aperv-tool` and creates no
shared manifest between the repositories.

The check SHALL be re-run after every task group that edits arms, and it gates this change. A non-empty
diff is either a re-expression bug — fix it — or an intentional divergence, which requires owner
approval and a **new arm name** (INV-APV-42). There is no third option.

After the final full diff and owner sign-off, the test SHALL be deleted and the baseline plus the final
diff output archived under `modules/aperv-tool/docs/` as the migration record. The check is one-time by
design: keeping it would recreate the retired INV-APV-14 — a constant validated against a frozen copy
of itself — under a new number.

#### Scenario: Baseline captured before edits
- **WHEN** the migration starts
- **THEN** `arm_effective_baseline.json` SHALL exist and cover all 29 pre-change arm names, including
  `ape_pure` and `bfs`, before any variant dict is modified

#### Scenario: Re-expression gated per group
- **WHEN** a group of arms has been re-expressed as preset + overrides
- **THEN** `test_arm_regeneration_diff.py` SHALL pass with an empty diff for every surviving arm,
  migrated and not-yet-migrated alike

#### Scenario: Retirements are listed, not diffed
- **WHEN** the diff report is produced
- **THEN** `ape_pure` and `bfs` SHALL appear in a "documented retirements" section naming why each was
  retired
- **AND** neither SHALL appear as a regeneration difference
- **AND** an arm that disappeared without being on the retirement list SHALL fail the check

#### Scenario: Typed comparison tolerates property-text formatting
- **WHEN** the baseline records `ape.llmPercentageNoSubstrate` as `-1.0` and the regenerated plan
  writes `-1`
- **THEN** the diff SHALL be empty for that key, because both parse to the same `DOUBLE`
- **AND** a genuine change from `-1` to `0` SHALL be reported as a difference

#### Scenario: Frozen prompt arm regenerates identically
- **WHEN** `sata_mop_llm_v13` is regenerated with its `frontier_boost_weight=200` and
  `activity_trigger_enabled=True` overrides
- **THEN** its effective configuration SHALL equal the baseline entry captured from the pre-change
  dict, which inherited both from the jar defaults
- **AND** removing either override SHALL make the diff non-empty, naming the two keys

#### Scenario: Check retired after sign-off
- **WHEN** the owner signs off the final full diff
- **THEN** `test_arm_regeneration_diff.py` SHALL be deleted and the baseline plus diff output archived
  under `modules/aperv-tool/docs/`
- **AND** no standing test SHALL compare arm definitions against a frozen copy of themselves

## REMOVED Requirements

### Requirement: Arm-Defining Flag Completeness (FR20)

**Reason**: This requirement's executable form is the `ARM_DEFINING_KEYS` / `_ARM_DEFINING_EXEMPT` /
`LLM_ARM_KEYS` constants in `tool.py` and the INV-APV-13/14/15/17/19/26/27 guard family in
`tests/test_aperv_tool.py` — a self-referential check that validated Python constants against other
Python constants and never touched the binary that runs. With arms expressed as preset + overrides the
property it enforced dissolves: an arm's identity is its preset (jar-resolved, fail-fast validated)
plus its explicit deltas, there is no expansion left to keep complete, and a missing or misspelled key
aborts the run in the jar instead of passing silently.

Deletion is complete, with no compatibility shim: the three constants, the guard tests, the
`_EXPECTED_ARM_DEFINING_MAPPING` fixture, the frozen name-table pins, and the calibration and
decisive-run expansion-diff tests are removed. Invariants INV-APV-13, INV-APV-14, INV-APV-15,
INV-APV-17, INV-APV-19 and INV-APV-26 are retired with the mechanism they constrain. When a producer
is deleted its outputs go too: `_ARM_DEFINING_EXEMPT` cannot outlive the guard it exempted from, and
`LLM_ARM_KEYS` cannot outlive the dicts it audited.

**Substitute recorded**: (a) the jar's stage-2 resolution, which rejects an unknown key, a retired key,
an invalid type and a non-neutral value of an inactive feature, at run time, with an abort before step
1 — strictly stronger than the retired guards, because it checks the artifact that executes; (b) the
one-time regeneration migration check (INV-APV-44), which proves the re-expression preserved every
surviving arm's calibrated configuration; and (c) write-only level-0 provenance — every trace opens
with `RUN_START` carrying the effective plan, so "which arm ran this task" is answerable from the trace
alone, post-hoc. Per owner decision D1 no runtime validation replaces the guards, and none is added by
this change (INV-APV-43). The single-factor contrasts the guards asserted by expansion are restated as
direct assertions on the override dicts in the "Decisive Run Arm Set" requirement.

---

### Requirement: Calibration Property Mappings (FR20, NFR05)

**Reason**: The requirement exists to state that `llm_max_tokens` and `llm_snap_tolerance_px` are
mapped but deliberately outside `LLM_ARM_KEYS` and set by no `cal_a*` arm — a statement about the
membership of a guard set that this change deletes. With `LLM_ARM_KEYS` gone there is no set to be
outside of, and the two keys become ordinary entries of the pass-through table, governed by
"Arm Property Overrides Pass-Through" and by the jar's own feature-dependency validation.

The mapping entries themselves are **not** removed: both are live `Feature.LLM` sub-parameters in the
jar's ownership table, and `llm_snap_tolerance_px` is set by `mop_on_llm_70`. They are carried into the
`ape.properties Generation` mapping table, where the rest of the pass-through entries are documented.
What is deleted is the requirement's framing — the Phase-A/Phase-B rationale and the guard-membership
claim — which described a campaign that has finished and a guard that no longer exists. INV-APV-27 is
retired with it.

This requirement entered the main spec through the archive of `gh88-cal-llm-control` on 2026-08-03,
which synced the calibration arm tier and the `LLM_ARM_KEYS` guard into `openspec/specs/aperv/spec.md`.
Removing it here is the reciprocal side of that archive, recorded in the re-architecture roadmap as
debt this change owns.
