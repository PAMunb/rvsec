## Purpose

This delta closes the gap between the plural contract of the experiment core and the scalar
surface of its CLI. `ExperimentConfig.timeouts` is a `List[int]`, the env var is named
`RV_TIMEOUTS` (plural), and task generation multiplies the execution matrix by the number of
timeouts (`|APKs| × |tool_configs| × repetitions × |timeouts|`, INV-PLT-01). Yet the only way
to feed that list from the command line is `--timeout`, a Click option that accepts exactly one
integer and is force-wrapped into a one-element list. Because the option's `default` is an
`int`, Click coerces the env value with `int(...)`, so `RV_TIMEOUTS="60,300"` does not degrade
gracefully — it crashes the CLI with "not a valid integer".

The practical cost is real: multi-timeout experiments (a standard design in the ICST study and
its follow-ups) currently require one container invocation per timeout value, chained through
auto-resume on a shared experiment name. `experimento-20260706/docker-compose.smoke.yml`
documents this workaround explicitly.

After this delta, the `run` command exposes `--timeouts`, a string option parsed as a
comma-separated list of positive integers, mirroring the `--tools` pattern (string option, manual
split downstream, INV-EXP-09 family). The flag rename is hard (P3): `--timeout` no longer exists
on `rv-experiment run`. The env var `RV_TIMEOUTS`, the `ENV_TIMEOUTS` constant, and the
CLI > env > default precedence (INV-EXP-32) are unchanged — Click keeps resolving the env value
through `envvar=`, it just receives a string now and parses it after the fact. Everything below
the CLI boundary (config models, controllers, task generation, resume identity) already handles
lists and is untouched.

Out of scope and easily confused: `rv-agent`'s own `--timeout` (agent execution timeout) and
`rv-experiment run --analysis-timeout` (static analysis timeout, "Static-Analysis Tuning CLI
Flags" requirement) are intentionally scalar and keep their names.

## Data Contracts

### Input

- `timeouts: str` — comma-separated positive integers, e.g. `"300"` or `"60,300,600"` (source:
  user input via Click `--timeouts` or `RV_TIMEOUTS` env var; default: `"300"`). Replaces the
  former `timeout: int` input. Parsed at the CLI boundary into `List[int]` before reaching
  `ExperimentConfig`.

### Output

- `ExperimentConfig.timeouts: List[int]` — the parsed list, in the order given by the user
  (destination: `ExecutionController` → `PlatformConfig` → task generation).

### Side-Effects

- None beyond existing experiment execution. Multiple timeouts multiply the task matrix, which
  was already the documented core behavior (INV-PLT-01).

### Error

- `click.BadParameter` — raised at CLI parse time when the timeouts string is empty, contains a
  non-integer token, or contains a value `<= 0`. The experiment MUST NOT start.

## Invariants

- **INV-EXP-33**: The `--timeouts` CLI option MUST be declared as a string and parsed into
  `List[int]` by splitting on commas, trimming whitespace, and coercing each token with `int()`.
  An empty result list, a non-integer token, or any value `<= 0` MUST abort the command with a
  `click.BadParameter` error before any experiment setup. The parsed list MUST preserve user
  order and MUST be passed to `ExperimentConfig.timeouts` without deduplication (duplicate
  timeouts produce identity-colliding tasks that the resume mechanism skips; the parser is not
  responsible for preventing that).

## ADDED Requirements

### Requirement: Timeout List CLI Flag (FR08, FR16, NFR05)

The `rv-experiment run` command MUST expose `--timeouts` (string, comma-separated positive
integers, default `"300"`) as the single command-line entry point for execution timeouts. The
option MUST bind to the `RV_TIMEOUTS` environment variable via Click's `envvar=` mechanism
(constant `ENV_TIMEOUTS` in `rv-android-core/constants.py`), preserving CLI > env > default
precedence per INV-EXP-32.

The value MUST be parsed at the CLI boundary into a `List[int]` (INV-EXP-33) and assigned to
`ExperimentConfig.timeouts`. Each timeout in the list becomes one arm of the task matrix — a
single invocation with `--timeouts 60,300` generates the same tasks that previously required two
invocations chained by auto-resume. Because task identity is the tuple
`(apk_name, tool_name, variant, repetition, timeout)`, resume continues to distinguish tasks
from different timeouts within one experiment.

The scalar flag `--timeout` MUST NOT exist on `rv-experiment run` (hard rename, P3 — no alias,
no deprecation shim). The `--analysis-timeout` flag and `rv-agent`'s `--timeout` are separate,
scalar concerns and MUST NOT be affected.

#### Scenario: Single Timeout (default behavior preserved)

- **WHEN** the user runs `rv-experiment run --tools monkey --timeouts 300`
- **THEN** the CLI MUST parse the value into `[300]`
- **AND** `ExperimentConfig.timeouts` MUST be `[300]`
- **AND** the generated task matrix MUST be identical to the pre-rename behavior with a single
  timeout of 300 seconds

#### Scenario: Multiple Timeouts in One Invocation

- **WHEN** the user runs `rv-experiment run --tools monkey --timeouts 60,300` against a
  directory with 2 APKs and `--repetitions 1`
- **THEN** `ExperimentConfig.timeouts` MUST be `[60, 300]`
- **AND** task generation MUST produce exactly 4 tasks (2 APKs × 1 tool × 1 rep × 2 timeouts)
- **AND** each task's identity tuple MUST carry its own timeout value

#### Scenario: Timeout List via Environment Variable

- **WHEN** a container or shell sets `RV_TIMEOUTS="60,300"` and runs
  `uv run rv-experiment run --tools monkey` (no `--timeouts` flag)
- **THEN** Click MUST resolve the option value from `RV_TIMEOUTS` via `envvar=`
- **AND** the effective `ExperimentConfig.timeouts` MUST be `[60, 300]`
- **AND** the command MUST NOT fail with an integer-coercion error

#### Scenario: CLI Flag Overrides Environment Variable

- **WHEN** the shell has `RV_TIMEOUTS="600"` exported
- **AND** the user runs `rv-experiment run --tools monkey --timeouts 60,120`
- **THEN** the effective `ExperimentConfig.timeouts` MUST be `[60, 120]` (CLI > env > default,
  INV-EXP-32)

#### Scenario: Invalid Timeout Value Fails Fast

- **WHEN** the user runs `rv-experiment run --tools monkey --timeouts 60,abc`
- **THEN** the CLI MUST fail with a `click.BadParameter` error naming the invalid token
- **AND** the experiment MUST NOT start

#### Scenario: Non-Positive Timeout Fails Fast

- **WHEN** the user runs `rv-experiment run --tools monkey --timeouts 0`
- **THEN** the CLI MUST fail with a `click.BadParameter` error stating timeouts must be positive
  integers
- **AND** the experiment MUST NOT start

#### Scenario: Old Scalar Flag No Longer Exists

- **WHEN** the user runs `rv-experiment run --tools monkey --timeout 300`
- **THEN** Click MUST reject the unknown option `--timeout` with a usage error
- **AND** the error output MUST list `--timeouts` among the valid options
