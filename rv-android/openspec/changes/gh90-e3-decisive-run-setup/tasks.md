<!-- Group order is the deadline-driven priority order: implemented and tested by 2026-07-31 09:00
     (hard max 2026-08-01 09:00), feeding the decisive run. Groups 1-4 are independent of the
     sister-repo jar and can be completed and green before it exists; Group 5 is the only one that
     needs the jar. This change touches ~5 files in one module — no subagent orchestration needed. -->

## 1. Decisive-run arms (A1 + B2)

- [ ] 1.1 Add the module-level `_MOP_OFF_OVERRIDES` constant in `modules/aperv-tool/src/aperv_tool/tools/aperv/tool.py`: the four MOP weights and `mop_frontier_weight` at `0`, `activity_trigger_enabled=False`. Document inline WHY the document stays present (INV-APV-29: an unset path aborts the run at `StatefulAgent.java:216-223`; an omitted `mop_data` also kills `WtgPass:29`/`FrontierPass:35`)
- [ ] 1.2 Declare the three decisive-run arms in `get_variants()` on `_FRONTIER_SUBSTRATE`: `mop_on_llm_off` (reference), `mop_off_llm_off` (control, `**_MOP_OFF_OVERRIDES`), `mop_on_llm_70` (LLM arm). Arm 3 carries the `cal_a1` LLM block verbatim — `llm_percentage=0.7`, `v13`, temperature 0, `top_p` 0.6, `top_k` 50, both triggers on (design D8)
- [ ] 1.3 Confirm `mop_activity_source_components=True` is explicit in all three arms (B2). Note that this is an explicitness requirement, not a behaviour change: `_FRONTIER_SUBSTRATE` already carries `True` (`tool.py:322`), so all three inherit it — B2 only alters arms that inherit the jar's `false` default
- [ ] 1.4 Add unit tests: control arm keeps `mop_data`; all five MOP weight keys are `0`; `activity_trigger_enabled` is `False`; `frontier_boost_weight` unchanged (INV-APV-30)
- [ ] 1.5 Add the single-factor guard tests: reference↔control diff is exactly the MOP keys; reference↔LLM-arm diff contains only LLM keys
- [ ] 1.6 Extend the `LLM_ARM_KEYS` guard scope (`tool.py:209-238`) so it covers `mop_on_llm_70`. It is scoped to the `cal_` prefix today, so without this the arm escapes the guard and task 1.7 passes vacuously (INV-APV-26)
- [ ] 1.7 Verify the pre-existing guards still pass with the new arms (`ARM_DEFINING_KEYS` mapping/explicitness, INV-APV-13/14; `LLM_ARM_KEYS` under its extended scope, INV-APV-26)
- [ ] 1.8 Run `/rv-test-run aperv-tool`

## 2. Offline substrate enrichment (N6)

- [ ] 2.1 Implement `_enrich_listener_reach(document) -> int` in `tool.py`: build the signature→`reachesTarget` index from `reachability[].methods[]`, then walk `windows[].widgets[].listeners[]` writing `handlerReachesTarget` and `handlerDirectlyReachesTarget`. Direct means any-depth reach of THIS widget's handler — never copy the producer's 0-hop `directlyReachesTarget` (INV-APV-32)
- [ ] 2.2 Wire it into `_compact_static_analysis_json` between the `transitions` dedup and the minified write; keep the existing `except (json.JSONDecodeError, OSError, MemoryError)` fallback intact and make an enrichment failure degrade to an un-enriched push, not to a source-file push (INV-APV-31)
- [ ] 2.3 Update the `_compact_static_analysis_json` docstring: "two lossless operations" becomes three, the third additive. Current-state only, no migration history (P4)
- [ ] 2.4 Add unit tests: transitive handler flagged direct; unreachable handler false on both; unknown signature false on both; app with zero widgets is a valid no-op; only the two keys are added; malformed `reachability` degrades to un-enriched push; source file byte-identical afterwards (INV-APV-20/31)
- [ ] 2.5 Measure the flagged fraction and record it. Expect sparsity, not saturation: the census over the 40-APK subset gives 0.4% (160 of 45,200 listeners) with only 7 apps carrying any flaggable listener, so the axis is reported as sparse (design Risks)
- [ ] 2.6 Run `/rv-test-run aperv-tool`

## 3. Per-run provenance and the B3 gate (N4 + B3)

- [ ] 3.1 Implement `_capture_llm_provenance(llm_url, jar_path) -> dict` — live `GET {llm_url}/v1/models` plus the jar file sha256; returns `llm_backend`, `llm_model`, `llm_sampling`, `jar_sha256`, `capture_status`. Failures are encoded in `capture_status`, never back-filled from config (INV-APV-33)
- [ ] 3.2 Call it once per run in the execute path for arms that declare LLM keys, and write the fields into the task output
- [ ] 3.3 Add the B3 declaration to the LLM arm: `llm_snap_tolerance_px=150` paired with the expected jar git sha. Do NOT attempt to read a capability stamp from the jar — the provenance is a dexed Java constant, not a packaged resource (`ape` INV-BUILD-09), and is only readable via the runtime `[APE-BUILD]` banner (design D4)
- [ ] 3.4 Add the guard test enforcing the pairing in both directions: tolerance 150 without a declared sha fails; a declared sha without the raised tolerance also fails (INV-APV-34)
- [ ] 3.5 Add unit tests: provenance from a live query; failure encoded not inferred; no query for non-LLM arms
- [ ] 3.6 Run `/rv-test-run aperv-tool`

## 4. Offline clock↔logcat join (A9)

- [ ] 4.1 Create `modules/aperv-tool/src/aperv_tool/analysis/clock_logcat_join.py`: read a run's recorded trace clock and `RVSEC:` logcat lines, emit per-run correlation rows. Offline and read-only — no device, no emulator (INV-APV-35)
- [ ] 4.2 Add the CLI entry point with `SystemExit(2)` on a missing or unreadable run directory, naming the path
- [ ] 4.3 Add the validation gate test against the recorded iter0 corpus: exactly 9,586 `RVSEC:` lines across 605 runs and 32 APKs — all three totals must match
- [ ] 4.4 Add unit tests: a run with zero violations yields a valid empty-violation row set (not an omission); every artifact read is byte-identical afterwards
- [ ] 4.5 Run `/rv-doc-code modules/aperv-tool/src/aperv_tool/analysis/clock_logcat_join.py`
- [ ] 4.6 Run `/rv-test-run aperv-tool`
- [ ] 4.7 Report what the join says about the "reaching a MOP screen fires the monitor" premise — this is the evidence base for the deferred N5 decision

## 5. Cross-repository integration (needs the sister jar)

- [ ] 5.1 Record the git sha of the `ape-rv.jar` build containing B1 and put it in the LLM arm's declaration (task 3.3)
- [ ] 5.2 Real smoke via `rv-platform` against a real SGLang server — infrastructure scope: 3 APKs × 3 arms, short timeout, all tasks COMPLETED, coverage > 0, SGLang answers. The APK set MUST include `freeotpplus` and `aegis` (task 5.5 is unreachable on the other 33). No mock LLM. **Never start, stop, or manage an emulator manually** — rv-platform owns the whole lifecycle
- [ ] 5.3 Smoke gate: the `[APE-BUILD]` banner's `git_sha` matches the arm's declared sha; a mismatch fails before the decisive run launches (INV-APV-34)
- [ ] 5.4 Smoke gate: in the control arm, `decision_source=MOP` count == 0 AND the `mop=` field is always 0 across every step. This is the one behavioural gate the smoke carries, because it is the single failure that invalidates the whole run
- [ ] 5.5 Smoke gate: the pushed `static_analysis.json` carries the two handler-reach booleans, and `[DM]` markers appear for widgets whose handlers reach JCA — verifiable only on the 7 apps with flaggable listeners (design Risks)
- [ ] 5.6 Smoke gate: provenance fields present in the task output, naming the model actually served

## 6. Verification

- [ ] 6.1 Run `/rv-qa-lint-fix aperv-tool`
- [ ] 6.2 Run `/rv-verify aperv-tool` — full suite green under the CI contract (`--import-mode=importlib -o "addopts="`)
- [ ] 6.3 Invoke `/rv-code-reviewer` via the Skill tool on the change set
- [ ] 6.4 Run `openspec validate "gh90-e3-decisive-run-setup"` — clean, artifacts coherent with the implemented state
- [ ] 6.5 Run `/rv-docs-sync aperv-tool` — update `modules/aperv-tool/CLAUDE.md` (variant table gains three arms; the compaction gotcha becomes three operations)
- [ ] 6.6 Check off every satisfied acceptance criterion in issue #90 before closing it
