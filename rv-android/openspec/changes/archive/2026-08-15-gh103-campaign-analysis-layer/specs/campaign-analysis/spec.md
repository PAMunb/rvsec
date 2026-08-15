# campaign-analysis Specification (delta)

## Purpose

`campaign-analysis` is the offline, read-only, campaign-level analysis library of `aperv_tool`, under `modules/aperv-tool/src/aperv_tool/analysis/`, beside the three shipped readers `trace_ndjson.py`, `coverage_dump.py` and `clock_logcat_join.py`. It turns a results tree — one or many batch directories of `tasks.json`, the five consolidated CSVs, per-run `.trace` / `.logcat` pairs and per-APK static JSON — into typed frames, admissible runs, outcomes, estimates and tables whose denominators, estimands, conventions and exclusions travel with the number.

The library exists because five campaigns re-derived the same code, and the derivations disagreed. The run-identity regex is copied in two shipped readers; `stats_utils.py` and `multiarm_stats.py` are byte-duplicated across campaign directories; the campaign consolidator exists in five copies; identity-keyed task dedup was reimplemented twice; the exact McNemar the E3 pre-registration declares as its primary estimator exists nowhere. Meanwhile readings were misled by numbers that were correct in isolation: a mean gain of +14 pp beside a median of 0.000, `n_disc` reported without `b`, `c` or direction, `mop_unique` recomputed under two dedup keys that disagree on 35.6 % of runs, a `per_apk_paired.csv` whose `mop_unique` column is a mean over replicas read as a count. The library's organising rule is therefore not "compute the statistic" but "compute the statistic and refuse to emit it without what makes it interpretable".

Its second organising rule is **generic**: no research-question identifier appears in any module, function, column or flag. Catalogue entries are callers, never identifiers, and every knob the pre-registration leaves open — the improvement margin, the primary `aperv` variant, the corpus, the GLM specification and reference level, the replica-aggregation rule, the dedup convention, the multiplicity strategy, the app-size offset — is a required parameter with no default. Code that supplies a default for a freeze item makes the author's decision for them.

Its third rule is **validity before outcome**: the five validity gates carried from the E3 decisive run (clean control, correct binary, arm attribution, task integrity, corpse detection) run before any outcome is read, and a failed gate invalidates what it protects rather than being worked around. This is what makes a null publishable.

The library is layered so a change in the log format touches Layer 3 only: **Layer 0** run model and corpus scoping (`run_identity`, `runspec`, `loader`, `liveness`, `gates`, `corpus`, `clones`); **Layer 1** outcome builders (`outcomes`, `screen_visits`); **Layer 2** estimators (`estimators/`); **Layer 3** stream readers (`step_bundle`, `state_coverage_join`, `violations`, `monitored_ops`, `static_artifact`, `tasks_record`, `baseline_ape`, `baseline_droidbot`, plus the three shipped readers); **Layer 4** `envelope`, `emit`, `provenance`; and `callers/` with `rq_map.toml`, the only place a research-question identifier may appear. The design authority is the plan `doutorado-tese/docs/estudo-03/analise/20260815_plano_scripts_analise.md` and its companion `20260815_segmentacao_visitas_tela.md`; the measured facts quoted below (cmp162 counts, the E2 dedup disagreement, the activity-visit distributions) come from those documents and are cited by section.

The library is validated on two fixture classes. **FIXTURE-REAL** is `experimento-comp162` — 162 APKs × 3 arms (`ape`, `aperv:mop_off_llm_off`, `aperv:mop_on_llm_off`) × 3 replicas × 300 s = 1458 identities, 1455 completed — pinned by a path+sha256 manifest; it validates everything that touches real file formats, and its three campaign artefacts `consolidado/wilcoxon.csv`, `consolidado/per_apk_paired.csv` and `censo_substrato.csv` are **parity** tests: reproducing them proves the pipeline is unchanged, not that the estimator is right. **FIXTURE-SYNTH** is generated frames with closed-form or known answers, at arbitrary shapes and at the degenerate cases; it validates estimator **correctness**. cmp162 is a fixture, not a corpus: no number computed on it answers a research question.

## Data Contracts

### Input
- `results_roots: list[Path]` — one or many batch directories (`results/<batch>/<batch>/…`, the double nesting is a bind-mount artefact and is tolerated). Read-only.
- `tasks.json`, `summary.csv`, `errors.csv`, `coverage.csv`, `performance.csv`, `app_events.csv` — rv-platform's per-batch record and consolidated CSVs, keyed `(apk, rep, timeout, tool)`.
- `<apk>/<apk>__<rep>__<timeout>__<arm>.trace` / `.logcat` — per-run raw streams; the `.trace` is read only through `trace_ndjson.TraceReader` for `aperv` arms and through `baseline_ape` / `baseline_droidbot` for the baselines.
- `<apk>.json` — the full static-analysis JSON (`components`, `reachability`, `windows`, `transitions`). Never `*.mop.json`.
- `arm_table: Mapping[str, tuple[str, str]]` — arm string → `(tool, variant)`, supplied as data.
- `clone_map: Path | None`, `corpus_subset: Path | None` — declared corpus transforms, with the reason recorded.
- Estimator knobs: `dedup_key`, `replica_rule`, `estimand`, `margin`, `offset`, `family`, `correction`, `reference_level` — all explicit, none defaulted when it is a freeze item.

### Output
- Tidy `pandas` frames at the `(apk, rep, timeout, arm)` grain (Layer 0), at the visit grain (`screen_visits`), at the step grain (`step_bundle`) and at the event grain (`violations`, `monitored_ops`).
- `Envelope` (Layer 4): `estimand`, `n`, `denominator`, `estimate`, `ci`, `convention`, `exclusions`, `provenance_ref`. Every Layer-2 function returns one.
- `GateReport`: per gate × per arm, `pass | fail | not-run`, with the evidence form named.
- Tables/figures from `emit.py`, consuming envelopes only.
- `Provenance`: inputs, their sha256 or paths, the parameter set, timestamps — never inside an estimate.

### Side-Effects
- **[Filesystem]**: none on inputs (INV-APV-35). Outputs are written only where a caller names a destination.
- **[Device]**: none. No emulator, no `adb`, no Docker.

### Error
- `FreezeItemUnset` — a required pre-registration parameter was not supplied (margin, offset, reference level, primary variant, corpus).
- `IdentityCollisionUnresolved` — two `COMPLETED` records for one identity with equal coverage and different payload.
- `UnknownArm` — an arm string absent from the arm table; never decomposed heuristically.
- `SchemaVersionMismatch` — `RUN_START.v` differs from the version the reader was written for.

## Invariants

- **INV-CAN-01**: The run-identity regex `^(?P<apk>.+\.apk)__(?P<repetition>\d+)__(?P<timeout>\d+)__(?P<arm>.+)$` SHALL exist exactly once in `aperv_tool`, in `analysis/run_identity.py`; `coverage_dump.py` and `clock_logcat_join.py` SHALL import it.
- **INV-CAN-02**: Arm decomposition into `(tool, variant)` SHALL be driven by a data table supplied by the caller. An arm absent from the table SHALL raise `UnknownArm`; no module SHALL split an arm string heuristically.
- **INV-CAN-03**: Task records SHALL be keyed by identity `(apk, tool, variant, repetition, timeout)`, never by `task_id`. On collision the `COMPLETED` record with the larger coverage SHALL be kept and the collision counted.
- **INV-CAN-04**: No loader or reader SHALL silently drop a run, a record or a line. Every omission SHALL be counted and surfaced in the returned diagnostics.
- **INV-CAN-05**: `liveness.py` SHALL be the sole owner of the per-run admissibility verdict. `gates.py` SHALL call it and SHALL NOT reimplement any of its predicates.
- **INV-CAN-06**: The five validity gates SHALL run before any outcome is read. A gate result SHALL be one of `pass`, `fail`, `not-run`; `not-run` SHALL never be reported as `pass`, and the evidence form used SHALL be named per arm.
- **INV-CAN-07**: The clean-control field pattern SHALL be anchored — `(?<![a-z_])mop=` — so that `activity_has_mop=1` never matches.
- **INV-CAN-08**: Task integrity SHALL require, per identity, ≥1 `COMPLETED` record **and** an observed duration ≥ the declared timeout, read from `tasks.json` / `performance.csv`, never from a trace.
- **INV-CAN-09**: No fraction SHALL be returned without the denominator it was computed against, and no basis SHALL be used without its cardinality asserted and its set relations to neighbouring bases printed by member name.
- **INV-CAN-10**: Every outcome builder SHALL take its dedup key, replica rule and estimand as explicit parameters and SHALL name the estimand in its output.
- **INV-CAN-11**: A pre-registration freeze item (margin, primary variant, corpus, GLM specification, reference level, offset) SHALL have no default; an unset freeze item SHALL raise `FreezeItemUnset`.
- **INV-CAN-12**: `screen_visits.py` SHALL never merge non-adjacent runs of the same `activity`; the k-th revisit SHALL be the k-th visit record of that activity.
- **INV-CAN-13**: No cross-run join, aggregate or comparison SHALL use a `STATE.key` (`INV-APV-36`); the state trail is intra-run data.
- **INV-CAN-14**: Every Layer-2 estimator SHALL return an `Envelope`; none SHALL know which research question it answers.
- **INV-CAN-15**: A paired-binary result SHALL report `b`, `c`, `n_disc`, `p` and the direction together, with the exact-McNemar power floor at the caller's α beside it; a paired-continuous result SHALL report the trimmed mean beside the raw mean and the paired median beside both, and the count of pairs with Δ≠0.
- **INV-CAN-16**: Exact tests SHALL be used for small n; an approximation SHALL be reported beside the exact result, never instead of it.
- **INV-CAN-17**: `count_glm.fit` SHALL take `offset` as a required explicit argument, SHALL warm-start the NB2 fit from a Poisson fit with the same offset, and SHALL use cluster-robust standard errors grouped by `apk`.
- **INV-CAN-18**: `step_bundle.py` SHALL place `RVSEC`, `RVSEC-COV` and diagnostic lines on the step timeline by the same heartbeat rule `clock_logcat_join` uses for violations, and SHALL report the heartbeat⇄step count discrepancy as a number.
- **INV-CAN-19**: The baseline parsers SHALL extract only fields present in the stream; an absent clock SHALL be an explicit `null`, a synthesized ordinal SHALL be flagged as synthesized, and no `aperv` field SHALL be inferred for a baseline.
- **INV-CAN-20**: A cross-tool step count SHALL carry its unit (`droidbot` dispatched event, `ape` `SATA begin/end` cycle, `aperv` `StepRecord`) and SHALL be presented as a per-tool rate, never as one quantity.
- **INV-CAN-21**: FIXTURE-REAL SHALL be pinned by a path+sha256 manifest; a parity test SHALL be labelled parity, and correctness SHALL be established only on FIXTURE-SYNTH.
- **INV-CAN-22**: No research-question identifier (`E\d+`, `T\d+`, `R\d+`, `RQ`) SHALL appear in any module, function, class, column or flag under `analysis/` except `analysis/callers/` and `rq_map.toml`; enforced by a test over the package's source.
- **INV-CAN-23**: The whole `analysis/` package SHALL be offline, read-only over recorded artefacts, and unreachable from the import graph of `tools/aperv/tool.py` (`INV-APV-48` generalised to the package).
- **INV-CAN-24**: No metric or reader under `analysis/` SHALL read a `*.mop.json` artefact (`INV-ANA-53`); the full `<apk>.json` is the sole static input.

## ADDED Requirements

### Requirement: Run Identity as a Single Seat and Arm Table (FR20, NFR03)

`analysis/run_identity.py` SHALL define the run-identity regex once, a frozen `RunKey(apk, repetition, timeout, arm)` value type, and `decompose_arm(arm, table) -> (tool, variant)` driven by a caller-supplied table (INV-CAN-01, INV-CAN-02). The two shipped readers SHALL import it. cmp162's arm strings contain a colon (`aperv:mop_on_llm_off`) and its paired columns are `{arm}__{metric}`, so a naive `split('_')` fails visibly on the fixture.

#### Scenario: Both shipped readers import the single seat
- **WHEN** the tests grep `aperv_tool/analysis/` for the literal `__(?P<repetition>`
- **THEN** it SHALL occur exactly once, in `run_identity.py`
- **AND** `coverage_dump.py` and `clock_logcat_join.py` SHALL resolve identities through it

#### Scenario: Unknown arm is an error, not a guess
- **WHEN** `decompose_arm("droidbot:bfs_greedy", table)` is called with a table lacking that arm
- **THEN** it SHALL raise `UnknownArm` naming the string
- **AND** it SHALL NOT return `("droidbot", "bfs_greedy")` by splitting on the colon

---

### Requirement: Loader and Identity-Keyed Task Records (FR14, NFR06)

`analysis/loader.py` SHALL read one or many batch directories into a tidy frame at `(apk, rep, timeout, arm)`, tolerating missing files, and `analysis/tasks_record.py` SHALL read `tasks.json` as the authoritative run record — the only place failures are visible, since `performance.csv` on cmp162 holds only `TaskState.COMPLETED` (1455/1455). Records SHALL be deduplicated by identity, never by `task_id` (INV-CAN-03): a resume appends a new record with a fresh UUID rather than overwriting. `experiment.current_status == "running"` in every cmp162 `tasks.json` SHALL NOT be used as a gate, and `state_transitions[]` inside a record SHALL NOT be counted as records. Every omission SHALL be counted (INV-CAN-04).

#### Scenario: cmp162 loads with its failures visible
- **WHEN** the loader runs over the eight cmp162 batches
- **THEN** it SHALL report 1458 identities, 1455 completed, 3 dead identities (`com.ds.avare_404.apk` × `aperv:mop_on_llm_off`, reps 1–3, retried three times each) and, of the 31 ERROR records, 22 recovered across 21 identities against 9 on the dead ones
- **AND** a loader that read `summary.csv` alone would see 1455 successes and no failure — the test SHALL assert the failures come from `tasks.json`

#### Scenario: Identity collision keeps the larger-coverage COMPLETED record
- **WHEN** an identity carries an ERROR record and a later COMPLETED record with a fresh UUID
- **THEN** the COMPLETED record SHALL be kept, the collision counted, and the identity counted once
- **AND** no per-container CSV field that a resume may have zeroed SHALL be read for that identity

---

### Requirement: Admissibility Has One Owner (NFR03)

`analysis/liveness.py` SHALL be the promotion of `experimento-comp162/scripts/admissibility.py:48-105` (byte-identical in `experimento-comp162-ajc` by design) into the package, and both campaign copies SHALL become imports of it. It SHALL own the per-run admissibility verdict — completion, full-budget execution, corpse signals — and `gates.py` SHALL delegate to it (INV-CAN-05), so an excluded run is counted exactly once.

#### Scenario: Gates delegate rather than reimplement
- **WHEN** the tests inspect `gates.py`
- **THEN** it SHALL import `liveness` and SHALL contain no predicate over trace size, coverage-all-zero or fatal exception of its own
- **AND** the two campaign `admissibility.py` files SHALL consist of an import and re-export only

---

### Requirement: Validity Gates Run Before Any Outcome (FR13, NFR06)

`analysis/gates.py` SHALL implement the five gates: **1 clean control** (`∀ run ∈ arm_predicate: forbidden_signal(run) == 0`, anchored pattern INV-CAN-07); **2 correct binary** (digest of the artefact under test, captured per run into a sidecar beside it or read from `RUN_START.build.sha`, compared to the manifest — `capture_status` never back-filled from config); **3 arm attribution** (evidenced from the artefact, never from the orchestrator's filename label); **4 task integrity** (identity-not-line, ≥1 COMPLETED, full budget — INV-CAN-08); **5 corpse detection** (three independent signals: trace below a size floor · coverage all zero · a named fatal exception, via `liveness`). Gates 2 and 3 SHALL name their evidence form per arm (INV-CAN-06): `aperv:*` — `RUN_START.build.sha` / `preset` / `features` / `params` against the manifest; `droidbot:*` — the `start sending events, policy is …` line against the policy in the filename, digest `not-run` unless a sidecar exists; `ape` — negative evidence, the trace carries zero `{`-leading NDJSON lines (proof the upstream `ape.jar`, not `ape-rv.jar`, ran), digest `not-run` unless a sidecar exists. `not-run` SHALL be reported as such and never as a pass. A richer corpse classification by last non-empty trace line (normal-end / crash / cut-during-teardown / cut-elsewhere) SHALL be emitted beside the boolean.

#### Scenario: Anchored clean-control pattern
- **WHEN** gate 1 scans a control-arm run whose trace contains `activity_has_mop=1` and no `mop=` field
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

---

### Requirement: Corpus Scoping, Basis Discipline and Clone Collapse (FR14, NFR08)

`analysis/corpus.py` SHALL apply a declared subset by application id with the reason recorded and SHALL emit both denominators — reachable and analysed (INV-CAN-09). It SHALL name each basis, assert its cardinality and print the set relations to every neighbouring basis by member name. `analysis/clones.py` SHALL collapse clone families from a clone-map file; nothing exists to reuse — E2 has no clone rule, and its `would_collapse` is a different concept.

#### Scenario: Both denominators travel with every fraction
- **WHEN** a caller requests a detection rate over a 40-APK subset of a 162-APK fixture
- **THEN** the result SHALL carry `reachable=162`, `analysed=40` and the subset's recorded reason
- **AND** a fraction without both SHALL be impossible to construct from the API

#### Scenario: Basis relations by member name
- **WHEN** two bases of 163 and 162 applications are declared
- **THEN** the report SHALL print `|163∖162| = 1` and name the application

---

### Requirement: Outcome Builders Take Their Conventions as Parameters (FR13, FR14)

`analysis/outcomes.py` SHALL provide `distinct_count(stream, dedup_key)`, `binarize(count, threshold, replica_rule)` with `replica_rule ∈ {majority, union, unanimity}`, `aggregate_replicas(values, estimand)` with the estimand named in the output, `time_to_first_event(stream, clock_origin)` with an explicit censoring flag, `capture_curve(stream, budget_grid, scope)`, and `restrict_window(stream, reference_instant, window)` (INV-CAN-10). `mop_errors_unique` SHALL be computed per run over the key `(class, method, spec)` — E2's definition, which disagreed with the message-level one on 5,749 of 16,137 runs (35.6 %) — and both keys SHALL be available, labelled, never substituted. Freeze items SHALL raise `FreezeItemUnset` when absent (INV-CAN-11).

#### Scenario: Replica rule is a parameter with three answers
- **WHEN** `binarize` runs over a cell with replica counts `[0, 1, 1]` and threshold 1
- **THEN** `majority` SHALL yield true, `union` true, `unanimity` false
- **AND** the mixed-replica census SHALL count this cell

#### Scenario: Estimand named in the output
- **WHEN** `aggregate_replicas` runs with `estimand="trimmed_mean_10"`
- **THEN** the returned frame's column SHALL be labelled with that estimand
- **AND** a caller mixing it with a `mean` column in one ratio SHALL be detectable from labels alone

#### Scenario: Parity with the campaign's per-APK aggregate
- **WHEN** the builders run over cmp162 with the campaign's conventions (mean over replicas)
- **THEN** they SHALL reproduce `consolidado/per_apk_paired.csv` (162 rows) exactly
- **AND** the test SHALL be labelled a parity test (INV-CAN-21)

---

### Requirement: Activity-Visit Segmentation (FR11, FR13)

`analysis/screen_visits.py` SHALL segment a run's `StepRow` stream into **activity-visits**: maximal runs of consecutive rows with equal `activity`, closed by the first of the row's `outcome.activity_changed`, the next row's `activity` differing, `outcome is None` (restart, component launch, non-model action), `outcome.resolved is False` (teardown), or end of trace. Non-adjacent runs SHALL never merge (INV-CAN-12): `A → B → A` yields `A#1`, `B#1`, `A#2` with `revisit_index`. Each `ActivityVisit` (frozen dataclass) SHALL carry `visit_ordinal`, `activity`, `activity_has_mop`, `revisit_index`, `visits_of_activity`, `first_step`, `last_step`, `n_steps`, `t_start_ms`, `t_end_ms`, `duration_ms`, `steps[]`, `state_trail[]` (ordered `(state_key, enter_step, exit_step, n_steps)`), `distinct_states`, `state_visits`, `action_type_counts`, `decision_source_counts`, `n_edittext_clicks`, `n_form_boosted_steps`, `n_llm_calls`, `closing_action`, `closing_type`, `exit_kind ∈ {activity_transition, no_outcome, teardown, run_end, next_activity_differs}`, `target_activity`, `target_activity_has_mop`, and — when built from `step_bundle` — `violations[]`, `monitored_ops[]`, `diagnostics[]` inside `[t_start, t_end)`, plus `uicov` aggregated over the trail's keys and flagged cumulative. `form_episodes(visit)` SHALL derive, inside one visit, maximal runs of `MODEL_CLICK` on `EditText` / `AutoCompleteTextView` / `SearchView` (state key free to change) closed by the first non-EditText `MODEL_CLICK` or the visit's end, carrying `n_fills`, `distinct_edit_targets`, `submit_action`, `submit_exit_kind`. The state grain is descriptive only (INV-CAN-13): measured on cmp162 it is step-level — median state-visit length 1, 75 % single-step, 85 % of closings same-activity state transitions — because a combobox, a dialog, a menu or the soft keyboard is another state in the same Activity. Fragment-based navigation inside one Activity is one visit (recorded limitation).

#### Scenario: Revisits are separate records
- **WHEN** a trace's rows visit `MainActivity` (steps 1–4), `SettingsActivity` (5–6), `MainActivity` (7–9)
- **THEN** the segmenter SHALL emit three visits with `revisit_index` 1, 1, 2 and `visits_of_activity` 2, 1, 2
- **AND** the two `MainActivity` visits SHALL NOT be merged

#### Scenario: Combobox stays inside the visit as a state trail
- **WHEN** rows 3–5 of one Activity carry state keys `S1, S2, S1` (a dropdown opened and closed)
- **THEN** the visit SHALL be one record with `state_trail` of length 3 and `distinct_states` 2
- **AND** no visit boundary SHALL be created at rows 3 or 5

#### Scenario: Form episode derived across state changes
- **WHEN** a visit's rows are three `MODEL_CLICK` on `EditText` (each changing the state key) followed by a `MODEL_CLICK` on a `Button` whose `outcome.activity_changed` is true
- **THEN** `form_episodes` SHALL return one episode with `n_fills=3` and `submit_exit_kind=activity_transition`
- **AND** the visit itself SHALL close on that click

#### Scenario: Measured cmp162 figures reproduce
- **WHEN** the segmenter runs over the first 60 `aperv:mop_on_llm_off` traces of cmp162
- **THEN** it SHALL report a median of 14.5 activity-visits per run, median length 2, mean 11.0, max 294
- **AND** the state-grain descriptive counts SHALL report median 156.5 state-visits per run and 75.5 % single-step

---

### Requirement: Estimators Return Envelopes and Follow the Reporting Rules (FR14, NFR06)

`analysis/estimators/` SHALL provide `paired_binary` (exact McNemar — binomial over discordant pairs, optional stratification, the power floor at the caller's α), `paired_continuous` (Wilcoxon signed-rank exact for small n with the continuity- and tie-corrected normal approximation beside it; trimmed-mean difference by paired bootstrap with the paired median beside it), `count_glm`, `multiplicity` (Holm and FDR, family declared by the caller), `decision` (margin supplied by the caller, no default), `resampling` (`paired_bootstrap_ci(a, b, B, seed, trim)` extracted from `experimento-cal/scripts/stats_utils.py:38` — the estimand is the difference of 10 % trimmed means recomputed per resample, paired by APK), `variance` (ICC that reports why it degenerates), `capacity` (outcome-specific), `multiarm` (Friedman + Holm + rank-biserial extracted from `multiarm_stats.py`). Every function SHALL return an `Envelope` (INV-CAN-14) and follow INV-CAN-15/16.

#### Scenario: Never n_disc alone
- **WHEN** `paired_binary.mcnemar_exact` runs on 40 pairs with `b=3`, `c=1`
- **THEN** the envelope SHALL carry `b=3`, `c=1`, `n_disc=4`, the direction, the exact two-sided `p`
- **AND** the power floor at α=0.025 (the smallest `n_disc` at which rejection is arithmetically possible, 7) SHALL be printed beside it, and the result SHALL say non-rejection below the floor is construction, not evidence

#### Scenario: Zero discordant pairs is a valid, degenerate result
- **WHEN** `mcnemar_exact` runs on pairs with `b=c=0`
- **THEN** it SHALL return `p=1.0`, `n_disc=0`, and the floor, without raising
- **AND** the envelope SHALL flag the result as below the power floor

#### Scenario: Exact beside approximate, never instead
- **WHEN** `paired_continuous.wilcoxon` runs on 12 non-zero differences with ties
- **THEN** it SHALL report the exact tail and the tie-corrected normal approximation side by side
- **AND** all-zero differences SHALL return a labelled degenerate envelope, not an exception

#### Scenario: Trimmed beside raw beside median
- **WHEN** `paired_continuous.trimmed_mean_difference` runs on paired data whose mean gain is +14 pp and whose median is 0.000
- **THEN** all three SHALL appear in the envelope with the count of pairs with Δ≠0
- **AND** the estimand of the bootstrap SHALL be labelled `diff_of_trimmed_means_10`

#### Scenario: Multiplicity family is declared, never inferred
- **WHEN** `multiplicity.adjust(p_values, family="secondary-variants", method="holm")` is called
- **THEN** the envelope SHALL carry the family name and `m`
- **AND** calling without `family` SHALL raise

#### Scenario: Margin has no default
- **WHEN** `decision.decide(estimate, ci)` is called without `margin`
- **THEN** it SHALL raise `FreezeItemUnset("margin")`

#### Scenario: Parity with the campaign's Wilcoxon table
- **WHEN** the estimators run over cmp162 in the campaign's mode (scipy-default approximate branch)
- **THEN** they SHALL reproduce `consolidado/wilcoxon.csv` (15 rows: 3 pairs × 5 metrics) exactly
- **AND** the test SHALL be labelled a parity test (INV-CAN-21)

---

### Requirement: Negative-Binomial Count GLM Carries E2's Fitter (FR14, NFR08)

`analysis/estimators/count_glm.py` SHALL carry E2's `_glm_fit_nb` (`ase-journal/data-analysis/rvsec/rq1_jca.py:216-228`) — `sm.NegativeBinomial` NB2 with `alpha` by ML, cluster-robust SEs by `apk`, IRR = `exp(beta)` with exponentiated Wald CI, **Poisson warm start with the same offset** (statsmodels' default start ignores the offset, which makes the pure-offset model diverge, `alpha → ∞`) — with `offset` a required explicit argument (INV-CAN-17), the reference level a required parameter, and covariates configurable. It SHALL also carry the NB-zero predictor, the boundary-corrected LR test (`0.5*chi2.sf(lr,1)`) and the automatic direction-flip / significance-loss detector. `statsmodels` SHALL be declared in `modules/aperv-tool/pyproject.toml`.

#### Scenario: Offset is required
- **WHEN** `count_glm.fit(formula, data)` is called without `offset`
- **THEN** it SHALL raise `FreezeItemUnset("offset")` — `offset=None` (no offset) is a legal explicit value, omission is not

#### Scenario: Synthetic IRRs are recovered under both specifications
- **WHEN** FIXTURE-SYNTH generates counts at known per-arm IRRs with a log-normal size covariate
- **THEN** the covariate specification's CIs SHALL cover the true IRRs
- **AND** the pure-offset specification SHALL converge and reproduce E2's qualitative signature — `alpha` inflating and every CI widening — which the test SHALL assert

#### Scenario: Reference level is a parameter
- **WHEN** `fit` is called with `reference_level="ape"` on a five-arm frame
- **THEN** the IRR table SHALL carry four contrasts against `ape`
- **AND** no `Treatment('monkey')` literal SHALL exist in the module

---

### Requirement: Step Bundle Places Every Logcat Stream on the Step Timeline (FR11, FR13)

`analysis/step_bundle.py` SHALL return one `StepBundle` per step: the `StepRow` plus `violations[]` (`RVSEC`), `monitored_ops[]` (`RVSEC-COV`) and `diagnostics[]` (the `RV_LOGCAT_DIAGNOSTICS` tags, via `rv_coverage`'s diagnostic parser) placed by the same heartbeat rule `clock_logcat_join` uses (INV-CAN-18), plus the per-state `UICOV` payload joined by `state_key` through `state_coverage_join.py` (intra-run only). It SHALL report the heartbeat⇄step discrepancy as a count — on cmp162, 15,701 heartbeats for 15,702 steps over 60 runs — and SHALL treat a run with no heartbeat as `UNALIGNED`, never repaired. It is intra-`aperv` by construction: `ape` and `droidbot` emit no NDJSON.

#### Scenario: RVSEC-COV lines reach the bundle
- **WHEN** a run's logcat carries heartbeats and `RVSEC-COV` lines between heartbeat 7 and heartbeat 8
- **THEN** those lines SHALL appear in step 7's `monitored_ops[]` with their signatures intact
- **AND** `clock_logcat_join`'s `RunJoin` output for the same run SHALL be unchanged

#### Scenario: Heartbeat gap is a number
- **WHEN** a run has 262 steps and 261 heartbeats
- **THEN** the bundle report SHALL state `heartbeat_gap=1` and name the step without one
- **AND** that step's events SHALL be attributed to the previous heartbeat with a flag, not dropped

#### Scenario: UICOV joins totally by state key within a run
- **WHEN** the run's teardown dump carries `UICOV state=<key>` lines
- **THEN** every `STATE.key` in the trace SHALL find at most one row and every UICOV row SHALL find its key (measured 3801/3801 on 120 cmp162 runs)
- **AND** the joined `discovered/interacted/byType` SHALL be flagged cumulative-per-run, never per-visit

---

### Requirement: Static Artifact Reader Emits the Size Covariate (FR14, NFR08)

`analysis/static_artifact.py` SHALL read the full `<apk>.json` (`components`, `reachability`, `windows`, `transitions`), emit the size covariate `sa_methods_reaches_mop` as the count of `reachability[].methods[].reachesTarget`, the stratum labels and the three-way handler verdict `hot / cold / unresolved` with `unresolved` first-class, and SHALL never read `*.mop.json` (INV-CAN-24). `<apk>.json`'s `complete: true` SHALL NOT be read as a quality signal.

#### Scenario: Covariate for every fixture APK
- **WHEN** the reader runs over cmp162's 162 `<apk>.json`
- **THEN** it SHALL emit `sa_methods_reaches_mop` for all 162 with no device
- **AND** it SHALL reproduce `censo_substrato.csv` (parity)

#### Scenario: mop.json is never opened
- **WHEN** the tests wrap `open` over a run of the reader
- **THEN** no path ending in `.mop.json` SHALL be opened

---

### Requirement: Baseline Parsers Extract Only What Is Certain (FR11, FR20)

`analysis/baseline_ape.py` SHALL split on the `SATA begin step [N][Elapsed: …]` … `SATA end step [N]` envelope (tolerating an unterminated final block), extracting per block the fully-qualified activity and run-local state key from `New   state:` — **not** `Curr  state:`, which the original wording named: APE's block epilogue prints `Last`/`Curr`/`New` as a three-deep history, so `New` is *this* step's state while `Curr` is the previous one, and on the pinned fixture `Curr  state:` is `null` on 8 of 50 blocks in the densest run and on 8 of 9 in another, which would report activity coverage of 84 % and 11 % against the ~99.8 % the survey measured, where `New   state:` is non-null on 106 of 106 blocks — the action descriptor and strategy from `Select action … by strategy …`, the Source/Action/Target transition and `GSTG(…)` statistics, and hoisting `// NOT RESPONDING` / `// CRASH` blocks as run-level events. `analysis/baseline_droidbot.py` SHALL skip to `start sending events, policy is …`, emit one record per `Action: <Type>(...)` with a synthesized ordinal flagged as such, the most recent policy line as provenance, the state from `Current state:` or the action's `state=`, and `clock: null` explicitly (INV-CAN-19). Both SHALL emit into the same tidy frames the `aperv` readers produce, carry `truncated`, report unparsed lines with counts, treat "no steps" as a first-class outcome, and join to `tasks.json` for the run window. Every cross-tool step count SHALL carry its unit (INV-CAN-20). Not attempted: per-event timing for droidbot, sub-second step latency for ape, cross-run state correspondence for ape, screen geometry for droidbot, APE's GUI-tree abstraction, droidbot's unexplored frontier, RVSEC-to-droidbot-action attribution.

#### Scenario: Droidbot clock is an explicit null
- **WHEN** `baseline_droidbot` parses a run with 89 `Action:` lines
- **THEN** it SHALL emit 89 records with `step_index` 1..89 flagged `synthesized=True` and `clock=None` on every record
- **AND** no timestamp SHALL be inferred from the surrounding logcat

#### Scenario: No steps is an outcome
- **WHEN** an `ape` trace carries no `SATA begin step` marker
- **THEN** the parser SHALL return a run record with `steps=0`, `truncated` as observed, and no exception
- **AND** the run SHALL keep its place in the denominator

#### Scenario: Activity left as observed for droidbot
- **WHEN** a droidbot event carries a simple activity name and the next carries none (`KeyEvent`)
- **THEN** the first record SHALL carry the simple name unresolved and the second `activity=None`, counted in `activity_unknown_steps`

---

### Requirement: Envelopes, Emitters and Provenance (FR14, NFR06, NFR08)

`analysis/envelope.py` SHALL define `Envelope(estimand, n, denominator, estimate, ci, convention, exclusions, provenance_ref)`; `analysis/emit.py` SHALL produce tables and figures from envelopes only; `analysis/provenance.py` SHALL record inputs, their sha256 or paths, and the parameter set, with timestamps there and never inside an estimate.

#### Scenario: A number cannot leave without its envelope
- **WHEN** `emit.table` is called with a bare float
- **THEN** it SHALL raise, naming `Envelope` as the required type

#### Scenario: Provenance re-derives the number
- **WHEN** a caller re-runs with the recorded parameter set over inputs whose sha256 match
- **THEN** the estimate SHALL be identical bit for bit
- **AND** a changed input hash SHALL be reported before any estimate

---

### Requirement: Fixtures, Genericity and Boundaries (NFR03, NFR08)

FIXTURE-REAL SHALL be pinned by `modules/aperv-tool/tests/fixtures/cmp162_manifest.json` (path + sha256 per file read) and a hashed baseline sample `baseline_sample_manifest.json` from the E2 raw corpus; FIXTURE-SYNTH SHALL cover every estimator including all-zero paired differences, a saturated binary outcome where ICC degenerates, zero discordant pairs, and GLM separation (INV-CAN-21). `analysis/callers/` + `rq_map.toml` SHALL be the only place a research-question identifier appears (INV-CAN-22); the package SHALL be offline, read-only and off the collection path (INV-CAN-23); an end-to-end smoke over two cmp162 applications SHALL run with no device, and a deliberately corrupted fixture (dead run, missing CSV, malformed record) SHALL yield reported exclusions.

#### Scenario: No RQ identifier in the library
- **WHEN** the tests scan every `.py` under `analysis/` except `callers/`
- **THEN** no identifier, column literal or flag SHALL match `\b[ETR]\d+\b` or `\bRQ\d*\b`
- **AND** the pattern SHALL admit `RVSEC`, an `INV-…` anchor and an ordinary word — a guard that fires on those is turned off within a week and then guards nothing

#### Scenario: Whole package off the collection path
- **WHEN** the tests walk the import graph of `tools/aperv/tool.py`
- **THEN** no module under `aperv_tool.analysis` SHALL be reachable

#### Scenario: Corrupted fixture reports, never degrades
- **WHEN** the smoke runs over a copy of two cmp162 applications with one trace truncated to 864 bytes, one `summary.csv` removed and one malformed `tasks.json` record
- **THEN** every envelope produced SHALL list the three exclusions by identity and reason
- **AND** no fraction's denominator SHALL silently shrink

#### Scenario: Entries with no caller are visible
- **WHEN** `rq_map.toml` lists an entry with no caller
- **THEN** the coverage report SHALL list it as uncovered
