<!-- Subagent dispatch hints:
     - Group 1 (env-var registry) must complete first — Group 2 reads the constants it declares,
       and Group 8 (Docker/compose surfaces) verifies them. No container can be started until the
       ENV_* names exist, because validate_env_vars.sh exits 64 on any undeclared RV_*.
     - Groups 2 (core boot gate) and 3 (core emulator session) are both in rv-android-core and
       touch adjacent code in android.py / emulator_manager.py — run them SEQUENTIALLY, in order.
     - Group 6 (rv-coverage drain) must land BEFORE Group 5 (platform finalization owner): the
       order Group 5 encodes is only meaningful once the drain it feeds exists, and Group 5's
       tests assert against it.
     - Groups 4 (platform device resolution), 7 (monitoring buckets) and 8 (Docker/compose) touch
       nothing the core groups touch and can run in PARALLEL from the start; only their
       verification steps need Group 1.
     - Group 9 (test rewrites) depends on Groups 2-6 being complete — the rewritten tests encode
       the new contract and cannot be written against half of it.
     - Group 10 integrates and verifies everything — must run last.
     - Critical path: 1 -> 2 -> 3 -> 6 -> 5 -> 9 -> 10. Groups 4, 7 and 8 hang off it in parallel.
     - This change touches ~25 files across five modules plus Docker, docs and compose surfaces —
       use subagent orchestration (parallel dispatch of 4, 7 and 8 alongside the core path). -->

## 1. Environment Variable Registry

The container dies with exit 64 on any `RV_*` not declared here, so this group must land whole and first.

- [ ] 1.1 Declare `ENV_EMULATOR_BOOT_TIMEOUT = "RV_EMULATOR_BOOT_TIMEOUT"`, `ENV_ADB_CMD_TIMEOUT = "RV_ADB_CMD_TIMEOUT"` and `ENV_APK_INSTALL_TIMEOUT = "RV_APK_INSTALL_TIMEOUT"` in the `ENV_*` block of `modules/rv-android-core/src/rv_android_core/constants.py`
- [ ] 1.2 Add the three names to `L1_INFRA_NAMES` in `scripts/check_env_vars_drift.py` (design D2 — do not rely on the literal-only regex blind spot to pass a lint that documents the opposite rule)
- [ ] 1.3 Document all three in `.env.example` under a boot/device timeouts section, following the file's convention: section header, prose comment, a `# (No CLI flag — ...)` line, and the commented assignment. Note the provisional status of the 300 s default inline
- [ ] 1.4 Add the three to the env table in `README.md` and to `CLAUDE.md` / `.claude/project-info.md` env tables
- [ ] 1.5 Run `uv run python scripts/check_env_vars_drift.py` and `uv run pytest --import-mode=importlib -o "addopts=" tests/lint/test_env_vars_drift.py`

## 2. Core — Boot Gate (C1, C3, C4)

- [ ] 2.1 Add the timeout resolution helper in `modules/rv-android-core/src/rv_android_core/util/android/android.py` following the explicit `int(env_value)` style of `rv_experiment/config.py:865`: explicit argument wins, then the env var, then the default; `ValueError` propagates on an invalid value. Do NOT use `util/utils.py:424-473` — it is dead and swallows `ValueError` (design D3)
- [ ] 2.2 Change `_wait_for_boot`'s signature to `boot_timeout: Optional[int] = None` and resolve inside, preserving the test injection point (INV-CORE-47)
- [ ] 2.3 Resolve `cmd_timeout` from `RV_ADB_CMD_TIMEOUT` (default 30); move the poll interval into a module constant and replace the two hardcoded `time.sleep(5)` calls with it. The poll interval is deliberately NOT an env var — how often the device is asked does not depend on the host, only how long it is given (core delta, Data Contracts)
- [ ] 2.4 **C1**: replace phase 2's quoted shell string with a Python poll of `["-s", serial, "shell", "getprop", "sys.boot_completed"]`, accepting only when `result.is_failure()` is `False` **and** `result.stdout.strip() == b"1"` (INV-CORE-44, INV-CORE-45). Remove the unconditional `break`. Drop the `wait-for-device` token at `android.py:202` along with the loop — the bounded Python poll is what it was standing in for
- [ ] 2.5 **C3**: in phase 1, handle `is_failure()` and empty stdout explicitly, logging the device serial and `get_combined_output()` at the point of detection instead of silently looping (INV-CORE-43)
- [ ] 2.6 Verify both phases still share one `start` timestamp and that each `TimeoutError` message names its phase distinguishably (INV-CORE-46) — the two strings are the historical signal in 322 stored records
- [ ] 2.7 **C4**: give every `Command` in `android.py` that addresses a device an explicit timeout, including `adb install` (from `RV_APK_INSTALL_TIMEOUT`), `adb emu kill`, `adb uninstall` and `pm grant` (INV-CORE-48)
- [ ] 2.8 **C6 (source side)**: confirm `install_apk` still raises `RuntimeError` carrying the exit code and `get_combined_output()`; fix the docstring at `android.py:273`, which claims the device is rooted for write access — false under `-read-only` (P4)
- [ ] 2.8b Fix the `Android` class docstring at `android.py:41-42`, which still advertises "multi-phase verification (boot animation, sys.boot_completed, root, remount)" — phase 3 was removed by gh50 and the file is being edited here anyway (P4)
- [ ] 2.9 **INV-CORE-43 sweep**: fix the discarded `adb root` result at `android.py:283-291`, then grep `util/android/` for other `invoke()` results used without `is_failure()` and record what is found (design Open Question 4)
- [ ] 2.10 Add unit tests for the boot gate: acceptance only on `b"1"`; exit 127 never ends the wait and raises `TimeoutError` at budget end; argv contains no quote or shell tokens; empty stdout continues polling; shared budget across phases; **C3** — a phase-1 probe whose `is_failure()` is `True` with `device offline` in stderr logs the serial and the combined output at the point of detection, identified as a probe failure rather than a not-yet-booted device (core scenario "Broken ADB is reported in seconds"). **`MagicMock().is_failure()` returns a truthy `MagicMock`** — every result mock must set `is_failure.return_value` explicitly
- [ ] 2.11 Add unit tests for timeout resolution: unset → default; valid integer honoured; explicit argument overrides the env; `"30O"` raises `ValueError`; `adb install` command carries a non-`None` timeout
- [ ] 2.12 Run `/rv-test-run rv-android-core`

## 3. Core — Emulator Session (C2, C5, C6)

- [ ] 3.1 **C2**: in `modules/rv-android-core/src/rv_android_core/util/android/emulator_manager.py`, restructure `start_emulator` by **nesting**: an outer `try` whose `finally` performs the existing teardown wraps everything; an inner `try/except` around the startup sequence only raises `EmulatorError`; the `yield` sits after that inner block, inside the outer `try` (INV-CORE-49).
      **Do NOT write two sibling blocks.** `try/except` for startup followed by a separate `try: yield / finally: teardown` looks equivalent, but a startup failure raises out of the first block and never enters the second — teardown would not run and task 3.2 would guarantee the orphan it exists to prevent
- [ ] 3.2 **C5**: move `self._active_emulators.add(avd_name)` to before `self.android.start_emulator(...)` so the teardown `finally` reclaims the port on a failed boot (INV-CORE-50)
- [ ] 3.3 Make the post-kill `time.sleep(10)` in `Android.kill_emulator` (`android.py:139`) conditional on the kill having succeeded (INV-CORE-52, design D4) — it exists to let the port be released, which is meaningless when nothing was killed
- [ ] 3.4 **C6**: stop `install_app` from discarding the ADB reason; carry the text preserved by `install_apk` up so it reaches the task's `error_message` (INV-CORE-51). Resolve design Open Question 2 (exception attribute vs result object) here and record the choice in this file
- [ ] 3.5 Correct the return annotation of `start_emulator` from `Android` to `Iterator[Android]` — it is a `@contextmanager`
- [ ] 3.6 Add unit tests: an exception raised in the `with` body reaches the caller with its original type; a genuine startup failure is still `EmulatorError` with the original as `cause`; a failed boot triggers `adb emu kill` for the registered AVD and leaves no orphan; an install failure carries `INSTALL_FAILED_*` upward, including through the signature-mismatch retry
- [ ] 3.6b Add the teardown-coverage tests that the nesting in 3.1 exists for: teardown runs when the `with` body raises **and** when startup itself raises before the `yield` is ever reached (core scenario "Teardown runs when startup itself fails"). A sibling-block implementation passes the first and fails the second — this pair is what distinguishes the two structures
- [ ] 3.6c Add a unit test that the post-kill settling delay is skipped when `adb emu kill` reports failure, and taken when it succeeds (INV-CORE-52)
- [ ] 3.7 Run `/rv-test-run rv-android-core`

## 4. Platform — Device Resolution (§6.3)

- [ ] 4.1 In `modules/rv-platform/src/rv_platform/components/emulator.py`, resolve `device_port` and `device_serial` from a single derivation so a task supplying only one key cannot boot one device and install on another (INV-PLT-28). The serial must follow from the port actually booted
- [ ] 4.2 Add unit tests: full parameters honoured as today; `{"device_port": 5558}` alone yields serial `"emulator-5558"`, not the independent `"emulator-5554"` fallback; neither key yields the 5554 defaults
- [ ] 4.3 Run `/rv-test-run rv-platform`

## 5. Platform — Finalization Owner (§6.4)

- [ ] 5.1 In `modules/rv-platform/src/rv_platform/execution/executor.py`, wrap the body of the `with` in `_run_emulator_session()` in `try/finally` and delete the inline block at `:440-448` entirely — no commented-out remnant (P3, INV-PLT-29)
- [ ] 5.2 Have the `finally` call `logcat_component.cleanup(context)` then `coverage_component.cleanup(context)`, in that order, guarded by the existing `if <component>` checks (INV-PLT-30, INV-PLT-31)
- [ ] 5.3 Confirm `CoverageComponent.cleanup()` and `LogcatComponent.cleanup()` are left in place and still reached by `_cleanup_components()` — INV-PLT-06 and the uniform duck-typed lifecycle both depend on it (design D5)
- [ ] 5.4 Replace the comment at `executor.py:435` with one stating the logcat→coverage order **and its reason** (producer stops first so the consumer's drain sees a frozen file); no migration history (P4)
- [ ] 5.5 Correct **every** documented statement of the old order to the new one, each carrying the reason (producer stops first so the consumer's drain sees a frozen file) — INV-PLT-31 requires correction with a reason, not deletion:
      - `docs/architecture/rv-platform.md:888` — "stop must precede logcat stop in the executor"
      - `docs/architecture/rv-platform.md:262` — "the executor stops coverage first ... then stops logcat capture"
      - `docs/architecture/subsystem-rv-experiment.md:279` — "teardown unwinds coverage first and logcat last so metrics finalize against a complete log"
      - `docs/architecture/subsystem-rv-experiment.md:816` — same claim, same wording
      The `subsystem-rv-experiment.md` pair states a *reason* that is inverted (coverage is the reader, logcat the writer); replace the reason, do not just flip the order
- [ ] 5.5b Grep `docs/` and `modules/*/CLAUDE.md` for any remaining assertion of the coverage-before-logcat order and record the result, so the sweep is demonstrably complete rather than assumed
- [ ] 5.6 Add unit tests: both `cleanup()` calls happen in order and before `adb emu kill` on the success path; the same on the failure path, with the original exception still propagating; an error inside `cleanup()` does not mask the original exception; the repeat call from `_cleanup_components` is inert and leaves `coverage_metrics` unchanged
- [ ] 5.7 Add a grep assertion that `executor.py` contains no direct call to `stop_tracking`, `process_results` or `stop_capture`
- [ ] 5.7b Add the INV-PLT-27 test: when the boot wait exhausts its budget, `EmulatorComponent.install_app()` is never called and the task's `error_message` does not contain `"Failed to install application"` (platform scenario "Installation is not attempted against a device that did not boot")
- [ ] 5.8 Run `/rv-test-run rv-platform`

## 6. Coverage — Final Drain (C8)

- [ ] 6.1 In `modules/rv-coverage/src/rv_coverage/analysis/coverage/tracker.py`, add a final drain to the `_track_coverage` thread's `finally`: read forward from the handle's current position to EOF under `_reader_lock` and process those lines through the existing path, **before** `flush_diagnostics()` (INV-ANA-53)
- [ ] 6.2 Ensure the drain reads forward only, never reprocessing consumed lines, so violations are not double-counted (INV-ANA-54)
- [ ] 6.3 Catch and log read errors during the drain; `stop()` must not raise, because the platform now calls it from a `finally` (INV-ANA-53)
- [ ] 6.4 Preserve the `if not self.is_running: return` guard in `stop()` (INV-ANA-55)
- [ ] 6.5 Add unit tests with a real temp file and real thread: lines appended after the last tail iteration are recovered; no double counting; drain precedes `flush_diagnostics`; `OSError` during drain does not propagate; stopping an already-stopped tracker is inert
- [ ] 6.6 Add the INV-PLT-18 round-trip test: with the producer stopped first, live `repository.calculate_metrics().to_dict()` equals the result of `parse_logcat_file` over the same file, within `0.01`, for every coverage and error field
- [ ] 6.7 Run `/rv-test-run rv-coverage`

## 7. Monitoring — Error Bucket Classification (C7)

- [ ] 7.1 In `experimento-20260706/scripts/rv_status.py:49-55`, classify on the most specific signal first (design D8): match `did not boot within`, `sys.boot_completed not set within`, and the composite `Failed to start emulator .* Failed to install application` explicitly, before the existing generic keyword buckets. Reordering alone is insufficient — `("timeout", ...)` currently captures every boot `TimeoutError` because `EmulatorError.__str__` embeds the cause type
- [ ] 7.1b Apply the identical correction to `experimento-20260604/scripts/rv_status.py:49-55` — the `ERROR_BUCKETS` block is byte-identical in both copies, so fixing one leaves the other misreporting the same runs
- [ ] 7.2 Add the new boot-failure message forms introduced by Groups 2-3 to the specific set
- [ ] 7.3 Add table-driven tests over verbatim `error_message` strings taken from stored artifacts, asserting that both boot signatures and the composite install message classify as `emulator/boot`, and that a genuine tool timeout still classifies as `timeout`. Neither `experimento-*/` tree has test infrastructure, so these live at `tests/lint/test_rv_status_buckets.py` alongside the other repo-level script tests, importing both copies by path and running the same table against each

## 8. Docker and Compose Surfaces

- [ ] 8.1 Add the three variables to the `environment:` blocks (or the `&rvandroid-env` YAML anchor in `docker/docker-compose.parallel.yml:10-21`) of the composes that expose `/dev/kvm`. The instrumentation-only composes do not need them
- [ ] 8.2 Extend `tests/integration/test_validate_env_vars.bats` to cover the three new names, asserting `validate_env_vars.sh` accepts them rather than exiting 64
- [ ] 8.3 Run `bats tests/integration/test_validate_env_vars.bats`

## 9. Test Rewrites (breaking by design)

These two files encode the old contract. Their failure during Groups 2-6 is expected, not a regression signal.

- [ ] 9.1 Rewrite `modules/rv-android-core/tests/unit/test_emulator_boot_retry.py` against the new contract. All 5 cases break: introducing the `is_failure()` guard makes every `MagicMock` result read as failed, and phase 2 no longer accepts `stdout=b""`. Set `is_failure.return_value` explicitly on every result mock
- [ ] 9.2 Remove the stale `# Phase 3 root done` / `# Phase 3 remount done` `side_effect` entries and their comments — dead since gh50 removed phase 3, never consumed (P4)
- [ ] 9.3 Replace the counted `time.time()` `side_effect` lists in both files with a monotonic fake clock, so the tests stop encoding exact call counts and stop breaking on unrelated future edits (design Risks)
- [ ] 9.4 Update `modules/rv-android-core/tests/util/android/test_android.py`: the exact-argv assertion, the exact log-string assertions including `"(timeout=180s)"`, the 3-element `Command` `side_effect` list in the `install_apk` test, and `patch("time.time", side_effect=range(20))` all fail on a correct change
- [ ] 9.5 Review `modules/rv-android-core/tests/util/android/test_emulator_manager.py` and `modules/rv-platform/tests/components/test_emulator.py` for assertions coupled to the old `EmulatorError` relabelling or the old device-resolution defaults
- [ ] 9.6 Run `/rv-test-run rv-android-core` and `/rv-test-run rv-platform`

## 10. Integration and Verification

- [ ] 10.1 Run the full affected suites: `uv run pytest --import-mode=importlib -o "addopts=" modules/rv-android-core/tests/ modules/rv-platform/tests/ modules/rv-coverage/tests/`
- [ ] 10.2 Run `/rv-qa-lint-fix rv-android-core`, `/rv-qa-lint-fix rv-platform`, `/rv-qa-lint-fix rv-coverage`
- [ ] 10.3 Run `/rv-verify rv-android-core`, `/rv-verify rv-platform`, `/rv-verify rv-coverage`
- [ ] 10.4 E2E local, single container. This is the only run this change commissions, so its configuration is fixed here rather than left to the implementer:

      `uv run rv-experiment run --tools monkey --apks-dir apks_examples --timeouts 120 --repetitions 1 --specification-set jca --name gh92_e2e`

      - `monkey` because it is deterministic, needs no SGLang and no external jar — it isolates the emulator layer from tool variance, which is what is under test
      - **no `--skip-monitors` / `--skip-instrument` / `--skip-static`**: `apks_examples/cryptoapp.apk` is the original APK, and skipping instrumentation would report 0 % coverage, which would silently void the coverage assertion below. Requires `RVSEC_HOME`. Pre-processing dominates the wall clock here, not the 120 s tool budget
      - emulator lifecycle is managed entirely by rv-platform; no manual emulator commands

      Assertions over the resulting `tasks.json`:
      - `tool_execution_start` is no longer `null`
      - the composite `Failed to start emulator ... Failed to install application` message is absent
      - `method_coverage > 0` — proof the instrumented APK actually ran and the tracker consumed its logcat

- [ ] 10.4b **C6 end to end.** The happy path never fails an installation, so the C6 acceptance criterion ("the ADB reason is verified in an artifact") has no procedure without one. Force a real failure inside the same run: install a differently-signed build of `cryptoapp` first, so the instrumented APK hits `INSTALL_FAILED_UPDATE_INCOMPATIBLE`. Assert the stored `error_message` carries the `INSTALL_FAILED_*` text and the ADB exit code — not the bare `"Failed to install application"`. This also exercises the signature-mismatch retry path in `install_apk`, which is otherwise only covered by mocks
- [ ] 10.4c **C8 round trip on a real task.** Unit test 6.6 proves the drain over a temp file; this proves it over an artifact the system actually produced. For the `COMPLETED` task from 10.4, compare the `coverage_metrics` stored live against re-parsing its `.logcat` with `parse_logcat_file`, and assert equality within `0.01` for every coverage and error field (INV-PLT-18). Without C8 this comparison is what would drift
- [ ] 10.5 Record the boot `elapsed` and the `adb install` duration that the 10.4 run produced (logged at `android.py:223-224`) in this file. One task is one boot, so this confirms the instrumentation emits the value and gives an order of magnitude — it is not a distribution and MUST NOT be written up as one
- [ ] 10.6 Record in `design.md` D9 that the boot-time distribution under contention is **deferred to production observation**, and write the procedure there: on the first real experiment run after this change lands, read the `emulator/boot` bucket from `rv_status.py` (now populated, per C7) and the `elapsed` values from the container logs; if boot `TimeoutError`s appear, raise `RV_EMULATOR_BOOT_TIMEOUT` in the compose. No dedicated validation run is commissioned — a 0.86 % historical failure rate needs ~350 tasks before an absence of failures is evidence, which is not a cost this change carries
- [ ] 10.7 Choose the `RV_APK_INSTALL_TIMEOUT` default by judgement rather than measurement (no distribution will exist), record the reasoning in `design.md` Open Question 1, and set it in `.env.example`, `README.md` and the composes. Err long: the failure mode of a value set too low is killing a healthy slow install, and the value is adjustable per host without a rebuild
- [ ] 10.8 Invoke `/rv-code-reviewer` via the Skill tool for the whole change
- [ ] 10.9 Run `/rv-docs-sync rv-platform` and `/rv-docs-sync rv-android-core` — `docs/architecture/rv-platform.md` and `docs/architecture/subsystem-rv-experiment.md` changed in task 5.5, and the `CLAUDE.md` / `.claude/project-info.md` env tables changed in task 1.4. `subsystem-rv-experiment.md` is outside `/rv-docs-sync rv-platform`'s scope, so confirm task 5.5's edits there survived rather than assuming the skill covered them
- [ ] 10.10 Check off every satisfied acceptance criterion in issue #92 before closing (WORKFLOW §2 rule 6)
