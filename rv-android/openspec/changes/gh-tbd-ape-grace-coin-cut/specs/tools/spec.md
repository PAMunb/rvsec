## Purpose

The `ape` built-in runs upstream APE as the control arm of the APE-RV comparison, and `aperv` runs the
APE-RV jar. Until this change the harness treated them differently:

- **Time.** `ape` was killed exactly at its budget, while `aperv` got a teardown grace on top of it.
  APE therefore lost its startup seconds to the host's timer, and `aperv` did not.
- **Captures.** Upstream APE writes a screenshot and a GUI-tree XML on every step by default, while
  `aperv` writes per-step captures in no cell.

This change gives the `ape` arm the same host grace as `aperv`, read from one constant in
`rv-android-core`, and the same rule for deciding whether a run happened. That rule is elapsed time
against the budget, never the exit code, because APE exits non-zero when the app under test crashes.
The arm also pushes an `ape.properties` that replaces per-step capture with capture on each new
abstract state. This is the only setting of the `ape` arm that departs from the author's defaults. The
`ape` results therefore stop being comparable with the e03igg and e03igg4 campaigns.

## Data Contracts

### Input
- `task.config.timeout: int`: the exploration budget in seconds (rv-platform).

### Output
- `/data/local/tmp/ape.properties` on the device, with exactly three lines:
  `ape.takeScreenshotForEveryStep=false`, `ape.saveGUITreeToXmlEveryStep=false` and
  `ape.takeScreenshotForNewState=true`. Upstream APE reads this path first, then
  `/sdcard/ape.properties` (`Config.java:31-32` at `8f51b99c`).

### Side-Effects
- **[Device]**: the file is not removed after the run. Each task boots its own emulator with
  `-read-only` and `-no-snapshot-save`, so the file does not outlive the task.

### Error
- `RVToolExecutionError`: raised when the properties push fails, or when APE returns before
  `timeout − TOOL_TEARDOWN_GRACE_S` seconds have elapsed.
- `RVToolTimeoutError`: raised when the command timeout (`timeout + TOOL_TEARDOWN_GRACE_S`) fires. It
  stays a normal end (INV-TOOL-06).

## Invariants

- **INV-TOOL-27**: The `ape` built-in SHALL run APE under a command timeout of the budget plus
  `TOOL_TEARDOWN_GRACE_S` (`rv_android_core.constants`, 45 s), the same constant `aperv-tool` uses. No
  tool module SHALL define its own copy of the grace.
- **INV-TOOL-28**: The `ape` built-in SHALL NOT decide a run's outcome from APE's exit code. A return
  that arrives earlier than the budget minus `TOOL_TEARDOWN_GRACE_S` SHALL raise
  `RVToolExecutionError`, naming the elapsed time and the budget. Any other return SHALL complete the
  task.
- **INV-TOOL-29**: Before starting APE, the `ape` built-in SHALL push `/data/local/tmp/ape.properties`
  holding exactly the three lines of the Output contract, in that order.

## ADDED Requirements

### Requirement: APE Built-in Shares the APE-RV Harness Timing and Capture Policy (FR19, NFR04)

`APETool` (`modules/rv-tools/src/rv_tools/builtin/ape/tool.py`) SHALL give APE the host time that
`aperv` gets. The `adb shell` command's timeout SHALL be the budget plus `TOOL_TEARDOWN_GRACE_S`, so
APE can end on its own `--running-minutes` timer and finish its teardown before the host kills it
(INV-TOOL-27).

Once APE ends on its own, the exit code reaches the tool. That code cannot tell a lost run from a
good one: APE exits non-zero when the app under test crashes, which is data the run exists to
collect, and a device that went away also yields non-zero. The tool SHALL therefore run the command
without the non-zero-exit check of `AbstractTool._execute_and_check_command` and judge the run by
elapsed time instead (INV-TOOL-28). This is `aperv`'s completion rule (`aperv` INV-APV-60). A command
timeout still raises `RVToolTimeoutError`, which stays a normal end.

Before starting APE, the tool SHALL push `/data/local/tmp/ape.properties` with the three capture lines
(INV-TOOL-29). Upstream APE then writes a screenshot and a GUI-tree XML only when a new abstract state
appears, rather than on every step, which is the capture policy the `aperv` jar applies by default.
The files stay on the emulator's `/sdcard`, and rv-android does not read them.

#### Scenario: the command timeout carries the grace
- **WHEN** `APETool.execute_tool_specific_logic()` runs with `task.config.timeout = 300`
- **THEN** the `adb` command SHALL carry `--running-minutes 5` and a timeout of `345` seconds

#### Scenario: a non-zero exit after the full budget completes the task
- **WHEN** APE returns exit code `1` after 310 s of a 300 s budget
- **THEN** the tool SHALL return without raising, and the task SHALL be stored as completed

#### Scenario: an early return is an error, whatever the exit code
- **WHEN** APE returns exit code `0` after 120 s of a 300 s budget
- **THEN** the tool SHALL raise `RVToolExecutionError` whose message names `120` and `300`

#### Scenario: a return just above the floor completes the task
- **WHEN** APE returns after 256 s of a 300 s budget (floor 255 s)
- **THEN** the tool SHALL return without raising

#### Scenario: the host timeout is still a normal end
- **WHEN** the `adb` command times out at 345 s
- **THEN** `RVToolTimeoutError` SHALL propagate, and `AbstractTool.execute()` SHALL treat it as a normal end (INV-TOOL-06)

#### Scenario: the capture properties are pushed before APE starts
- **WHEN** the tool runs on device `emulator-5554`
- **THEN** an `adb -s emulator-5554 push` to `/data/local/tmp/ape.properties` SHALL run before the APE command
- **AND** the pushed file SHALL be exactly `ape.takeScreenshotForEveryStep=false\nape.saveGUITreeToXmlEveryStep=false\nape.takeScreenshotForNewState=true\n`
- **AND** a failed push SHALL raise `RVToolExecutionError`, and APE SHALL NOT start
