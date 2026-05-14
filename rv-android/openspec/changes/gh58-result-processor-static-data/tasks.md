# Tasks — gh58: result_processor static_data fix + ASE-Journal CSV schema

Module: `rv-platform` (single module; ~5 files touched). No subagent orchestration needed (well under the 20-file threshold from WORKFLOW.md §5).

GitHub Issue: #58. Canonical plan: `docs/20260514_regenerar_planilhas.md`.

## 1. Regression test (RED, before fix)

- [ ] 1.1 Create fixture dir `modules/rv-platform/tests/components/fixtures/gh58/` with: `sample_task.logcat` (5 `RVSEC-COV:` entries for methods + 2 `RVSEC:` violations) and `sample_apk.json` (minimal `StaticAnalysisData` JSON: `package`, `mainActivity`, `reachability` with 10 classes / 30 methods including the 5 from the logcat, `windows` and `transitions` can be `[]`).
- [ ] 1.2 In `modules/rv-platform/tests/components/test_result_processor.py`, add `test_reconstruct_repository_from_logcat_populates_coverage_with_static_data` that builds a fake task with `apk_name`, `results_dir` pointing at the fixture dir, `app.code_package = "com.example.app"`, `result.logcat_file = sample_task.logcat`, calls `_reconstruct_repository_from_logcat(task)`, and asserts `len(repo.get_method_calls()) >= 1` and `repo.calculate_metrics().to_dict()["method_coverage"] > 0`. This MUST fail against the pre-fix code (RED).
- [ ] 1.3 Add `test_coverage_csv_cov_class_uses_class_coverage_not_method_coverage` and `test_summary_csv_cov_class_uses_class_coverage_not_method_coverage`: build a task where `class_coverage != method_coverage` (e.g. 5 classes / 30 methods, 2 classes / 5 methods called) and assert the value written to the `cov_class` column equals `class_coverage`, not `method_coverage`. **MUST fail against the pre-fix code** because line 322 of `result_processor.py` writes `method_coverage` into that slot.
- [ ] 1.4 Run `/rv-test-run modules/rv-platform/tests/components/test_result_processor.py` and confirm tests added in 1.2 and 1.3 are RED.

(Helper-level tests `test_resolve_static_data_reuses_task_attribute`, `test_resolve_static_data_returns_none_when_json_missing`, and `test_resolve_static_data_tolerates_task_app_none` are deferred to task 2.3 — after the helper exists in code — to avoid wrong-reason `AttributeError` failures during RED phase.)

## 2. Core fix — `_resolve_static_data` helper + reconstruct rewire

- [ ] 2.1 In `modules/rv-platform/src/rv_platform/components/result_processor.py`, add private helper `_resolve_static_data(self, task)` that returns `task.static_data` if non-`None`; else calls `static_analysis_parser.read_static_analysis_files(task.results_dir, task.config.apk_name, task.app.code_package if task.app else None)`, caches the result on `task.static_data`, and returns it. Catches all exceptions, logs warning, returns `None`. Imports: `from rv_static_analysis.parser.static import static_analysis_parser` (matches existing import in `static_analysis.py:25`). The parser already tolerates `package=None` (line 254: `if package and package not in normalized`), so `task.app is None` is safe.
- [ ] 2.2 Modify `_reconstruct_repository_from_logcat` to call `_resolve_static_data(task)` and pass the result to `parse_logcat_file(logcat_file, static_data)`. Update the method's docstring to reflect that per-method coverage IS now reconstructable.
- [ ] 2.3 Now that `_resolve_static_data` exists, add the deferred helper-level tests: `test_resolve_static_data_reuses_task_attribute`, `test_resolve_static_data_returns_none_when_json_missing`, `test_resolve_static_data_tolerates_task_app_none`.
- [ ] 2.4 Run `/rv-test-run modules/rv-platform/tests/components/test_result_processor.py::test_reconstruct_repository_from_logcat_populates_coverage_with_static_data` and confirm GREEN.

## 3. CSV writers — unify cascade, fix cov_class slot, extend headers

- [ ] 3.1 In `_write_task_coverage_data` (lines 230-348), delete the `else` block at lines 332-348 entirely. Always go through the (formerly Branch 1) repository path. **Fix the pre-existing bug at line 322**: replace the `round(method_coverage, 2)` written into the `cov_class` slot with `round(metrics_dict["class_coverage"], 2)` from `repository.calculate_metrics().to_dict()`. If `task.repository is None` after `_reconstruct_repository_from_logcat` was attempted (i.e. logcat missing), early-return with no rows. For each method call, append the three new columns (`cov_reachable`, `cov_reaches_mop`, `cov_directly_reaches_mop`) pulled from progressive sets against `to_dict()` denominators (`reachable_method_coverage`, `mop_method_coverage`, `direct_mop_method_coverage`).
- [ ] 3.2 In `_generate_coverage_csv` (~line 188), update the header row to the 15-column schema (see `specs/platform/spec.md` Scenario "Coverage CSV Format").
- [ ] 3.3 In `_write_task_summary_data` (lines 502-555), **collapse the 3-tier cascade to a single repository-based path**: delete the primary `if hasattr(task, "result") and hasattr(task.result, "coverage_metrics"):` branch (lines 519-524), delete the secondary `elif hasattr(task, "repository") and task.repository:` branch (lines 525-530), delete the tertiary `else:` zero branch (lines 531-536). Replace with: call `_reconstruct_repository_from_logcat(task)` if `task.repository is None`; then unconditionally read `metrics_dict = task.repository.calculate_metrics().to_dict()` if repository is now non-`None`; if still `None` (logcat missing), set all 9 coverage/error values to 0 and log warning. Write the 13-column row using `metrics_dict` keys: `cov_act=activity_coverage, cov_class=class_coverage, cov_method=method_coverage, cov_rv_method=mop_method_coverage, cov_reachable=reachable_method_coverage, cov_reaches_mop=mop_method_coverage, cov_directly_reaches_mop=direct_mop_method_coverage, mop_errors_total=total_errors, mop_errors_unique=unique_errors`.
- [ ] 3.4 In `_generate_summary_csv` (~line 466), update the header row to the 13-column schema (see `specs/platform/spec.md` Scenario "Summary CSV Format").
- [ ] 3.5 Add the integration tests from design.md "Testing Strategy" rows 3-5: `test_coverage_csv_header_15_columns`, `test_summary_csv_header_13_columns`, `test_write_coverage_data_uniform_path_resumed_and_runtime`, `test_write_summary_data_no_fallback_to_serialized_metrics` (asserts that when `task.result.coverage_metrics` and `task.repository` both exist with **different** values, the row reflects `repository.calculate_metrics()`, not `coverage_metrics`).
- [ ] 3.6 Update any pre-existing tests in `test_result_processor.py` that assert the old 8-column summary header or 12-column coverage header. Audit with `grep -n "cov_act.*cov_method.*cov_rv_method.*errors\|cov_rv_method.*errors" modules/rv-platform/tests/`.
- [ ] 3.7 Add `test_reconstruct_warns_and_zeroes_coverage_when_json_missing` (covers FR10-ext "Static Analysis JSON Missing on Resume" scenario): logcat present, JSON absent → row with 0 coverage, errors still captured.

## 4. ADR + docstring polish

- [ ] 4.1 Invoke `/rv-doc-adr` via Skill tool with title "Resume path obtains static_data via on-demand JSON re-parse, not via tasks.json serialization" and the context from `design.md` D1. Output file: `docs/adr/adr-NNNN-resume-path-static-data-reparse.md` (NNNN assigned by the skill).
- [ ] 4.2 Invoke `/rv-doc-code modules/rv-platform/src/rv_platform/components/result_processor.py` via Skill tool to update docstrings on `_resolve_static_data`, `_reconstruct_repository_from_logcat`, `_write_task_coverage_data`, `_write_task_summary_data`, `_generate_coverage_csv`, `_generate_summary_csv`. Remove the now-incorrect note that "Per-method coverage CANNOT be reconstructed" from the reconstruct docstring.

## 5. Verification

- [ ] 5.1 Run `/rv-qa-lint-fix modules/rv-platform` via Skill tool — fix any formatting/import issues introduced.
- [ ] 5.2 Run `/rv-verify modules/rv-platform` via Skill tool — pytest + black + flake8 must all pass.
- [ ] 5.3 Invoke `/rv-code-reviewer` via Skill tool on the diff.
- [ ] 5.4 Run `openspec validate --change gh58-result-processor-static-data` and `openspec status --change gh58-result-processor-static-data` — confirm 4/4 artifacts done and structural validation passes.
- [ ] 5.5 Invoke `/opsx:verify gh58-result-processor-static-data` via Skill tool — confirms implementation matches artifacts.

## 6. Archive

- [ ] 6.1 Invoke `/opsx:archive gh58-result-processor-static-data` via Skill tool — syncs delta specs to main specs (`openspec/specs/platform/spec.md`, `openspec/specs/analysis/spec.md`) and moves change dir to `openspec/changes/archive/YYYY-MM-DD-gh58-result-processor-static-data/`.
- [ ] 6.2 Run `/rv-docs-sync modules/rv-platform` via Skill tool if CLAUDE.md or architecture docs reference the old CSV schema.
- [ ] 6.3 Commit the implementation (separate commits per logical group: regression test, fix + helpers, CSV header extension, ADR, archive). Final commit body includes `Closes #58`.
- [ ] 6.4 Run `gh issue close 58 --comment "Closed by gh58 implementation; see archived change at openspec/changes/archive/YYYY-MM-DD-gh58-result-processor-static-data/."` (only if the close trailer in the merge commit hasn't already auto-closed it).

## Out of Scope (do NOT include in any commit of this change)

- Committing `scripts/regenerate_results/` — separate follow-up PR.
- Renaming `_regen.csv → _all.csv` in `/home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/RESULTADOS/` — manual operation by the researcher in an external tree.
- Changes to `performance.csv` or `results.json` schema.
- Changes to `rv-coverage` or `rv-static-analysis` code (analysis spec delta is documentation only).
