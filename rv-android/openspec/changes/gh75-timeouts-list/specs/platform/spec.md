## Purpose

This delta gives the standalone rv-platform CLI (`rv-platform run`) parity with the renamed
rv-experiment flag: `--timeouts` accepting a comma-separated list of positive integers instead
of the scalar `--timeout`. The platform core needs no change — `PlatformConfig.timeouts` is
already `List[int]` (validated by Pydantic field validators, INV-PLT-09) and
`Platform._generate_tasks()` already iterates the full list to build the cartesian task matrix
(INV-PLT-01). The only scalar bottleneck is the argparse declaration in
`modules/rv-platform/src/rv_platform/__main__.py`, which reads one `int` and wraps it as
`timeouts=[args.timeout]`.

The parsing mirrors the existing `--tools` handling in the same file (string argument, manual
`split(",")` downstream) and applies the same validation rules as the rv-experiment side: every
token must be a positive integer, and an empty or invalid list aborts the command before any
platform setup. The rename is hard (P3): `--timeout` no longer exists on `rv-platform run`.

## Data Contracts

### Input

- `timeouts: str` — comma-separated positive integers, e.g. `"300"` or `"60,300"` (source: user
  input via argparse `--timeouts`, default `"300"`). Replaces the former `--timeout: int`
  argument. Parsed into `List[int]` before constructing `PlatformConfig`.

### Output

- `PlatformConfig.timeouts: List[int]` — the parsed list, consumed by `Platform._generate_tasks()`.

### Side-Effects

- None new. Multiple timeouts multiply the task matrix per INV-PLT-01, as already specified.

### Error

- argparse/CLI error (exit code 2) — when the timeouts string is empty, contains a non-integer
  token, or contains a value `<= 0`. The platform MUST NOT start.

## Invariants

- **INV-PLT-22**: The `rv-platform run --timeouts` argument MUST be declared as a string and
  parsed into `List[int]` with the same rules as the rv-experiment CLI (comma split, whitespace
  trim, positive integers only, order preserved, no deduplication). Invalid input MUST abort
  with a CLI usage error before `PlatformConfig` construction.

## ADDED Requirements

### Requirement: Standalone CLI Timeout List (FR08)

The `rv-platform run` command MUST expose `--timeouts` (string, comma-separated positive
integers, default `"300"`) and MUST parse it into a `List[int]` assigned to
`PlatformConfig.timeouts`. Parsing and validation MUST match the rv-experiment CLI behavior
(INV-PLT-22), so a researcher can move an invocation between the two entry points without
changing the flag value.

The scalar flag `--timeout` MUST NOT exist on `rv-platform run` (hard rename, P3 — no alias).

#### Scenario: Multiple Timeouts via Standalone CLI

- **WHEN** the user runs `rv-platform run --tools monkey --apks-dir ./apks_examples --timeouts 60,300`
  against a directory with 1 APK and default repetitions (1)
- **THEN** `PlatformConfig.timeouts` MUST be `[60, 300]`
- **AND** `Platform._generate_tasks()` MUST produce exactly 2 tasks (1 APK × 1 tool × 1 rep × 2
  timeouts)

#### Scenario: Invalid Timeout Rejected Before Platform Setup

- **WHEN** the user runs `rv-platform run --tools monkey --timeouts 300,-5`
- **THEN** the CLI MUST exit with a usage error stating timeouts must be positive integers
- **AND** no `PlatformConfig` MUST be constructed and no task generation MUST occur

#### Scenario: Old Scalar Flag No Longer Exists

- **WHEN** the user runs `rv-platform run --tools monkey --timeout 300`
- **THEN** argparse MUST reject the unknown argument `--timeout` with a usage error
