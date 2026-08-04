<!-- Ordering, and why it is not negotiable:
     Group 1 (capture allowlist) must land before Group 4 can produce anything — a heartbeat
     under an unadmitted tag is discarded at the device, so a run captured before Group 1 cannot
     show heartbeat lines no matter how the jar behaves.
     Groups 2 and 3 are independent of Group 1 and of each other.
     Group 5 is split deliberately: 5.1-5.4 (swap the regex for reader rows) is safe at any time,
     because reader rows carry the same epoch clock `[APE-STEP] clock=` carried. 5.5-5.9 (delete the
     offset reconstruction) is BLOCKED on Group 4's recorded evidence — INV-APV-54. Deleting a
     working mechanism in favour of an unobserved one is the failure this change exists to prevent.
     Critical path: 1 → 4 → 5.5.
     This change touches ~14 files; no subagent orchestration needed.

     Pre-existing findings at HEAD that MUST be left alone (they add diff noise and are not this
     change's): `tests/test_aperv_tool.py:439` E741; a `black` reformat around
     `tests/test_aperv_tool.py:1422`; 67 E501 in `tools/aperv/tool.py`, all in comment prose. -->

## 1. Capture allowlist: the heartbeat tag reaches the file

- [x] 1.1 Add `TAG_APERV_HEARTBEAT = "ApeRvHb"` to `modules/rv-android-core/src/rv_android_core/util/logging/constants.py`, beside `TAG_RVSEC` and `TAG_RVSEC_COV`, with a comment stating it is a cross-repository contract with the APE-RV jar (`ape` design D-6) and that a mismatch fails as an empty capture rather than an error (INV-CORE-53)
- [x] 1.2 Change `LogcatManager.default_tags` in `modules/rv-android-core/src/rv_android_core/util/android/logcat_manager.py` to `[TAG_RVSEC, TAG_RVSEC_COV, TAG_APERV_HEARTBEAT]`, built from the constants rather than string literals; the two existing tags keep their position and order
- [x] 1.3 Update the `LogcatManager` command tests so the flag-off baseline is `adb -s emulator-5554 logcat -v threadtime -s RVSEC:V RVSEC-COV:V ApeRvHb:V` (amended INV-CORE-37), and the flag-on case asserts the three baseline tags first, in order, followed by the four diagnostic tags (INV-CORE-38 unchanged)
- [x] 1.4 Add `test_heartbeat_tag_declared_once`: the literal `"ApeRvHb"` appears exactly once in `modules/rv-android-core/src/`, as the value of `TAG_APERV_HEARTBEAT` (INV-CORE-53)
- [x] 1.5 Add `test_heartbeat_lines_change_no_parsed_value` to the rv-coverage parser tests: `parse_logcat_file` over a captured logcat with heartbeat lines and over the same file with them removed yields identical `calculate_metrics()`, `total_errors`, `unique_errors`, every coverage value, and an identical diagnostic-event collection (INV-CORE-54)
- [x] 1.6 Update `modules/rv-platform/.../tests` guards for INV-PLT-21: the flag-off command is the three-tag form, and `LogcatComponent` passes `default_tags` through without filtering, reordering or subsetting. No production code change is expected in `components/logcat.py` — if one turns out to be needed, that is a finding, not a fix to slip in silently
- [x] 1.7 Run `/rv-test-run rv-android-core` and `/rv-test-run rv-platform`

## 2. Native NDJSON reader

- [x] 2.1 Write `modules/aperv-tool/tests/fixtures/trace_ndjson_golden.ndjson` **first**, from the `event-sink` spec of `ape`'s `rearch-04-step-ndjson-telemetry` — it is the contract, not an afterthought. It MUST contain: a `RUN_START` with `t0`; `ACT` entries with `mop:1` and `mop:0`; two `STATE` entries; a step with no boost fields; a step with `dec.patched:0`; a step with no `patched` member; a step with two `llm[]` entries in occurrence order; a step whose `out` resolves to a new state; a step closed with no `out`; a step flushed with `out:{"resolved":false}`; one unparseable line; and a truncated final line. Record its provenance in `tests/fixtures/README.md`
- [x] 2.2 Implement the row model in `modules/aperv-tool/src/aperv_tool/analysis/trace_ndjson.py`: `RunStart`, `LlmCall`, `StepOutcome`, `Counterfactual`, `ComponentDispatch`, `StepRow`, `TraceDiagnostics` — frozen dataclasses following `analysis/coverage_dump.py` (design D-2)
- [x] 2.3 Implement `TraceReader`: one forward streaming pass (design D-1), `ACT`/`STATE` ID tables resolved as encountered, `RUN_START` captured as the first record, `llm[]` and `out` attached to their step's row
- [x] 2.4 Implement default materialization: the six boosts at `0` and the two outcome booleans at `false`; `dec.patched` and `dec.cf` left absent when absent (INV-APV-49) — a defaulted `patched` would erase the tri-state the jar emits explicitly
- [x] 2.5 Implement `activity_has_mop` re-derivation: step side from the record's `ACT` entry, outcome side via `out.target` → `STATE.act` → `ACT.mop`
- [x] 2.6 Implement epoch expansion via `RUN_START.t0`, and report it unavailable (`t_epoch_ms is None`) when `RUN_START` is absent — no base inferred from mtime, logcat, or anything else (INV-APV-51)
- [x] 2.7 Implement malformed handling: skip and count in `TraceDiagnostics.malformed`, never raise; a reference to an undefined `ACT`/`STATE`/`out.target` ID takes the same branch and no placeholder string is emitted (INV-APV-50)
- [x] 2.8 Add the reader unit tests, asserting the golden fixture field for field against expected rows — one named test per rule: joined row, boost defaults, tri-state `patched`, `llm[]` order, outcome absent vs `resolved:false`, `activity_has_mop` on both sides, malformed count (exactly 2 for the fixture), undefined dictionary ID, missing `RUN_START`
- [x] 2.9 Add `test_reader_never_imported_by_collection_path`: `trace_ndjson` is not reachable from the import graph of `tools/aperv/tool.py` (INV-APV-48)
- [x] 2.10 Run `/rv-doc-code modules/aperv-tool/src/aperv_tool/analysis/trace_ndjson.py`
- [x] 2.11 Run `/rv-test-run aperv-tool`

## 3. gzip at collection

- [x] 3.1 Implement `_gzip_trace(trace_path)` in `modules/aperv-tool/src/aperv_tool/tools/aperv/tool.py`: stream into `Path(str(trace_path) + ".ndjson.gz")` with `gzip.open` + `shutil.copyfileobj` (design D-3); catch every exception, log WARNING naming the trace path, continue (INV-APV-52)
- [x] 3.2 Call it as step 10 of `execute_tool_specific_logic`, after `_check_empty_trace`
- [x] 3.3 Call it on the timeout path too — inside the `RVCommandTimeoutError` handler, before re-raising `RVToolTimeoutError` (step 8). Timeout is how a normal exploration run ends, so this is the majority path
- [x] 3.4 Add tests: trace byte-identical (hash before/after) with the `.gz` decompressing to the same bytes; gzip failure non-fatal and status-neutral (monkeypatched `gzip.open`); timeout path runs collection before re-raising
- [x] 3.5 Add `test_no_collection_path_reads_run_end`: no source file under `tools/aperv/` references `RUN_END` (INV-APV-53)
- [x] 3.6 Run `/rv-test-run aperv-tool`

## 4. Evidence: heartbeat lines are actually in a captured run

<!-- Owner-executed on a device, through rv-experiment/rv-platform, which own the emulator lifecycle.
     The assistant never starts, stops or manages an emulator, in any context. Blocked on Group 1
     landing AND on a stage-4 jar being deployable. -->

- [ ] 4.1 With Group 1 merged and a stage-4 `ape-rv.jar` in place, run one short `aperv` task via `uv run rv-experiment run` and grep the resulting `task.result.logcat_file` for tag `ApeRvHb`
- [ ] 4.2 Record the evidence in `openspec/changes/gh94-ndjson-trace-reader/heartbeat-evidence.md`: the run identity, the observed heartbeat line count, and a comparison against the trace's `StepRecord` count with the `s` values agreeing. If the counts disagree, that is the finding — stop and report it rather than proceeding to Group 5.5
- [ ] 4.3 If no heartbeat line appears, do **not** advance to 5.5. Diagnose whether the tag differs between the two repositories, whether the jar's heartbeat flag is off, or whether capture was launched before Group 1 landed

## 5. Migrate the clock-to-violation join

<!-- 5.1-5.4 are safe at any time. 5.5 onward is BLOCKED on 4.2 (INV-APV-54). -->

- [x] 5.1 Replace `_read_steps` in `modules/aperv-tool/src/aperv_tool/analysis/clock_logcat_join.py` with a `TraceReader`-backed step map (`dict[int, StepRow]`), deleting the `[APE-STEP]` regex at `:62-63`. The offset reconstruction stays for now — reader rows carry the same epoch clock the regex read, so this step changes the source and nothing else
- [x] 5.2 Implement `_read_heartbeats(logcat_path)`: parse `ApeRvHb` lines into `(stamp, step, t_rel_ms)`, using the existing `_TIMESTAMP` pattern
- [x] 5.3 Add the heartbeat-side test fixtures: a stage-4 trace paired with a logcat carrying matching heartbeat lines, and a second logcat with `RVSEC` lines but no heartbeat at all
- [x] 5.4 Run `/rv-test-run aperv-tool`
- [ ] 5.5 **Gated on 4.2.** Switch placement to heartbeats: each violation is placed against the last heartbeat at or before its stamp, and the matched step keys into the `StepRow` map for activity and state (design D-4, D-5)
- [ ] 5.6 **Gated on 4.2.** Delete `_align_clocks()` (`:348-384`), `_naive_epoch_ms`, `_read_capture_start`, the year-candidate search, the quarter-hour rounding, `_QUARTER_HOUR_MS`, and the anchor selection — deleted, not disabled, and backed up to `backup/` first (P3)
- [ ] 5.7 **Gated on 4.2.** Remove `alignment_residual_ms` **and** `clock_offset_ms` from `RunJoin` and from every consumer and docstring. `clock_offset_ms` holds the reconstructed UTC offset and has no producer once `_align_clocks` is gone; keeping it would be the dead shim P3 forbids (design D-4)
- [ ] 5.8 **Gated on 4.2.** Compose the reported absolute timestamp forward as `t0 + hb.t_rel_ms + (violation_stamp − hb.stamp)` when `RUN_START` was present, and report it unavailable otherwise. Rewrite the module docstring to describe what the module does now — one clock, no reconstruction — with no migration history (P4)
- [ ] 5.9 **Gated on 4.2.** Add the join tests: placement with no reconstruction; a run whose logcat has no heartbeat yields `UNALIGNED` violations and stays in the report with its denominator; artifacts byte-identical after the run (INV-APV-35); `RunJoin` carries neither deleted field
- [ ] 5.10 Run `/rv-test-run aperv-tool`

## 6. Carve-out, documentation and verification

- [x] 6.1 Add `test_frozen_corpus_scripts_untouched`: the paths named by INV-APV-55 — `scripts/cmpm_stratify.py`, `scripts/analyze_cmpv2_llm.py`, `experimento-cal/scripts/*`, `experimento-20260721/scripts/*`, `calibracao/*` — are unmodified by this change
- [x] 6.2 Record the frozen-corpus carve-out in `modules/aperv-tool/CLAUDE.md`: which scripts, why they keep the legacy parser, why that is not a P3 violation, and the operational test (`clock_logcat_join.py` migrated because it reads new traces; these never will). Add `analysis/trace_ndjson.py` to the module's file table and note that `coverage_dump.py` is unaffected because it reads only the `UICOV` lines
- [x] 6.3 Run `/rv-qa-lint-fix aperv-tool` — do not touch the three pre-existing findings listed at the top of this file
- [ ] 6.4 Run `/rv-verify aperv-tool` (~4 min; run it in the background), `/rv-verify rv-android-core` and `/rv-verify rv-platform`
- [ ] 6.5 Invoke `/rv-code-reviewer` via the Skill tool for the whole change
- [ ] 6.6 Run `/rv-docs-sync aperv-tool`
- [ ] 6.7 Run `/opsx:verify gh94-ndjson-trace-reader` before archiving
