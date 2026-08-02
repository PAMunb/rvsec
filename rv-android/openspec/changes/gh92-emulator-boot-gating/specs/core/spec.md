# Delta Specification: Core Infrastructure — Emulator Boot Gating

## Purpose

`rv-android-core` owns every interaction with the Android device. `util/android/android.py` wraps ADB as a set of class methods on `Android`; `util/android/emulator_manager.py` wraps those in a context manager that brackets an emulator's lifetime; and `commands/command.py` provides the `Command` model that actually spawns the subprocesses. Everything above — the platform's task executor, every testing tool, the coverage and logcat machinery — reaches the device through this layer and trusts the contract it advertises.

That contract has one central promise: **when `Android.start_emulator()` returns, the device is ready to accept work.** This delta makes that promise true and makes it enforceable.

Today it is not true. `Android._wait_for_boot` runs two sequential phases against a shared clock. Phase 1 polls `getprop init.svc.bootanim` until it reads `stopped`. Phase 2 is supposed to poll `sys.boot_completed`, and it is where the real readiness signal lives — but it is a no-op that has never fired. Two independent errors combine to hide each other. First, the check is handed to `Command` as a single argv element containing literal single quotes (`"'while [[ -z $(getprop sys.boot_completed) ]]; do sleep 1; done;'"`); because `Command.invoke()` calls `Popen(cmd_args)` without `shell=True` — a deliberate choice, documented in that file, to avoid shell injection and keep process-tree cleanup reliable — nothing ever strips those quotes, and the device's `sh` treats the entire string as one quoted word. The result is "command not found", exit 127. Second, `Command.invoke()` raises only on timeout and on local `OSError`; a non-zero exit logs a warning and returns a `CommandResult`, and the boot loop never inspects that value, so its unconditional `break` fires on the failure. `_wait_for_boot` then logs `"booted!"` and returns successfully, in milliseconds.

The asymmetry in the recorded artifacts is what makes this diagnosis solid rather than merely plausible: across 781 `tasks.json` files, phase 1's timeout message appears **322 times** while phase 2's appears **zero** times — on the same shared budget. Phase 2 is not generous; it is structurally incapable of spending the clock.

Phase 1 alone is a weak gate. The emulator is launched with `-no-boot-anim` (`android.py:107`), so the animation service can report `stopped` before the Android framework is up. Its comparison is also strict and silent: `check_result.stdout.strip().decode("ascii") == "stopped"`. When `getprop` fails, stdout is empty, the comparison is simply false, and the loop keeps going — a genuinely broken ADB burns the entire budget instead of reporting itself in seconds.

The underlying anti-pattern — *"the call did not raise, therefore it worked"* — is not confined to the boot wait. `install_apk` invokes `adb root` and immediately overwrites the result without checking it (`android.py:283-291`), and several `Command` constructions in this module carry no timeout at all, so `communicate(timeout=None)` can block a task forever. This delta encodes the rule as an invariant so the pattern is caught by review rather than by archaeology.

Finally, the boot budget itself. `boot_timeout=180` is a default parameter that no production caller ever overrides (`android.py:122` calls `_wait_for_boot(device_name)`), reachable by no environment variable, CLI flag, or configuration field. That has been harmless only because the gate never engaged. Once phase 2 becomes real, this budget governs a cold boot that the execution environment guarantees on every single task — the emulator runs with `-read-only`, `-no-cache` and `-no-snapshot-save`, so the AVD is permanently in a never-booted state — under 8 to 16 containers competing for KVM, CPU and RAM. Restoring the gate without sizing it would trade one failure mode for another. The two corrections are indivisible, and the parameterization is therefore part of this delta rather than a follow-up.

The parameters are read from the environment at the point of use, not threaded through configuration objects. This follows the "L1 cross-layer infra exception" already established in `util/validation/config.py:75-88` for `RV_PYDANTIC`. The reason is that a boot budget is a property of the machine and its concurrency level, not of the experiment's semantics: the same experiment definition needs a different budget on a laptop than on a 16-container GCP VM. Carrying it through `ExperimentConfig` → `PlatformConfig` → `TaskConfiguration` would be plumbing across three module boundaries to reach a fourth, and `rv-experiment`'s CLI carries an explicit in-code prohibition against widening its `envvar=` pattern.

## Data Contracts

### Input

- `device_name: str` — ADB serial of the target device, e.g. `"emulator-5554"` (source: `Android.start_emulator`, derived from `device_port`).
- `boot_timeout: Optional[int]` — total seconds allowed across both boot phases. When `None`, resolved from `RV_EMULATOR_BOOT_TIMEOUT`; the parameter remains for direct injection by tests.
- `RV_EMULATOR_BOOT_TIMEOUT: str` — process environment; integer seconds; default `300`.
- `RV_ADB_CMD_TIMEOUT: str` — process environment; integer seconds applied to each individual ADB probe; default `30`.
- `RV_APK_INSTALL_TIMEOUT: str` — process environment; integer seconds applied to `adb install`. There is no value in force today to preserve, and no measured distribution of install durations, so this delta fixes the obligation (a timeout MUST exist) and not the number. The default is chosen during implementation from the durations observed in the validation runs, and recorded in `.env.example` alongside the other two.

The boot poll interval is deliberately **not** an environment variable. It is a module constant in `rv-android-core`: unlike the three budgets above, its correct value does not vary with the host or the concurrency level — a slower machine needs a longer budget, not a rarer probe.

### Output

- `Android._wait_for_boot` returns `None` on success. Its only observable output is the pair of log lines carrying the device serial and the measured `elapsed` (`android.py:222-224`), which is the instrumentation the provisional 300 s default depends on.

### Side-Effects

- **[Device]**: repeated `adb -s <serial> shell getprop ...` probes at the configured poll interval until the acceptance condition holds or the budget expires.
- **[Process]**: on timeout of an individual probe, `Command` kills the process tree via `kill_process_tree()` before raising `RVCommandTimeoutError`.
- **[Logging]**: one WARNING per retried probe; one INFO carrying the total elapsed boot time on success.

### Error

- `TimeoutError` — the shared budget expired in either phase. The message MUST identify which phase and the budget in force.
- `RVCommandTimeoutError` — a single ADB probe exceeded its per-command timeout. Caught and retried inside the boot loops; it does not end the wait.
- `ValueError` — an environment variable holds a value that is not a valid integer. It MUST propagate; a mistyped timeout must fail loudly rather than silently reverting to the default.
- `RuntimeError` — `Android.install_apk` failed; the message carries the ADB exit code and the combined output.

## Invariants

- **INV-CORE-43**: No code path in `rv-android-core` may treat a returned `CommandResult` as success without inspecting it. Any loop, branch, or sequence that proceeds on the basis of `Command.invoke()` having returned MUST check `result.is_failure()` first. `Command.invoke()` raises only on `RVCommandTimeoutError` and `CommandNotFoundError`; a non-zero exit status is reported exclusively through the returned `CommandResult` (`commands/command.py:184-201`), so "it did not raise" carries no information about whether the command succeeded.

- **INV-CORE-44**: `Android._wait_for_boot` MUST NOT return successfully unless the string `"1"` was actually read from `sys.boot_completed` on the target device. Concretely: the phase-2 loop MAY terminate only when `result.is_failure()` is `False` **and** `result.stdout.strip()` equals `b"1"`. Any other outcome — non-zero exit, empty stdout, any other value — MUST continue polling until the shared budget expires, at which point `TimeoutError` MUST be raised.

- **INV-CORE-45**: The argument vector constructed for either boot probe MUST NOT contain shell metacharacters that depend on a shell for interpretation, and MUST NOT contain literal quote characters. Because `Command.invoke()` spawns processes with `shell=False`, every argv element reaches the target verbatim. Iteration MUST be performed in Python, not by a loop embedded in a device-side shell string.

- **INV-CORE-46**: Both boot phases MUST share a single budget measured from one `start` timestamp taken before phase 1. The `TimeoutError` raised by each phase MUST name that phase distinguishably, so the two failure modes remain separable in stored `error_message` values as they are today.

- **INV-CORE-47**: Every timeout parameterized by this change MUST resolve as: explicit argument when provided; otherwise the environment variable when set; otherwise the documented default. A set-but-invalid value MUST raise `ValueError` rather than fall back to the default. The names MUST be declared as `ENV_*` constants in `modules/rv-android-core/src/rv_android_core/constants.py` — `docker/rvandroid/scripts/validate_env_vars.sh` parses that block as an allow-list and terminates the container with exit 64 for any undeclared `RV_*` variable.

- **INV-CORE-48**: Every `Command` constructed in `util/android/android.py` that addresses a device MUST declare a timeout. `Command.timeout` defaults to `None`, which becomes `communicate(timeout=None)` and can block a task indefinitely; `adb install` is the case with observable consequences, because it runs while the emulator session holds the device.

- **INV-CORE-49**: `EmulatorManager.start_emulator` MUST NOT relabel exceptions raised by the body of the `with` block. The `yield` MUST sit outside the `try` whose `except` raises `EmulatorError`, so that a failure during installation, logcat, coverage, or tool execution propagates with its own type.

  Device teardown MUST remain guaranteed **on every path, including a failed startup**. The `finally` that kills the emulator MUST enclose both the startup sequence and the `yield` — not the `yield` alone. Narrowing the `except` is therefore a *nesting* change, not a split into two sibling blocks: a sibling arrangement would raise `EmulatorError` out of the first block and never enter the second, so the teardown would not run and INV-CORE-50 could not hold.

- **INV-CORE-50**: An AVD MUST be registered in `EmulatorManager._active_emulators` before the emulator process is launched, so that the teardown `finally` — which acts only on registered AVDs — reclaims the port when the boot wait fails. A failed boot MUST NOT leave a daemonized `emulator` process holding its port.

- **INV-CORE-51**: When APK installation fails, the reason reported by ADB MUST reach the caller. `EmulatorManager.install_app` MUST NOT reduce a failure to a bare `False` while discarding the message; the `INSTALL_FAILED_*` code or equivalent ADB text preserved by `Android.install_apk` MUST be carried up so it can reach the task's `error_message`.

- **INV-CORE-52**: `Android.kill_emulator`'s post-kill settling delay MUST be conditional on the kill having been issued successfully. The delay exists to let the port be released; when nothing was killed there is no port to wait for. INV-CORE-50 makes teardown fire on paths where no emulator process may exist, so an unconditional delay would tax every failed launch for no effect.

## ADDED Requirements

### Requirement: Emulator Boot Completion Gating (FR07, NFR04)

`Android._wait_for_boot` MUST verify that the Android framework has completed boot before returning, and MUST NOT return successfully on the basis of a command that failed.

The wait MUST proceed in two phases against a single shared budget. Phase 1 polls `adb -s <serial> shell getprop init.svc.bootanim` and advances when the device reports `stopped`. Phase 1 is a coarse gate only: the emulator is launched with `-no-boot-anim`, so the animation service can report `stopped` before the framework is usable. Phase 2 polls `adb -s <serial> shell getprop sys.boot_completed` and is the authoritative readiness signal.

Phase 2 MUST be implemented as a Python poll issuing a plain `getprop` on each iteration. It MUST NOT delegate iteration to a shell loop embedded in a command string: `Command.invoke()` spawns processes with `shell=False`, so quoting characters in an argv element are delivered literally to the device and the whole string is interpreted as a single command name.

The `wait-for-device` token the current argv carries before `shell` is dropped along with the loop. It exists to block until ADB sees the device, which is what a Python poll bounded by the shared budget now does explicitly and observably; keeping it would reintroduce an unbounded wait inside a single probe, answerable only to the per-command timeout.

Both phases MUST inspect the returned `CommandResult` before acting on it. `RVCommandTimeoutError` from an individual probe MUST be caught and the probe retried, because ADB responds slowly during early boot; a non-zero exit or an unexpected value MUST NOT terminate the wait.

Phase 1 MUST distinguish "the device is not ready yet" from "ADB is broken". An empty stdout or a failed probe MUST be reported with diagnostics at the point it occurs, rather than silently consuming the budget for the full duration.

#### Scenario: Boot completes normally

- **WHEN** `_wait_for_boot("emulator-5554")` is called and `getprop init.svc.bootanim` returns `b"stopped"` with exit `0`, then `getprop sys.boot_completed` returns `b"1"` with exit `0`
- **THEN** the method MUST return without raising
- **AND** it MUST log the device serial together with the elapsed boot time measured from the single `start` timestamp

#### Scenario: Phase 2 probe fails with a non-zero exit

- **WHEN** `getprop sys.boot_completed` returns a `CommandResult` whose `is_failure()` is `True` — for example exit `127`, the status produced today by the quoted shell string
- **THEN** the wait MUST NOT terminate
- **AND** polling MUST continue until the shared budget expires
- **AND** `TimeoutError` MUST then be raised naming phase 2 and the budget in force

#### Scenario: Phase 2 probe returns an unset property

- **WHEN** `getprop sys.boot_completed` succeeds with exit `0` but `stdout.strip()` is `b""` — the device answered, the property is simply not set yet
- **THEN** the wait MUST NOT terminate
- **AND** the next poll MUST be issued after the configured interval

#### Scenario: Argument vector carries no shell dependency

- **WHEN** the argument vector for the `sys.boot_completed` probe is constructed
- **THEN** it MUST contain no literal `'` or `"` characters
- **AND** it MUST contain no `$(`, `[[`, `while`, or `;` tokens
- **AND** it MUST be the plain form `["-s", "<serial>", "shell", "getprop", "sys.boot_completed"]`

#### Scenario: Broken ADB is reported in seconds, not after the full budget

- **WHEN** the phase-1 probe returns a `CommandResult` whose `is_failure()` is `True` with `stderr` containing `b"device offline"`
- **THEN** the condition MUST be logged with the device serial and the combined command output at the point of detection
- **AND** the log MUST identify it as a probe failure rather than a not-yet-booted device

#### Scenario: Both phases share one budget

- **WHEN** `_wait_for_boot("emulator-5554", boot_timeout=10)` is called and phase 1 consumes 8 seconds before reporting `stopped`
- **THEN** phase 2 MUST have at most the remaining 2 seconds before `TimeoutError` is raised
- **AND** the raised message MUST identify phase 2, distinguishably from phase 1's message

### Requirement: Environment-Parameterized Device Timeouts (FR07, NFR04)

The boot budget, the per-command ADB timeout, and the `adb install` timeout MUST be configurable per environment through environment variables, with the values in force today as defaults where one exists.

The correct value for each depends on the host and its concurrency level, not on the experiment being run: the same cold boot that finishes quickly on an idle machine disperses far beyond that under 8 to 16 containers competing for KVM, CPU and RAM — the recorded phase-1 timeouts already span a p50 of 182 s and a maximum of 871 s on the same 180 s budget. These are properties of the environment, and MUST be read from the environment at the point of use, following the L1 cross-layer infra exception established in `util/validation/config.py:75-88`.

The boot poll interval is not included. It stays a module constant, because the interval at which the device is asked does not depend on the machine — only the budget does.

Each variable MUST be declared as an `ENV_*` constant in `constants.py` and documented in `.env.example`. A value that is set but not a valid integer MUST raise, not silently revert to the default — a mistyped budget that quietly becomes the default is indistinguishable from a working configuration until an experiment fails.

`adb install` MUST run under a timeout. It has none today, so a hung install blocks the task for as long as the process lives, holding the emulator session open.

#### Scenario: Default applies when the variable is unset

- **WHEN** `RV_EMULATOR_BOOT_TIMEOUT` is absent from the environment and `_wait_for_boot("emulator-5554")` is called with no explicit `boot_timeout`
- **THEN** the budget in force MUST be `300` seconds
- **AND** the initial log line MUST report that value

#### Scenario: Valid integer is honoured

- **WHEN** `RV_EMULATOR_BOOT_TIMEOUT` is `"600"` and `_wait_for_boot("emulator-5554")` is called with no explicit `boot_timeout`
- **THEN** the budget in force MUST be `600` seconds

#### Scenario: Explicit argument overrides the environment

- **WHEN** `RV_EMULATOR_BOOT_TIMEOUT` is `"600"` and `_wait_for_boot("emulator-5554", boot_timeout=10)` is called
- **THEN** the budget in force MUST be `10` seconds, preserving the injection point the unit tests rely on

#### Scenario: Invalid value fails loudly

- **WHEN** `RV_EMULATOR_BOOT_TIMEOUT` is `"30O"` — a capital letter O typed for a zero
- **THEN** `ValueError` MUST propagate from the resolution
- **AND** the default MUST NOT be substituted

#### Scenario: APK installation runs under a timeout

- **WHEN** `Android.install_apk` constructs the `adb install -r -g <path>` command
- **THEN** that `Command` MUST carry a non-`None` timeout resolved from `RV_APK_INSTALL_TIMEOUT`
- **AND** exceeding it MUST raise `RVCommandTimeoutError` after the process tree is killed, rather than blocking indefinitely

#### Scenario: New variables are declared in the registry

- **WHEN** `RV_EMULATOR_BOOT_TIMEOUT`, `RV_ADB_CMD_TIMEOUT` and `RV_APK_INSTALL_TIMEOUT` are set in a container's environment
- **THEN** each MUST appear as an `ENV_*` constant in `constants.py`
- **AND** `docker/rvandroid/scripts/validate_env_vars.sh` MUST accept them rather than terminating the container with exit `64`

### Requirement: Emulator Session Failure Attribution (FR07, NFR04, NFR06)

`EmulatorManager.start_emulator` MUST report failures with their true origin. A failure that occurs while the emulator session is in use MUST NOT be relabelled as a failure to start the emulator.

The context manager currently places its `yield` inside the `try` whose `except` raises `EmulatorError(f"Failed to start emulator {avd_name}", cause=e)`. In a `@contextmanager`, an exception raised in the body of the `with` is re-raised at the `yield`, so every failure during installation, logcat capture, coverage tracking, or tool execution is caught there and re-labelled. The resulting message — `EmulatorError: Failed to start emulator RVSec caused by TaskExecutionError: Failed to install application` — is self-contradictory, since it is only generable when startup succeeded, and it is present in 1,174 stored failure records.

Startup and session MUST therefore be separated, with only startup covered by the `except` that produces `EmulatorError`. Teardown MUST remain unconditional and MUST cover **both**: the `finally` that kills the emulator encloses the startup sequence and the `yield` together, so neither a failing session nor a failing startup can leave a device running for the next task. This is the one structural detail that is easy to get wrong — placing the `except` and the `finally` on two sibling blocks satisfies the relabelling requirement while silently removing teardown from the startup-failure path, which is exactly the path the next obligation exists for.

The AVD MUST be registered in `_active_emulators` before the emulator process is launched. Registration currently happens after `Android.start_emulator` returns — which includes the boot wait — and the teardown `finally` acts only on registered AVDs, so a genuine boot failure leaves the daemonized emulator alive holding its port for the next task to find.

Registering earlier makes teardown fire on paths where no emulator process may exist. The settling delay that follows `adb emu kill` MUST therefore become conditional on the kill having succeeded, so a failed launch is not taxed for a port release that is not happening.

#### Scenario: Failure inside the session keeps its identity

- **WHEN** the body of `with emulator_manager.start_emulator("RVSec") as android:` raises `TaskExecutionError("Failed to install application", task_id)`
- **THEN** the caller MUST receive `TaskExecutionError`, not `EmulatorError`
- **AND** the message MUST NOT contain `"Failed to start emulator"`

#### Scenario: Genuine startup failure is still labelled as such

- **WHEN** `Android.start_emulator` raises `TimeoutError("emulator-5554 sys.boot_completed not set within 300s")`
- **THEN** the caller MUST receive `EmulatorError` whose message names the AVD
- **AND** its `cause` MUST be the original `TimeoutError`

#### Scenario: Teardown runs even when the session fails

- **WHEN** the body of the `with` block raises any exception
- **THEN** `Android.kill_emulator` MUST still be invoked for the registered AVD with the device serial derived from `device_port`
- **AND** the AVD MUST be removed from `_active_emulators`

#### Scenario: Failed boot leaves no orphan holding the port

- **WHEN** `Android.start_emulator("RVSec", no_window=True, device_port=5556)` raises `TimeoutError` during the boot wait
- **THEN** `"RVSec"` MUST already be present in `_active_emulators` at that moment
- **AND** the teardown `finally` MUST issue `adb -s emulator-5556 emu kill`
- **AND** no `emulator` process MUST remain holding port `5556`

#### Scenario: Teardown runs when startup itself fails

- **WHEN** the startup sequence raises and `EmulatorError` is produced, so the `with` body is never entered
- **THEN** `Android.kill_emulator` MUST still be invoked for the registered AVD
- **AND** `"RVSec"` MUST be removed from `_active_emulators`
- **AND** the `EmulatorError` MUST continue to propagate to the caller unchanged

#### Scenario: Post-kill delay is skipped when nothing was killed

- **WHEN** teardown issues `adb emu kill` for an AVD whose emulator process never came up, and the kill command reports failure
- **THEN** the settling delay MUST NOT be taken
- **AND** teardown MUST return without waiting for a port that was never bound

### Requirement: ADB Failure Reason Propagation (FR07, NFR06)

When APK installation fails, the reason ADB gave MUST reach the task's `error_message`.

`Android.install_apk` already preserves it: on failure it raises `RuntimeError` carrying the exit code and `result.get_combined_output()`. The information is discarded one layer up, where `EmulatorManager.install_app` catches the exception, logs it, and returns bare `False`. The caller therefore has a boolean, and the stored `error_message` records only `"Failed to install application"`. Across 1,174 recorded install failures, not one carries an `INSTALL_FAILED_*` code.

This matters beyond diagnostics. The AVD baked into `phtcosta/rvsec_android:0.9.3` has `disk.dataPartition.size = 800M`, against 6 GB on the host AVD built from the same `pixel` profile. That raises an untested hypothesis: `INSTALL_FAILED_INSUFFICIENT_STORAGE` as a **direct** cause of install failure, independent of the boot gate, producing an identical symptom. It is recorded here as a hypothesis and not as a finding — it cannot be decided from existing artifacts precisely because the reason is never stored. Propagating the reason is what allows the next occurrence to distinguish the two causes from a single record.

#### Scenario: Installation failure carries the ADB reason

- **WHEN** `adb install -r -g <path>` exits non-zero with stderr containing `INSTALL_FAILED_INSUFFICIENT_STORAGE`
- **THEN** the failure surfaced by `EmulatorManager.install_app` MUST carry that text
- **AND** the text MUST reach the task's stored `error_message`
- **AND** the message MUST NOT be reduced to `"Failed to install application"` alone

#### Scenario: Signature-mismatch retry preserves the final reason

- **WHEN** the first `adb install` fails with `INSTALL_FAILED_UPDATE_INCOMPATIBLE`, the package is uninstalled, and the retry also fails with `INSTALL_FAILED_INSUFFICIENT_STORAGE`
- **THEN** the reason propagated MUST be the one from the retry
- **AND** it MUST include the ADB exit code
