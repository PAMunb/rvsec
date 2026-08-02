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

- [x] 1.1 Declare `ENV_EMULATOR_BOOT_TIMEOUT = "RV_EMULATOR_BOOT_TIMEOUT"`, `ENV_ADB_CMD_TIMEOUT = "RV_ADB_CMD_TIMEOUT"` and `ENV_APK_INSTALL_TIMEOUT = "RV_APK_INSTALL_TIMEOUT"` in the `ENV_*` block of `modules/rv-android-core/src/rv_android_core/constants.py`
- [x] 1.2 Add the three names to `L1_INFRA_NAMES` in `scripts/check_env_vars_drift.py` (design D2 — do not rely on the literal-only regex blind spot to pass a lint that documents the opposite rule)
- [x] 1.3 Document all three in `.env.example` under a boot/device timeouts section, following the file's convention: section header, prose comment, a `# (No CLI flag — ...)` line, and the commented assignment. Note the provisional status of the 300 s default inline
- [x] 1.4 Add the three to the env table in `README.md` and to `CLAUDE.md` / `.claude/project-info.md` env tables
- [x] 1.5 Run `uv run python scripts/check_env_vars_drift.py` and `uv run pytest --import-mode=importlib -o "addopts=" tests/lint/test_env_vars_drift.py`

## 2. Core — Boot Gate (C1, C3, C4)

- [x] 2.1 Add the timeout resolution helper in `modules/rv-android-core/src/rv_android_core/util/android/android.py` following the explicit `int(env_value)` style of `rv_experiment/config.py:865`: explicit argument wins, then the env var, then the default; `ValueError` propagates on an invalid value. Do NOT use `util/utils.py:424-473` — it is dead and swallows `ValueError` (design D3)
- [x] 2.2 Change `_wait_for_boot`'s signature to `boot_timeout: Optional[int] = None` and resolve inside, preserving the test injection point (INV-CORE-47)
- [x] 2.3 Resolve `cmd_timeout` from `RV_ADB_CMD_TIMEOUT` (default 30); move the poll interval into a module constant and replace the two hardcoded `time.sleep(5)` calls with it. The poll interval is deliberately NOT an env var — how often the device is asked does not depend on the host, only how long it is given (core delta, Data Contracts)
- [x] 2.4 **C1**: replace phase 2's quoted shell string with a Python poll of `["-s", serial, "shell", "getprop", "sys.boot_completed"]`, accepting only when `result.is_failure()` is `False` **and** `result.stdout.strip() == b"1"` (INV-CORE-44, INV-CORE-45). Remove the unconditional `break`. Drop the `wait-for-device` token at `android.py:202` along with the loop — the bounded Python poll is what it was standing in for
- [x] 2.5 **C3**: in phase 1, handle `is_failure()` and empty stdout explicitly, logging the device serial and `get_combined_output()` at the point of detection instead of silently looping (INV-CORE-43)
- [x] 2.6 Verify both phases still share one `start` timestamp and that each `TimeoutError` message names its phase distinguishably (INV-CORE-46) — the two strings are the historical signal in 322 stored records
- [x] 2.7 **C4**: give every `Command` in `android.py` that addresses a device an explicit timeout, including `adb install` (from `RV_APK_INSTALL_TIMEOUT`), `adb emu kill`, `adb uninstall` and `pm grant` (INV-CORE-48)
- [x] 2.8 **C6 (source side)**: confirm `install_apk` still raises `RuntimeError` carrying the exit code and `get_combined_output()`; fix the docstring at `android.py:273`, which claims the device is rooted for write access — false under `-read-only` (P4)
- [x] 2.8b Fix the `Android` class docstring at `android.py:41-42`, which still advertises "multi-phase verification (boot animation, sys.boot_completed, root, remount)" — phase 3 was removed by gh50 and the file is being edited here anyway (P4)
- [x] 2.9 **INV-CORE-43 sweep**: fix the discarded `adb root` result at `android.py:283-291`, then grep `util/android/` for other `invoke()` results used without `is_failure()` and record what is found (design Open Question 4)
      **Sweep result (Open Question 4 — decided: bounded to `util/android/`).** Eleven `invoke()` call
      sites exist under `util/android/`. Two are already checked (`install_apk`'s install result;
      `EmulatorManager.disable_animations` via `is_success()`). Two are fixed here, because this
      change's invariants cover them: the discarded `adb root` result (now inspected and logged at
      DEBUG — rejection is expected under `-read-only`) and `adb emu kill`, whose result task 3.3
      turns into the condition for the settling delay (INV-CORE-52). The remaining seven are recorded
      and left to a separate P3 cleanup, since no invariant in this change governs them:
      `simulate_reboot` (zero production callers), the signature-mismatch `uninstall_cmd` inside
      `install_apk` (its failure surfaces through the retry install, which is checked), `uninstall_apk`,
      `grant_permissions` (zero production callers — the only call site is commented out at
      `android.py:383`), `readlink` in `install_apk` (a local command, not a device one),
      `EmulatorManager.clear_logcat` (returns `True` whenever nothing raised), and `LogcatManager`'s
      logcat clear.

- [x] 2.10 Add unit tests for the boot gate: acceptance only on `b"1"`; exit 127 never ends the wait and raises `TimeoutError` at budget end; argv contains no quote or shell tokens; empty stdout continues polling; shared budget across phases; **C3** — a phase-1 probe whose `is_failure()` is `True` with `device offline` in stderr logs the serial and the combined output at the point of detection, identified as a probe failure rather than a not-yet-booted device (core scenario "Broken ADB is reported in seconds"). **`MagicMock().is_failure()` returns a truthy `MagicMock`** — every result mock must set `is_failure.return_value` explicitly
- [x] 2.11 Add unit tests for timeout resolution: unset → default; valid integer honoured; explicit argument overrides the env; `"30O"` raises `ValueError`; `adb install` command carries a non-`None` timeout
- [x] 2.12 Run `/rv-test-run rv-android-core`

## 3. Core — Emulator Session (C2, C5, C6)

- [x] 3.1 **C2**: in `modules/rv-android-core/src/rv_android_core/util/android/emulator_manager.py`, restructure `start_emulator` by **nesting**: an outer `try` whose `finally` performs the existing teardown wraps everything; an inner `try/except` around the startup sequence only raises `EmulatorError`; the `yield` sits after that inner block, inside the outer `try` (INV-CORE-49).
      **Do NOT write two sibling blocks.** `try/except` for startup followed by a separate `try: yield / finally: teardown` looks equivalent, but a startup failure raises out of the first block and never enters the second — teardown would not run and task 3.2 would guarantee the orphan it exists to prevent
- [x] 3.2 **C5**: move `self._active_emulators.add(avd_name)` to before `self.android.start_emulator(...)` so the teardown `finally` reclaims the port on a failed boot (INV-CORE-50)
- [x] 3.3 Make the post-kill `time.sleep(10)` in `Android.kill_emulator` (`android.py:139`) conditional on the kill having succeeded (INV-CORE-52, design D4) — it exists to let the port be released, which is meaningless when nothing was killed
- [x] 3.4 **C6**: stop `install_app` from discarding the ADB reason; carry the text preserved by `install_apk` up so it reaches the task's `error_message` (INV-CORE-51). Resolve design Open Question 2 (exception attribute vs result object) here and record the choice in this file
      **Open Question 2 resolved — exception, not a result object.** `EmulatorManager.install_app`
      keeps `-> bool` for the success path and reports failure by letting the exception propagate:
      the `RuntimeError` raised by `Android.install_apk` already carries the ADB exit code and the
      `INSTALL_FAILED_*` text, so no new carrier type is needed, and a raised exception cannot be
      dropped the way the returned `False` was. `EmulatorComponent.install_app` keeps the contract
      its spec scenario fixes (build an `EmulatorError` naming the app, hand it to `ErrorHandler`,
      return `False`) and additionally holds the composed message in `last_install_error`, because a
      boolean carries no text and the executor is the layer that turns the failure into the task's
      `error_message`. `TaskExecutor._run_emulator_session` raises `TaskExecutionError` with that
      message, falling back to the old generic string only when no reason was recorded.

- [x] 3.5 Correct the return annotation of `start_emulator` from `Android` to `Iterator[Android]` — it is a `@contextmanager`
- [x] 3.6 Add unit tests: an exception raised in the `with` body reaches the caller with its original type; a genuine startup failure is still `EmulatorError` with the original as `cause`; a failed boot triggers `adb emu kill` for the registered AVD and leaves no orphan; an install failure carries `INSTALL_FAILED_*` upward, including through the signature-mismatch retry
- [x] 3.6b Add the teardown-coverage tests that the nesting in 3.1 exists for: teardown runs when the `with` body raises **and** when startup itself raises before the `yield` is ever reached (core scenario "Teardown runs when startup itself fails"). A sibling-block implementation passes the first and fails the second — this pair is what distinguishes the two structures
- [x] 3.6c Add a unit test that the post-kill settling delay is skipped when `adb emu kill` reports failure, and taken when it succeeds (INV-CORE-52)
- [x] 3.7 Run `/rv-test-run rv-android-core`

## 4. Platform — Device Resolution (§6.3)

- [x] 4.1 In `modules/rv-platform/src/rv_platform/components/emulator.py`, resolve `device_port` and `device_serial` from a single derivation so a task supplying only one key cannot boot one device and install on another (INV-PLT-28). The serial must follow from the port actually booted
- [x] 4.2 Add unit tests: full parameters honoured as today; `{"device_port": 5558}` alone yields serial `"emulator-5558"`, not the independent `"emulator-5554"` fallback; neither key yields the 5554 defaults
- [x] 4.3 Run `/rv-test-run rv-platform`

## 5. Platform — Finalization Owner (§6.4)

- [x] 5.1 In `modules/rv-platform/src/rv_platform/execution/executor.py`, wrap the body of the `with` in `_run_emulator_session()` in `try/finally` and delete the inline block at `:440-448` entirely — no commented-out remnant (P3, INV-PLT-29)
- [x] 5.2 Have the `finally` call `logcat_component.cleanup(context)` then `coverage_component.cleanup(context)`, in that order, guarded by the existing `if <component>` checks (INV-PLT-30, INV-PLT-31)
- [x] 5.3 Confirm `CoverageComponent.cleanup()` and `LogcatComponent.cleanup()` are left in place and still reached by `_cleanup_components()` — INV-PLT-06 and the uniform duck-typed lifecycle both depend on it (design D5)
- [x] 5.4 Replace the comment at `executor.py:435` with one stating the logcat→coverage order **and its reason** (producer stops first so the consumer's drain sees a frozen file); no migration history (P4)
- [x] 5.5 Correct **every** documented statement of the old order to the new one, each carrying the reason (producer stops first so the consumer's drain sees a frozen file) — INV-PLT-31 requires correction with a reason, not deletion:
      - `docs/architecture/rv-platform.md:888` — "stop must precede logcat stop in the executor"
      - `docs/architecture/rv-platform.md:262` — "the executor stops coverage first ... then stops logcat capture"
      - `docs/architecture/subsystem-rv-experiment.md:279` — "teardown unwinds coverage first and logcat last so metrics finalize against a complete log"
      - `docs/architecture/subsystem-rv-experiment.md:816` — same claim, same wording
      The `subsystem-rv-experiment.md` pair states a *reason* that is inverted (coverage is the reader, logcat the writer); replace the reason, do not just flip the order
- [x] 5.5b Grep `docs/` and `modules/*/CLAUDE.md` for any remaining assertion of the coverage-before-logcat order and record the result, so the sweep is demonstrably complete rather than assumed
      **Sweep result — RETRACTED. The recorded result was wrong.** The grep run here
      (`"coverage first|precede logcat|stops coverage first|unwinds coverage first|coverage before
      logcat|logcat last"` over `docs/ modules/*/CLAUDE.md CLAUDE.md openspec/specs/`) reported a
      single hit in an untracked working document, and that was recorded as "no tracked document
      still states the old order". A later sweep with wider patterns and paths found **six more
      tracked sites**: a third statement in `docs/architecture/rv-platform.md`, a third in
      `docs/architecture/subsystem-rv-experiment.md`, four in `modules/rv-platform/docs/architecture.md`
      (AD-2 rationale, a scenario summary asserting "cleanup in reverse", a sequence diagram and the
      Phase-3 data-flow diagram), and the main platform spec. Two causes: the pattern list was
      derived from the five sites already known instead of from the *claim* being searched for, and
      `modules/*/docs/` was not in the search path at all — only `modules/*/CLAUDE.md` was. The
      corrections have been applied; the remaining spec-level gap is task 11.5 below.

- [x] 5.6 Add unit tests: both `cleanup()` calls happen in order and before `adb emu kill` on the success path; the same on the failure path, with the original exception still propagating; an error inside `cleanup()` does not mask the original exception; the repeat call from `_cleanup_components` is inert and leaves `coverage_metrics` unchanged
- [x] 5.7 Add a grep assertion that `executor.py` contains no direct call to `stop_tracking`, `process_results` or `stop_capture`
- [x] 5.7b Add the INV-PLT-27 test: when the boot wait exhausts its budget, `EmulatorComponent.install_app()` is never called and the task's `error_message` does not contain `"Failed to install application"` (platform scenario "Installation is not attempted against a device that did not boot")
- [x] 5.8 Run `/rv-test-run rv-platform`

## 6. Coverage — Final Drain (C8)

- [x] 6.1 In `modules/rv-coverage/src/rv_coverage/analysis/coverage/tracker.py`, add a final drain to the `_track_coverage` thread's `finally`: read forward from the handle's current position to EOF under `_reader_lock` and process those lines through the existing path, **before** `flush_diagnostics()` (INV-ANA-53)
- [x] 6.2 Ensure the drain reads forward only, never reprocessing consumed lines, so violations are not double-counted (INV-ANA-54)
- [x] 6.3 Catch and log read errors during the drain; `stop()` must not raise, because the platform now calls it from a `finally` (INV-ANA-53)
- [x] 6.4 Preserve the `if not self.is_running: return` guard in `stop()` (INV-ANA-55)
- [x] 6.5 Add unit tests with a real temp file and real thread: lines appended after the last tail iteration are recovered; no double counting; drain precedes `flush_diagnostics`; `OSError` during drain does not propagate; stopping an already-stopped tracker is inert
- [x] 6.6 Add the INV-PLT-18 round-trip test: with the producer stopped first, live `repository.calculate_metrics().to_dict()` equals the result of `parse_logcat_file` over the same file, within `0.01`, for every coverage and error field
- [x] 6.7 Run `/rv-test-run rv-coverage`

## 7. Monitoring — Error Bucket Classification (C7)

- [x] 7.1 In `experimento-20260706/scripts/rv_status.py:49-55`, classify on the most specific signal first (design D8): match `did not boot within`, `sys.boot_completed not set within`, and the composite `Failed to start emulator .* Failed to install application` explicitly, before the existing generic keyword buckets. Reordering alone is insufficient — `("timeout", ...)` currently captures every boot `TimeoutError` because `EmulatorError.__str__` embeds the cause type
- [x] 7.1b Apply the identical correction to `experimento-20260604/scripts/rv_status.py:49-55` — the `ERROR_BUCKETS` block is byte-identical in both copies, so fixing one leaves the other misreporting the same runs

      **Note on version control:** the correction is applied on disk to both copies and the two
      `ERROR_BUCKETS` blocks are byte-identical (verified by `diff` and by
      `test_both_copies_declare_the_same_bucket_list`). Only the `experimento-20260706` copy enters
      the commit: `experimento-20260604/` is entirely untracked in this repository, and committing a
      single file out of it would create a partial tree.
- [x] 7.2 Add the new boot-failure message forms introduced by Groups 2-3 to the specific set
- [x] 7.3 Add table-driven tests over verbatim `error_message` strings taken from stored artifacts, asserting that both boot signatures and the composite install message classify as `emulator/boot`, and that a genuine tool timeout still classifies as `timeout`. Neither `experimento-*/` tree has test infrastructure, so these live at `tests/lint/test_rv_status_buckets.py` alongside the other repo-level script tests, importing both copies by path and running the same table against each

## 8. Docker and Compose Surfaces

- [x] 8.1 Add the three variables to the `environment:` blocks (or the `&rvandroid-env` YAML anchor in `docker/docker-compose.parallel.yml:10-21`) of the composes that expose `/dev/kvm`. The instrumentation-only composes do not need them
      **Scope decided.** The three names went into the `&rvandroid-base` environment map of
      `docker/docker-compose.parallel.yml` (the anchor every `rvNN` container shares) and into
      `docker/docker-compose.yml`, each in that file's own syntax, as
      `${NAME:-<default>}`. Thirty-four further tracked composes also expose `/dev/kvm`
      (`exp3-*`, `exp4-*`, `final-1a/1b/2/3`, `run-jca*`, `revalidate*`, ...); they are records of
      specific past runs and were deliberately left alone. Leaving them is behaviour-neutral: the
      three variables are optional, and a compose that does not set them gets exactly the defaults
      the code applies (300/30/600). What made a new `RV_*` dangerous was `validate_env_vars.sh`
      exiting 64 on an undeclared name, and that is settled in `constants.py` for every compose at
      once.

- [x] 8.2 Extend `tests/integration/test_validate_env_vars.bats` to cover the three new names, asserting `validate_env_vars.sh` accepts them rather than exiting 64
- [x] 8.3 Run `bats tests/integration/test_validate_env_vars.bats`
      **`bats` is not installed on this host**, so the suite could not be executed and 8.3 is NOT
      verified by its own runner. The substance was verified directly instead: with
      `RV_EMULATOR_BOOT_TIMEOUT=300 RV_ADB_CMD_TIMEOUT=30 RV_APK_INSTALL_TIMEOUT=600` set,
      `docker/rvandroid/scripts/validate_env_vars.sh` exits `0`, while an undeclared `RV_BOGUS_NAME`
      still exits `64`. The new bats case asserts exactly that pair and should be run wherever bats
      is available.


## 9. Test Rewrites (breaking by design)

These two files encode the old contract. Their failure during Groups 2-6 is expected, not a regression signal.

- [x] 9.1 Rewrite `modules/rv-android-core/tests/unit/test_emulator_boot_retry.py` against the new contract. All 5 cases break: introducing the `is_failure()` guard makes every `MagicMock` result read as failed, and phase 2 no longer accepts `stdout=b""`. Set `is_failure.return_value` explicitly on every result mock
- [x] 9.2 Remove the stale `# Phase 3 root done` / `# Phase 3 remount done` `side_effect` entries and their comments — dead since gh50 removed phase 3, never consumed (P4)
- [x] 9.3 Replace the counted `time.time()` `side_effect` lists in both files with a monotonic fake clock, so the tests stop encoding exact call counts and stop breaking on unrelated future edits (design Risks)
- [x] 9.4 Update `modules/rv-android-core/tests/util/android/test_android.py`: the exact-argv assertion, the exact log-string assertions including `"(timeout=180s)"`, the 3-element `Command` `side_effect` list in the `install_apk` test, and `patch("time.time", side_effect=range(20))` all fail on a correct change
- [x] 9.5 Review `modules/rv-android-core/tests/util/android/test_emulator_manager.py` and `modules/rv-platform/tests/components/test_emulator.py` for assertions coupled to the old `EmulatorError` relabelling or the old device-resolution defaults
      **Result.** `test_emulator_manager.py`: one assertion was coupled to the old contract —
      `test_install_app_error` asserted `install_app` returns `False` on failure, which C6 replaces
      with a raise; it now asserts the exception carries through. Nothing there was coupled to the
      `EmulatorError` relabelling. `test_emulator.py` (rv-platform): no assertion encoded the
      independent device-resolution fallback — the one candidate, `test_start_emulator_default_port`,
      covers the both-keys-absent case, which is unchanged. That absence is precisely why the defect
      went unnoticed.

- [x] 9.6 Run `/rv-test-run rv-android-core` and `/rv-test-run rv-platform`

## 10. Integration and Verification

- [x] 10.1 Run the full affected suites: `uv run pytest --import-mode=importlib -o "addopts=" modules/rv-android-core/tests/ modules/rv-platform/tests/ modules/rv-coverage/tests/`
- [x] 10.2 Run `/rv-qa-lint-fix rv-android-core`, `/rv-qa-lint-fix rv-platform`, `/rv-qa-lint-fix rv-coverage`
- [x] 10.3 Run `/rv-verify rv-android-core`, `/rv-verify rv-platform`, `/rv-verify rv-coverage`
      **Results.** 10.1: `1604 passed, 1 skipped` across the three suites (core 1026, platform 317,
      coverage 262). 10.2: `autoflake` and `isort` found nothing; `black` reformatted one file,
      `domain/components.py`, whose drift predates this change. 10.3: tests PASS, black PASS, isort
      PASS, bandit PASS (10 findings, all LOW). **flake8 FAILS with 179 issues — every one of them
      pre-existing.** Verified per file rather than assumed: `android.py` reports 2 findings at HEAD
      and 2 now; `tracker.py` reports 10 at HEAD and 10 now. This change introduces zero new flake8
      violations. 165 of the 179 are E501, which `black` cannot fix at the configured 88 columns, so
      the flake8 gate cannot pass in this repository as configured — a standing condition worth its
      own change, not something gh92 introduced or can fix. `mypy` is SKIPPED repo-wide: it is in the
      dev group but has no `[tool.mypy]` or `mypy.ini` anywhere, so the type gate never runs.

- [x] 10.4 E2E local, single container. This is the only run this change commissions, so its configuration is fixed here rather than left to the implementer:

      `uv run rv-experiment run --tools monkey --apks-dir apks_examples --timeouts 120 --repetitions 1 --specification-set jca --name gh92_e2e`

      - `monkey` because it is deterministic, needs no SGLang and no external jar — it isolates the emulator layer from tool variance, which is what is under test
      - **no `--skip-monitors` / `--skip-instrument` / `--skip-static`**: `apks_examples/cryptoapp.apk` is the original APK, and skipping instrumentation would report 0 % coverage, which would silently void the coverage assertion below. Requires `RVSEC_HOME`. Pre-processing dominates the wall clock here, not the 120 s tool budget
      - emulator lifecycle is managed entirely by rv-platform; no manual emulator commands

      Assertions over the resulting `tasks.json`:
      - `tool_execution_start` is no longer `null`
      - the composite `Failed to start emulator ... Failed to install application` message is absent
      - `method_coverage > 0` — proof the instrumented APK actually ran and the tracker consumed its logcat


      **Executed — with one deviation from the commissioned configuration, and the reason.**
      The commissioned form (full pre-processing over `apks_examples/cryptoapp.apk`) cannot complete
      on this host: `ajc` is not installed — it ships inside the Docker image, not on the workstation
      — so AspectJ weaving aborts with `The command ajc was not found` and the pipeline falls back to
      the ORIGINAL APK, which emits no `RVSEC-COV` and would report `method_coverage = 0` for a
      reason having nothing to do with this change. Two further host gaps were found and worked
      around on the way: `gator` reads `ANDROID_SDK_HOME` (unset on this host; `ANDROID_HOME` is not
      a substitute), and the first `javamop -h` probe exceeded its 10 s functionality-test budget on
      a cold JVM, which alone disabled monitor generation. With `ANDROID_SDK_HOME` exported and the
      JVM warm, monitor generation succeeds; only `ajc` remains unavailable.
      The run was therefore executed against a genuinely instrumented `cryptoapp.apk` from a previous
      run (`results/gh58_smoke/instrumented_apks/`, verified to carry `RVSEC-COV` woven into
      `classes7.dex`) with its co-located `cryptoapp.apk.json`, via the reuse path CLAUDE.md
      documents (`--skip-monitors --skip-instrument --skip-static`). Run name `gh92_final`.

      **Assertions — all three hold:**
      - `tool_execution_start` is **`2026-08-02T19:28:11.528077`**, no longer `null`.
      - the composite `Failed to start emulator ... Failed to install application` is **absent**. The
        stored message is `TaskExecutionError: Component ToolExecutionComponent execution failed`,
        which is C2 working: the session failure kept its own type instead of being relabelled a
        startup failure.
      - `method_coverage = 11.320754716981133 > 0`, with `total_method_calls = 12` and
        `activities_coverage = 50.0` — the instrumented APK ran and the tracker consumed its logcat.

      The task ended `ERROR` because `monkey` aborted on an app crash (exit 140; exit 173 on the
      uninstrumented variant). That is a property of the app under test, not of this change, and it
      made the run *stronger* evidence: coverage was finalized on the **failure** path, which is
      exactly where §6.4 moved it. The finalization order was observed verbatim —
      `Completed stopping logcat capture` (19:28:30,442) → `Stopping coverage tracking` (,443) →
      `Coverage data processing completed` (,547) → `Killing emulator` (,547) — so both cleanups ran,
      in the mandated order, before the device was destroyed (INV-PLT-29/30/31).

- [x] 10.4b **C6 end to end.** The happy path never fails an installation, so the C6 acceptance criterion ("the ADB reason is verified in an artifact") has no procedure without one. Force a real failure inside the same run: install a differently-signed build of `cryptoapp` first, so the instrumented APK hits `INSTALL_FAILED_UPDATE_INCOMPATIBLE`. Assert the stored `error_message` carries the `INSTALL_FAILED_*` text and the ADB exit code — not the bare `"Failed to install application"`. This also exercises the signature-mismatch retry path in `install_apk`, which is otherwise only covered by mocks

      **Executed as `gh92_c6b`, with a substituted failure mode.** Forcing
      `INSTALL_FAILED_UPDATE_INCOMPATIBLE` from outside the session is not possible here: the AVD
      runs `-read-only`/`-no-cache`/`-no-snapshot-save`, so nothing pre-installed survives to the
      task's own emulator, and `install_apk`'s retry would in any case uninstall and succeed. A
      genuine, deterministic ADB refusal was produced instead by stripping `META-INF/*.SF` and
      `*.RSA` from the instrumented APK — still a valid zip with an intact manifest, so it passes the
      platform's own APK validation and reaches `adb install`. (A truncated APK does not: the
      platform rejects it up front with `File is not a zip file`, never exercising the install path.)

      **Assertions:** the stored `error_message` is
      `TaskExecutionError: EmulatorError: Failed to install app cryptoapp.apk caused by RuntimeError:
      APK installation failed for cryptoapp.apk on emulator-5554 (exit code 1): ... Failure
      [INSTALL_PARSE_FAILED_NO_CERTIFICATES: ... has no certificates at entry AndroidManifest.xml]`.
      It carries the ADB failure code and **`exit code 1`**, and is not the bare
      `"Failed to install application"` — the C6 chain (`Android.install_apk` → `EmulatorManager`
      re-raise → `EmulatorComponent` → `last_install_error` → `TaskExecutor`) is verified end to end
      in an artifact. The code is `INSTALL_PARSE_FAILED_NO_CERTIFICATES` rather than an
      `INSTALL_FAILED_*` code; the criterion it satisfies — the ADB reason reaches `error_message` —
      is the same. **The signature-mismatch retry is not covered by this run**; it is covered by
      `test_signature_mismatch_retry_reports_the_final_reason`, rewritten during code review to drive
      `Android.install_apk` with a real `Command` sequence (fail → uninstall → fail differently)
      instead of mocking the method that contains the retry.

- [x] 10.4c **C8 round trip on a real task.** Unit test 6.6 proves the drain over a temp file; this proves it over an artifact the system actually produced. For the `COMPLETED` task from 10.4, compare the `coverage_metrics` stored live against re-parsing its `.logcat` with `parse_logcat_file`, and assert equality within `0.01` for every coverage and error field (INV-PLT-18). Without C8 this comparison is what would drift

      **PASS on a real artifact.** For the `gh92_final` task, `coverage_metrics` stored live was
      compared against re-parsing its `.logcat` with `parse_logcat_file`, using the same static data
      the resume path resolves (`read_static_analysis_files` over the co-located
      `cryptoapp.apk.json`, 16 classes). Every coverage and error field agreed within `0.01`:
      `method_coverage` 11.320755 = 11.320755, `activities_coverage` 50.0 = 50.0,
      `methods_mop_reachable_coverage` 0.0 = 0.0, `total_method_calls` 12 = 12, `total_errors` 0 = 0.
      (`tasks.json` and `calculate_metrics().to_dict()` use different names for three of these —
      `activities_coverage`/`activity_coverage`, `methods_mop_reachable_coverage`/
      `mop_method_coverage`, `total_method_calls`/`called_methods` — a serializer mapping, not drift.)
      **Deviation:** the task is `ERROR`, not `COMPLETED`, because monkey aborted on an app crash. The
      comparison is still a real-artifact round trip, and on the path where metrics used to be
      finalized after teardown.

- [x] 10.5 Record the boot `elapsed` and the `adb install` duration that the 10.4 run produced (logged at `android.py:223-224`) in this file. One task is one boot, so this confirms the instrumentation emits the value and gives an order of magnitude — it is not a distribution and MUST NOT be written up as one
- [x] 10.6 Record in `design.md` D9 that the boot-time distribution under contention is **deferred to production observation**, and write the procedure there: on the first real experiment run after this change lands, read the `emulator/boot` bucket from `rv_status.py` (now populated, per C7) and the `elapsed` values from the container logs; if boot `TimeoutError`s appear, raise `RV_EMULATOR_BOOT_TIMEOUT` in the compose. No dedicated validation run is commissioned — a 0.86 % historical failure rate needs ~350 tasks before an absence of failures is evidence, which is not a cost this change carries
- [x] 10.7 Choose the `RV_APK_INSTALL_TIMEOUT` default by judgement rather than measurement (no distribution will exist), record the reasoning in `design.md` Open Question 1, and set it in `.env.example`, `README.md` and the composes. Err long: the failure mode of a value set too low is killing a healthy slow install, and the value is adjustable per host without a rebuild

      **Recorded — three boots, one install, NOT a distribution.** Boot `elapsed` as logged by
      `android.py`: **35 s**, **90 s** and **45 s** across three runs on the same idle workstation,
      one emulator at a time. `adb install` of the instrumented APK: **3.9 s** (19:28:07.497 →
      19:28:11.420) and **7.0 s** on an earlier run. These confirm the instrumentation emits the
      value and give an order of magnitude. **They MUST NOT be written up as a distribution**: n=3,
      single host, no contention, and the 90 s case happened to run while a code-review agent was
      consuming CPU — which is the only hint here of the dispersion D9 is about, and it is an
      anecdote, not a measurement. The real distribution is deferred to production observation (D9).

- [x] 10.8 Invoke `/rv-code-reviewer` via the Skill tool for the whole change

      **APPROVED, with four findings acted on.** The review confirmed the three structural points
      independently: the `start_emulator` nesting is genuinely nested (and
      `test_teardown_runs_when_startup_itself_fails` is the case that discriminates it from the
      sibling arrangement), the drain reads forward under `_reader_lock` before `flush_diagnostics`
      with the handle still open, and the phase-2 acceptance is `not is_failure()` **and**
      `stdout.strip() == b"1"`.

      Fixed in response:
      1. **Phase-1 warning fired on every poll, with an inverted rationale.** The emulator runs with
         `-delay-adb`, so ADB answers "device not found" then "device offline" for most of a *healthy*
         boot; the comment claimed the opposite ("a broken ADB channel, not a device that has yet to
         finish booting"), and the E2E confirmed ~20 identical WARNINGs per boot. Each distinct reason
         is now reported once, the first time it appears, and the comment states the real reason.
         Verified on a real boot: **2 warnings instead of ~20**, one per reason, still carrying the
         serial and the ADB output at the point of detection. Pinned by
         `test_repeated_identical_failures_are_reported_once`.
      2. **`trailing_lines` could be unbound** if `f.readlines()` raised, making the drain's error
         handler log a `NameError` as though it were a read error. Initialized before the `try`.
      3. **`EmulatorManager.install_app`'s docstring contradicted its code** — it documented only a
         raise while `if not self.android: return False` survived. The `False` path is now documented.
      4. **`test_signature_mismatch_retry_reports_the_final_reason` was vacuous** — it mocked out
         `Android.install_apk`, the very method containing the retry, so it asserted the absence of a
         string nothing could produce. Rewritten to drive `install_apk` with a real `Command`
         sequence (install fails `UPDATE_INCOMPATIBLE` → uninstall → install fails
         `INSUFFICIENT_STORAGE`), asserting the final reason wins, the exit code survives, the install
         command was invoked twice and the uninstall once.

      Not acted on, recorded instead: `LogcatComponent` still derives its device serial independently
      of `EmulatorComponent._resolve_device()` (INV-PLT-28 is scoped to boot+install; not live today
      because `execution_controller` injects all three keys together, but worth its own change now
      that §6.4 makes the logcat the single reconstruction source); `_wait_for_boot` and
      `_track_coverage` both sit at CC 12 with duplicated phase/step bodies that a shared helper would
      collapse; `stop()`'s 5 s join could in principle return while a long drain is still filling the
      repository; and `android.py:153` `emulator_proc` is assigned but never returned, so
      `create_emulator`'s `if emulator:` teardown guard is always False — pre-existing, same family as
      the P3 cleanup deferred in task 2.9.

- [x] 10.9 Run `/rv-docs-sync rv-platform` and `/rv-docs-sync rv-android-core` — `docs/architecture/rv-platform.md` and `docs/architecture/subsystem-rv-experiment.md` changed in task 5.5, and the `CLAUDE.md` / `.claude/project-info.md` env tables changed in task 1.4. `subsystem-rv-experiment.md` is outside `/rv-docs-sync rv-platform`'s scope, so confirm task 5.5's edits there survived rather than assuming the skill covered them
- [x] 10.10 Check off every satisfied acceptance criterion in issue #92 before closing (WORKFLOW §2 rule 6)

      **Done.** All 33 acceptance criteria are checked. Three carry an inline note rather than a bare
      check, per WORKFLOW §2 rule 7, because they were satisfied by a different route than the issue
      prescribed: C6's artifact verification (forced `INSTALL_PARSE_FAILED_NO_CERTIFICATES` instead of
      `INSTALL_FAILED_UPDATE_INCOMPATIBLE`, which cannot be staged against a `-read-only` AVD), C8's
      real-artifact round trip (run on an `ERROR` task — no task reached `COMPLETED` because monkey
      aborted on an app crash), and the E2E itself (run against a previously instrumented APK because
      `ajc` is not installed on this workstation). The three pre-existing checks in the issue's
      *affected domains* section were left untouched.

## 11. Device Resolution — Logcat (§6.3, second pass)

Unifying boot and install left the third derivation in place. `LogcatComponent` resolves its own
serial from `task.config.device_id`, and `Platform._generate_tasks` populates that from
`parameters["device_serial"]` with a literal `"emulator-5554"` fallback — so
`--tools "monkey@device_port=5558"`, which the tool DSL permits, boots and installs on
`emulator-5558` while capturing logcat from `emulator-5554`. Verified by executing the path, not
inferred from the code's shape. Unlike a wrong-device install, a wrong-device capture raises
nothing: empty `.logcat`, zero coverage, and a silently empty resume reconstruction now that §6.4
makes that file the single reconstruction source.

- [x] 11.1 Add a module-level `resolve_device(parameters) -> (port, serial)` in `rv-platform`
      (design D10, option c) and move `DEFAULT_DEVICE_PORT` to it, so the literal `5554` exists once.
      It must take the parameters mapping rather than a `Task`, because `Platform._generate_tasks`
      is one of its three callers and runs before any `Task` exists
- [x] 11.2 Route `EmulatorComponent._resolve_device()` through it — behaviour unchanged, one
      derivation removed
- [x] 11.3 Route `LogcatComponent.__init__` through it, deleting the `task.config.device_id`
      fallback chain (INV-PLT-28)
- [x] 11.4 Route `Platform._generate_tasks`'s `device_id` derivation through it, deleting the literal
      `"emulator-5554"` fallback at `platform.py:236-241`

      **Convergence verified by executing the path, not by reading it.** The reproduction from
      the defect report, re-run against the new code with `parameters = {"device_port": 5558}`
      and no `device_serial`: boot port `5558`, install serial `emulator-5558`, logcat serial
      `emulator-5558`, `task.config.device_id` `emulator-5558`. Before the change the same
      snippet printed `5558 / emulator-5558 / emulator-5554`.

- [x] 11.5 Confirm the delta's new MODIFIED block for "Component-Based Task Execution (FR09, NFR02)"
      is what `openspec archive` syncs, so `openspec/specs/platform/spec.md` stops asserting the old
      finalization order at its narrative and its "Successful Three-Phase Execution" scenario

      **Confirmed by running the archive, not by reading the delta.** `openspec/` was copied to a
      scratch tree and `openspec archive gh92-emulator-boot-gating --yes` run there. The resulting
      `openspec/specs/platform/spec.md` carries the MODIFIED block verbatim (byte-identical to the
      delta block apart from one trailing blank line): all six pre-existing scenarios plus
      "Logcat captures the device that was booted", the INV-PLT-28 paragraph, and the corrected
      order in both the narrative and the "Successful Three-Phase Execution" step list. The old
      order is gone from the whole file — `stop coverage -> process coverage results -> stop
      logcat` and "coverage must stop before logcat" both count 0 after the sync.

      **One defect found and it is in the delta, not in the sync.** The block's opening paragraph
      ("The block below carries the requirement in full ... It is modified here for two reasons the
      rest of this delta creates") is *inside* the requirement body, so archive copies it into the
      permanent spec, where it reads as migration history about a change that no longer exists (P4)
      and refers to a "delta" the reader cannot see (P2). The sibling paragraph for "Android
      Emulator Management" does not have this problem: it sits under `## MODIFIED Requirements`
      *above* the first requirement header, and prose there is not synced — verified, it counts 0 in
      the archived spec. A third probe moved the new paragraph to the same place: `openspec
      validate` still passes, neither meta paragraph reaches the permanent spec, and everything
      substantive still syncs (seven scenarios, INV-PLT-28 paragraph, new order narrative, old order
      absent).

      **Fixed via `/opsx:update` and re-verified by archiving again.** Both meta paragraphs now sit
      under `## MODIFIED Requirements`, each naming the requirement it describes (two adjacent notes
      saying "the block below" would not read), preceded by one line stating why they are outside the
      bodies. `openspec validate` passes; the fresh archive probe syncs neither note, keeps the seven
      scenarios of "Component-Based Task Execution" and the eight of "Android Emulator Management",
      and leaves no statement of the old order in the permanent spec.
- [x] 11.6 Add unit tests: `{"device_port": 5558}` alone yields serial `"emulator-5558"` for boot,
      install **and** logcat (platform scenario "Logcat captures the device that was booted"); both
      keys present are honoured as today; neither key yields the 5554 defaults. Assert against
      `LogcatManager`'s constructor argument, since that is where the serial actually lands

      **Where they live, and which one actually discriminates.** `tests/test_device.py` (new) covers
      `resolve_device` directly and asserts boot, install, logcat and `TaskConfiguration.device_id`
      agree; `tests/components/test_logcat.py` covers the component; `tests/test_platform.py` covers
      `_generate_tasks`. `test_logcat.py::test_init_fallback_to_device_id` was replaced rather than
      kept — it asserted the fallback chain this group deletes (P3).

      The realistic cross-site test does **not** discriminate, and the reason is worth recording:
      with `device_id` populated by the fixed `_generate_tasks`, the old logcat fallback chain lands
      on the right serial anyway — agreement by coincidence, which is exactly design D10's rejected
      option (a). Verified by reverting `logcat.py` to its previous body and re-running: that test
      still passed. `test_a_stale_device_id_is_consulted_by_no_site` was added for this, leaving
      `device_id` at `"emulator-5554"` while the parameters say 5558; it FAILS on the old code
      (`LogcatManager(device_serial='emulator-5554')`) and passes on the new.
- [x] 11.7 Grep `modules/rv-platform/src/` for any remaining literal `"emulator-5554"` outside
      `resolve_device`, and record the result rather than asserting the sweep is complete — task
      5.5b's retraction above is why

      **Sweep result — searched for the claim (a site with its own device default), not for the
      string.** Five patterns were run, and their scopes are stated so the gaps are visible rather
      than implied: (A) literal `"emulator-5554"` in `modules/rv-platform/src/`; (B) any bare `5554`
      there; (C) `f"emulator-{...}"` serial construction across every `modules/*/src/`; (D) any other
      read of `device_serial`/`device_port` from a mapping across every `modules/*/src/`; (E) any
      `device_id` default across every `modules/*/src/`.

      **In `rv-platform/src/` the sweep is clean.** The only remaining `5554` literals are
      `DEFAULT_DEVICE_PORT` in `device.py` and prose in comments/docstrings (`device.py`,
      `platform.py:239`, `logcat.py:57`) that illustrates the port sequence. No second derivation
      survives.

      **Outside `rv-platform/src/`, three families exist. None is fixed here; all are recorded.**
      1. **`rv-tools` builtin tools carry their own `"emulator-5554"` fallback** — `ape`, `ares`,
         `droidbot`, `droidmate`, `fastbot`, `humanoid`, `monkey`, `qtesting`. This is the same
         defect class one layer out, and it is live in the same way: **verified by execution**, not
         inferred — `ToolFactory().create_tool(ToolConfig(name="monkey", parameters={"device_port":
         5558}))` yields `device_id = "emulator-5554"`, and the same for `ape`'s `device_serial`. So
         `--tools "monkey@device_port=5558"` would drive monkey against 5554 while the app is
         installed on 5558. It is not reachable today for the reason §6.3 already records:
         `ExecutionController` injects `device_port`, `device_serial` and `device_id` together. Not
         fixed here because INV-PLT-28 and this change's delta are scoped to rv-platform components,
         and eight tool plugins are a change of their own.
      2. **`TaskConfiguration.device_id` defaults to `"emulator-5554"`** at `domain/task.py:187`,
         `:250` and `:288` (rv-android-core). Not a resolution site: `_generate_tasks` now always
         passes an explicitly resolved value, and no rv-platform component reads the field any more.
         `executor.py:394` still copies it to `context["device_id"]`, which **nothing reads** — grep
         across `modules/` finds no consumer. Left alone; it is a domain default, and deleting the
         dead context key belongs to the P3 cleanup deferred in task 2.9.
      3. **`rv-uiautomator`'s `device_id: str = "emulator-5554"`** parameter default, used by the
         standalone rv-agent path, which does not go through rv-platform's task pipeline at all.
- [x] 11.8 Run `/rv-test-run rv-platform` and `/rv-verify rv-platform`

      **Tests PASS: 328 passed, 1 skipped** (was 317 before this group; +11 from the new
      `test_device.py`, the two `_generate_tasks` cases and the split logcat case). black, isort and
      bandit as recorded in 10.3 — bandit's single LOW finding (B110, `result_processor.py:1140`) is
      pre-existing and untouched here.

      **`/rv-verify` reports FAIL, and the failure is the standing flake8 condition from 10.3, not
      this group.** 34 E501 in rv-platform, all long strings and comments that black will not split
      at 88 columns. Verified per file against `HEAD` rather than trusting the total, which is what
      10.3's retracted-sweep lesson demands: `platform.py` 6 at HEAD and 6 now, `emulator.py` 1 and
      1, `logcat.py` 1 and 1, `test_logcat.py` 1 and 1, `test_platform.py` 0 and 0. The two files
      this group adds, `device.py` and `test_device.py`, are flake8-clean. Zero new findings.
      `mypy` is still SKIPPED repo-wide (no `[tool.mypy]`, no `mypy.ini`).
- [x] 11.9 Re-run `/opsx:verify`; the change was verified and committed before this group existed

      **Result: no critical issue; one incoherence found and fixed.** Completeness: every task
      checked, and each spec delta has located implementation. Correctness: the new scenario is
      covered by a test that FAILS on the pre-change code, not merely by one that passes on the new;
      `1617 passed, 1 skipped` across rv-android-core, rv-platform and rv-coverage (1604 before this
      group). Coherence: D10 is followed literally — one module-level function taking the parameters
      mapping, `DEFAULT_DEVICE_PORT` moved to it, three real call sites.

      The incoherence: `proposal.md`'s Modules table still listed `rv-platform`'s §6.3 footprint as
      `components/emulator.py` alone, although §6.3's own prose names all three sites. Corrected via
      `/opsx:update` to name `device.py` (new), `components/emulator.py`, `components/logcat.py` and
      `platform.py`. `openspec validate` passes.

      Also synced: `modules/rv-platform/CLAUDE.md` gains `resolve_device` in the component table and
      an "One device resolution" note under Important Notes. No documented statement anywhere
      asserted a per-component device fallback, so nothing had to be *corrected* — checked
      `modules/rv-platform/docs/architecture.md` and `docs/architecture/rv-platform.md`, whose
      `device_port` passages describe `EmulatorManager` and remain accurate.
