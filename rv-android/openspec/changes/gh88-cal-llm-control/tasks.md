# Tasks: gh88-cal-llm-control

**GitHub Issue**: #88 (commits use `refs #88`; final commit `closes #88`)

<!-- Subagent dispatch hints:
     - Group 1 (aperv-tool arms + guard) must complete first — Group 2's generator resolves arms from get_variants().
     - Groups 3, 4, 5 are independent of each other after Group 2 (preflight/smoke, monitor, consolidate/verify).
     - Group 6 (analyze/stats) is independent of Groups 3-5 (consumes CSV fixtures), can run in parallel after Group 2.
     - Group 7 (journal/templates/README) is independent, can run any time after Group 2.
     - Group 8 integrates and verifies — must run after all other groups.
     - Critical path: 1 -> 2 -> 8. -->

## 1. aperv-tool: calibration arms, guard, mappings (R1)

- [x] 1.1 Add `LLM_ARM_KEYS` frozenset to `modules/aperv-tool/src/aperv_tool/tools/aperv/tool.py` (the 11 Phase-A LLM keys per INV-APV-26; comment stating why `llm_max_tokens`/`llm_snap_tolerance_px` stay out until the Phase-B jar)
- [x] 1.2 Add `llm_max_tokens` → `ape.llmMaxTokens` and `llm_snap_tolerance_px` → `ape.llmSnapTolerancePx` to `APERV_PROPERTY_MAPPING` (INV-APV-27)
- [x] 1.3 Add the 9 `cal_a1`…`cal_a9` variants to `get_variants()` as explicit dict literals on the `sata_mop_act_frontier` substrate (frontier flags ON: `mop_activity_source_components=true`, `frontier_boost_weight=200`, `mop_frontier_weight=200`, `activity_trigger_enabled=true`) plus the LLM keys per the delta-spec arm table (`cal_a1` = cmp_llm LLM-key config on the frontier substrate)
- [x] 1.4 Add guard test `test_cal_variants_declare_all_llm_keys` (every `cal_*` variant ⊇ `LLM_ARM_KEYS`, failure names variant + missing keys) to `modules/aperv-tool/tests/test_aperv_tool.py::TestArmVariants`
- [x] 1.5 Add `test_cal_arms_match_plan_table` (concrete value assertions for all 9 arms incl. the frontier substrate values in every `cal_*` arm, the cal_a5/cal_a6 isolation and cal_a3 stagnation-only scenarios) and `test_property_mapping_covers_llm_max_tokens_and_snap` (mappings present; no `cal_a*` arm sets either key)
- [x] 1.6 Run `/rv-test-run aperv-tool` (CI flags: `--import-mode=importlib -o "addopts="`)

## 2. Scaffold foundation: phase config, generator (CONFIG-GEN)

- [x] 2.1 Create `experimento-cal/` skeleton: `scripts/`, `phases/`, `templates/`, `tests/` (+ `tests/fixtures/`)
- [x] 2.2 Write `experimento-cal/phases/cala.json` from plan §6: 11 arms (`ape:default` + `aperv:sata_mop_act_frontier` + `aperv:cal_a1..a9`), subset file path (`calibracao/subset40.txt`, may not exist yet), reps=2, timeout=300, containers=8, smoke arms (`cal_a1`,`cal_a3`,`cal_a8`) with 4 APKs/90s/1 rep, bootstrap seed
- [x] 2.3 Implement `experimento-cal/scripts/gen_iteration.py`: arm resolution from `get_variants()`, expected config-ack fields via `APERV_PROPERTY_MAPPING`, artifact snapshot + sha256, `git describe --dirty` capture, manifest, run/smoke composes (shared sglang, 8 containers, arm rotation `i mod n_arms`, image tag pinned in the compose with the resolved ID recorded in the manifest for preflight `docker inspect` verification, `:ro` mounts from `iterN/artifacts/`), per-container filters, refuse existing `iterN/` (exit 2)
- [x] 2.4 Add unit tests: `test_manifest_resolves_from_get_variants`, `test_snapshot_hashes_recorded`, `test_compose_rotation_and_filters`, `test_refuses_existing_iter` in `experimento-cal/tests/test_gen_iteration.py` (fixture subset file; dummy jar for `--jar` path)
- [x] 2.5 Run `/rv-doc-code experimento-cal/scripts/gen_iteration.py`

## 3. Verifier gates: preflight (PRE-FLIGHT) and smoke (SMOKE)

- [x] 3.1 Implement `experimento-cal/scripts/preflight.py` with independent parsing (no import of `gen_iteration.py`): manifest×`get_variants()` field equality, manifest×compose env/mounts/image audit, identity dry-run (≥11 distinct `(tool,variant)`; total = arms×|subset|×reps), artifact hash re-verification, sglang service check; per-check PASS/FAIL report, exit 1 on any FAIL
- [x] 3.2 Implement `experimento-cal/scripts/smoke_check.py`: per smoke task, `[APE-LLM-CONFIG]` field-by-field vs manifest, `[APE-LLM-CONFIG-ACK] server_model`, identity COMPLETED + cov>0, 0 VerifyError; exit 1 on mismatch
- [x] 3.3 Add tests: `test_preflight_detects_mismatch` (tampered compose fixture), `test_identity_dryrun_counts`, `test_preflight_import_independence` (import-graph assertion per INV-CAL-04), `test_smoke_config_ack_field_by_field` (fixture traces incl. one deliberate mismatch)
- [x] 3.4 Run `/rv-doc-code experimento-cal/scripts/preflight.py`

## 4. Run monitoring (RUN+MONITOR)

- [x] 4.1 Implement `experimento-cal/scripts/monitor.sh` (derive from `experimento-20260721/scripts/monitor.sh`): identity-distinct progress per container from result trees, restart ONLY exit-137 containers, report (never restart) other exits/stalls, resume-pass instructions, completion check = identity-distinct non-empty logcats (INV-CAL-06/07)
- [x] 4.2 Dry-run `monitor.sh` against a fixture results tree (no docker): progress counting and completion detection verified; document the manual/live checks it cannot cover in the script header

## 5. Consolidation (CONSOLIDATE) and independent verification (VERIFY)

- [x] 5.1 Implement `experimento-cal/scripts/consolidate_cal.py`: N-arm consolidation from raw logcats dedup by identity → `per_apk_paired.csv` (one row/APK, column group/arm, reps averaged) + `tel_proxies.csv` from `.trace` files (d90c1f4 grammar reuse permitted)
- [x] 5.2 Implement `experimento-cal/scripts/verify_iteration.py` with independent re-derivation (no import of `consolidate_cal.py`/`consolidate_compare.py`/`analyze_cmpv2_llm.py`): direct `RVSEC-COV`/`RVSEC` and config-ack extraction, all INV-CAL-09 numeric gates, seeded ≥10-task hand-count sample table, verdict `admissible`/`quarantine` with justification
- [x] 5.3 Add tests on a synthetic 2-arm × 2-APK fixture tree (crafted logcats/traces/tasks.json incl. a duplicate identity, a missing-arm APK, and a divergent count): `test_consolidate_dedup_and_pairing`, `test_verify_gates_on_fixtures`, `test_verify_import_independence`
- [x] 5.4 Run `/rv-doc-code experimento-cal/scripts/verify_iteration.py`

## 6. Analysis (ANALYZE) and statistics

- [x] 6.1 Vendor `experimento-cal/scripts/stats_utils.py` (copy verbatim from `rvsec-calibracao/scripts/stats_utils.py` with a provenance header; pull any extra `power_analysis.py` primitive on demand) and implement `experimento-cal/scripts/multiarm_stats.py` importing it **locally** (no env var, no `sys.path`, no sibling-repo path): trimmed-mean 10% + raw mean, paired bootstrap B≥10,000 fixed-seed CIs vs ANC1/ANC2, rank-biserial, Friedman+Holm (descriptive) for N arms
- [x] 6.2 Implement `experimento-cal/scripts/analyze_iteration.py`: `analysis.md` with the four gates in pre-declared order (proxy elimination → bootstrap ranking with raw-mean alongside → mechanistic prediction-vs-observed with CI95 flag, temperature arms descriptive-only → between-reps identical-trace determinism <30% target)
- [x] 6.3 Add tests: `test_multiarm_stats_selftest` (known-answer mini dataset; both estimators reported), `test_analyze_gate_order_and_prediction_section` (fixture CSVs)
- [x] 6.4 Run `/rv-doc-code experimento-cal/scripts/analyze_iteration.py`

## 7. Decision template, journal, operating procedure

- [x] 7.1 Write `experimento-cal/templates/decision.md`: declarative per-phase rules (screening promotes top 2–3 passing all gates, never concludes by p-value; confirmation applies pre-registered GO/NO-GO/INCONCLUSIVE and stops), next-iteration config section
- [x] 7.2 Implement `experimento-cal/scripts/journal.py append` (one JSON line `{ts, iter, state, artifact, sha256}` to `calibracao/journal.jsonl`, append-only, creates `calibracao/` on first use) + `test_journal_append_schema`
- [x] 7.3 Write `experimento-cal/README.md`: the operating procedure — state machine walk-through per iteration, script per state, agent-driven transitions, human gates G1–G4, the never-list (no emulator management, no mid-run config change, no `ape` repo edits, no `backup/`, no `@override` arms)

## 8. Integration & Verification

- [x] 8.1 Integration dry-run: `gen_iteration.py --phase phases/cala.json --iter 0` with a fixture subset (real `get_variants()`) → `preflight.py` PASS with 11 distinct identities; then delete `iter0/` (test artifact, not provenance)
- [x] 8.2 Run full scaffold test suite: `uv run pytest experimento-cal/tests --import-mode=importlib -o "addopts="`
- [x] 8.3 Run `/rv-qa-lint-fix aperv-tool`
- [x] 8.4 Run `/rv-verify aperv-tool`
- [x] 8.5 Invoke `/rv-code-reviewer` via Skill tool ("Review gh88-cal-llm-control implementation")
- [x] 8.6 Grep for dangling references / P3 check (no dead code, no unused fixtures); confirm nothing under `backup/` was touched
- [x] 8.7 Run `/rv-docs-sync aperv-tool` (CLAUDE.md of aperv-tool mentions variant tiers; root CLAUDE.md unaffected)
- [x] 8.8 Address code-review warning: extract `verify_iteration.py::verify()` five gates into helpers (`_gate_config`/`_gate_collisions`/`_gate_pairing`/`_gate_latency`/`_gate_divergence`), leaving `verify()` a thin orchestrator (CC 65 → per-gate); tests stay green

## 9. Campaign status tracking (acompanhamento)

- [x] 9.1 Implement `experimento-cal/scripts/status.py`: DERIVE the campaign position from `calibracao/journal.jsonl` + `iterN/` artifacts + `phases/*.json` (never a hand-maintained file, INV-CAL-14); per-iteration 8-state loop marked done/current/pending (done = journal transition corroborated by the state's expected artifact; journal↔artifact inconsistency flagged), pending human gate G1–G4, next action (script to run), cross-iteration summary (phase, DECIDE verdict, promoted arms); read-only
- [x] 9.2 Add `experimento-cal/tests/test_status.py`: fixture journal + `iter*/` dirs asserting current-state/next-action/gate derivation and the journal↔artifact inconsistency flag
- [x] 9.3 Update `experimento-cal/README.md` "The loop" with the `status.py` acompanhamento step (how a session answers "where are we / what's next" without reconstructing by hand)

<!-- Groups 1-9 above = scaffold + arms (the deterministic tooling; all committed in 92592419).
     Groups 10-13 below = the calibration campaign itself, tracked as milestone tasks. gh88 closes
     (closes #88 + archive) only when Group 13 completes. Per-iteration loop state (CONFIG-GEN...DECIDE)
     is DERIVED by status.py from calibracao/journal.jsonl (INV-CAL-14) — these tasks track phase
     milestones and the human gates G1-G4, never the loop states (a hand-maintained loop status drifts). -->

## 10. Fase 0 — offline campaign inputs (methodology P1–P4)

- [x] 10.1 P1 (Fase 0.3) — spec harmonization + selftest (done; methodology §P1, GATE selftest 100%)
- [x] 10.2 P2 (Fase 0.4) — power analysis: MDEs per metric/n, Fase C n=80–100, SESOI 2.0pp pre-registered in plan §5-0.4 (done 2026-07-21; pre-registration GATE met)
- [x] 10.3 P3 (Fase 0.1) — produce `calibracao/subset40.txt` (+ `calibracao/subset90.txt` for Fase C), generated `filters/`, representativeness memo (means, KS, strata); stratify on `ape__cov_mop` quantiles + mop_unique>0 fraction (~70%) + LLM proxy, greedy optimization, leave-10-out stability check. GATE: |Δmean| ≤ 1.0pp on target metrics, KS n.s., `.apk`+`.apk.json` present for all. **Unblocks `gen_iteration.py` (hard-fails until `subset40.txt` lands).**
- [x] 10.4 P4 (Fase 0.2) — produce `calibracao/nomatch_decomposition.md` (no-match causal decomposition; sizes H4, fixes the snapping-tolerance candidate for the `ape`-side J1). GATE: ≥90% of calls classified unambiguously. Feeds J1 (`ape` repo, gate G2 — external to gh88).

## 11. Phase A campaign — `cala` (methodology P7)

<!-- Loop CONFIG-GEN→PRE-FLIGHT→SMOKE→RUN+MONITOR→CONSOLIDATE→VERIFY→ANALYZE→DECIDE runs via the
     scaffold scripts; status.py derives per-iteration progress. These tasks = the phase milestone + G3. -->

- [ ] 11.1 G3 — human launch approval for the Phase-A run (agent prepares `gen_iteration` → `preflight` PASS → smoke PASS and requests go; GPU + emulator only after explicit go-ahead)
- [ ] 11.2 Execute Phase A through DECIDE → `calibracao/cala_decision.md`: bootstrap-CI ranking vs ANC1/ANC2, gates applied (proxy → ranking → prediction-vs-observed → determinism), 2–3 survivors promoted, Phase-B hypotheses/predictions **pre-registered** (screening SELECTS, never concludes by p-value)
- [ ] 11.3 VERIFY verdict `admissible` + journal complete for the Phase-A iteration(s) (independent re-derivation gates pass; provenance recorded in `calibracao/journal.jsonl`)

## 12. Phase B campaign — `calb` (methodology P9)

<!-- Depends on the ape-side J1–J4 jar (P8, gate G2 — tracked in the `ape` repo, external to gh88).
     Phase B bind-mounts the audited ape-rv.jar from iterN/artifacts/ onto the same 0.9.3 image. -->

- [ ] 12.1 Define `cal_b*` arms in `get_variants()` from the Phase-A survivors (same `LLM_ARM_KEYS` guard, same `sata_mop_act_frontier` substrate); extend the aperv delta-spec calibration tier + guard tests in the same commit
- [ ] 12.2 G3 — human launch approval for the Phase-B run (jar sha256 recorded in the iteration manifest; diff bytecode-audited per the cmp_llm standard)
- [ ] 12.3 Execute Phase B through DECIDE → `calibracao/calb_decision.md`: final candidate config + Phase-C **pre-registration**
- [ ] 12.4 (optional) P10 micro-Optuna (R3) — only if P10 is approved; a separate change `gh<N>-cal-optuna-micro`, external to gh88

## 13. Phase C campaign — `calc` confirmation (methodology P11) + close-out

- [ ] 13.1 G3 — human launch approval for the Phase-C confirmation run (n=80–100, `subset90.txt`, pre-registered one-sided tests, SESOI 2.0pp)
- [ ] 13.2 Execute Phase C through DECIDE → `calibracao/calc_decision.md`: GO / NO-GO / INCONCLUSIVE verdict (confirmation APPLIES the pre-registered criteria and STOPS)
- [ ] 13.3 G4 — human ratification of the final verdict and the final-experiment (181-APK) config
- [ ] 13.4 Close-out: final commit `closes #88`; archive the change via `/opsx:archive`
