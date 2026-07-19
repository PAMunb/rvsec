# Tasks: gh83-reconstruction-time-stamping

## 1. Parser Timing Stamping (rv-coverage)

- [x] 1.1 Add `_stamp_time(time_occurred, tool_execution_start) -> int` module-private helper in `modules/rv-coverage/src/rv_coverage/parser/log/logcat_parser.py` implementing `max(0, int((time_occurred − epoch).total_seconds()))` (INV-ANA-49)
- [x] 1.2 Add optional `tool_execution_start: Optional[datetime] = None` parameter to `parse_logcat_file`; stamp `time_since_task_start` on every parsed `RvErrorLog`, `RvCoverageLog`, and diagnostic event before registration; when epoch is `None` and at least one entry was parsed, log exactly one warning about degraded timing
- [x] 1.3 Add unit tests (failing before 1.1–1.2): stamping for errors/coverage/diagnostic events with known logcat timestamps + fixed epoch; clamp for entries predating the epoch; degraded no-epoch warning; propagation of first-call time into `MethodCoverageData` and `get_method_calls()` `time` values (delta spec scenarios "Reconstruction With Tool Execution Start Stamps Timing", "…Clamps…", "…Degrades Explicitly")
- [x] 1.4 Run `/rv-test-run modules/rv-coverage`

## 2. Reconstruction Epoch Forwarding + Writer Guard Removal (rv-platform)

- [x] 2.1 `_reconstruct_repository_from_logcat` in `modules/rv-platform/src/rv_platform/components/result_processor.py`: pass `tool_execution_start=task.result.tool_execution_start` to `parse_logcat_file`; log WARNING naming `task.id` when it is `None` (INV-PLT-23)
- [x] 2.2 Delete the `if time_value is None or time_value == 0: time_value = i` fabrication guards (and the `i` fallback in the corresponding `.get(...)` calls) from `_write_task_error_data` and `_write_task_app_events`; write `time_since_task_start` as-is (INV-PLT-24, P3 — no shim)
- [x] 2.3 `CoverageComponent._parse_existing_logcat` in `modules/rv-platform/src/rv_platform/components/coverage.py`: forward `self.task.result.tool_execution_start` in both `parse_logcat_file` calls (design Decision 5)
- [x] 2.4 Add unit tests (failing before 2.1–2.3): epoch forwarded to parser (spy); `errors.csv`/`app_events.csv` write `0` for legitimate t=0 entries (no row index); WARNING logged for missing epoch (delta spec scenarios "Errors CSV Format" time assertion, "Reconstruction Without Persisted Epoch Degrades Explicitly")
- [x] 2.5 Run `/rv-test-run modules/rv-platform`

## 3. Round-Trip Integration Tests

- [x] 3.1 Integration test: build a repository live via `CoverageTracker` from a logcat fixture, serialize the task (`to_dict`/`from_dict`), reconstruct via `_reconstruct_repository_from_logcat`, and assert the `time` column of `coverage.csv`, `errors.csv`, and `app_events.csv` rows is identical between the two paths (delta spec scenario "Time Column Round-Trip Equivalence on Resume"; reuse the gh58 regression-test fixture pattern in `modules/rv-platform/tests/`)
- [x] 3.2 Integration test: `coverage.csv` rows for a reconstructed task are chronologically ordered by real `time` (progressive `cov_*` columns monotonic where expected)
- [x] 3.3 Run `/rv-verify modules/rv-platform`

## 4. Verification & Documentation

- [x] 4.1 Run `/rv-qa-lint-fix modules/rv-coverage` and `/rv-qa-lint-fix modules/rv-platform`
- [x] 4.2 Run `/rv-verify modules/rv-coverage`
- [x] 4.3 Invoke `/rv-code-reviewer` via Skill tool
- [x] 4.4 Update inline docs touched by the change (docstrings of `parse_logcat_file`, `_reconstruct_repository_from_logcat`, writer methods) to current-state behavior (P4); run `/rv-docs-sync modules/rv-coverage` and `/rv-docs-sync modules/rv-platform` if CLAUDE.md/architecture docs mention the old behavior
- [x] 4.5 Check off satisfied acceptance criteria in GitHub issue #83
