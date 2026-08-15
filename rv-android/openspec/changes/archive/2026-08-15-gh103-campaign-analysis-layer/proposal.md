# Campaign analysis layer: run model, validity gates, outcomes, estimators, step bundles, activity-visits and baseline parsers

GitHub Issue: #103

## Why

Every campaign analysed in this repository has re-derived its analysis code under time pressure — the run-identity regex is copied verbatim in two shipped readers, `stats_utils.py` and `multiarm_stats.py` are byte-duplicated across campaign directories, the campaign consolidator exists in five copies, the identity-keyed task dedup was reimplemented twice, and the exact McNemar the E3 pre-registration declares as its primary estimator exists nowhere. The final E3 campaign (`ape` and one `droidbot` variant against three `aperv` variants, 1800 s, one replica per (APK, arm)) needs a generic, offline analysis layer that already exists when its output lands, so numbers carry their denominators, estimands and exclusions by construction rather than by memory.

The design authority is the plan `doutorado-tese/docs/estudo-03/analise/20260815_plano_scripts_analise.md` (module map §4, validity gates §5, reuse map §6, fixtures §7, baseline parsers §8, phasing §9, open items §10) and its companion `20260815_segmentacao_visitas_tela.md` (the activity-visit unit, measured on cmp162). This proposal does not restate them; it binds their decisions to specs, tests and tasks in the repository where the code and its invariants live (plan O5).

## What Changes

- **New subpackage layout under `modules/aperv-tool/src/aperv_tool/analysis/`**, beside the three shipped readers (`trace_ndjson.py`, `coverage_dump.py`, `clock_logcat_join.py`), organised in the plan's five layers:
  - Layer 0 — run model and corpus scoping: `run_identity.py` (single seat of the `<apk>.apk__<rep>__<timeout>__<arm>` regex, arm decomposition driven by a data table), `runspec.py` (all 13 `RUN_START` members, `v` checked — closes findings F1/F2), `loader.py`, `liveness.py` (promotion of `experimento-comp162/scripts/admissibility.py`), `gates.py` (the five validity gates, per-arm evidence form, `not-run` reported), `corpus.py`, `clones.py`.
  - Layer 1 — outcome builders: `outcomes.py` (dedup key, replica rule, estimand, censoring, capture curve, window — every convention a parameter) and `screen_visits.py` (activity-visit segmentation with `state_trail`, revisits separate, `form_episodes()` derived).
  - Layer 2 — estimators under `analysis/estimators/`: `paired_binary.py` (exact McNemar), `paired_continuous.py` (exact/approximate Wilcoxon contract, trimmed-mean difference with the paired median beside it), `count_glm.py` (E2's `_glm_fit_nb` verbatim, generalised; `offset=` required, no default), `multiplicity.py` (Holm + FDR, family declared by the caller), `decision.py` (margin supplied by the caller, no default), `resampling.py` (extracted `paired_bootstrap_ci` + permutation harness), `variance.py` (ICC that reports why it degenerates), `capacity.py` (outcome-specific power floor), `multiarm.py` (extracted Friedman + Holm + rank-biserial).
  - Layer 3 — stream readers: `step_bundle.py` (one record per step with `RVSEC`, `RVSEC-COV` and diagnostic events placed by the heartbeat — the step-centric inverse of the existing violation-centric join), `state_coverage_join.py` (per-state `UICOV` payload onto the step timeline by `STATE.key`, intra-run only), `violations.py`, `monitored_ops.py`, `static_artifact.py` (never reads `*.mop.json`, INV-ANA-53), `tasks_record.py` (identity-keyed dedup, never `task_id`), `baseline_ape.py`, `baseline_droidbot.py` (extract only what is certain, plan §8.6).
  - Layer 4 — `envelope.py`, `emit.py`, `provenance.py`.
  - `callers/` + `rq_map.toml` — the only place a research-question identifier may appear.
- **`trace_ndjson.RunStart` exposes all 13 `RUN_START` members and the reader checks `v`** (findings F1/F2 of the plan §3.2–3.3). **BREAKING** for `RunStart`'s field set: `t0_ms` and `params` stay; `v`, `seed`, `agent`, `preset`, `features`, `inert`, `corpus_basis`, `digest`, `props_digest`, `build` are added; no consumer in this repository reads a field that is removed, because none is removed.
- **`clock_logcat_join`'s heartbeat placement becomes tag-parametric** and is reused by `step_bundle` for `RVSEC-COV` and the diagnostic tags; the violation-centric `RunJoin` output and its scenarios are unchanged.
- **`statsmodels` is declared** as a dependency of `aperv-tool` (plan D2, O1 — compatibility with Python 3.14 / numpy 2.4.2 / pandas 3.0.0 / scipy 1.17.0 measured on 2026-08-15; declaration still owed). `pandas`, `numpy`, `scipy` are declared explicitly on `aperv-tool` rather than inherited transitively.
- **Two fixture classes are pinned:** FIXTURE-REAL — cmp162 (`experimento-comp162/results`, 1458 identities) by a path+sha256 manifest, plus a hashed sample of `ape` and `droidbot` logcats/traces from the E2 raw corpus for the baseline parsers; FIXTURE-SYNTH — generated frames with known answers for every estimator, including the degenerate cases.
- **Duplication absorbed, not repeated:** the two copies of the run-identity regex become imports; `experimento-comp162{,-ajc}/scripts/admissibility.py` become imports of `liveness.py` (plan O2 — author decision recorded in this proposal as *promote*); `stats_utils.py` / `multiarm_stats.py` are extracted once. The frozen legacy-corpus readers named by INV-APV-55 are not touched.
- **No research-question identifier** appears in any module, function, column or flag under `analysis/`; enforced by a test.

## Capabilities

### New Capabilities

- `campaign-analysis`: the offline, read-only, campaign-level analysis library of `aperv_tool.analysis` — run identity and provenance, admissibility and validity gates, corpus scoping, outcome builders (including activity-visits), estimators with result envelopes, step bundles and stream readers, baseline parsers, fixtures and the caller layer. Invariants `INV-CAN-nn`.

### Modified Capabilities

- `aperv`: **Native NDJSON Trace Reader** — `RunStart` carries the full `RUN_START` record and the reader checks the `v` schema gate (MODIFIED, full block carried). **Offline Clock-to-Violation Join** — unchanged in behaviour; a new ADDED requirement in the same delta records the tag-parametric placement that `step_bundle` reuses, rather than modifying the join's requirement.

## Impact

- **Modules:** `aperv-tool` (all new code; `trace_ndjson.py` and `clock_logcat_join.py` modified; `pyproject.toml` gains `statsmodels`, `pandas`, `numpy`, `scipy`); `experimento-comp162/scripts/admissibility.py` and `experimento-comp162-ajc/scripts/admissibility.py` replaced by imports (the byte-identity contract between them is preserved trivially — both become the same import); `experimento-cal/scripts/stats_utils.py` and `experimento-rearch-aperv/scripts/*` are read for extraction and left in place (INV-APV-55 covers `experimento-cal/scripts/*`).
- **Not touched:** `tools/aperv/tool.py` and the whole collection path (INV-APV-48 extended to the entire `analysis/` package by test); `*.mop.json` artefacts (INV-ANA-53); the frozen legacy readers (INV-APV-55); the `ape` repository (the wire format is its authority — findings F3–F6 of the plan are reported to it, not fixed here); any device, emulator or `adb` (INV-APV-35).
- **PRD:** FR11 (logcat parsing), FR12 (coverage), FR13 (violations), FR14 (result generation), FR20 (variants as data), NFR03 (testability — two fixture classes), NFR06 (observability — envelopes and provenance), NFR08 (reproducibility — pinned fixtures, parity tests, hashed inputs).
- **Cross-repository:** the thesis repository consumes emitted tables, never this code; E2's reference implementation in `ase-journal/data-analysis/rvsec/rq1_jca.py` is read for extraction and cross-checked in its own pinned environment (plan O3), never edited.
- **Deliberately unfilled (pre-registration freeze items, plan §10):** the margin, the primary `aperv` variant, the corpus, the GLM specification and reference level, E46's subset, E51's TOST margin, whether E05 is discarded. The code refuses to guess them: each is a required argument with no default.
