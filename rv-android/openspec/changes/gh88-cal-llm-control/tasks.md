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

- [ ] 1.1 Add `LLM_ARM_KEYS` frozenset to `modules/aperv-tool/src/aperv_tool/tools/aperv/tool.py` (the 11 Phase-A LLM keys per INV-APV-26; comment stating why `llm_max_tokens`/`llm_snap_tolerance_px` stay out until the Phase-B jar)
- [ ] 1.2 Add `llm_max_tokens` → `ape.llmMaxTokens` and `llm_snap_tolerance_px` → `ape.llmSnapTolerancePx` to `APERV_PROPERTY_MAPPING` (INV-APV-27)
- [ ] 1.3 Add the 9 `cal_a1`…`cal_a9` variants to `get_variants()` as explicit dict literals on the `sata_mop_act_frontier` substrate (frontier flags ON: `mop_activity_source_components=true`, `frontier_boost_weight=200`, `mop_frontier_weight=200`, `activity_trigger_enabled=true`) plus the LLM keys per the delta-spec arm table (`cal_a1` = cmp_llm LLM-key config on the frontier substrate)
- [ ] 1.4 Add guard test `test_cal_variants_declare_all_llm_keys` (every `cal_*` variant ⊇ `LLM_ARM_KEYS`, failure names variant + missing keys) to `modules/aperv-tool/tests/test_aperv_tool.py::TestArmVariants`
- [ ] 1.5 Add `test_cal_arms_match_plan_table` (concrete value assertions for all 9 arms incl. the frontier substrate values in every `cal_*` arm, the cal_a5/cal_a6 isolation and cal_a3 stagnation-only scenarios) and `test_property_mapping_covers_llm_max_tokens_and_snap` (mappings present; no `cal_a*` arm sets either key)
- [ ] 1.6 Run `/rv-test-run aperv-tool` (CI flags: `--import-mode=importlib -o "addopts="`)

## 2. Scaffold foundation: phase config, generator (CONFIG-GEN)

- [ ] 2.1 Create `experimento-cal/` skeleton: `scripts/`, `phases/`, `templates/`, `tests/` (+ `tests/fixtures/`)
- [ ] 2.2 Write `experimento-cal/phases/cala.json` from plan §6: 11 arms (`ape:default` + `aperv:sata_mop_act_frontier` + `aperv:cal_a1..a9`), subset file path (`calibracao/subset40.txt`, may not exist yet), reps=2, timeout=300, containers=8, smoke arms (`cal_a1`,`cal_a3`,`cal_a8`) with 4 APKs/90s/1 rep, bootstrap seed
- [ ] 2.3 Implement `experimento-cal/scripts/gen_iteration.py`: arm resolution from `get_variants()`, expected config-ack fields via `APERV_PROPERTY_MAPPING`, artifact snapshot + sha256, `git describe --dirty` capture, manifest, run/smoke composes (shared sglang, 8 containers, arm rotation `i mod n_arms`, image tag pinned in the compose with the resolved ID recorded in the manifest for preflight `docker inspect` verification, `:ro` mounts from `iterN/artifacts/`), per-container filters, refuse existing `iterN/` (exit 2)
- [ ] 2.4 Add unit tests: `test_manifest_resolves_from_get_variants`, `test_snapshot_hashes_recorded`, `test_compose_rotation_and_filters`, `test_refuses_existing_iter` in `experimento-cal/tests/test_gen_iteration.py` (fixture subset file; dummy jar for `--jar` path)
- [ ] 2.5 Run `/rv-doc-code experimento-cal/scripts/gen_iteration.py`

## 3. Verifier gates: preflight (PRE-FLIGHT) and smoke (SMOKE)

- [ ] 3.1 Implement `experimento-cal/scripts/preflight.py` with independent parsing (no import of `gen_iteration.py`): manifest×`get_variants()` field equality, manifest×compose env/mounts/image audit, identity dry-run (≥11 distinct `(tool,variant)`; total = arms×|subset|×reps), artifact hash re-verification, sglang service check; per-check PASS/FAIL report, exit 1 on any FAIL
- [ ] 3.2 Implement `experimento-cal/scripts/smoke_check.py`: per smoke task, `[APE-LLM-CONFIG]` field-by-field vs manifest, `[APE-LLM-CONFIG-ACK] server_model`, identity COMPLETED + cov>0, 0 VerifyError; exit 1 on mismatch
- [ ] 3.3 Add tests: `test_preflight_detects_mismatch` (tampered compose fixture), `test_identity_dryrun_counts`, `test_preflight_import_independence` (import-graph assertion per INV-CAL-04), `test_smoke_config_ack_field_by_field` (fixture traces incl. one deliberate mismatch)
- [ ] 3.4 Run `/rv-doc-code experimento-cal/scripts/preflight.py`

## 4. Run monitoring (RUN+MONITOR)

- [ ] 4.1 Implement `experimento-cal/scripts/monitor.sh` (derive from `experimento-20260721/scripts/monitor.sh`): identity-distinct progress per container from result trees, restart ONLY exit-137 containers, report (never restart) other exits/stalls, resume-pass instructions, completion check = identity-distinct non-empty logcats (INV-CAL-06/07)
- [ ] 4.2 Dry-run `monitor.sh` against a fixture results tree (no docker): progress counting and completion detection verified; document the manual/live checks it cannot cover in the script header

## 5. Consolidation (CONSOLIDATE) and independent verification (VERIFY)

- [ ] 5.1 Implement `experimento-cal/scripts/consolidate_cal.py`: N-arm consolidation from raw logcats dedup by identity → `per_apk_paired.csv` (one row/APK, column group/arm, reps averaged) + `tel_proxies.csv` from `.trace` files (d90c1f4 grammar reuse permitted)
- [ ] 5.2 Implement `experimento-cal/scripts/verify_iteration.py` with independent re-derivation (no import of `consolidate_cal.py`/`consolidate_compare.py`/`analyze_cmpv2_llm.py`): direct `RVSEC-COV`/`RVSEC` and config-ack extraction, all INV-CAL-09 numeric gates, seeded ≥10-task hand-count sample table, verdict `admissible`/`quarantine` with justification
- [ ] 5.3 Add tests on a synthetic 2-arm × 2-APK fixture tree (crafted logcats/traces/tasks.json incl. a duplicate identity, a missing-arm APK, and a divergent count): `test_consolidate_dedup_and_pairing`, `test_verify_gates_on_fixtures`, `test_verify_import_independence`
- [ ] 5.4 Run `/rv-doc-code experimento-cal/scripts/verify_iteration.py`

## 6. Analysis (ANALYZE) and statistics

- [ ] 6.1 Vendor `experimento-cal/scripts/stats_utils.py` (copy verbatim from `rvsec-calibracao/scripts/stats_utils.py` with a provenance header; pull any extra `power_analysis.py` primitive on demand) and implement `experimento-cal/scripts/multiarm_stats.py` importing it **locally** (no env var, no `sys.path`, no sibling-repo path): trimmed-mean 10% + raw mean, paired bootstrap B≥10,000 fixed-seed CIs vs ANC1/ANC2, rank-biserial, Friedman+Holm (descriptive) for N arms
- [ ] 6.2 Implement `experimento-cal/scripts/analyze_iteration.py`: `analysis.md` with the four gates in pre-declared order (proxy elimination → bootstrap ranking with raw-mean alongside → mechanistic prediction-vs-observed with CI95 flag, temperature arms descriptive-only → between-reps identical-trace determinism <30% target)
- [ ] 6.3 Add tests: `test_multiarm_stats_selftest` (known-answer mini dataset; both estimators reported), `test_analyze_gate_order_and_prediction_section` (fixture CSVs)
- [ ] 6.4 Run `/rv-doc-code experimento-cal/scripts/analyze_iteration.py`

## 7. Decision template, journal, operating procedure

- [ ] 7.1 Write `experimento-cal/templates/decision.md`: declarative per-phase rules (screening promotes top 2–3 passing all gates, never concludes by p-value; confirmation applies pre-registered GO/NO-GO/INCONCLUSIVE and stops), next-iteration config section
- [ ] 7.2 Implement `experimento-cal/scripts/journal.py append` (one JSON line `{ts, iter, state, artifact, sha256}` to `calibracao/journal.jsonl`, append-only, creates `calibracao/` on first use) + `test_journal_append_schema`
- [ ] 7.3 Write `experimento-cal/README.md`: the operating procedure — state machine walk-through per iteration, script per state, agent-driven transitions, human gates G1–G4, the never-list (no emulator management, no mid-run config change, no `ape` repo edits, no `backup/`, no `@override` arms)

## 8. Integration & Verification

- [ ] 8.1 Integration dry-run: `gen_iteration.py --phase phases/cala.json --iter 0` with a fixture subset (real `get_variants()`) → `preflight.py` PASS with 11 distinct identities; then delete `iter0/` (test artifact, not provenance)
- [ ] 8.2 Run full scaffold test suite: `uv run pytest experimento-cal/tests --import-mode=importlib -o "addopts="`
- [ ] 8.3 Run `/rv-qa-lint-fix aperv-tool`
- [ ] 8.4 Run `/rv-verify aperv-tool`
- [ ] 8.5 Invoke `/rv-code-reviewer` via Skill tool ("Review gh88-cal-llm-control implementation")
- [ ] 8.6 Grep for dangling references / P3 check (no dead code, no unused fixtures); confirm nothing under `backup/` was touched
- [ ] 8.7 Run `/rv-docs-sync aperv-tool` (CLAUDE.md of aperv-tool mentions variant tiers; root CLAUDE.md unaffected)
