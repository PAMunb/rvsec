<!-- Ordering is the point of this list, not a convenience.
     Group 1 captures leg A's provenance and MUST complete before anything else — the baseline image
     ID is destroyed by a `docker prune` and is unrecoverable afterwards.
     Group 5 (the freeze) MUST complete before Group 6 (the jar and image) and Group 8 (the campaign).
     Nothing after the freeze may edit the pre-registration; an unplanned analysis is exploratory
     by definition and is reported as such.
     Groups 2, 3 and 4 are independent of each other and may run in any order after Group 1.
     Critical path: 1 -> 4 -> 5 -> 6 -> 7 -> 8 -> 9 -> 10. -->

## 1. Baseline provenance — capture before anything can destroy it

- [x] 1.1 Record leg A's image identity: tag `phtcosta/rvandroid:0.9.3`, ID `sha256:b2904fdfc3ddfc81ad455abd5e5685ddc97666c9411c4d994fec9111311aedec`, created `2026-08-01T11:47:43-03:00`, into the change's working notes. `:latest` points at the same ID — record that too, so a later retag cannot be mistaken for a rebuild.
- [x] 1.2 Record leg A's jar sha256 (`386ce08d1846a4088755a8d755e5b70391af3b42add091d231dbcc52aed24e69`) and the baseline commit (`5dcf2259…`), and confirm the deployed jar still hashes to that value.
- [x] 1.3 Compute and record the SHA-256 of `calibracao/subset40.txt` — this is the `corpus_basis` digest both legs are declared against.
- [x] 1.4 Confirm `experimento-e3-decisiva/per_apk_paired.csv` has 40 rows and the three expected arms, and record its sha256 as leg A's frozen input.

## 2. Corpus basis — the only code the gate adds

- [x] 2.1 Add `corpus_basis → ape.corpusBasis` to `APERV_PROPERTY_MAPPING` in `modules/aperv-tool/src/aperv_tool/tools/aperv/tool.py`.
- [x] 2.2 Validate the value in `configure()` against `^[A-Za-z0-9._-]+:[0-9a-f]{64}$`, raising `ConfigurationError` naming the key and the rejected value, before any device interaction.
- [x] 2.3 Emit `ape.corpusBasis=<value>` from `_push_properties()` when configured; omit the key entirely when absent (INV-APV-56) — no placeholder, no warning.
- [x] 2.4 Add unit tests: the line is written with the configured value byte-identical; an absent basis emits no key; a malformed basis raises before any push.
- [x] 2.5 Add the source-sweep test proving no module under `modules/aperv-tool/src` reads `RUN_START` (INV-APV-57).
- [x] 2.6 Pre-check the DSL seam locally — `RV_TOOLS: "aperv:mop_on_llm_off:mop_off_llm_off:mop_on_llm_70@corpus_basis=subset40:<sha256>"` — by inspecting the generated `ape.properties` on a single local run. `_parse_single_tool_spec` emits a plural `variants` shape its own `TODO(FR15)` calls dead against `ToolConfig(variant: str)`. This is the cheap check, not the authoritative one: the seam is verified over the chain the campaign actually uses in task 7.2. If either check fails, fall back to a per-arm `overrides` entry set by the campaign configuration and record the deviation here.
- [x] 2.7 Run `/rv-test-run aperv-tool`

## 3. Margins and premises — derived from leg A, before any plan is frozen

- [x] 3.1 Compute per-outcome replica dispersion from `experimento-e3-decisiva/results/e3_decisiva_*/coverage.csv` at `(apk, rep, tool)` granularity, for `cov_method`, `cov_act`, `cov_mop`, `mop_unique` and `mop_total`.
- [x] 3.2 Derive the G1 margin per outcome from 3.1, floored at 1.5 pp for the percentage outcomes (twice the documented −0.743 pp between-campaign drift). Record the derivation, not only the result.
- [x] 3.3 Settle whether `mop_total` gates or is descriptive, on the evidence of 3.1 — it counts violation lines rather than distinct violations and is the noisiest of the five. Decide before the freeze; the decision is not revisitable after.
- [x] 3.4 Compute the expected substrate displacement for G3: per-application flagged-widget delta over the 40 applications, old parser against `derive_mop_artifact.py`, using the pinned static-analysis corpus.
- [x] 3.5 Re-confirm host-side that no application in the corpus would have hit the pre-`gh96` footprint guard, against the guard's actual threshold. Leg A shows no arm with `cov_method < 5`, which is evidence but not the threshold itself. Any affected application is declared before the campaign, never excluded after.
- [x] 3.6 Record `cov_act`'s ceiling (median 100.0 in both guided arms) as a declared premise of G2, with G2 stated one-sided.

## 4. Campaign scaffold and the adapted scripts

- [ ] 4.1 Create `experimento-rearch-aperv/` with its `README.md` (design, how to run, partitioning), modelled on `experimento-e3-decisiva/README.md`.
- [ ] 4.2 Generate `filters/batch_00.txt` … `batch_07.txt` — 5 applications each, deterministic alphabetical split of `calibracao/subset40.txt`. Assert union == subset, no duplicate, no loss.
- [ ] 4.3 Write `docker-compose.yml`: 8 containers on `phtcosta/rvandroid:0.9.3-rearch`, each running all three arms over its own 5 applications, `RV_TIMEOUTS=1800`, `RV_REPETITIONS=3`, the three skip flags, `RVSMART_LLM_MODE=true` with the `sglang` service, and the jar bind-mount `../modules/aperv-tool/src/aperv_tool/tools/aperv/ape-rv.jar:…:ro` following the `docker/docker-compose.cmpft2.yml` precedent.
- [ ] 4.4 Copy `consolidate_cal.py`, `verify_iteration.py`, `multiarm_stats.py` and `stats_utils.py` into the campaign's `scripts/`. Do not edit the originals under `experimento-cal/scripts/` (`gh94` INV-APV-55).
- [ ] 4.5 Adapt only the trace-reading paths of the copies onto `aperv_tool.analysis.trace_ndjson` (`gh94`'s deliverable). Leave the logcat and `tasks.json` paths untouched — they produce `per_apk_paired.csv`, and changing them would break the pairing the gate rests on. `stats_utils.py` stays byte-identical.
- [ ] 4.6 Write `scripts/preflight_runstart.py`: reads the first line of one trace per arm with `json.loads`, checks `props_digest`, `preset` + `params` against the arm's declared overrides, `build.sha` against the built `rearch` commit, and `corpus_basis` against the digest from 1.3. The `corpus_basis` check distinguishes two blocking failure modes and names them separately in the report — **absent** means the DSL parameter path dropped the value before it reached `ape.properties`, **mismatched** means it arrived carrying the wrong list. Reports every check PASS/FAIL and exits 1 on any FAIL. It is an operator script and never runs on an execution path (INV-RUN-03, `gh95` D1).
- [ ] 4.7 Write `scripts/compare.py`: G1 paired against leg A on the control arm, G2 as the within-campaign contrast on `cov_act`, G3 descriptive with the 3.4 displacement, all via `stats_utils.paired_bootstrap_ci` (B=10,000, seed 42).
- [ ] 4.8 Add unit tests for `compare.py` over synthetic paired vectors with known answers.
- [ ] 4.9 Run `/rv-doc-code` on each new script.
- [ ] 4.10 Run `/rv-test-run aperv-tool`

## 5. Pre-registration and freeze — nothing downstream may change it

- [ ] 5.1 Write the pre-registration document under `docs/`, modelled on `docs/20260730_preregistro_corrida_decisiva.md`: the grid, the arms, the corpus and its digest, the seeds, both image IDs, both jar shas, both git shas, the CSV each outcome is read from, G1/G2/G3 with the margins from 3.2, the declared premises from 3.5/3.6, and the tie rule.
- [ ] 5.2 State the substrate confound explicitly, with the direction the change is expected to move and the reason no magnitude is predicted, so no later reading can present it as a discovery.
- [ ] 5.3 Declare what counts as a blocking regression: a CI excluding zero in the harmful direction **and** |Δ| above the derived margin, on G1; and G2's contrast losing its sign or its CI including zero.
- [ ] 5.4 Freeze the document: record its sha256 in `calibracao/journal.jsonl` with a `FREEZE-PREREGISTRO` state, before the jar is built. Everything after this point that was not planned here is exploratory and is reported as such.

## 6. The jar and the image — only after both sides are complete

- [ ] 6.1 Confirm `ape` stages `rearch-03` through `rearch-07` are complete and `gh94` and `gh95` are applied here. This gate is not advisory: an unapplied `gh94` leaves no NDJSON reader, and an unapplied `gh95` leaves nothing for the pre-flight's `preset` check to verify.
- [ ] 6.2 Build the jar from the `ape-rearch` worktree (branch `rearch`) and copy it to `modules/aperv-tool/src/aperv_tool/tools/aperv/ape-rv.jar`. Record its sha256 and the built commit.
- [ ] 6.3 Push the rv-android commits — the image's stage-4 layer clones `PAMunb/rvsec` at build time, so unpushed work is silently absent from the image.
- [ ] 6.4 Build and push `phtcosta/rvandroid:0.9.3-rearch`. Do not reuse or move `0.9.3` or `latest`.
- [ ] 6.5 Record the new image's ID beside leg A's, in the pre-registration's provenance section — an appendix of measured facts, not a change to the frozen plan.

## 7. Smoke and the pre-flight gate

- [ ] 7.1 Run the smoke: a small application subset, 1 repetition, reduced timeout, all three arms.
- [ ] 7.2 Run `scripts/preflight_runstart.py` over the smoke's traces. The campaign does not start until it reports 3/3 arms PASS on all four checks. A `build.sha` mismatch here means the image's own default-branch jar won the mount — the gh71 failure mode, caught before 24 hours are spent. An **absent** `corpus_basis` here is the authoritative verdict on the DSL parameter seam of task 2.6: it exercises the whole `RV_TOOLS` → `_parse_single_tool_spec` → `configure()` fold → `ape.properties` → `RUN_START` chain over the exact configuration the campaign will run, which the local pre-check cannot do.
- [ ] 7.3 Confirm the smoke's tasks are COMPLETED with coverage > 0 and no `VerifyError` in the logcats.
- [ ] 7.4 Record the pre-flight report and a `PREFLIGHT` entry in `calibracao/journal.jsonl`.

## 8. The campaign

- [ ] 8.1 Launch: `docker compose up -d` from the campaign directory. `rv-platform` owns the emulator lifecycle throughout — no manual emulator management, in any context, without exception.
- [ ] 8.2 Monitor with the campaign's monitor script, counting identity-distinct completed work per container, never by grepping `tasks.json` for COMPLETED (which double-counts through `state_transitions`).
- [ ] 8.3 Run one final resume pass to recover transient `adb install` failures, and confirm identity-distinct completions equal 360.
- [ ] 8.4 Extract the traces before any `docker compose down` — device artifacts are ephemeral.

## 9. Validity gates, then outcomes — in that order

- [ ] 9.1 Gate: control arm is clean — `decision_source=MOP` == 0 and `mop=` == 0 in every step of `mop_off_llm_off`, anchored on `(?<![a-z_])mop=` so the pattern does not also match the tail of `activity_has_mop=1`.
- [ ] 9.2 Gate: jar and preset — the pre-flight's checks hold across the full campaign, not only the smoke, on a sampled basis per arm.
- [ ] 9.3 Gate: arm attribution — every run's effective plan matches its declared arm, 40/40 per arm.
- [ ] 9.4 Gate: task integrity — all tasks COMPLETED; lost runs reported as a count, never silenced.
- [ ] 9.5 Run `scripts/verify.py` and confirm it is clean. No outcome is read before 9.1–9.5 pass; a failed gate invalidates what it protects, and the analysis is not adjusted to route around it.
- [ ] 9.6 Run `scripts/consolidate.py` to produce `per_apk_paired.csv` and `tel_proxies.csv`.

## 10. Verdict

- [ ] 10.1 Run `scripts/compare.py` and produce the report: G1, G2 and G3 with point estimates and CIs for every outcome, including the ones that do not gate.
- [ ] 10.2 Write the result document — whatever it says, including a tie, with its CIs and the declared premises restated. A tie is a valid and useful outcome.
- [ ] 10.3 List every analysis that was not in the frozen plan and label it exploratory.
- [ ] 10.4 Record the merge verdict for the `rearch` line, and a `DECIDE` entry in `calibracao/journal.jsonl`.
- [ ] 10.5 Run `/rv-qa-lint-fix aperv-tool`
- [ ] 10.6 Run `/rv-verify aperv-tool`
- [ ] 10.7 Invoke `/rv-code-reviewer` via Skill tool
- [ ] 10.8 Run `/rv-docs-sync aperv-tool`
