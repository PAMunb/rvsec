<!-- Subagent dispatch hints:
     - Groups 1 (B, harness) and 2 (C, coin cut) touch disjoint files and run in parallel.
     - Group 3 (smoke and full tests) runs after both. Group 4 (lint, verify, review, docs) runs last.
     - Subagents run no git state command (stash, checkout, reset, branch, commit).
     - Tests: `uv run pytest --import-mode=importlib -o "addopts=" <module>/tests`. -->

## 1. B: shared grace and the ape harness (rv-android-core, rv-tools, aperv-tool constant readers)

- [x] 1.1 Add `TOOL_TEARDOWN_GRACE_S = 45` to `modules/rv-android-core/src/rv_android_core/constants.py`, moving the comment block from `aperv/tool.py:95-101` (two uses that must agree; a hypothesis about censored teardown, not a measurement), generalized to APE and APE-RV
- [x] 1.2 `modules/aperv-tool/src/aperv_tool/tools/aperv/tool.py`: delete `APERV_TEARDOWN_GRACE_S`, import `TOOL_TEARDOWN_GRACE_S` from core, and update every use and comment (lines ~1117, 1162, 1171, 1258, 1452); update `tests/test_aperv_tool.py` imports and asserts
- [x] 1.3 `modules/aperv-tool/src/aperv_tool/analysis/liveness.py`: delete `TEARDOWN_GRACE_S`, read the core constant (docstrings at lines ~30 and ~380 included); update `tests/test_liveness.py` (line ~210, and line ~466, which keeps comparing the frozen `experimento-comp162/scripts/admissibility.py` value against the core constant), `tests/test_gates.py:260` and `tests/test_no_rq_identifier.py:100` to the new name; leave `experimento-comp162/` untouched
- [x] 1.4 `modules/rv-tools/src/rv_tools/builtin/ape/tool.py`: add the `APE_PROPERTIES_CONTENT` constant and `_push_ape_properties()` (temporary file, `adb -s <serial> push` to `/data/local/tmp/ape.properties`, timeout 60, `RVToolExecutionError` on failure), called after the jar push and before the APE command (INV-TOOL-29)
- [x] 1.5 Same file: command timeout = budget + `TOOL_TEARDOWN_GRACE_S`; run the command with `Command.invoke` instead of `_execute_and_check_command`; measure the elapsed time with `time.monotonic()` and raise `RVToolExecutionError` (naming elapsed and budget) when it is below `timeout − TOOL_TEARDOWN_GRACE_S`; keep `RVToolTimeoutError` as the normal end; remove the dead commented-out blocks in that method and rewrite the comments and docstrings to the current behaviour (INV-TOOL-27, INV-TOOL-28)
- [x] 1.6 `modules/rv-tools/tests/builtin/test_ape_tool.py`: tests for each scenario of the tools delta spec: timeout 345 for a 300 s budget; exit 1 at 310 s passes; exit 0 at 120 s raises with 120 and 300; 256 s passes; timeout propagates; properties pushed before APE with exact content; failed push raises and APE does not start
- [x] 1.7 Grep the workspace for `APERV_TEARDOWN_GRACE_S` and `liveness.TEARDOWN_GRACE_S` (code, docs, CLAUDE.md, `docs/architecture/`) and rename them to `TOOL_TEARDOWN_GRACE_S`, in `modules/aperv-tool/CLAUDE.md`, `modules/aperv-tool/docs/architecture.md`, `docs/architecture/ape-rv.md` and `docs/architecture/rv-experiment.md`; also document the ape grace and properties in `modules/rv-tools/src/rv_tools/builtin/ape/README.md`
- [x] 1.8 Run `/rv-test-run rv-tools`, `/rv-test-run aperv-tool` and `/rv-test-run rv-android-core`

## 2. C: coin cut in the MOP artifact derivation (aperv-tool derive)

- [x] 2.1 `modules/aperv-tool/src/aperv_tool/tools/aperv/derive_mop_artifact.py`: delete `CALLBACK_PARAMS` and its comment block; reduce `HANDLER_METHOD_PATTERN` to `onClick|onLongClick|invoke` and rewrite its comment; delete the `CALLBACK_PARAMS` branch of `_handler_events` and rewrite its docstring (INV-DRV-11)
- [x] 2.2 Grep the module for any other text that describes the callbacks as handler methods (module docstring, `_index_reachability` docstring, `_emit_handlers`) and rewrite it to the current behaviour
- [x] 2.3 `modules/aperv-tool/tests/test_derive_mop_artifact.py`: rewrite the callback tests (~lines 2060-2170, 2447) to the delta scenarios (callback-only classes not listed; a class with View `onClick` and `onOptionsItemSelected` carries only the View record, `dist.click == [[0, 3]]`); the cryptoapp ground truth has exactly 2 handler keys, and `MainActivity` and `MainActivity$1` are absent; leave the fixture `tests/fixtures/cryptoapp.apk.json` unchanged
- [x] 2.4 Check `modules/aperv-tool/docs/architecture.md` and `CLAUDE.md` for text on the callback handler records and update it
- [ ] 2.5 At archive: the aperv requirement is renamed to "MOP Artifact Projection and Handler Table" — update the cross-reference in `openspec/specs/instrumentation/spec.md` (View app-callback paragraph, ~line 3641), whose sentence "that table gives the callback's class a `click` record" no longer holds; hand-sync the delta Purpose, Data Contracts and INV-DRV-11 into `openspec/specs/aperv/spec.md`, and INV-TOOL-27..29 into `openspec/specs/tools/spec.md`
- [x] 2.6 Run `/rv-test-run aperv-tool`

## 5. Step fuzzing in the trace reader (added 22/10)

- [x] 5.1 `modules/aperv-tool/src/aperv_tool/analysis/trace_ndjson.py`: add `StepRow.fuzz_events: Optional[Tuple[str, ...]] = None` (docstring entry) and map `dec.fz` to it, raising `TypeError` on a non-array as `dec.ret` does (INV-APV-69)
- [x] 5.2 `modules/aperv-tool/tests/test_trace_ndjson.py`: the four scenarios of "The Trace Reader Carries the Step's Fuzzing"; add `fuzz_events` to the absent-on-older-traces field list
- [x] 5.3 Update `modules/aperv-tool/CLAUDE.md` / `docs/architecture.md` where the `dec` → `StepRow` mapping is listed
- [x] 5.4 Run `/rv-test-run aperv-tool`

## 3. Smoke and full tests

- [x] 3.1 Smoke: derive the MOP artifact of two e7-corpus JSONs that contain callback classes, with the new and the old derive, and check that only the callback-only classes leave `handlers` and that everything else is byte-identical; write the outputs to the scratchpad, not the repo
- [x] 3.2 Smoke: build the `ape` command and the properties file with a fake device (no emulator) and print the command, its timeout and the pushed content
- [x] 3.3 Full tests of rv-android-core, rv-tools and aperv-tool with `--import-mode=importlib -o "addopts="`; `openspec validate gh-tbd-ape-grace-coin-cut --strict`

## 4. Lint, verify, review

- [x] 4.1 Run `/rv-qa-lint-fix` on rv-tools and aperv-tool (per module; touch only changed lines)
- [ ] 4.2 Run `/rv-verify` on rv-tools and aperv-tool
- [ ] 4.3 Invoke `/rv-code-reviewer` via the Skill tool on the branch diff
- [ ] 4.4 Run `/rv-docs-sync aperv-tool` and `/rv-docs-sync rv-tools` if docs drift
- [ ] 4.5 Commit by path (no Co-Authored-By), no push; report the worktree, branch and SHAs to mini-experimento
