# Proposal: Emulator Boot Gating

**GitHub Issue**: #92

## Why

RV-Android waits for the Android emulator to boot in two phases, and phase 2 — the only phase that checks whether the Android framework is actually up — is a silent no-op. It has never once fired in the recorded history of the project. The wait returns declaring success in milliseconds, and the APK is then installed against a device that never completed boot.

This produces **1,174 failed task records on disk**, spanning February to August 2026 and seven different testing tools (`ape`, `aperv`, `fastbot`, `rvagent`, `rvsmart`, `humanoid`, `monkey`). Each carries `"tool_execution_start": null` and `method_coverage: 0.0` — the tool never ran, so the task contributes nothing to the experiment. It is still happening: the two most recent records are inside the live gh90 decisive run, at 2026-08-01T15:50 and 2026-08-02T03:15.

The failures have been misdiagnosed for months because the error message lies about its own cause. It reads `EmulatorError: Failed to start emulator RVSec caused by TaskExecutionError: Failed to install application`, which is only generable when the emulator start **succeeded** — a self-contradiction produced by a context manager whose `except` clause wraps its `yield`. Anyone reading that message investigates emulator startup and finds nothing wrong there.

The originally reported symptom — "the boot timeout is too short and not parameterizable, and it seems to install the APK anyway" — is confirmed, but the cause is inverted. The timeout never fires. Fixing the timeout alone would change nothing; fixing the gate alone would convert today's false install failures into legitimate boot timeouts, because the execution environment guarantees a cold boot on every task and the current 180 s budget has already been exhausted 322 times by the phase that does work. The two corrections are indivisible.

## What Changes

**C1 — Make phase 2 a real gate.** Replace the current command, whose shell loop never executes, with a Python poll of `adb -s <serial> shell getprop sys.boot_completed`. Accept only when `result.is_failure()` is false **and** `stdout.strip() == b"1"`. The `wait-for-device` token the current argv carries before `shell` (`android.py:202`) goes with the loop: an explicit poll bounded by the shared budget is what it was standing in for, and keeping it would hide an unbounded wait inside a single probe. The present code passes a shell loop to `Command` as one argv element containing literal single quotes; `Command.invoke()` uses `Popen(cmd_args)` without `shell=True` (`commands/command.py:180`), so nothing strips them and the device's `sh` treats the whole string as a single quoted word — command not found, exit 127. Compounding it, `Command.invoke()` raises only on timeout and `OSError`; a non-zero exit merely logs a warning and returns a `CommandResult` (`command.py:184-201`), and the loop never inspects that result, so the unconditional `break` at `android.py:215` fires on exit 127.

**C2 — Narrow the context manager's `try`.** In `util/android/emulator_manager.py:90-111`, the `yield` at line 103 sits inside the `try` whose `except` raises `EmulatorError`. Nest the blocks so failures inside the `with` body propagate with their own identity: an inner `try/except` around startup only, wrapped by an outer `try/finally` that covers startup *and* the `yield`. The nesting is load-bearing. Two sibling blocks — `try/except` for startup, then `try/finally` for the `yield` — would read as equivalent and satisfy C2, but a startup failure would raise out of the first block without ever entering the second, so the teardown would not run and the orphan C5 exists to reclaim would be guaranteed rather than prevented.

**C3 — Fail fast with diagnostics in phase 1.** Phase 1 (`android.py:176-193`) compares only `stdout.strip() == "stopped"`. A broken adb yields empty stdout, the comparison is false, and the loop silently burns the entire budget. Handle empty stdout and `is_failure()` explicitly.

**C4 — Parameterize the timeouts via environment variables.** Three of them: `boot_timeout` (`android.py:143`, default raised to **300 s, provisional**), the per-command adb timeout, and a new timeout for `adb install` — which today has none at all, so `communicate(timeout=None)` can block indefinitely. Read at the point of use, following the gh55 "L1 cross-layer infra exception" pattern established in `util/validation/config.py:75-88`. The poll interval is also unhardcoded, but into a module constant rather than a variable: how often the device is asked is not a property of the host, only how long it is given.

**C5 — Prevent orphaned emulators.** `emulator_manager.py:93` registers the AVD in `_active_emulators` only *after* `start_emulator` returns, and the teardown `finally` kills only registered AVDs. A genuine boot failure therefore leaves the daemonized `emulator` process alive holding the port, and the next task on that port talks to a zombie. Register before launch. Because that makes teardown fire on paths where no emulator process may exist, the unconditional `time.sleep(10)` after `adb emu kill` (`android.py:139`) becomes conditional on the kill having succeeded — it exists to let a port be released, which is meaningless when nothing was bound.

**C6 — Propagate the adb reason.** `Android.install_apk` preserves the adb failure text in a `RuntimeError` (`android.py:305-310`), but `EmulatorManager.install_app` (`emulator_manager.py:244-248`) catches it, logs it, and returns bare `False`. No `INSTALL_FAILED_*` code has ever reached a task's `error_message`. Carry the reason up.

**C7 — Make the monitoring buckets mutually exclusive.** `experimento-20260706/scripts/rv_status.py:49-55` classifies by first-matching regex, in the order `timeout`, `oom/killed`, `install/adb`, `emulator/boot`. The same block exists byte-identically at `experimento-20260604/scripts/rv_status.py:49-55`; both are corrected, because a bucket list that is wrong in one copy is wrong in the other. Verified against artifacts: a genuine phase-1 boot timeout is stored as `EmulatorError: Failed to start emulator RVSec caused by TimeoutError: emulator-5554 did not boot within 180s` (because `EmulatorError.__str__` embeds the cause's type), which matches `timeout`; the composite install message matches `install/adb`. **No boot failure of either kind reaches the `emulator/boot` bucket** — its counters are empty by construction. Reordering alone is insufficient.

**C8 — Add a final drain to `CoverageTracker.stop()`.** The tail loop is `while not self._stop_event.is_set()` (`tracker.py:304`) and the `finally` only flushes diagnostics and closes the handle (`tracker.py:330-342`) — there is no final read. Lines appended after the thread's last `readlines()` never reach the repository, and `CoverageComponent.process_results()` reads that in-memory repository (`coverage.py:280-283`), not the file. The resume path re-parses the file in full, so a `COMPLETED` task's live metrics can differ from its reconstructed metrics — a latent violation of **INV-PLT-18** (live/resume round-trip equality within 0.01). Magnitude is **unmeasured**: the window is the tail loop's 0.5–1.0 s sleep plus the duration of `process_results()`.

**§6.3 — Resolve the device from one source.** Boot reads `parameters["device_port"]` (`components/emulator.py:112-120`) while install reads `parameters["device_serial"]` (`:181-189`). If only one key is injected, install targets `emulator-5554` while the booted device is on another port.

**§6.4 — Give coverage/logcat finalization a single owner.** Delete the inline block at `execution/executor.py:440-448` and have the `with` body's `finally` call `logcat_component.cleanup(context)` then `coverage_component.cleanup(context)`. One implementation, one firing point, emulator alive on both paths. Both `cleanup()` methods survive, so `_cleanup_components` still runs them and **INV-PLT-06** (cleanup-always) holds; the second invocation is a no-op because `CoverageTracker.stop()` guards on `is_running` (`tracker.py:265`) and `LogcatManager.stop_capture()` guards on `if self.logcat_process` and nulls it (`logcat_manager.py:246-250`). The finalization order is inverted to logcat→coverage.

**BREAKING (documentation)**: five places assert that coverage must stop before logcat — the comment at `executor.py:435`, `docs/architecture/rv-platform.md:262` and `:888`, and `docs/architecture/subsystem-rv-experiment.md:279` and `:816`. Three of them state it flatly; the two in `subsystem-rv-experiment.md` add a reason — "so metrics finalize against a complete log" — which inverts the actual data flow, since coverage is the reader and logcat the writer. That assertion is reversed here, in all five places. The producer (`adb logcat`) and the consumer (`CoverageTracker`) are decoupled by the filesystem — the tracker opens the file by path with its own handle (`tracker.py:293`), so stopping the producer cannot EOF or break it. Stopping the producer first is what makes C8's drain deterministic. C8 and this reorder only work together: the reorder without the drain changes nothing, and the drain without the reorder closes only part of the window.

**BREAKING (tests)**: C1 and C3 change the contract of both boot phases, so existing tests break by design and must be rewritten, not extended.

### Out of scope

Warm-booting the AVD at image build time (impossible — `docker build` does not expose `/dev/kvm`), runtime snapshots or quickboot, reusing the emulator across tasks, removing `-read-only`/`-no-cache`, and enabling GPU in any form are all rejected; see `design.md` for the rationale and the ADR that records it. Tuning `hw.ramSize` / `hw.cpu.ncore` / `disk.dataPartition.size` requires measurement first and belongs to a separate change. The pre-existing `rv-android-core ↔ rv-coverage` import cycle (`domain/task.py:682`) and the unused `get_env_or_default` helper (`util/utils.py:424-473`) are noted but not touched here. The helper has zero production call sites, but it is not free to delete: `tests/util/test_utils.py:469-502` holds eight tests for it, which the separate P3 cleanup will have to remove with it.

## Capabilities

### New Capabilities

None. This change modifies documented behavior in three existing domains; it introduces no new capability.

### Modified Capabilities

- `core`: the emulator boot-completion contract becomes a real gate with an explicit acceptance condition; boot and adb timeouts become environment-parameterized with the current values as defaults; a new invariant forbids treating a returned `CommandResult` as success without checking `is_failure()`. The `adb install` timeout obligation is added as part of the new device-timeout requirement rather than folded into the existing "System Command Execution" requirement, which describes the `Command` model itself and does not change here.
- `platform`: the "Android Emulator Management" requirement (FR07, NFR04, NFR07) gains an install precondition — installation is attempted only after boot completion was positively observed — plus a single-owner rule for coverage/logcat finalization and its position relative to emulator teardown. The device must resolve from one consistent source across boot and install. Relationship to **INV-PLT-13** (which governs the *missing-component* case, not error propagation) is stated rather than extended; INV-PLT-06 and INV-PLT-18 are both load-bearing here.
- `analysis`: `CoverageTracker.stop()` gains a final drain obligation. The current spec documents the stop lifecycle (INV-ANA-05 and the scenario "CoverageTracker context manager lifecycle") without requiring that the thread consume the remainder of the file before terminating.

## Impact

### Modules

| Module | What changes |
|---|---|
| `rv-android-core` | `util/android/android.py` (C1, C3, C4, C6 source), `util/android/emulator_manager.py` (C2, C5, C6), `constants.py` (new `ENV_*` entries) |
| `rv-platform` | `components/emulator.py` (§6.3), `execution/executor.py` (§6.4) |
| `rv-coverage` | `analysis/coverage/tracker.py` (C8) |

No new inter-module dependency edge is introduced. `rv-android-core` is the Layer-1 foundation with fan-in 14 of 16 workspace modules and zero declared `rv-*` dependencies; reading the timeouts from the environment at the point of use keeps its efferent coupling unchanged, whereas threading the value through `ExperimentConfig` → `PlatformConfig` → `TaskConfiguration` would create plumbing across three module boundaries to reach a fourth (P1).

### Non-module surfaces

- `docker/rvandroid/scripts/validate_env_vars.sh` parses `constants.py` as an allow-list and **kills the container with exit 64** on any unknown `RV_*`. A new variable that is not declared as an `ENV_*` constant breaks every container rather than being ignored.
- `scripts/check_env_vars_drift.py` and `tests/lint/test_env_vars_drift.py`: cross-check (c) requires every `ENV_*` constant to appear in `README.md` **or** `.env.example`. The script also declares rv-experiment the only Python module allowed to read user-facing `RV_*` vars, with an `L1_INFRA_NAMES` frozenset of six names; `android.py` is already in `L1_ALLOWLIST_FILES` and the read-form regexes match string literals only, so reading via the `ENV_*` constant passes silently. Whether to extend `L1_INFRA_NAMES` rather than rely on that gap is decided in `design.md`.
- `.env.example` (canonical inventory), `README.md` env table, and the `environment:` blocks of the composes that run an emulator.
- `docs/architecture/rv-platform.md` — the finalization-order statements at `:262` and `:888`; `docs/architecture/subsystem-rv-experiment.md` — the same claim at `:279` and `:816`.
- `experimento-20260706/scripts/rv_status.py` and its byte-identical twin `experimento-20260604/scripts/rv_status.py` — C7.

### Tests

Sixty-two existing tests sit in the blast radius across five files: `test_emulator_boot_retry.py` (5), `test_android.py` (10), `test_emulator_manager.py` (12), `test_emulator.py` (23) and `test_executor.py` (12). Two of the five require rewriting rather than extension:

- `modules/rv-android-core/tests/unit/test_emulator_boot_retry.py` (5 tests) — every case breaks, and not only because phase 2's contract changes: `MagicMock().is_failure()` returns a truthy `MagicMock`, so introducing the `is_failure()` guard makes phase 1 read as failed too. The file also carries `# Phase 3 root/remount` `side_effect` entries that have been dead since gh50 removed phase 3 (P4).
- `modules/rv-android-core/tests/util/android/test_android.py` (10 tests) — asserts the emulator argv exactly, asserts exact log strings including `"(timeout=180s)"`, drives `install_apk` with a 3-element `Command` `side_effect` list, and patches `time.time` with `side_effect=range(20)`. All of these fail on a correct change; their failure is expected, not a regression signal.

### Requirements

FR07 (Android Emulator Management), FR09 (Component-Based Task Execution). NFR04 (resilience) and NFR07 are touched through the platform requirement. `INV-PLT-13` was deliberately excluded from the issue's *Related FRs/NFRs* field — it is a spec invariant rather than a PRD requirement, and it governs the missing-component case, not error propagation.

### Risk

High. The emulator chain is a strict linear pipeline with exactly one caller per link (`_wait_for_boot` ← `Android.start_emulator` ← `EmulatorManager.start_emulator` ← `EmulatorComponent` ← `TaskExecutor`), which makes each layer independently verifiable but places every experiment behind it. `Command.invoke`'s signature must not change: 17 production files across six modules call it, and the boot gate needs only the existing `CommandResult` return (`is_failure()`, `stdout`).

The 300 s default is provisional and stays provisional. Three historical phase-1 timeouts exceeded it (max 871 s), so it ships together with instrumentation of the real boot `elapsed`, already logged at `android.py:223-224`. No contention run is commissioned to size it: the failure it would look for occurs in 0.86 % of recent tasks, which needs roughly 350 tasks before an absence of failures means anything, and C4 makes the budget correctable from a compose without a rebuild. The distribution is collected by observing the first real experiment run after this lands (design D9).
