## Purpose

This delta keeps the offline analysis layer of `aperv-tool` faithful to the trace of the APE-RV group-isolation
jar (`RUN_START.v == 2`), while it keeps reading the traces of every earlier jar (`v == 1`) as before. The reader
change itself is in the `aperv` delta. This delta covers the consumers whose logic depends on a value that
changes meaning or presence in version 2.

Three things change for a consumer:

- **What a control is.** On the earlier jars, the control arm (`mop_off_llm_off`) mounted MOP with its weights
  zeroed, so "clean" meant that no MOP boost fired. On the new jar a control is a cell that does not mount the MOP
  group (`base`, `as`, `as_llm`). "Clean" then means that no member of the MOP group appears in any step record:
  no MOP boost, no MOP stamp, no MOP coin draw, no MOP owner; nor a `mop` member on an `ACT` record, nor a
  non-zero MOP counter in `RUN_END`, which that jar writes only with MOP mounted. The artifact census `MOP_DATA` still appears in `as`
  and `as_llm`, because those cells load the artifact for STATIC. It reports a load, not a mechanism, and it does
  not make a control dirty.
- **How a run proves its cell.** `RUN_START.variant` names the cell directly, beside `preset`, `features` and
  `params`.
- **What two fields mean.** `decision_source` is the largest boost under `v == 1` and the executed owner under
  `v == 2`. `activity_has_mop` is absent where the jar did not compute it.

The clean-control gate also had a defect that predates this change. Its anchored pattern `(?<![a-z_])mop=`
(`analysis/gates.py:83`) matches the retired `key=value` line format, and it cannot match an NDJSON `"mop":` member.
So on every stage-4 trace the gate counted zero whatever the trace carried. The legacy pattern is kept for the
legacy format, and the NDJSON form below replaces it for every NDJSON trace.

## Invariants

- **INV-CAN-07** (replaced): the clean-control signal SHALL be computed in exactly one place, by the form that
  matches the trace. Over a legacy `key=value` stream the pattern SHALL be anchored, `(?<![a-z_])mop=`, so that
  `activity_has_mop=1` never matches. Over an NDJSON trace the signal SHALL be the count of the MOP-group members
  listed in "Validity Gates Run Before Any Outcome", which follow the `ape` clean-control gate (`event-sink`
  INV-SNK-18) on a `v == 2` trace. On a `v == 1` trace it SHALL be the count of steps carrying a non-zero MOP boost
  (`mop` or `mop_frontier`), the meaning the legacy pattern had. `MOP_DATA` SHALL NOT count.
- **INV-CAN-21** (new): no consumer SHALL compare or pool `decision_source` values across traces of different
  `RUN_START.v`. A count of `decision_source` SHALL carry the version it was computed under.
- **INV-CAN-22** (new): a consumer SHALL carry `activity_has_mop = None` through as absent. It SHALL NOT coerce it
  to `False` in an output column, because `None` means "not computed by this cell", not "no MOP".

## MODIFIED Requirements

### Requirement: Validity Gates Run Before Any Outcome (FR13, NFR06)

`analysis/gates.py` SHALL implement the five gates: **1 clean control** (`∀ run ∈ arm_predicate: forbidden_signal(run) == 0`, INV-CAN-07); **2 correct binary** (digest of the artefact under test, captured per run into a sidecar beside it or read from `RUN_START.build.sha`, compared to the manifest — `capture_status` never back-filled from config); **3 arm attribution** (evidenced from the artefact, never from the orchestrator's filename label); **4 task integrity** (identity-not-line, ≥1 COMPLETED, full budget — INV-CAN-08); **5 corpse detection** (three independent signals: trace below a size floor · coverage all zero · a named fatal exception, via `liveness`). Gates 2 and 3 SHALL name their evidence form per arm (INV-CAN-06): `aperv:*` — `RUN_START.build.sha` / `preset` / `features` / `params` against the manifest, plus `RUN_START.variant` against the manifest's cell when the trace is `v == 2`; `droidbot:*` — the `start sending events, policy is …` line against the policy in the filename, digest `not-run` unless a sidecar exists; `ape` — negative evidence, the trace carries zero `{`-leading NDJSON lines (proof the upstream `ape.jar`, not `ape-rv.jar`, ran), digest `not-run` unless a sidecar exists. `not-run` SHALL be reported as such and never as a pass. A richer corpse classification by last non-empty trace line (normal-end / crash / cut-during-teardown / cut-elsewhere) SHALL be emitted beside the boolean.

**The forbidden signal has two forms (INV-CAN-07).** `count_forbidden_signal` keeps its anchored pattern for a
legacy `key=value` stream. A new `count_mop_group_signal(reader)` counts the MOP-group signals of an NDJSON
trace. On a `v == 2` trace the members are the ones the `ape` change lists for its own clean-control gate
(`event-sink` INV-SNK-18; author's decision, 2026-10-17). Each `StepRow` carrying at least one of the following
counts once:

- a non-zero `mop`, `mop_frontier`, `wtg` or `menu`;
- a present `mop_distance`, `mop_stamp`, `retired_targets` or `mop_exposure`;
- an `owner.u_mop`;
- a `scorer_cf` key among `mop`, `mopf`, `wtg`, `menu`;
- a `nav.component == "mop"`;
- a `pick_channel` of `mop_coin` or `launcher`;
- a `decision_source` or an `owner.intended` of `mop` or `launcher`;
- an `activity_has_mop` or `target_activity_has_mop` that is not `None`, which the reader derives from an `ACT`
  record carrying `mop`.

Outside the step rows, each of the following counts once:

- a `UICOV` line carrying `mopReach` (read through `coverage_dump`), which the jar writes only when MOP is mounted
  (`ape` D-B14.21);
- a `RUN_END` (read through `TraceReader.run_end`) whose `counters` carry a non-zero `coinMop`, `launches`,
  `stampHits` or `retired`.

Each of these is a MOP signal because the group-isolation jar writes it only with MOP mounted: `ACT.mop` (`ape`
D-B14.9), `mopReach` (D-B14.21), the MOP scorers and stamps, and those counters, which stay at 0 without MOP.

**On a `v == 1` trace the list is the legacy one** (author's decision, 2026-10-17). The control arm of that jar
(`mop_off_llm_off`) mounted the MOP group with its weights zeroed, so the MOP pass ran and wrote its by-products in
a clean run: on a recorded cmp162 control of 73 steps, `mop_exposure` is on all 73, `wtg` is non-zero on 1, every
`UICOV` line carries `mopReach`, and every `ACT` carries `mop`. Clean meant that no MOP boost fired. So on `v == 1`
a `StepRow` counts once when its `mop` or `mop_frontier` is non-zero, and nothing else counts; that control counts
0. The counter SHALL read the
trace through `TraceReader`, never by a second parser. `MOP_DATA` SHALL NOT count: it reports that the artifact was
loaded, which a STATIC cell does by design.

Which arms are controls is a parameter of the gate (`arm_predicate`), not a constant of the module. On a
group-isolation campaign the controls are the cells that do not mount MOP: `aperv:base`, `aperv:as`,
`aperv:as_llm`.

#### Scenario: Anchored clean-control pattern
- **WHEN** gate 1 scans a legacy control-arm run whose trace contains `activity_has_mop=1` and no `mop=` field
- **THEN** the forbidden-signal count SHALL be 0
- **AND** the unanchored pattern would have counted it — the test SHALL include that line

#### Scenario: Per-arm evidence form and not-run
- **WHEN** gates 2 and 3 run over a cmp162 identity of arm `ape` with no provenance sidecar
- **THEN** gate 2 SHALL report `not-run` with reason `no digest emitted, no sidecar`
- **AND** gate 3 SHALL report `pass` with evidence form `negative: 0 NDJSON lines` when the trace has none, and `fail` if it has any

#### Scenario: A single NDJSON record in an ape-labelled run fails attribution
- **WHEN** an `ape`-labelled trace contains one `{`-leading line
- **THEN** gate 3 SHALL report `fail` for that identity naming the line number

#### Scenario: Corpse detected on the decisive-run pattern
- **WHEN** a run is `COMPLETED` at 65 s of an 1800 s budget with an 864-byte trace, zero step lines and all-zero coverage
- **THEN** gate 4 SHALL fail on duration and gate 5 SHALL classify it `crash` with all three signals set
- **AND** the run SHALL be excluded once, by `liveness`, and reported with its reason

#### Scenario: A STATIC control with the artifact loaded is clean
- **WHEN** gate 1 runs `count_mop_group_signal` over an `aperv:as` trace (`v == 2`) that carries `MOP_DATA`, `ACT` records without `mop`, and steps owned by `sata` and `llm` with `cov`, `navf` and `form` boosts
- **THEN** the count SHALL be 0
- **AND** gate 1 SHALL report `pass` for that run

#### Scenario: A MOP member in a control is counted
- **WHEN** the same trace carries one step with `dec.src:"mop"`, another with `dec.mopd:2`, and one `UICOV` line with `mopReach=3`
- **THEN** the count SHALL be 3
- **AND** gate 1 SHALL report `fail` naming the run

#### Scenario: An ACT MOP fact or a MOP counter in a v2 control is counted
- **WHEN** gate 1 runs `count_mop_group_signal` over an `aperv:as` trace (`v == 2`) whose two steps refer to an `ACT` record carrying `mop:0`, and whose `RUN_END` counters hold `coinMop:1`
- **THEN** the count SHALL be 3: two rows whose `activity_has_mop` is not `None`, and one `RUN_END`
- **AND** the value `0` of `ACT.mop` SHALL count, because on this jar its presence means MOP was mounted

#### Scenario: The v1 ACT fact and RUN_END counters are not a signal
- **WHEN** gate 1 runs `count_mop_group_signal` over a `v == 1` control trace whose `ACT` records carry `mop:1` and whose `RUN_END` counters hold `stampHits:5` and `retired:2`, with no MOP member on any step
- **THEN** the count SHALL be 0

#### Scenario: A v1 control counts only fired MOP boosts
- **WHEN** gate 1 runs `count_mop_group_signal` over a `v == 1` `mop_off_llm_off` trace whose 73 steps all carry `mopx`, one of them `wtg:200`, whose `UICOV` lines all carry `mopReach`, and whose steps carry no `mop` or `mopf` boost
- **THEN** the count SHALL be 0
- **AND** the same trace with one step carrying `mop:500` SHALL count 1

#### Scenario: The legacy pattern is blind on NDJSON, and the gate does not use it there
- **WHEN** an NDJSON trace whose steps carry `"mop":500` is scanned with `count_forbidden_signal`
- **THEN** the pattern count SHALL be 0, because the NDJSON member is `"mop":`, not `mop=`
- **AND** gate 1 SHALL select `count_mop_group_signal` for any trace whose first sink record is `{`-leading, so the blind count is never reported

#### Scenario: The variant is attribution evidence on the new jar
- **WHEN** gate 3 checks an `aperv:as_mop` run whose `RUN_START` has `v: 2`, `preset: "as_mop"` and `variant: "as_mop"`, against a manifest entry for cell `as_mop`
- **THEN** gate 3 SHALL report `pass` with an evidence form that names `variant`
- **AND** the same run with `variant: "as"` SHALL report `fail`, even though the preset matches

## ADDED Requirements

### Requirement: Analysis Consumers Follow the Trace Version (FR11, FR13)

The consumers of `StepRow` in `analysis/` SHALL treat the two jar generations as two vocabularies, not one. The
reader tells them apart through `run_start.v`.

- **`screen_visits.py`**:
  - `ActivityVisit.decision_source_counts` SHALL be reported beside the trace's `run_start.v` (INV-CAN-21). A
    caller that aggregates counts across runs SHALL refuse to pool versions.
  - `ActivityVisit.activity_has_mop` and `target_activity_has_mop` SHALL be `Optional[bool]` and carry `None`
    through (INV-CAN-22).
  - The visit SHALL NOT aggregate `StepRow.input_source`. The jar's `dec.inp` folds two facts into one value: why
    the field was filled (`llm`, `form`) and which generator wrote the text (`typed`, `heuristic`, `random`), with
    `llm` > `form` > the generator. A count per visit would hide the generator on exactly the form and LLM fills,
    and the LLM never writes the text (`ApeAgent.checkInput`). The per-step value stays on the row.
- **`step_bundle.py`** SHALL carry `activity_has_mop` as `Optional[bool]` into its frame column, written as
  null when absent (INV-CAN-22).
- **`runspec.attribution_evidence`** SHALL compare `RunStart.variant` with the manifest arm's cell when both are
  present. It SHALL report the check as `not-run` when the trace is `v == 1`, which carries no variant, rather than
  as a pass.
- **`baseline_ape.py` and `baseline_droidbot.py`** SHALL write `None` for every `StepRow` field the two baselines
  cannot carry, the fifteen fields added by the reader included (INV-CAN-19), and SHALL keep deriving their column
  list from `fields(StepRow)`.

The consumers whose inputs do not change are left as they are: `clock_logcat_join`, `violations`,
`monitored_ops`, `liveness`, `run_identity`, `tasks_record`, `loader`, the estimators and the caller glue. The
group-isolation change touches no logcat tag and no heartbeat. Its one `UICOV` change, `mopReach` written only
where MOP is mounted, is handled by `coverage_dump` and `state_coverage_join` under the `aperv` delta's
"Offline Coverage-Dump Parser at Activity Grain". The arm literals of
`callers/rq_map.toml` name the decisive corpus (cmp162/E3), whose runs are recorded data. A group-isolation
campaign declares its own entries where its analysis is defined, and this change adds none.

#### Scenario: Decision-source counts carry their version
- **WHEN** `screen_visits` segments a `v == 2` trace whose visit has steps owned by `sata` (5) and `mop` (2)
- **THEN** the visit's `decision_source_counts` SHALL be `{"sata": 5, "mop": 2}` reported with version `2`
- **AND** a cross-run aggregation given that visit and a `v == 1` visit SHALL raise rather than add the two counts

#### Scenario: A STATIC cell's visits report the MOP fact as absent
- **WHEN** `screen_visits` segments an `aperv:as` trace whose `ACT` records carry no `mop`
- **THEN** every visit's `activity_has_mop` SHALL be `None`
- **AND** the `step_bundle` frame's `activity_has_mop` column SHALL be null on every row, not `False`

#### Scenario: Variant attribution is not-run on an old trace
- **WHEN** `runspec.attribution_evidence` checks a cmp162 `aperv:mop_on_llm_off` trace (`v == 1`)
- **THEN** the variant check SHALL be `not-run`
- **AND** the digest, preset, features and params checks SHALL give the same verdicts as before this change

#### Scenario: Baseline frames keep the aperv column list
- **WHEN** `baseline_ape` parses a fixture run after the reader gains its fifteen fields
- **THEN** the frame's first block of columns SHALL equal `APERV_STEP_COLUMNS`, derived from `fields(StepRow)`
- **AND** `owner`, `scorer_cf`, `sata_path`, `rotation` and the other new columns SHALL be null on every row
