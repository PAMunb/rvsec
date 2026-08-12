<!-- Subagent dispatch hints:
     - Group 1 (parser) must complete first — Groups 2 and 3 depend on the new signatures.
     - Groups 2 (rv-static-analysis call sites + 77 tests) and 3 (rv-platform + rv-agent call sites)
       are independent of each other and can run in parallel after Group 1.
     - Group 4 (corpus verification) needs Groups 1-3 green; Group 5 integrates and verifies.
     - Critical path: 1 -> 2 -> 4 -> 5.
     - This change touches ~10 source files plus ~83 test call sites concentrated in one module.
       Group 2 is the only one large enough to justify a dedicated subagent dispatch. -->

## 1. Parser — remove the key from the consumption path

- [x] 1.1 Delete the package filter in `_parse_classes` (`modules/rv-static-analysis/src/rv_static_analysis/parser/static/static_analysis_parser.py`) so every entry of `reachability` is loaded; drop the `package` parameter and update the docstring to state that the artefact is already scoped by its producer (INV-ANA-59)
- [x] 1.2 Replace the package prefix test in `_parse_windows` with membership in `reachability` for `ACTIVITY` windows (`classes.get_clazz(normalized_name)` resolves); keep non-`ACTIVITY` types admitted unconditionally; drop the `package` parameter (INV-ANA-60)
- [x] 1.3 Drop the `package` parameter from `StaticAnalysisParser.parse_file`, `StaticAnalysisParser.read_static_analysis_files`, and the two module-level singleton wrappers (INV-ANA-61)
- [x] 1.4 Grep the parser module for residual references to `code_package`/`INV-ANA-03` and remove them — no guards, no defaulted parameters, no `# removed` comments (P3, P4)
- [x] 1.5 Add unit tests: `reachability` loaded whole for an artefact whose `package` member carries a build suffix; framework `ACTIVITY` absent from `reachability` excluded; `DIALOG` absent from `reachability` admitted; signatures reject a package argument
- [x] 1.6 Run `/rv-test-run rv-static-analysis`

## 2. rv-static-analysis — call sites and existing tests

- [x] 2.1 Update `analysis/static/static_analysis.py:439` to call `parser.parse_file(self.analysis_file)`; confirm `self.app.code_package` is still read where the run **records** its key, and left untouched there
- [x] 2.2 Verify `RVStaticAnalysisConfig.get_tool_command` still emits `-clientParam codePackage=` unchanged — the production path is out of scope (design D4)
- [x] 2.3 Update the 77 call sites in `modules/rv-static-analysis/tests/` that pass a package to `parse_file`/`read_static_analysis_files`; expectations must not change except where a test asserted the old filtering behaviour
- [x] 2.4 Rewrite any test that asserted package-based filtering to assert the new scoping rule instead; delete tests that only existed to exercise INV-ANA-03
- [x] 2.5 Run `/rv-test-run rv-static-analysis`

## 3. rv-platform and rv-agent — call sites

- [x] 3.1 Update `rv-platform/src/rv_platform/components/static_analysis.py:133` to call `read_static_analysis_files(results_dir, apk_name)` and stop reading `self.task.app.code_package`; update the comment block, which currently explains the key it no longer passes (P4)
- [x] 3.2 Update `rv-platform/src/rv_platform/components/result_processor.py:270` the same way, including the `code_package` local it resolves for the call
- [x] 3.3 Update the 2 `rv-platform` and 4 `rv-agent` test call sites
- [x] 3.4 Run `/rv-test-run rv-platform` and `/rv-test-run rv-agent`

## 4. Corpus verification — the numbers the change is for

- [x] 4.1 Write an offline script that parses all 162 artefacts of `APKS_INSTRUMENTED_jca_dexlib2_experimento-FINAL_selected162` with the new parser and reports classes, methods and activities per APK
- [x] 4.2 Assert the 75 applications with `applicationIdSuffix` now yield a non-zero denominator, and that the parsed class count equals the artefact's `reachability` length for all 162
- [x] 4.3 Assert the activity count matches the producer-key decision for all 162 (1526 activities, zero divergence) — the regression guard for design D2
- [x] 4.4 Record the before/after table in the change directory as evidence for the archive

## 5. Integration and verification

- [x] 5.1 Grep the whole workspace for any remaining caller passing a package to the parser — zero dangling references (P3)
- [x] 5.2 Run `/rv-qa-lint-fix rv-static-analysis` and `/rv-qa-lint-fix rv-platform`
- [x] 5.3 Run `/rv-verify rv-static-analysis`
- [x] 5.4 Invoke `/rv-code-reviewer` via Skill tool
- [x] 5.5 Run `/rv-docs-sync rv-static-analysis` — the module CLAUDE.md documents the filtering behaviour being removed
- [x] 5.6 Sync the delta spec into `openspec/specs/analysis/spec.md` via `/openspec-sync-specs`: add INV-ANA-59/60/61, remove INV-ANA-03, narrow INV-ANA-58

## 6. Downstream — unblock the campaign

- [ ] 6.1 Rebuild `phtcosta/rvandroid:0.9.3-comp162` with `--no-cache` so the corrected parser ships in the image
- [ ] 6.2 Re-run the `comp162` smoke and confirm 7/7 gates with a non-zero denominator on `io.keepalive.android_133` and `de.markusfisch.android.binaryeye_174`, both of which carry a build suffix
- [x] 6.3 Record in `docs/20260812_comp162.md` that measurements taken after this change are not comparable to `cmp163` for the affected applications, and why
