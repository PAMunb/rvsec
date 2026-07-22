<!-- Single primary module (rv-agent) + rvagent-tool adapter; reuses rv-coverage parsers.
     <20 files — no subagent orchestration. Group 5 (reward) is BLOCKED on the open
     decision and must not start until the user resolves the reward scope. TDD per group. -->

## 1. Feed plumbing — path seam (rv-agent + rvagent-tool)

- [ ] 1.1 Write failing tests: `rvagent-tool` maps `task.result.logcat_file` → `RVAgentConfig.logcat_feed_path`; core imports no rv-platform types (`test_toolmaps_logcat_path`, `test_core_has_no_platform_import`) (INV-AGT-60)
- [ ] 1.2 Add `logcat_feed_path: str | None` to `RVAgentConfig`
- [ ] 1.3 In `rvagent-tool` config mapping, inject `task.result.logcat_file` into `logcat_feed_path` (adapter does the translation; core receives only a str)
- [ ] 1.4 Run `uv run pytest modules/rv-agent modules/rvagent-tool --import-mode=importlib -o "addopts=" -k "logcat_path or platform_import"`

## 2. Add rv-coverage dependency (rv-agent)

- [ ] 2.1 Add `rv-coverage` to `modules/rv-agent/pyproject.toml` dependencies; run `uv sync`
- [ ] 2.2 Confirm no dependency cycle (rv-coverage depends only on rv-android-core)

## 3. Runtime-feed reader (rv-agent) — reuse parsers, no CoverageTracker

- [ ] 3.1 Write failing tests using synthetic logcat files built from real lines under `results/`: incremental read advances offset; dedup by signature; partial last line buffered; no-feed is a no-op (`test_incremental_read`, `test_dedup_by_signature`, `test_partial_line_buffered`, `test_no_feed_no_error`) (INV-AGT-61/62)
- [ ] 3.2 Implement `read_new_events(path, offset)` reusing `parse_logcat_line` + `DiagnosticEventParser.feed_line`; episode-local seen-set; no background thread
- [ ] 3.3 Standalone fallback: own `LogcatManager(clear_buffer=False)` + teardown that stops the process; platform mode never starts a second capture nor clears the buffer (`test_standalone_clear_buffer_false`, `test_platform_no_second_logcat`)
- [ ] 3.4 Run `/rv-doc-code modules/rv-agent/src/rv_agent/agent/nodes/learn_node.py`
- [ ] 3.5 Run `uv run pytest modules/rv-agent --import-mode=importlib -o "addopts=" -k "read or feed or standalone"`

## 4. Event classification & static cross-ref (rv-agent)

- [ ] 4.1 Write failing tests: any confirmed reach (`reaches_target` ∪ `directly_reaches_target`) coverage = confirmed progress; RVSEC violation recognized; repeated/within-process coverage not new; crash annotates the next hash jump (no reward); VerifyError/ANR not consumed in v1; diagnostics-off inert (`test_confirmed_reach_is_progress`, `test_violation_recognized`, `test_repeated_coverage_not_new`, `test_crash_attributes_hash_jump`, `test_verifyerror_anr_not_consumed_v1`, `test_diagnostics_flag_off_inert`)
- [ ] 4.2 Implement `is_confirmed_mop_progress(signature, static_data)` matching `reaches_target` OR `directly_reaches_target` against the already-loaded `StaticAnalysisData`; classify violation events; recognize crash events
- [ ] 4.3 Wire crash-event annotation so a process restart's hash jump is not treated as a new screen (crash does NOT enter the reward); VerifyError/ANR parsed but not consumed in v1
- [ ] 4.4 Run `uv run pytest modules/rv-agent --import-mode=importlib -o "addopts=" -k "progress or violation or crash or diagnostic"`

## 5. Reward integration (rv-agent)

<!-- Reward scope RESOLVED (design.md D5): all confirmed reaches (one-shot) + RVSEC violations (max weight, one-shot); diagnostics deferred to v2. -->
- [x] 5.0 Reward-scope decision resolved with the user and recorded in proposal.md / design.md D5 / agent spec "Requirement: Reward Scope"
- [ ] 5.1 Write failing tests: all confirmed reaches rewarded once; violation rewarded at max weight once; a restart/re-log does not re-reward (INV-AGT-64); a spent-violation screen is ejected by the plateau signal (`test_reward_all_reaches`, `test_reward_violation_max_once`, `test_restart_does_not_rereward`, `test_violation_no_retrap`)
- [ ] 5.2 Implement the reader-side seen-set (stable signature key) enforcing one-shot per episode (INV-AGT-64)
- [ ] 5.3 Implement the reward hook in `learn_node` (~:677): reward every new confirmed reach as novelty; reward RVSEC violations at max weight (> any single coverage reward, same order of magnitude, non-saturating); crash/VerifyError/ANR do NOT enter the reward
- [ ] 5.4 Run `uv run pytest modules/rv-agent --import-mode=importlib -o "addopts=" -k reward`

## 6. Integration & Verification

- [ ] 6.1 Integration test: adapter injects `logcat_feed_path` end to end; import-graph assertion that rv-agent core does not import rv-platform (INV-AGT-60)
- [ ] 6.2 Confirm zero changes under `rvsec/` (rvsec-core untouched, INV-AGT-63); `ErrorDescription` bug remains documented only
- [ ] 6.3 Run `/rv-qa-lint-fix rv-agent`
- [ ] 6.4 Run `/rv-verify rv-agent`
- [ ] 6.5 E2E: live feed with an instrumented APK via `rv-experiment run` (may need `RV_LOGCAT_DIAGNOSTICS=true`)
- [ ] 6.6 Invoke `/rv-code-reviewer` via Skill tool for the gh79 implementation
- [ ] 6.7 Run `/opsx:verify gh79-runtime-mop-signal`
