# Design — gh103 campaign analysis layer

## Context

The E3 final campaign (`ape` + one `droidbot` variant vs three `aperv` variants; 1800 s; one replica per (APK, arm)) will produce a results tree of the same shape as `experimento-comp162` — `tasks.json`, five consolidated CSVs, per-run `.trace`/`.logcat`, per-APK `<apk>.json`. Nothing in the repository turns that tree into estimates without a per-campaign script directory, and each such directory so far has re-derived the same code with different conventions. This design places one library under `modules/aperv-tool/src/aperv_tool/analysis/` (plan D1), beside the three shipped readers, and organises it in the plan's five layers so that the log format touches Layer 3 only.

The plan and its companion note (`doutorado-tese/docs/estudo-03/analise/20260815_plano_scripts_analise.md`, `20260815_segmentacao_visitas_tela.md`) are the design authority; this document maps their decisions to files, signatures and tests. Where a number below is "measured", it was measured on cmp162 on 2026-08-15 with the throwaway scripts kept beside the note (`scripts/20260815_measure_*.py`), never on a device.

Constraints that bind every file: read-only over recorded artefacts and no device (INV-APV-35); off the collection path (INV-APV-48, generalised as INV-CAN-23); `*.mop.json` never read (INV-ANA-53 / INV-CAN-24); the frozen legacy readers untouched (INV-APV-55); no literal jar digest in `modules/` (INV-APV-59 — gate 2 compares against a manifest supplied as data); no research-question identifier in the library (INV-CAN-22); no default for a pre-registration freeze item (INV-CAN-11). PRD: FR11–FR14, FR20, NFR03, NFR06, NFR08.

## Architecture

```
results tree (read-only)                         aperv_tool.analysis
─────────────────────────                        ───────────────────────────────────────────────
tasks.json ───────────────► tasks_record ──┐     Layer 0  run_identity · runspec · loader · liveness
summary/errors/coverage/    ───────────────┼──►           gates · corpus · clones
performance/app_events.csv                 │              │ tidy frame @ (apk, rep, timeout, arm), GateReport
<apk>__<rep>__<to>__<arm>.trace ─► trace_ndjson (RunStart×13, v) ──┐
                                   baseline_ape / baseline_droidbot ┤ Layer 3  step_bundle · state_coverage_join
<...>.logcat ─────────────► clock_logcat_join.read_tagged_lines ───┤          violations · monitored_ops
                            (RVSEC | RVSEC-COV | diagnostics)      │          static_artifact
[APE-RV] UICOV ───────────► coverage_dump ─────────────────────────┘
<apk>.json ───────────────► static_artifact  (size covariate, strata; never *.mop.json)
                                                          │
                                   Layer 1  outcomes (dedup/replica/estimand/censor/curve/window)
                                            screen_visits (activity-visits, state_trail, form_episodes)
                                                          │
                                   Layer 2  estimators/ paired_binary · paired_continuous · count_glm
                                            multiplicity · decision · resampling · variance · capacity · multiarm
                                                          │  Envelope
                                   Layer 4  envelope · emit · provenance
                                                          │
                                   callers/ + rq_map.toml  ← the only place an entry id appears
```

### Key Components

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| `run_identity.RunKey`, `parse_run_filename`, `decompose_arm` | single seat of the identity regex; arm → (tool, variant) by table | filename, arm table | `RunKey`, `(tool, variant)` / `UnknownArm` |
| `trace_ndjson.RunStart` (modified) | full `RUN_START` record; `v` gate | `.trace` | `RunStart` ×13, `TraceDiagnostics.schema_version_mismatch` |
| `runspec.attribution_evidence(run_start, manifest_arm)` | gate-3 evidence for `aperv` arms; params resolution against `build.sha` | `RunStart`, manifest | `AttributionEvidence(form, verdict)` |
| `tasks_record.load(tasks_json)` | identity-keyed dedup, collision policy, retry census | `tasks.json` | frame + `TaskDiagnostics` |
| `loader.load(roots, arm_table)` | one tidy frame at the grain, omissions counted | batch dirs | frame + `LoadDiagnostics` |
| `liveness.verdict(run)` | sole owner of admissibility (C1/C2/C5, full budget, corpse signals) | run record + artefact facts | `Admissibility(admissible, reasons)` |
| `gates.run_all(frame, arm_manifest)` | five gates, per-arm evidence form, `not-run` | frame, manifest | `GateReport` |
| `corpus.scope`, `clones.collapse` | declared subset, both denominators, basis relations, clone map | frame, subset/clone files | frame + `Basis` |
| `outcomes.*` | metric-agnostic builders, conventions as parameters | streams/frames | labelled frames |
| `screen_visits.segment(rows)`, `form_episodes(visit)` | activity-visit segmentation, state trail, revisits, form episodes | `Iterable[StepRow]` (or `StepBundle`) | `list[ActivityVisit]`, `list[FormEpisode]` |
| `clock_logcat_join.place_on_timeline`, `read_tagged_lines` (extracted) | tag-agnostic placement | logcat, tag | `(Phase, step, anchor)`, `[(stamp, payload)]` |
| `step_bundle.bundle_run(trace, logcat)` | one record per step with all placed streams; heartbeat gap counted | trace + logcat | `list[StepBundle]`, `BundleDiagnostics` |
| `state_coverage_join.join(reader, dump)` | per-state UICOV onto steps by `STATE.key`, intra-run | trace + dump | frame (per run) |
| `violations`, `monitored_ops` | event streams at declared grain | `errors.csv` / logcat | frames |
| `static_artifact.read(apk_json)` | size covariate, strata, `hot/cold/unresolved` | `<apk>.json` | `StaticFacts` |
| `baseline_ape.parse`, `baseline_droidbot.parse` | extract-only-what-is-certain parsers into the shared frames | `.trace`/`.logcat` | frames + `truncated`, unparsed counts |
| `estimators.*` | one estimator per module; every function returns `Envelope` | outcome column, contrast, knobs | `Envelope` |
| `envelope.Envelope`, `provenance.Provenance`, `emit.*` | result data structure, re-derivability, tables/figures | envelopes | files where the caller names them |
| `callers/*.py`, `rq_map.toml` | entry id → (builder, estimator, parameters); coverage report | toml | tables |

## Mapping: Spec → Implementation → Test

| Requirement / Invariant | Implementation | Test |
|---|---|---|
| Run identity single seat (INV-CAN-01/02) | `analysis/run_identity.py`; imports in `coverage_dump.py:66-69`, `clock_logcat_join.py:94-96,222` | `test_run_identity.py::test_regex_declared_once`, `::test_unknown_arm_raises`, `::test_cmp162_arm_strings_with_colon` |
| RunStart ×13, `v` gate (INV-APV-61/62) | `analysis/trace_ndjson.py` `RunStart`, `TraceReader(strict=)`, `TraceDiagnostics.schema_version_mismatch` | `test_trace_ndjson.py::test_run_start_thirteen_members`, `::test_v_mismatch_strict_raises`, `::test_v_mismatch_counted`, `::test_first_brace_line_is_header` |
| Tag-agnostic placement (INV-APV-63) | `clock_logcat_join.place_on_timeline`, `read_tagged_lines` | existing `test_clock_logcat_join.py` unchanged; `test_step_bundle.py::test_rvsec_cov_placed_same_rule` |
| Identity-keyed tasks (INV-CAN-03/04) | `analysis/tasks_record.py` | `test_tasks_record.py::test_identity_not_task_id`, `::test_cmp162_3_dead_22_recovered` |
| Admissibility owner (INV-CAN-05) | `analysis/liveness.py`; `experimento-comp162{,-ajc}/scripts/admissibility.py` → re-export | `test_liveness.py::test_campaign_copies_are_imports`, `test_gates.py::test_gates_delegate_to_liveness` |
| Five gates, per-arm evidence, `not-run` (INV-CAN-06/07/08) | `analysis/gates.py` | `test_gates.py::test_anchored_mop_pattern`, `::test_ape_negative_evidence`, `::test_droidbot_policy_line`, `::test_not_run_never_pass`, `::test_full_budget_required`, `::test_decisive_corpse` |
| Denominators & basis (INV-CAN-09) | `analysis/corpus.py`, `clones.py` | `test_corpus.py::test_both_denominators`, `::test_basis_relations_by_name`, `test_clones.py` |
| Outcome conventions (INV-CAN-10/11) | `analysis/outcomes.py` | `test_outcomes.py::test_three_replica_rules`, `::test_estimand_labelled`, `::test_freeze_item_unset`, `::test_parity_per_apk_paired` |
| Activity-visits (INV-CAN-12/13) | `analysis/screen_visits.py` | `test_screen_visits.py::test_revisits_separate`, `::test_combobox_in_trail`, `::test_form_episode_across_states`, `::test_cmp162_measured_figures` |
| Envelopes & reporting rules (INV-CAN-14/15/16) | `analysis/estimators/*.py`, `envelope.py` | `test_estimators_*.py` per module; `::test_never_n_disc_alone`, `::test_zero_discordant`, `::test_exact_beside_approx`, `::test_trimmed_raw_median`, `::test_family_required`, `::test_margin_required`, `::test_parity_wilcoxon` |
| NB GLM (INV-CAN-17) | `analysis/estimators/count_glm.py` | `test_count_glm.py::test_offset_required`, `::test_synth_irr_recovered`, `::test_offset_alpha_inflates`, `::test_reference_level_param`, `::test_no_monkey_literal` |
| Step bundle (INV-CAN-18) | `analysis/step_bundle.py`, `state_coverage_join.py` | `test_step_bundle.py::test_heartbeat_gap_counted`, `::test_uicov_total_join`, `::test_unaligned_not_repaired` |
| Static artefact (INV-CAN-24) | `analysis/static_artifact.py` | `test_static_artifact.py::test_covariate_162`, `::test_parity_censo`, `::test_mop_json_never_opened` |
| Baseline parsers (INV-CAN-19/20) | `analysis/baseline_ape.py`, `baseline_droidbot.py` | `test_baseline_ape.py::test_no_steps_outcome`, `::test_unterminated_block`; `test_baseline_droidbot.py::test_clock_null`, `::test_synth_ordinal_flag`, `::test_activity_unknown_counted` |
| Fixtures, genericity, boundaries (INV-CAN-21/22/23) | `tests/fixtures/cmp162_manifest.json`, `baseline_sample_manifest.json`, `tests/synth/` | `test_fixture_manifest.py`, `test_no_rq_identifier.py`, `test_analysis_off_collection_path.py`, `test_smoke_two_apps.py`, `test_corrupted_fixture.py` |
| Envelope/provenance | `analysis/envelope.py`, `provenance.py`, `emit.py` | `test_envelope.py::test_bare_float_rejected`, `test_provenance.py::test_rederive_bitwise` |
| Callers coverage | `analysis/callers/`, `rq_map.toml` | `test_callers.py::test_uncovered_entries_listed` |

## Goals / Non-Goals

**Goals:** one generic, offline library that the final campaign's analysis runs on unmodified; every number leaves with its envelope; validity before outcome; the duplication named in the proposal absorbed; the two reader defects closed; the activity-visit unit and the step bundle available to every downstream question; two fixture classes with parity and correctness kept distinct.

**Non-Goals:** answering any research question (no number computed on cmp162 answers one); running or launching experiments; editing the `ape` repository (findings F3–F6 are reported to it); a `SET_TEXT`-like reconstruction of typing (the trace has none — the fill proxy is the EditText click); reconstructing an `aperv`-equivalent step record for the baselines (plan §8.6); cross-run comparison at state-key grain; splitting activity-visits on `MODEL_BACK`/`MODEL_MENU` (recorded refinement, decided against a concrete question); a Fragment-aware screen abstraction; a plugin/CLI surface beyond `callers/` and the smoke.

## Decisions

- **D-1 Location: `aperv_tool.analysis`, one package, five layers, `estimators/` and `callers/` as subpackages.** Alternative: a new workspace module `rv-analysis`. Rejected for now — the three shipped readers already live here, INV-APV-48's import-graph test already guards the boundary, and the analysis is intra-`aperv` for everything step-level; the naming tension with the baseline parsers is plan O4 and is recorded, not solved, here.
- **D-2 `statsmodels` declared, E2's fitter carried verbatim.** Alternative: hand-rolled IRLS with ML `alpha` and cluster-robust SEs. Rejected — unacceptable correctness risk on the estimator that carries the hypothesis; the fitter is twelve lines and its Poisson warm start is load-bearing (measured: without it the pure-offset model diverges). Compatibility with Python 3.14 / numpy 2.4.2 / pandas 3.0.0 / scipy 1.17.0 measured 2026-08-15 with `statsmodels==0.14.6`, `patsy==1.0.2`.
- **D-3 `RunStart` grows in place; no `runspec.RunSpec` shadow type.** Alternative: keep `RunStart` at three fields and add a second dataclass parsed by `runspec.py`. Rejected — two parsers of one record is the defect being closed; `runspec.py` holds only the derived logic (attribution evidence, params-vs-default resolution by `build.sha`).
- **D-4 Placement extracted from `clock_logcat_join`, not copied into `step_bundle`.** Alternative: a private copy of `_place` in `step_bundle`. Rejected — the plan's whole premise is absorbing duplication; the extraction is behaviour-preserving and the existing test suite is the guard.
- **D-5 `liveness` owns admissibility; `gates` delegates.** Alternative: gates 4/5 with their own predicates. Rejected — an excluded run must be counted exactly once, and the decisive-run corpse detector already exists as `admissibility.py`; promotion replaces both campaign copies with imports (plan O2, decided *promote* in this change).
- **D-6 Gates 2/3 have a per-arm evidence form; `not-run` is a first-class result.** Alternative: attribute baselines from the filename and call it a pass. Rejected — the filename is written by the code that was supposed to apply the configuration; for `droidbot` the policy line is evidence, for `ape` the absence of NDJSON is evidence, and where no evidence exists the honest result is `not-run`. INV-APV-59 forbids a literal expected digest in `modules/`, so gate 2's expectation is a runtime manifest supplied by the caller.
- **D-7 Activity-visit is the unit; state grain is descriptive; form episode is derived inside a visit.** Alternative: state-key visits (the note's first draft). Rejected on measurement — median state-visit length 1, 75 % single-step, 85 % of closings same-activity state transitions; a combobox, dialog, menu or soft keyboard is another state in the same Activity, and typing changes the key in 40 % of EditText clicks (74 % of those with `W` changing). The Activity grain is also the only cross-run comparable one (INV-APV-36). Non-adjacent runs never merge; the state trail is kept so nothing is lost.
- **D-8 Golden campaign artefacts are parity tests; correctness comes from FIXTURE-SYNTH.** Alternative: call the reproduction of `wilcoxon.csv` a validation. Rejected — the campaign's Wilcoxon is scipy-default approximate and `per_apk_paired.csv` holds means over replicas; reproducing them proves the pipeline unchanged, not the estimator right. Both fixture classes are pinned by hash so a refactor cannot silently change what "passing" means.
- **D-9 Freeze items are required arguments raising `FreezeItemUnset`; `offset=None` is a legal explicit value, omission is not.** Alternative: sensible defaults. Rejected by the pre-registration: a default is the author's decision made by code. Decided on 2026-08-15 and therefore *not* freeze items: budget 1800 s, one replica, five arms — still parameters, never constants.
- **D-10 Baseline parsers extract only what is certain and emit into the shared frames.** Alternative: reconstruct an aperv-like step record. Rejected — measured capability matrix (plan §8.2–8.5): droidbot has no per-event clock and no structured output retained; ape has 1-second `Elapsed` and a run-local state key. Absent signals are explicit nulls; step units differ and are named (INV-CAN-20).
- **D-11 `pandas` frames as the tidy carrier; frozen dataclasses for records; no Pydantic in the analysis path.** Alternative: Pydantic models throughout. Rejected — the readers already use frozen dataclasses (`coverage_dump`, `trace_ndjson`) and the analysis path has no untrusted external input to validate; consistency with the siblings wins (P1).

## API Design

### `run_identity.parse_run_filename(path: Path) -> RunKey`
Precondition: basename matches the identity regex. Postcondition: `RunKey(apk, repetition, timeout, arm)`; raises `ValueError` naming the basename otherwise. `decompose_arm(arm: str, table: Mapping[str, tuple[str, str]]) -> tuple[str, str]` raises `UnknownArm`.

### `trace_ndjson.TraceReader(path, *, strict: bool = False)`
`run_start: RunStart | None` with the thirteen members (`build: BuildStamp | None`, `BuildStamp(sha, time)`); `diagnostics.schema_version_mismatch: int`; `strict=True` raises `SchemaVersionMismatch(found, expected)` before iteration when `RUN_START.v != FORMAT_VERSION`. Header candidate = first `{`-leading line.

### `clock_logcat_join.place_on_timeline(stamp: datetime, heartbeats: list[Heartbeat]) -> tuple[Phase, int | None, Heartbeat]`
Precondition: `heartbeats` chronological, non-empty (caller handles empty → `UNALIGNED`). `read_tagged_lines(logcat: Path, tag: str) -> list[tuple[datetime, str]]` admits exactly `tag` (with logcat's tag padding), never a prefix match.

### `tasks_record.load(tasks_json: Path) -> tuple[pd.DataFrame, TaskDiagnostics]`
Identity `(apk, tool, variant, repetition, timeout)`; on collision keep `COMPLETED` with larger coverage; `TaskDiagnostics(lines, identities, collisions, error_records, recovered_retries, dead_identities)`.

### `liveness.verdict(run: RunFacts) -> Admissibility`
`RunFacts(identity, task_state, execution_time_s, declared_timeout_s, trace_bytes, coverage_all_zero, fatal_exception: str | None, last_trace_line: str | None)`; `Admissibility(admissible: bool, reasons: tuple[str, ...], corpse_class: Literal["normal_end","crash","cut_during_teardown","cut_elsewhere","n/a"])`.

### `gates.run_all(frame: pd.DataFrame, arm_manifest: ArmManifest, *, alpha_signal: Pattern = ANCHORED_MOP) -> GateReport`
`ArmManifest` supplied by the caller (declared digests, expected `preset`/`features`, control-arm predicate); `GateReport.results[(gate, arm)] = GateResult(status: Literal["pass","fail","not-run"], evidence_form: str, detail: str)`.

### `outcomes.binarize(counts: pd.Series, threshold: int, replica_rule: Literal["majority","union","unanimity"]) -> pd.Series`
Index = identity without replica; output labelled with `replica_rule`. `aggregate_replicas(values, estimand: Literal["mean","median","trimmed_mean_10"])` — column named by estimand. `distinct_count(stream, dedup_key: tuple[str, ...])`. `time_to_first_event(stream, clock_origin) -> (value, censored)`. `capture_curve(stream, budget_grid, scope)`. `restrict_window(stream, reference_instant, window)`.

### `screen_visits.segment(rows: Iterable[StepRow | StepBundle]) -> list[ActivityVisit]`
Closing rules and record fields as in the `campaign-analysis` spec; `form_episodes(visit: ActivityVisit) -> list[FormEpisode]`. Pure functions, no I/O.

### `step_bundle.bundle_run(trace: Path, logcat: Path | None, *, diagnostics: bool = True) -> tuple[list[StepBundle], BundleDiagnostics]`
`StepBundle(row: StepRow, violations, monitored_ops, diagnostics, uicov: StateCoverage | None)`; `BundleDiagnostics(steps, heartbeats, heartbeat_gap, unaligned_lines_by_tag)`.

### `estimators.paired_binary.mcnemar_exact(a: pd.Series, b: pd.Series, *, alpha: float, strata: pd.Series | None = None) -> Envelope`
Envelope `estimate` carries `b, c, n_disc, direction, p_two_sided, power_floor_n_disc, below_floor: bool`. `paired_continuous.wilcoxon(d, *, exact_max_n: int) -> Envelope` (exact + approximate side by side; degenerate label on all-zero). `paired_continuous.trimmed_mean_difference(a, b, *, B, seed, trim=0.10) -> Envelope` (trimmed, raw, median, `pairs_delta_nonzero`). `count_glm.fit(formula, data, *, offset, reference_level, cluster="apk") -> Envelope` — `offset` and `reference_level` keyword-only, no default. `multiplicity.adjust(p, *, family: str, method: Literal["holm","fdr_bh"]) -> Envelope`. `decision.decide(estimate, ci, *, margin) -> Envelope`. `resampling.paired_bootstrap_ci(a, b, *, B=10_000, seed=42, trim=0.10)`, `permutation(stat, groups, *, n_perm, seed)`. `variance.icc(frame, *, unit, replica) -> Envelope` with `degenerate_reason`. `capacity.expected_discordance(p_unit, *, n, replicas, effect, outcome_name) -> Envelope`. `multiarm.friedman_holm(frame, *, arms) -> Envelope`.

### `envelope.Envelope`
`Envelope(estimand: str, n: int, denominator: Denominator, estimate: Mapping[str, float | int | str | bool], ci: tuple[float, float] | None, convention: Mapping[str, str], exclusions: tuple[Exclusion, ...], provenance_ref: str)`; frozen. `emit.table(envelopes: Sequence[Envelope], dest: Path)` raises `TypeError` on anything else.

## Data Flow

1. `loader.load(roots, arm_table)` walks the batch dirs → `tasks_record.load` per batch → identities deduped → joined to the CSVs by `RunKey` → tidy frame + `LoadDiagnostics` (files missing, records dropped, why).
2. `gates.run_all(frame, manifest)` → for each identity, evidence gathered per arm (`runspec.attribution_evidence` on `aperv` traces; policy line on droidbot; NDJSON-line count on ape; provenance sidecar if present) → `liveness.verdict` per run → `GateReport`; the caller stops on any `fail` it declares blocking.
3. `corpus.scope` / `clones.collapse` produce the analysed frame with `Basis` (both denominators).
4. Layer 3 readers produce streams: `step_bundle.bundle_run` per `aperv` run (trace → `TraceReader`; logcat → `read_tagged_lines` × three tags → `place_on_timeline`; dump → `coverage_dump` → `state_coverage_join`); `baseline_*` per baseline run into the same frame shapes; `violations` / `monitored_ops` from CSV or logcat; `static_artifact` per APK.
5. Layer 1: `outcomes.*` over streams with conventions; `screen_visits.segment` over bundles.
6. Layer 2: an estimator over an outcome column and a contrast → `Envelope`, `provenance.stamp` recording inputs' sha256 and the parameter set.
7. Layer 4: `emit.table/figure` from envelopes; `callers/<entry>.py` wires builder + estimator + parameters from `rq_map.toml`; `callers.coverage()` lists uncovered entries.

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| `FreezeItemUnset` | any estimator/builder called without a required freeze-item argument | raise before computing | caller supplies the decided value explicitly |
| `UnknownArm` | `decompose_arm` | raise naming the arm | extend the arm table (data) |
| `SchemaVersionMismatch` | `TraceReader(strict=True)` | raise before rows | open non-strict for a survey; do not compare across versions |
| `IdentityCollisionUnresolved` | `tasks_record` when two `COMPLETED` records tie on coverage and differ | raise with both records | author decides; never silent |
| malformed trace line | `TraceReader` | skip + count (INV-APV-50) | reported in diagnostics |
| missing `.logcat` | `step_bundle`, `clock_logcat_join` | zero lines, run kept | denominator survives |
| no heartbeat | `step_bundle` | all lines `UNALIGNED`, run kept | reported, never repaired |
| missing consolidated CSV | `loader` | run kept with `NaN` payload, omission counted | visible in `LoadDiagnostics` |
| bare float to `emit` | `emit.table` | `TypeError` | wrap in `Envelope` |
| gate evidence absent | `gates` | `not-run` with reason | never coerced to `pass` |

## Risks / Trade-offs

- [The `aperv_tool` name now hosts baseline parsers (plan O4)] → recorded here and in the proposal; a rename is a separate mechanical change, not slipped into this one.
- [Extracting `place_on_timeline` could alter the join] → the existing suite must pass unmodified and `join_run` must be byte-identical over fixtures (spec scenario).
- [cmp162 has R = 3, the final campaign R = 1] → the replica machinery is validated on the fixture and marked inapplicable at R = 1 in the envelopes' `convention`; nothing assumes replicas.
- [E2 cross-check on a different pandas/numpy may not reproduce E2's numbers] → plan O3: run inside `ase-journal`'s pinned environment, compare emitted numbers, not environments; out of this change's tests.
- [Activity grain collapses single-Activity apps into one long visit (max measured 294 steps)] → recorded limitation; `state_trail` keeps the inner structure; the BACK/MENU split is a named future refinement.
- [Baseline fixture lives outside any repository (39.8 GB tree)] → a hashed sample is copied under `tests/fixtures/baseline_sample/` and pinned by manifest; the full tree is never required by a test.
- [`statsmodels` adds a heavy dependency to `aperv-tool`] → declared explicitly; imported lazily inside `count_glm` so the readers and the collection path never load it.
- [Two parsers of `RUN_START` briefly coexist (`check_run_start.py` in `rvsec-calibracao`)] → that script lives outside this repository; the change records that its reason to exist is gone and does not edit it.

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Unit | every builder, estimator, segmenter, parser rule; every INV-CAN/APV-61..63 | FIXTURE-SYNTH frames, hand-written trace/logcat snippets, golden fixtures | ~120 tests |
| Parity | `per_apk_paired.csv`, `wilcoxon.csv`, `censo_substrato.csv` reproduced exactly in the campaign's mode | cmp162 via the pinned manifest (skipped with an explicit reason if the tree is absent) | 3 tests |
| Integration | loader → gates → outcomes → estimator → emit on two cmp162 applications; the corrupted-fixture smoke | real files, no device | ~8 tests |
| Boundary | no RQ identifier; import graph off `tools/aperv/tool.py`; `*.mop.json` never opened; regex declared once | static scans, monkeypatched `open` | ~6 tests |
| Measured-figure | activity-visit and state-visit distributions on the first 60 `aperv:mop_on_llm_off` traces | cmp162 | 1 test |

## Open Questions

- Which `droidbot` variant is the campaign baseline (plan O10) — the parser handles all four; the caller layer needs the name.
- Whether the change is split at implementation time by phase (P0–P1, P2–P3, P4–P6 of the plan) into follow-up changes referencing #103, or applied as one — the tasks are grouped so either works.
- The GLM reference level (`ape` recommended) — a freeze item; the code takes it as a required argument either way.
- Whether `aperv_tool.analysis` is renamed once the baseline parsers land (plan O4).
