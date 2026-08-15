<!-- Subagent dispatch hints:
     Groups map to the plan's phases P0–P6 (doutorado-tese/docs/estudo-03/analise/20260815_plano_scripts_analise.md §9).
     Group 1 (P0 — dependency + fixtures) must complete first: every parity and measured-figure test
     depends on the pinned manifests, and Group 5 depends on statsmodels.
     Group 2 (P1 — Layer 0 + Layer 4 + the two reader edits) must complete before Groups 3–7.
     Groups 3 (Layer 1), 4 (Layer 3 additions) and 6 (baseline parsers) are independent of each other
     after Group 2 and can run in parallel; Group 5 (estimators) depends only on Group 2 (envelope).
     Group 7 (callers + smoke) integrates everything — must run last.
     Critical path: 1 → 2 → {3,4,5,6} → 7 → 8.
     This change touches ~45 files (≈30 new modules/tests) — use subagent orchestration
     (four parallel dispatches for Groups 3–6 after Group 2). Each task below is scoped for one session.
     Read-only over every artefact; no device, no emulator, no adb, no Docker at any point (INV-APV-35).
     Do NOT touch: tools/aperv/tool.py, *.mop.json, the INV-APV-55 legacy readers, the ape repository. -->

## 1. P0 — Dependency, fixtures, findings recorded

- [x] 1.1 Declare `statsmodels>=0.14.6`, `pandas>=3.0.0`, `numpy>=2.4.0`, `scipy>=1.17.0` in `modules/aperv-tool/pyproject.toml` `[project].dependencies`; run `uv sync`; add `test_statsmodels_importable` and `test_statsmodels_not_loaded_by_readers` (importing `aperv_tool.analysis.trace_ndjson` / `coverage_dump` / `clock_logcat_join` leaves `statsmodels` out of `sys.modules`)
- [x] 1.2 Write `modules/aperv-tool/tests/fixtures/cmp162_manifest.json`: for `experimento-comp162/results/*/*/`, the relative path and sha256 of every `tasks.json`, the five consolidated CSVs per batch, `consolidado/wilcoxon.csv`, `consolidado/per_apk_paired.csv`, `censo_substrato.csv`, the 162 `<apk>.json`, and the `.trace`/`.logcat` of a declared 12-application subset (the two smoke applications, `com.ds.avare_404.apk`, `app.eduroam.geteduroam`, `com.flxrs.dankchat_40038.apk` and seven more named in the manifest) — plus the identity totals (1458 / 1455 / 3 dead / 22 recovered ERROR records) as manifest facts. Add `tests/fixtures/README.md` §cmp162 recording provenance and the "fixture, not corpus" rule
<!-- measured, spec reworded in the same pass: the 31 ERROR records split 9 (the three dead
     identities, retried three times each) and 22 (across 21 identities that later completed).
     The old "28" was 1486 records - 1458 identities, i.e. superseded records, not recoveries.
     Tests assert against the manifest's four measured numbers, never a literal. -->

- [x] 1.3 Write `tests/fixtures/baseline_sample/` — 6 `ape` and 6 `droidbot` (`bfs_greedy`, `bfs_naive`, `dfs_greedy`, `dfs_naive` — at least one each, two of them 300 s) `.trace`+`.logcat` pairs and their `tasks.json` slice copied from `/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/RESULTS`, including one `ape` trace with no `SATA begin step` marker and one droidbot run that reached an orderly stop — with `baseline_sample_manifest.json` (path + sha256 + source path) and README provenance
- [x] 1.4 Add `tests/test_fixture_manifest.py`: every manifest entry present with matching sha256, or the dependent tests `skip` with the reason `FIXTURE-REAL not present` — never a silent pass
- [x] 1.5 Report findings F3–F6 of the plan (§3.4) to the `ape` repository as one issue (spec/producer divergences: `MOP_DATA` extra fields, `PIPELINE.stages`, `RUN_END.detail`, `RUN_END` verified by nothing) — read-only from here, no code
<!-- Verified against ape@e93dea86 (phtcosta/ape at workspace-rv/ape; NOT rvsec/ape, a build dir).
     None of it is a defect in the tool and none of it moves a number: it is drift between ape's
     own spec prose and ape's own emitter.
       F3 CONFIRMED  NdjsonSink.mopData() writes formatVersion, sourceDigest, components;
                     event-sink/spec.md:124's SHALL sentence lists 12 fields, none of the three.
       F4 CONFIRMED  NdjsonSink.pipeline() writes "stages"; spec.md:130's SHALL names only
                     `passes` and `candidates`.
       F5 CONFIRMED  NdjsonSink.runEnd() writes "detail" when non-null; spec.md:160's schema line
                     does not carry it.
       F6 REFUTED    ape covers RUN_END in three test files (NdjsonSinkTest,
                     StatefulAgentRunEndTest, LlmTelemetryTest), `detail` included. Only the
                     CONSUMER side is unvalidated, which is the spec's own decision D5.
     Recorded here rather than filed as an ape issue (author, 2026-08-15). The ape tree is never
     edited. Nothing else in the change depends on this. -->
- [x] 1.6 Run `/rv-test-run aperv-tool`

## 2. P1 — Layer 0, Layer 4, and the two reader edits

- [x] 2.1 Create `analysis/run_identity.py`: the identity regex (INV-CAN-01), `RunKey`, `parse_run_filename`, `decompose_arm(arm, table)` raising `UnknownArm` (INV-CAN-02); replace the copies at `coverage_dump.py:66-69` and `clock_logcat_join.py:94-96,222` with imports; add `test_run_identity.py` (`test_regex_declared_once` greps the package, `test_unknown_arm_raises`, `test_cmp162_arm_strings_with_colon`)
- [x] 2.2 Extend `trace_ndjson.RunStart` to the thirteen `RUN_START` members with `BuildStamp(sha, time)`, absent → `None` (INV-APV-61); header candidate = first `{`-leading line; add the `v` check with `TraceDiagnostics.schema_version_mismatch` and `TraceReader(strict=)` raising `SchemaVersionMismatch` (INV-APV-62); extend `trace_ndjson_golden.ndjson` with all thirteen members and add `trace_ndjson_v2_header.ndjson`; tests `test_run_start_thirteen_members`, `test_inert_absent_is_none`, `test_v_mismatch_strict_raises`, `test_v_mismatch_counted`, `test_first_brace_line_is_header`; existing reader tests unchanged
- [x] 2.3 Extract `clock_logcat_join.place_on_timeline` and `read_tagged_lines(path, tag)` (INV-APV-63) with `join_run` calling them under `tag="RVSEC"`; the existing `test_clock_logcat_join.py` passes unmodified and `join_run` is byte-identical over its fixtures (add `test_join_unchanged_after_extraction` hashing `RunJoin` values)
<!-- 2.3 the new cases live in tests/test_clock_logcat_join_extraction.py, so
     test_clock_logcat_join.py is byte-untouched (`git diff` on it is empty) and
     "the existing suite passes unmodified" stays checkable rather than argued.
     Behaviour preservation was measured, not asserted: HEAD's join and the
     extracted join were run side by side over all 892 recorded runs of
     experimento-cal/iter0/results and agree field for field, digest for digest.
     JOIN_DIGEST in the new file is the PRE-extraction value on its own fixture. -->

- [x] 2.4 Create `analysis/runspec.py`: `attribution_evidence(run_start, manifest_arm)` for `aperv` arms (`preset`/`features`/`params` vs manifest, `build.sha` vs declared digest), `params_resolved(run_start)` documenting that absence means "jar default for this `build.sha`"; tests
<!-- 2.4 decisions: the spec fixes the pass/fail/not-run vocabulary but not how the
     four checks combine. Implemented as any-fail => fail, else any-not-run =>
     not-run, else pass, with the per-check verdicts carried so gates reads gate 2
     (digest) and gate 3 (configuration) out of one call. `features` is compared as
     an exact set in BOTH directions: an unexpected feature is what catches a mop_on
     jar running under a mop_off_llm_off label, which the filename can never detect.
     `params` is compared by declared key only, and a declared key ABSENT from the
     header is a fail — the run sat at its own jar default and whether that default
     equals the declared value is not knowable from the artefact.
     2.10: `emit.figure` takes a caller-supplied `render` because no plotting library
     is a declared dependency; the module owns the refusal, not the chart.
     `FreezeItemUnset`'s seat is corpus.py (task 2.9) — later modules import it. -->

- [x] 2.5 Create `analysis/tasks_record.py`: identity-keyed dedup (INV-CAN-03), collision policy, `TaskDiagnostics`; `state_transitions[]` never counted; `experiment.current_status` never a gate; tests `test_identity_not_task_id`, `test_collision_keeps_larger_coverage`, `test_cmp162_3_dead_22_recovered` (manifest-gated)
- [x] 2.6 Create `analysis/loader.py`: one or many roots (double nesting tolerated) → tidy frame at `(apk, rep, timeout, arm)` + `LoadDiagnostics`; never drops a run silently (INV-CAN-04); `.trace.ndjson.gz` never counted as a second stream; tests incl. `test_cmp162_1458_identities` and `test_missing_csv_counted_not_dropped`
<!-- finding, 2.5: the ERROR-class split recorded in the session-2 handoff is wrong.
     Measured over all 31 records: 18 `install_failure` (51-69 s, coverage 0.0/0.0) and
     13 `tool_execution_failure` (127-298 s, coverage sometimes non-zero) - NOT 19/12.
     Durations and the "sometimes non-zero" claim hold; only the counts were off. These
     are not manifest facts, so the gated test asserts the PARTITION (the two classes sum
     to error_records) and the structural property (all 3 dead rows are tool_execution_failure
     with method_coverage > 0), never a literal. 18/13 is recorded in the module docstring.
     finding, 2.5/2.7 - RESOLVED (session 3): `arm_label` had TWO seats, tasks_record.arm_label
     and liveness.arm_label (promoted from admissibility.py), byte-equal, written by two agents
     that could not see each other's file. One seat per rule is the point of this change.
     The seat is now `run_identity.arm_label` - NOT liveness, which the session-3 handoff had
     suggested. Reason: arm_label is the exact inverse of `decompose_arm`, which already lives
     in run_identity under INV-CAN-02, and the label is identity vocabulary rather than an
     admissibility criterion. Seating it there also keeps liveness a faithful promotion of the
     campaign rule (the whole credibility of its parity test), avoids a Layer-1 reader importing
     a judgement module, and keeps pandas out of liveness. Both modules import it, so
     `liveness.arm_label` still resolves for anything reaching for it there. Guarded by
     `test_arm_label_declared_once` (greps `def arm_label(` over the package, the shape of
     `test_regex_declared_once`), `test_arm_label_consumers_import_the_seat`,
     `test_arm_label_collapses_the_builtin_ape` and
     `test_arm_label_round_trips_through_decompose`.
     2.6 scope: the loader joins only the two identity-grain CSVs (summary, performance).
     errors/coverage/app_events are event-grain and would multiply the run grain; they belong
     to the Layer-3 stream readers. `_PAYLOAD_COLUMNS` declares the payload shape so that
     "kept with NaN payload" means something - NaN needs a column to sit in. -->

- [x] 2.7 Create `analysis/liveness.py` by promoting `experimento-comp162/scripts/admissibility.py:48-105` (byte-identical in `-ajc`); replace both campaign files with an import + re-export (INV-CAN-05, plan O2); add full-budget predicate to `RunFacts`; corpse classification by last non-empty trace line; tests `test_campaign_copies_are_imports`, `test_decisive_corpse_pattern`, `test_full_budget_required`
<!-- BOUNDARY, 2.7 — the two campaign `admissibility.py` files were NOT edited (author
     instruction 2026-08-15: nothing in rv-android outside the analysis layer). Both are
     still byte-identical, sha256 8fa95bd1...94a2. The duplication this change exists to
     absorb therefore SURVIVES at this point; that is visible here rather than implicit.

     AUTHOR DECISION, 2026-08-15 (session 3): the two campaign files STAY AS THEY ARE, and
     this half of 2.7 is deliberately not done. The boundary was the occasion; the reason is
     stronger and technical. `tests/test_liveness.py:35` loads
     `experimento-comp162/scripts/admissibility.py` from disk by importlib and compares its
     verdicts against the package's, identity by identity - the campaign copy IS the
     pre-promotion reference, and it is the only evidence that the promotion preserved the
     rule. Replacing it with `from aperv_tool.analysis.liveness import ...` would make that
     test compare liveness against itself: green, and vacuous. The two consequences that were
     to be weighed (report() would print English where the campaign printed pt-BR;
     judge_identities gained an optional keyword changing no C-criterion) are moot.
     The dependency direction is one-way and stays so: nothing under
     `modules/aperv-tool/src/` references anything outside the module - verified by grep for
     imports, sys.path and campaign paths. The only outward references are read-only reads of
     the campaign tree as recorded artefact, in tests/ (test_liveness.py, fixture_gate.py,
     fixtures/build_cmp162_manifest.py).
     `test_campaign_copies_are_imports` was replaced by `test_promoted_rule_matches_the_campaign_copy`,
     which loads the campaign file read-only and asserts the verdicts agree identity by
     identity over a synthetic tasks.json — a stronger check than an import assertion, and
     inside the boundary.

     findings, 2.7/2.8, each verified against the artefact:
     (a) `RunFacts` as designed is two facts short. C1 needs `error_message` (the campaign
         fails a COMPLETED record carrying one) and C5 is method_coverage > 0 AND
         activities_coverage > 0, which a single `coverage_all_zero` cannot express. Keeping
         the promoted rule UNCHANGED won: RunFacts carries error_message, method_coverage and
         activities_coverage; "coverage all zero" is derived, for the corpse signal only.
     (b) INV-CAN-08 says duration >= declared timeout; the promoted C2 says >= timeout - 45.
         Measured on 1486 cmp162 task records: durations cluster at median 366 s against a
         300 s budget (install and teardown are inside the number) while early deaths sit at
         51-61 s; 31 records below 300 s, 28 below 255 s. The grace floor is the tool's own
         contract, so C2 is implemented and the relation documented on `full_budget`.
     (c) TRACE_FLOOR_BYTES had no declared value anywhere. Grounded on the fixture: over
         1458 cmp162 traces the minimum is 251,204 bytes and p5 is 1.06 MB, against the
         decisive corpse's 864 bytes. Default 64 KiB, overridable per call.
     (d) cmp162 traces are the jar's stdout (interleaved [APE] text + NDJSON), not NDJSON-only,
         so `classify_last_line` keys off markers observed in those files rather than a record
         type. -->

- [x] 2.8 Create `analysis/gates.py`: five gates, anchored `(?<![a-z_])mop=` (INV-CAN-07), per-arm evidence form and `not-run` (INV-CAN-06), gate 4 identity-not-line + full budget from `tasks.json`/`performance.csv` (INV-CAN-08), gate 5 via `liveness`; `ArmManifest` supplied by the caller (no literal digest in `modules/`, INV-APV-59); tests `test_anchored_mop_pattern`, `test_ape_negative_evidence`, `test_ape_one_ndjson_line_fails`, `test_droidbot_policy_line`, `test_not_run_never_pass`, `test_gates_delegate_to_liveness`
- [x] 2.9 Create `analysis/corpus.py` (declared subset + reason, both denominators, basis cardinality assert, set relations by member name — INV-CAN-09) and `analysis/clones.py` (clone-map collapse); tests `test_both_denominators`, `test_basis_relations_by_name`, `test_clone_collapse`
<!-- 2.9 decisions: `subset` is a keyword defaulting to None so that omitting the
     corpus raises FreezeItemUnset("corpus") rather than TypeError (INV-CAN-11
     needs the named error, not an arity error). Clone collapse RELABELS rows onto
     the survivor instead of dropping them — dropping would shrink a run-level
     denominator as a side effect of an application-level decision, i.e. a second
     undeclared scoping. `Basis.cardinality` is DECLARED and checked against the
     members, and a repeated id is an error: a duplicate in a hand-maintained
     subset file silently shrinks a basis by one. `FreezeItemUnset`'s seat is
     corpus.py; later modules import it from there. -->

- [x] 2.10 Create `analysis/envelope.py` (`Envelope`, `Denominator`, `Exclusion`, frozen), `analysis/provenance.py` (inputs' sha256/paths, parameter set, timestamps — never inside an estimate), `analysis/emit.py` (tables/figures from envelopes only, `TypeError` on a bare float); tests `test_bare_float_rejected`, `test_rederive_bitwise`
- [x] 2.11 Add `test_analysis_off_collection_path.py` (walk the import graph of `tools/aperv/tool.py`; nothing under `aperv_tool.analysis` reachable — INV-CAN-23) and `test_no_rq_identifier.py` (scan every `.py` under `analysis/` except `callers/` for `\b[ETR]\d+\b` and `\bRQ\d*\b` — INV-CAN-22)
<!-- finding, 2.11: the scenario's testable regex cannot fail on this project's own
     vocabulary. `\b[ETR]\d{2}\b` needs two digits, so it misses E1/E2/E3, and
     `\bRQ\b` needs a non-word char after the Q, so it misses RQ1/RQ2. Between
     them they match none of the identifiers actually in use — and coverage_dump.py:8
     carried "the E3 study" while the invariant read as satisfied. The test
     implements INV-CAN-22 as the INVARIANT states it (`E\d+`,`T\d+`,`R\d+`,`RQ`):
     `\b[ETR]\d+\b|\bRQ\d*\b`. That one docstring line in coverage_dump.py was
     reworded (no identifier, same meaning); nothing else in analysis/ matched.
     The spec scenario should be corrected to the invariant's form. -->

- [x] 2.12 Run `/rv-doc-code` on each new module of this group; run `/rv-verify aperv-tool`
<!-- 2.12: `/rv-doc-code` and `/rv-verify` are rv-android project skills and are not
     registered in a session opened from another repository; their SKILL.md was read and
     executed by hand. autoflake + isort + black over src/ and tests/; `flake8
     src/aperv_tool/analysis/` silent; over all of `src/` the only remaining findings are
     the 42 pre-existing ones in `tools/aperv/tool.py`, which is off-limits and untouched.
     Complexity (radon) over analysis/ carries no new C-or-worse function from this change;
     `liveness.select` is D(25) and stays so - it is byte-faithful to the campaign rule it
     was promoted from, and simplifying it would break the parity test that is the whole
     evidence the promotion preserved behaviour. -->

## 3. P2 — Layer 1: outcomes and activity-visits

- [x] 3.1 Create `analysis/outcomes.py`: `distinct_count(stream, dedup_key)` with both `mop_unique` keys available and labelled (`(class, method, spec)` = E2's; message-level beside it), `binarize(counts, threshold, replica_rule)` + mixed-replica census, `aggregate_replicas(values, estimand)` with the estimand as column label (INV-CAN-10), `time_to_first_event` with censoring flag, `capture_curve(stream, budget_grid, scope)`, `restrict_window`; `FreezeItemUnset` on absent freeze items (INV-CAN-11); FIXTURE-SYNTH tests `test_three_replica_rules`, `test_estimand_labelled`, `test_censoring_flag`, `test_freeze_item_unset`
- [x] 3.2 Add the parity test `test_parity_per_apk_paired` (162 rows, exact, campaign conventions; labelled parity — INV-CAN-21; manifest-gated)
- [x] 3.3 Create `analysis/screen_visits.py`: `ActivityVisit`, `segment(rows)` with the five closing rules, `revisit_index`/`visits_of_activity`, `state_trail`, counts, `exit_kind`; `FormEpisode`, `form_episodes(visit)`; INV-CAN-12/13; pure functions; docstring records the measured rationale (state grain step-level) and the Fragment limitation
- [x] 3.4 Add `test_screen_visits.py`: `test_revisits_separate` (A→B→A), `test_combobox_in_trail` (S1,S2,S1 one visit), `test_no_outcome_closes_visit`, `test_teardown_closes_visit`, `test_form_episode_across_states`, `test_form_episode_no_submit_ends_with_visit`, `test_step_numbers_may_skip`; and the manifest-gated `test_cmp162_measured_figures` (first 60 `aperv:mop_on_llm_off`: median 14.5 activity-visits/run, median length 2, mean 11.0, max 294; state-grain median 156.5 visits/run, 75.5 % single-step, 84.6 % same-activity closings)
- [x] 3.5 Run `/rv-doc-code` on both modules; run `/rv-test-run aperv-tool`
<!-- Group 3: all 16 measured figures reproduce EXACTLY, nothing adjusted to hit a target —
     runs 60 · steps 15702 · activity-visits/run median 14.5 · len mean 11.0 / median 2 /
     p90 32 / max 294 · share_len1 0.378 · distinct states/visit 2.68 · state-visits/run
     median 156.5 · state len mean 1.66 / median 1 · share_len1 0.755 · exit-kind shares
     .846/.085/.059/.006/.003 · EditText clicks 954 / 382. `heartbeats: 15701` is NOT
     asserted here: it is a logcat count owned by step_bundle, not by the segmenter.
     3.2 parity passes over loader.load: 162 rows x 3 arms x 6 metrics + n_reps, the nan /
     zero-replica cells of com.ds.avare_404.apk included. Measured while doing it:
     summary.csv's `mop_errors_total` EQUALS the campaign's logcat-derived `mop_total` on
     all 1455 runs, so the parity needs no 1.9 GB logcat re-read.
     Deliberate deviations: (a) `StateSpan` carries a fifth field `exit_kind` — without it
     the manifest's state_exit_kind_share is not re-derivable from the library, and that
     share is the measurement that chose the Activity grain. (b) state spans are computed
     over the WHOLE run, not per visit: classifying a visit's last row against the end of a
     slice turns key_change_without_outcome into run_end. Spans nest inside visits (an
     Activity change implies a key change), asserted on real traces. (c) screen_visits does
     not import StepBundle (Layer 3, another owner): a bundle is recognised by carrying a
     `row`, and the stream fields are read by getattr defaulting to empty. (d) closing-rule
     ORDER is no_outcome -> teardown -> activity_changed -> next_activity_differs -> run_end,
     not the order the spec sentence lists: an outcome must exist before its members are
     read, and an unresolved record's flags were never written. -->


## 4. P4 — Layer 3 additions: step bundle, streams, static artefact

- [x] 4.1 Create `analysis/state_coverage_join.py`: per-state `UICOV` payload onto steps by `STATE.key` via `coverage_dump`; per-run frame only, refuses to emit a cross-run key; flagged cumulative-per-run; test `test_uicov_total_join` (3801/3801 on the fixture subset), `test_no_cross_run_key`
- [x] 4.2 Create `analysis/step_bundle.py`: `bundle_run(trace, logcat)` → `StepBundle` per step with `violations[]` (`RVSEC`), `monitored_ops[]` (`RVSEC-COV`), `diagnostics[]` (via `rv_coverage`'s diagnostic parser over the `RV_LOGCAT_DIAGNOSTICS` tags) placed by `clock_logcat_join.place_on_timeline` (INV-CAN-18, INV-APV-63), `uicov` via 4.1; `BundleDiagnostics` with `heartbeat_gap` and per-tag `UNALIGNED` counts; tests `test_rvsec_cov_placed_same_rule`, `test_heartbeat_gap_counted` (262 steps / 261 heartbeats), `test_unaligned_not_repaired`, `test_placement_exists_once` (grep), `test_ape_arm_yields_zero_bundles`
- [x] 4.3 Create `analysis/violations.py` (from `errors.csv` or raw `RVSEC` lines — 7 comma-separated fields, split bounded at six) and `analysis/monitored_ops.py` (`RVSEC-COV` full Soot signatures; join key to `<apk>.json` `reachability[].methods[].signature` is exact string equality); tests incl. `test_message_with_commas_kept_whole`
- [x] 4.4 Create `analysis/static_artifact.py`: `components`, `reachability`, `windows`, `transitions`; `sa_methods_reaches_mop` = count of `reachability[].methods[].reachesTarget`; strata; three-way handler verdict `hot/cold/unresolved`; `complete: true` never a quality signal; never opens `*.mop.json` (INV-CAN-24); tests `test_covariate_162` (manifest-gated), `test_mop_json_never_opened` (monkeypatched `open`), `test_unresolved_first_class`
- [x] 4.5 Add the parity test `test_parity_censo_substrato` (163 lines, labelled parity, manifest-gated)
- [x] 4.6 Run `/rv-doc-code` on the new modules; run `/rv-verify aperv-tool`
<!-- Group 4 measured: UICOV join 3801 dump states / 3801 matched / 0 orphans BOTH directions
     over 120 runs, equal to manifest["uicov_join"]. The manifest does not declare WHICH 120
     runs; the basis is the first 120 `results/*/*/*/*__aperv:*.trace` in sorted path order and
     it reproduces exactly (the 105 sha-pinned aperv traces alone give 3201/3201/0 — also total,
     but a different basis). Covariate emitted for all 162, sum sa_methods_reaches_mop = 308,881
     (min 1, median 779.5, max 25,136); strata discriminative 93 / saturated 39 / inert 28 /
     rare 2; handlers 2962 distinct = 431 hot + 1398 cold + 1133 UNRESOLVED (38.3%), so
     `unresolved` is populated, not theoretical. Heartbeat gap over the 60-trace basis:
     15,702 steps / 15,701 heartbeats, gap 1, in one run.
     findings: (a) "262 steps / 261 heartbeats" is NOT a cmp162 fact — the single real gap run
     is com.gelakinetic.mtgfam_99.apk__1__300__aperv:mop_on_llm_off with 303 steps / 302
     heartbeats, missing step 52. The scenario is satisfied literally by a synthetic 262/261
     run and the campaign aggregate is asserted against the manifest. (b) censo_substrato.csv
     parity CANNOT be total by design: experimento-comp162/scripts/censo_substrato.py computes
     9 of its 11 columns through derive_mop_artifact.derive() — collection-path code the
     analysis layer deliberately does not import — and it read the DATASET directory, not the
     campaign tree. The parity test is scoped to the two artefact-owned columns plus membership
     and line count, and says so instead of claiming the file. (c) test_mop_json_never_opened
     must patch `io.open` as well as `builtins.open`: Path.read_text does not go through
     builtins.open, so patching only the latter passes VACUOUSLY. (d) read_tree globs
     `*.apk*.json`, not `*.apk.json`: the narrow pattern would make the INV-CAN-24 refusal
     unreachable, and a counter that can never fire proves nothing — so the derived artefact is
     met, refused by name, and counted. (e) rv_coverage's DiagnosticEventParser is imported
     LAZILY (not a declared dependency of aperv-tool) and its naive `time_occurred` is re-framed
     into the placeholder year/zone clock_logcat_join reads stamps in — otherwise it is
     incomparable with a heartbeat. Absence degrades to diagnostics_read=False, never to a
     silent empty stream. -->


## 5. P3 — Layer 2: estimators

- [x] 5.1 Create `analysis/estimators/__init__.py`, `resampling.py` (extract `paired_bootstrap_ci(a, b, *, B=10_000, seed=42, trim=0.10)` and `diff_of_trimmed_means` from `experimento-cal/scripts/stats_utils.py:35-55` — estimand = difference of 10 % trimmed means recomputed per resample, paired by APK; add `permutation`), `multiarm.py` (extract Friedman + Holm + rank-biserial from `experimento-{cal,rearch-aperv}/scripts/multiarm_stats.py:56-218`; descriptive, never a verdict); FIXTURE-SYNTH tests with known answers; the campaign copies are left in place (INV-APV-55 covers `experimento-cal/scripts/*`)
- [x] 5.2 Create `paired_binary.py`: `mcnemar_exact(a, b, *, alpha, strata=None)` — binomial over discordant pairs; envelope carries `b, c, n_disc, direction, p, power_floor_n_disc, below_floor` (INV-CAN-15); tests `test_never_n_disc_alone`, `test_zero_discordant_valid`, `test_power_floor_7_at_0025`, `test_stratified`
- [x] 5.3 Create `paired_continuous.py`: `wilcoxon(d, *, exact_max_n)` exact + tie/continuity-corrected approximate side by side, all-zero degenerate label (INV-CAN-16); `trimmed_mean_difference(a, b, *, B, seed, trim)` with trimmed, raw, median and `pairs_delta_nonzero`; tests `test_exact_beside_approx`, `test_all_zero_degenerate`, `test_trimmed_raw_median`, `test_pairs_delta_nonzero`
- [x] 5.4 Create `count_glm.py`: E2's `_glm_fit_nb` verbatim from `ase-journal/data-analysis/rvsec/rq1_jca.py:216-228` (Poisson warm start with the same offset, NB2 `alpha` by ML, `cov_type='cluster'` by `apk`), `fit(formula, data, *, offset, reference_level, cluster="apk")` with `offset` and `reference_level` keyword-only and required (INV-CAN-17, INV-CAN-11), IRR table + exponentiated Wald CI, NB-zero predictor, boundary-corrected LR (`0.5*chi2.sf(lr,1)`), direction-flip / significance-loss detector; `statsmodels` imported lazily; the E2 constants (`assert len(df)==16137`, `Treatment('monkey')`, `m=10`, `TOOL_LABELS`, 60/300) become parameters; tests `test_offset_required`, `test_offset_none_is_explicit`, `test_synth_irr_recovered_both_specs`, `test_offset_alpha_inflates`, `test_reference_level_param`, `test_no_monkey_literal`, `test_separation_reported`
- [x] 5.5 Create `multiplicity.py` (`adjust(p, *, family, method ∈ {holm, fdr_bh})`, family required), `decision.py` (`decide(estimate, ci, *, margin)`, no default), `variance.py` (`icc` with `degenerate_reason` on a saturated binary outcome), `capacity.py` (`expected_discordance(p_unit, *, n, replicas, effect, outcome_name)`, outcome-specific); tests `test_family_required`, `test_margin_required`, `test_icc_degenerate_reason`, `test_capacity_records_outcome`
- [x] 5.6 Add the parity test `test_parity_wilcoxon` (15 rows, campaign mode = scipy-default approximate branch, labelled parity, manifest-gated)
- [x] 5.7 Run `/rv-doc-code` on `analysis/estimators/`; run `/rv-verify aperv-tool`
<!-- finding, 5.6 — the Wilcoxon parity does NOT reproduce from `per_apk_paired.csv`.
     That file rounds each per-application mean to 4 decimals, and the rounding MANUFACTURES
     TIES: 22 of 195 fields disagree. Example: aperv:mop_off_llm_off vs aperv:mop_on_llm_off
     on cov_mop gains 2 ties and W moves 3896.0 -> 3793.0; mop_unique p goes 0.84416 ->
     0.66143. All 15 rows reproduce field for field from `consolidado/per_rep.csv`, which is
     what the campaign's own consolidate.py:150-176 actually used. The estimator was not
     adjusted — the INPUT was corrected. Both parity files are digest-checked against
     manifest["files"] before anything is computed.
     Deviations, each deliberate: (a) resampling.paired_bootstrap_ci / diff_of_trimmed_means
     return plain values, not Envelopes — task 5.1 mandates VERBATIM extraction and the source
     returns a triple; INV-CAN-14 binds "every Layer-2 estimator", and the enveloped seat is
     paired_continuous.trimmed_mean_difference, so the trimmed mean still cannot be quoted
     without its companions. (b) `wilcoxon` gained a REQUIRED `continuity_correction: bool`:
     the campaign's mode is scipy's default, which omits it, and with correction=True the
     parity fails on 10 of 15 p-values (0.09625 vs 0.09462). Making it a required declaration
     lets the reporting mode and the parity mode coexist without a hidden default. (c) icc
     gained a required `value` column, (d) expected_discordance a required `replica_rule` and
     `alpha`, (e) friedman_holm a required `trim` — each is a knob without which the number
     is not defined. (f) count_glm.fit refuses a frame whose formula would drop rows: the
     cluster vector is positional, so a dropped row misaligns it and statsmodels blames the
     cluster length instead. The INTERCEPT is excluded from the CI-widening assertion and from
     compare_specifications' default terms — it absorbs the offset and is not the same
     quantity across the two fits (the sibling study's own focal list excludes it too).
     Synthetic GLM: true IRR 1.6/2.4 recovered at 1.5693 (1.4614,1.6851) and 2.3773
     (2.2155,2.5509), log_size CI covers exp(0.5); the pure-offset signature DID appear —
     alpha 0.2619 -> 0.3280 and both arm-contrast CI widths grew. -->


## 6. P5 — Baseline parsers

- [x] 6.1 Create `analysis/baseline_ape.py`: `SATA begin step [N][Elapsed: …]` … `SATA end step [N]` envelope split (unterminated final block tolerated), per block `New   state:` (FQ activity + run-local key), `Select action … by strategy …`, Source/Action/Target, `GSTG(…)`, `// NOT RESPONDING` / `// CRASH` hoisted as run-level events with the preceding step index; `truncated`, unparsed-line count; "no steps" is an outcome; emits into the shared frames; unit named (INV-CAN-19/20); tests over `tests/fixtures/baseline_sample/`: `test_no_steps_outcome`, `test_unterminated_block`, `test_strategy_provenance`, `test_elapsed_one_second_grain`
<!-- finding, 6.1 - SPEC CORRECTED, not the code. This task and the delta spec's Baseline
     requirement both said `Curr  state:`. APE's block epilogue prints `Last`/`Curr`/`New` as
     a THREE-DEEP HISTORY, so `New` is this step's state and `Curr` is the previous one. On
     the pinned fixture `Curr  state:` is null on 8 of 50 blocks in the densest run and 8 of
     9 in another - activity coverage of 84 % and 11 % against the ~99.8 % the survey
     measured - while `New   state:` is non-null on 106 of 106 blocks. The module reads
     `New` and keeps `Curr` nowhere. Spec sentence and this task line reworded to match the
     artefact (session 4); the module docstring no longer describes itself as deviating from
     the spec, because it no longer does (P4). -->

- [x] 6.2 Create `analysis/baseline_droidbot.py`: skip to `start sending events, policy is …`; one record per `Action: <Type>(...)` with `step_index` synthesized and flagged; policy line as provenance; state from `Current state:` or `state=`; `activity` simple name unresolved, `None` counted in `activity_unknown_steps`; `clock=None` explicit; `truncated`, unparsed count; tests `test_clock_null`, `test_synth_ordinal_flag`, `test_activity_unknown_counted`, `test_orderly_stop_not_truncated`, `test_intent_killapp_no_widget`
- [x] 6.3 Add `test_baseline_frames_match_aperv_shape` (both parsers' frames carry the same columns as the `aperv` per-step frame with `null` where the signal does not exist) and `test_step_unit_named`
- [x] 6.4 Run `/rv-doc-code` on both parsers; run `/rv-test-run aperv-tool`
<!-- findings, Group 6 — the spec is wrong against the data in two places, both verified
     on the pinned baseline_sample:
     (a) "the fully-qualified activity and run-local state key from `Curr state:`" — on the
         fixture `Curr  state:` is NULL on 8 of 50 blocks in the densest run and 8 of 9 in
         another, which would put activity coverage at 84% and 11% against the ~99.8% the
         survey measured. APE prints a three-deep history: `New   state:` / `New  action:`
         are THIS step's state and the action its own `Select action ...` line chose, and
         `New   state:` is non-null on 106/106 fixture blocks. The parser reads `New` and
         keeps `Curr` nowhere. Plan §8.7 and the spec's Baseline requirement should say `New`.
     (b) "the most recent policy line as provenance" for droidbot — the `policy is <x>`
         announcement is printed ONCE, so it rides every row as `policy`; the per-action
         provenance is the policy logger's message immediately above the `Action:`, consumed
         ONCE. An IntentEvent dispatched with no line of its own gets decision_source=None
         rather than inheriting the previous event's reason (80 of 109 events on the densest
         run carry one). Inheriting would fabricate a decision that was never printed.
     Measured on the twelve fixture runs: ape 0/5/9/16/26/50 steps, 0 unparsed lines, all six
     truncated (no Monkey epilogue anywhere — matches 0 of 150), one NOT_RESPONDING hoisted at
     after_step=8, activity on 106/106 steps. droidbot 227 events over six runs, 0 unparsed,
     preamble 1467-1780 lines, one orderly stop (truncated=False), activity on 60.4% of events
     against the survey's ~58%. `state_key` is null on IntentEvent/KillAppEvent — a hole in the
     stream, asserted as such rather than filled. Boost columns are None for both baselines,
     never 0: a zero would assert a scorer ran. -->


## 7. P6 — Callers, coverage report, end-to-end smoke

- [x] 7.1 Create `analysis/callers/__init__.py`, `analysis/callers/rq_map.toml` (entry id → builder, estimator, parameters — the only place an entry id appears), `analysis/callers/coverage.py` listing entries with no caller; two example callers (one paired-binary, one count-GLM) driven by the toml; test `test_uncovered_entries_listed`
<!-- 7.1 as built: `Entry.parameter` raises FreezeItemUnset for ANY undeclared knob, not
     only the named freeze items - the catalogue supplies no defaults at all, which is
     INV-CAN-11 applied at the configuration boundary. TOML has no null, so a knob whose
     DECIDED value is "none" is the empty string, read back through `Entry.optional`;
     `offset_column = ""` says none out loud, omitting the key says nothing and raises.
     The four entries are grounded in the author's own recorded decisions
     (doutorado-tese/docs/estudo-03/rqs/, 2026-08-04), not invented: E01 paired-binary
     (alpha 0.025, whose exact-test power floor IS the pre-registered 7 discordant pairs),
     E15 count-GLM with the size offset, E19 the primary GLM, E14 declared and unwired.
     finding: E19 carries THREE knobs deliberately ABSENT - offset_column, reference_level,
     margin - because the author recorded them as still open ("STILL OPEN, do not fill",
     20260804_correcoes_rqs_e3.md). Filling them to make the entry runnable would decide
     them on the author's behalf. So E19 loads, reports as COVERED, and raises
     FreezeItemUnset if run; `test_an_open_freeze_item_stops_the_run` pins that as the
     intended behaviour so a later pass does not "fix" it by adding a plausible value.
     Coverage distinguishes `undeclared` (no caller yet - normal early state) from
     `unresolved` (the catalogue claims a caller that does not import - the urgent one);
     folding them together would hide a broken reference behind a routine gap.
     No new dependency: `tomllib` is stdlib at the declared requires-python >=3.12. -->

- [x] 7.2 Create `tests/test_smoke_two_apps.py`: loader → gates → corpus → outcomes → one estimator → emit over the two smoke applications of the cmp162 manifest, no device; asserts every envelope carries estimand, n, denominator, convention, exclusions
<!-- finding, 7.2 - THE SMOKE CAUGHT A REAL DEFECT ON ITS FIRST RUN, and it is the defect
     the task exists for: `gates.run_all(loader.load(...)[0], ...)` raised
     ValueError("the frame cannot be gated without its identity columns: ['repetition']").
     `gates._IDENTITY_COLUMNS` and `liveness.RunFacts.from_mapping` read `repetition`;
     `tasks_record`/`loader`/`outcomes`/`baseline_*` write and read `rep`. So Layer 0 could
     NEVER be composed with the gates on a real frame - and every gate test passed, because
     `test_gates.row()` hand-built its rows with the other spelling. Unit tests on both sides
     of a seam cannot see the seam.
     Resolved by seating the frame-column names once, in `run_identity.IDENTITY_COLUMNS`
     ("apk","arm","rep","timeout_s"), imported by `tasks_record` (was a literal) and by
     `gates` (was its own tuple); `liveness.from_mapping` now reads `rep`. `rep` wins on the
     artefact: it is the column of every consolidated CSV the campaign writes
     (`apk,rep,tool,...`) and of `summary.csv`. Three spellings of one fact remain, each
     correct in its own layer, and that is documented at the seat: `rep` = frame column,
     `repetition` = RunKey attribute AND the raw `tasks.json` config key (so
     `liveness.py:496` and `tasks_record.py:249` are CORRECT and must not be "fixed"), and
     the filename's second field. `clock_logcat_join.py:604` / `coverage_dump.py:518` say
     `repetition` in their CLI CSV headers - those are the frozen shipped readers
     (INV-APV-55), a different artefact, untouched.
     finding, 7.2 (b): `find_batches` on the campaign ROOT returns 10 batches, not 8 - the
     tree carries `results_smoke/` with two more. That is correct discovery, not a defect,
     but it means the root is a SUPERSET of what the fixture manifest pins. The smoke loads
     `campaign/results` so every count it asserts (1458 identities, 162 applications, batch
     count) is a manifest fact rather than whatever is on disk.
     The smoke asserts no result: with two applications the estimator is below its own power
     floor by construction, and the test pins that it SAYS so. Gate 3 reads `not-run` because
     the loader fills no `run_start` column and the fixture declares no digest - asserted as
     `not-run`, never a pass (INV-CAN-06). -->

- [x] 7.3 Create `tests/test_corrupted_fixture.py`: a temp copy of the two applications with one trace truncated to 864 bytes, one `summary.csv` removed and one malformed `tasks.json` record → the three exclusions listed by identity and reason in every envelope; no denominator shrinks silently
<!-- finding, 7.3 (a) - A SECOND COLUMN-NAME DEFECT of the same family as 7.2's, and this one
     did NOT raise. `liveness.RunFacts.from_mapping` read `task_state`; the loader's frame
     carries `state` (the tasks.json state) and reserves `perf_task_state` for
     performance.csv's. So on any real frame every run read as a null state, failed C1, and
     the WHOLE CAMPAIGN came back inadmissible with a perfectly plausible reason. It surfaced
     only because this test asserted which runs were excluded, not that some were. Fixed to
     `state`; documented at `from_mapping` beside the `rep` note, since both are the same
     mistake - a frame column and a dataclass attribute sharing a meaning are not thereby
     the same string.
     finding, 7.3 (b) - the loader resolved `trace_path` but never `trace_bytes`, so
     `liveness`'s trace-floor signal could not fire on a bare Layer-0 frame and gate 5 was
     decorative on every real campaign. The loader already stats those files to count them,
     so it now carries the size beside the path (None, never 0 - a zero would assert an empty
     file was measured). This is the fact that separates "produced nothing" from "produced
     nothing this reader looked at".
     finding, 7.3 (c) - the truncated trace is NOT a corpse and the test does not claim it is.
     `is_corpse` requires ALL THREE signals by deliberate design (each alone has a benign
     reading); truncating the artefact while the record still says COMPLETED with real
     coverage fires exactly `trace_below_floor` and the run stays admissible. Excluding it is
     therefore a CALLER POLICY, made explicitly in the test's own pipeline with the signal
     named in the reason - never dressed up as the library's verdict. A companion test
     asserts exactly one run fired the signal, so the assertion cannot pass vacuously (the
     first draft did: with defect (a) live, all 17 runs were inadmissible).
     Delivery of exclusions required a contract the callers did not have: `analysis/callers/
     basis.py` (one seat, used by both callers) takes `scope` and upstream `exclusions` and
     re-issues the estimator's envelope against the DECLARED basis. Without it `mcnemar_exact`
     reports a denominator of the pairs it happened to receive, so an application dropped
     upstream takes the denominator down with it and the fraction silently rises - INV-CAN-09
     exactly. The campaign total stays visible in `convention["corpus"]`.
     The copy excludes `*.trace.ndjson.gz` (gzip of its sibling, not a second stream) and
     `*.mop.json` (INV-CAN-24 made structural for this fixture rather than merely asserted);
     ~50 MB into tmp_path. The two smoke applications live in DIFFERENT batches (comp162_05
     and comp162_00), so removing one `summary.csv` removes the payload for exactly one of
     them - which is what makes the denominator shrink from 2 to 1 with a recorded reason.
     A final test re-hashes every pinned `results/**` file against the manifest to prove the
     campaign tree was not touched. -->

- [x] 7.4 Add `docs/analysis-layer.md` (P2 narrative: layers, the freeze-item rule, the fixture classes, how to run the smoke, the activity-visit unit and its measured rationale) and update `modules/aperv-tool/README.md`; run `/rv-docs-sync aperv-tool`
<!-- 7.4: every figure in the narrative is quoted from the fixture manifest's `measured_figures`
     or from the module docstring that owns it, never retyped from a handoff. The smoke section
     records why the smoke earns its place (it caught the two column-name defects of 7.2/7.3),
     which is the only claim in the document about the library's own history and is there
     because it is the argument for keeping the test. `/rv-docs-sync` is an rv-android project
     skill and is not registered in a session started from another repository; its content was
     read and applied by hand. -->


## 8. Verification and review

- [x] 8.1 Run `/rv-qa-lint-fix aperv-tool` (executed by hand: autoflake + isort + black over `src/` and `tests/`; 6 files reformatted, 102 clean)
- [x] 8.2 Run `/rv-verify aperv-tool` (tests + lint + types; the manifest-gated tests run, not skip, on this machine)
<!-- 8.2 result: **698 passed, 22 skipped in ~48 s** (649/22 at the session-3 handoff).
     The 22 skips are the pre-existing migration tier, which needs an `ape` checkout via
     $APE_REPO; NO cmp162-gated test skips - every one runs against the pinned tree on this
     machine, which is the acceptance condition. Lint clean per 2.12. -->
- [x] 8.3 Confirm `test_analysis_off_collection_path`, `test_no_rq_identifier`, `test_regex_declared_once`, `test_placement_exists_once` and `test_mop_json_never_opened` all pass; confirm `experimento-comp162{,-ajc}/scripts/admissibility.py` are UNCHANGED, and that `arm_label` has one seat
<!-- 8.3: 14 tests selected by those names plus the four new arm_label ones - all pass.
     The second half of this task was REWRITTEN, not satisfied: the campaign copies are
     confirmed byte-identical and untouched (both sha256 8fa95bd1...94a2, both absent from
     `git status`), which is the decision recorded on task 2.7. Turning them into imports
     would make `test_promoted_rule_matches_the_campaign_copy` compare liveness against
     itself. `arm_label` single seat confirmed by `test_arm_label_declared_once`. -->
- [x] 8.4 Invoke `/rv-code-reviewer` via Skill tool: "Review gh103-campaign-analysis-layer implementation"
<!-- 8.4: `/rv-code-reviewer` is an rv-android project skill and is not registered in a
     session opened from another repository; its SKILL.md and the mandatory metrics step were
     read and executed by hand - pyflakes + vulture (--min-confidence 80) + radon over
     `src/aperv_tool/analysis/`, then the P1-P4 review.
     vulture: nothing at confidence >= 80. radon: no new C-or-worse function from this
     change. pyflakes: one finding, `count_glm.py:164 log assigned but never used`.
     FOUR FINDINGS, all fixed in this pass:
     (1) `count_glm._fit_nb`'s `log = np.log` is NOT dead - patsy resolves a formula's
         function calls from that frame - but nothing exercised it, so a cleanup pass would
         delete it and silently break every formula transforming a covariate inline.
         `test_a_formula_may_call_log` now fits `count ~ {arm} + log(size)`. The line keeps
         its noqa; flake8 is silent, pyflakes does not read noqa.
     (2) `basis.merged_conventions` wrote its attrition summary under the key `exclusions`,
         colliding with the Envelope FIELD of that name - an emitted table would carry two
         columns called `exclusions` with different contents. Renamed to `attrition`.
     (3) `count_model` passed the offset array to statsmodels unchecked. A NaN offset raises
         NOWHERE: patsy never sees the offset so its dropped-rows check cannot catch it, and
         the fit emits a well-formed row of NaN rate ratios. Now refused, naming the rows
         (`test_a_non_finite_offset_is_refused_not_absorbed`). Same failure class the change
         exists to close.
     (4) `test_corrupted_fixture` imported ARM_TABLE/arm_manifest from `test_smoke_two_apps`
         - a test module importing another test module. Extracted to `tests/cmp162_arms.py`,
         the pattern `fixture_gate.py` and `baseline_runs.py` already follow here.
     After the fixes: 700 passed, 22 skipped; flake8 on analysis/ silent; black/isort clean
     over 103 files. -->
- [ ] 8.5 Check off the acceptance criteria in issue #103; commit with `closes #103` (or close via MCP if committed with `refs #103`)
<!-- 8.5 BLOCKED ON THE AUTHOR by the checkpoint rule: both halves are outward-facing writes
     (a commit, and an edit to a GitHub issue), and neither happens without an explicit OK.
     The 14 criteria were assessed locally against the code. Twelve are met as written.
     THREE are met differently from how the issue words them, and the issue text - not the
     implementation - is what is wrong in each case:
     - criterion 2 says `runspec.py` exposes the 13 RUN_START members. They live in
       `trace_ndjson.RunStart` (task 2.2), which is the sanctioned reader the criterion's own
       problem statement names; `runspec` consumes them for attribution.
       Second half of the criterion, `check_run_start.py`'s reason to exist outside the
       package: VERIFIED, and it splits in two. The file is
       `workspace-rv/rvsec-calibracao/scripts/check_run_start.py` (a SIBLING of `rvsec/`, not
       inside it - an earlier note in this file put it one directory level off and called it
       absent; that was wrong). The CAPABILITY GAP that forced it is closed: the package now
       exposes all 13 members and gates `v`. The SCRIPT itself was not migrated - it still
       carries its own `extract_run_start` at :73 and imports no `aperv_tool`. Migrating it is
       work in a different repository and outside this change's boundary, so the criterion is
       met as written ("the reason ... is gone") and NOT met as it might be read ("the script
       now imports the package"). The author decides which reading closes the box.
     - criterion 4 says '28 recovered retries'. Measured: 22 recovered retry records across
       21 identities; 28 is 1486 records - 1458 identities, i.e. SUPERSEDED records, a
       different quantity. Recorded on task 1.2 and asserted against the manifest.
     - criterion 5 says outcomes reproduces `per_apk_paired.csv` exactly. It cannot: that file
       rounds each per-application mean to 4 decimals and the rounding MANUFACTURES TIES (22
       of 195 fields disagree; `cov_mop` gains 2 ties, W 3896.0 -> 3793.0). All 15 rows
       reproduce field for field from `consolidado/per_rep.csv`, which is what the campaign's
       own `consolidate.py:150-176` used. The input was corrected, not the estimator.
     - criterion 8 (`censo_substrato.csv`) is met in the scoped form recorded on task 4.x:
       9 of its 11 columns come through `derive_mop_artifact.derive()`, collection-path code
       the analysis layer deliberately does not import. The parity test covers the two
       artefact-owned columns plus membership and line count, and says so. -->
