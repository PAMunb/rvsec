# Design: CLI `--timeout` → `--timeouts` accepting a comma-separated list

GitHub Issue: #75 · Proposal: `proposal.md` · Investigation: `docs/20260712_investigacao_rv_timeouts_lista.md`

## Context

The experiment core is list-native: `ExperimentConfig.timeouts: List[int]`,
`PlatformConfig.timeouts: List[int]` (Pydantic-validated, INV-PLT-09), and
`Platform._generate_tasks()` builds the cartesian task matrix over the timeout list
(`modules/rv-platform/src/rv_platform/platform.py:189-219`, FR08 / INV-PLT-01). Task identity —
`(apk_name, tool_name, variant, repetition, timeout)` — already distinguishes tasks from
different timeouts, so resume works unchanged with multiple timeouts.

The two CLI entry points are the only scalar bottleneck:

- `modules/rv-experiment/src/rv_experiment/__main__.py:332` — Click option `--timeout` with
  `default=DEFAULT_TIMEOUT` (int → Click infers `type=INT`) and `envvar=ENV_TIMEOUTS`. A list
  value in `RV_TIMEOUTS` crashes on `int("60,300")`. The scalar is wrapped as
  `timeouts=[timeout]` at `__main__.py:1133`.
- `modules/rv-platform/src/rv_platform/__main__.py:98` — argparse `--timeout` with `type=int`,
  wrapped as `timeouts=[args.timeout]` at `__main__.py:406`.

Reference pattern: `--tools` is a plain string option in both CLIs, split manually downstream
(`_split_tool_specifications()` in rv-experiment; `args.tools.split(",")` in rv-platform). The
`--timeouts` option follows the same shape.

Constraints: P3 hard rename (no `--timeout` alias); `RV_TIMEOUTS` / `ENV_TIMEOUTS`
(`rv-android-core/constants.py:79`) unchanged; CLI > env > default precedence (INV-EXP-32)
preserved via Click's existing `envvar=` mechanism; core untouched.

## Architecture

No new components. The change is confined to the two CLI boundary layers:

```
user / RV_TIMEOUTS env
        │  "60,300"  (string)
        ▼
rv-experiment __main__.py            rv-platform __main__.py
  --timeouts (Click, type=str)         --timeouts (argparse, type=str)
  _parse_timeouts(raw) → [60,300]      _parse_timeouts(raw) → [60,300]
        │                                     │
        ▼                                     ▼
  ExperimentConfig(timeouts=[...])     PlatformConfig(timeouts=[...])
        │                                     │
        └────────► Platform._generate_tasks() ◄┘   (unchanged, already list-aware)
```

### Key Components

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| `rv_experiment.__main__._parse_timeouts` | Split/validate CSV string at CLI boundary | `str` | `list[int]` or `click.BadParameter` |
| `rv_platform.__main__._parse_timeouts` | Same rules, argparse flavor | `str` | `list[int]` or argparse error (exit 2) |
| `rv_experiment.__main__.run()` | Renamed param `timeout: int` → `timeouts: str`; parse before config construction | CLI args | `ExperimentConfig` |
| `rv_platform.__main__._create_platform_config` | `timeouts=_parse_timeouts(args.timeouts)` | `argparse.Namespace` | `PlatformConfig` |

## Mapping: Spec → Implementation → Test

| Requirement | Implementation | Test |
|-------------|---------------|------|
| Timeout List CLI Flag (experiment delta) | `rv_experiment/__main__.py` option + `_parse_timeouts` | `test_cli_envvar_precedence.py` (renamed captures + new list cases) |
| INV-EXP-33 (parse rules, fail-fast) | `_parse_timeouts` raising `click.BadParameter` | new `test_timeouts_invalid_*` cases |
| INV-EXP-32 (CLI > env > default) | unchanged Click `envvar=ENV_TIMEOUTS` | existing precedence tests, assertions become lists |
| Standalone CLI Timeout List (platform delta) | `rv_platform/__main__.py` argparse + parse | new CLI-level test (parse function unit tests) |
| INV-PLT-22 (identical rules) | same parse body in both CLIs | mirrored unit cases |
| INV-PLT-01 (matrix, unchanged) | no change | existing platform tests |

## Goals / Non-Goals

**Goals:**
- One CLI invocation expresses a multi-timeout experiment (`--timeouts 60,300`).
- `RV_TIMEOUTS="60,300"` works identically inside and outside Docker, no CLI crash.
- Invalid input fails at parse time with a message naming the rule (positive integers, comma-separated).
- Zero changes below the CLI boundary.

**Non-Goals:**
- No `multiple=True` / repeated-flag form (`--timeouts 60 --timeouts 300`) — conflicts with a
  single env var value and diverges from the `--tools` precedent.
- No deduplication or reordering of the list (see Decisions).
- No change to `--analysis-timeout` (rv-experiment) or rv-agent's `--timeout` — separate scalar concerns.
- No change to the env-var resolution architecture (`gh-tbd-env-vars-architecture` remains orthogonal).

## Decisions

1. **String option + `_parse_timeouts` split, no custom ParamType.** Mirrors `--tools` — the
   established repo pattern for list-valued options that must also arrive via a single env var.
   A custom `ParamType` would work for Click but has no argparse counterpart, breaking parity.
   Rejected: `multiple=True` (poor `envvar` interaction, no argparse parity). **Where the parse
   runs differs per CLI, forced by each framework's error path:** rv-experiment wires
   `_parse_timeouts` as a Click **`callback=`** (not a call inside `run()`), because `run()` is
   wrapped by `@handle_errors`, which absorbs every exception and would turn a `BadParameter`
   into a silent exit 0 — the callback runs during Click's parameter processing, before that
   wrapper, so the usage error surfaces and exits 2 (INV-EXP-33 fail-fast). rv-platform wires it
   as argparse **`type=_parse_timeouts`** (plus `allow_abbrev=False` on the `run` subparser), so
   `parse_args()` raises the usage error and exits 2 before `PlatformConfig` is built, since
   `cmd_run`'s `except` would otherwise return 1. Both satisfy "parse at the CLI boundary, fail
   before setup"; the invariants do not mandate the mechanism.

2. **Duplicate the ~6-line parser in each CLI, not a shared helper in rv-android-core.** P1:
   the `--tools` precedent already duplicates split logic per CLI; the two copies raise
   CLI-native errors (`click.BadParameter` vs `parser.error`), so a shared pure function would
   still need per-CLI wrapping. Six lines duplicated beats a new cross-module API surface for
   one concern. INV-PLT-22 pins the rules so drift is a spec violation caught by mirrored tests.
   Rejected: helper in `rv_android_core/util/` (premature abstraction for 2 call sites).

3. **No dedup/sort of the parsed list.** Order is user intent; duplicates produce
   identity-colliding tasks that `_skip_completed_tasks()` already skips harmlessly on resume.
   Validating against duplicates would add a rule the core doesn't need. (INV-EXP-33 documents
   this explicitly.)

4. **`default="300"` derives from `DEFAULT_TIMEOUT`.** rv-experiment uses
   `default=str(DEFAULT_TIMEOUT)` (constant at `rv_experiment/constants.py:58`); rv-platform
   keeps its literal `"300"` (it has no constants dependency on rv-experiment). Keeping the
   default as a string is what stops Click from inferring `type=INT` and re-breaking env lists.

5. **Hard rename, no alias (P3).** `--timeout` disappears from both CLIs in the same commit as
   all doc/test updates. Verification: `grep -rn '\-\-timeout\b'` must return only rv-agent's
   own flag and `--analysis-timeout`.

## API Design

### `_parse_timeouts(raw: str) -> list[int]` (rv-experiment flavor)

```python
def _parse_timeouts(raw: str) -> list[int]:
    """Parse the --timeouts CSV string into a list of positive integers."""
    try:
        values = [int(t.strip()) for t in raw.split(",") if t.strip()]
    except ValueError as e:
        raise click.BadParameter(f"timeouts must be comma-separated integers: {raw!r}") from e
    if not values or any(v <= 0 for v in values):
        raise click.BadParameter(f"timeouts must be positive integers: {raw!r}")
    return values
```

- **Preconditions**: `raw` is the Click-resolved option value (flag, env, or default — always str).
- **Postconditions**: non-empty `list[int]`, all `> 0`, user order preserved.
- **Errors**: `click.BadParameter` (Click renders usage + message, exit code 2).

rv-platform flavor: identical body, but raises `argparse.ArgumentTypeError` (Click's
`BadParameter` has no argparse analogue). It is wired as the argument's `type=_parse_timeouts`
so argparse runs it during `parse_args()` and renders the usage error (exit 2) before any
`PlatformConfig` is built — the whole CSV is a single token, so the `type=` callable receives it
whole. `allow_abbrev=False` on the `run` subparser stops the removed `--timeout` from being
accepted as a prefix abbreviation of `--timeouts`.

### Click option (rv-experiment)

```python
@click.option(
    "--timeouts",
    default=str(DEFAULT_TIMEOUT),
    envvar=ENV_TIMEOUTS,
    callback=_timeouts_callback,  # parses to List[int] before @handle_errors-wrapped run()
    help=f'Execution timeouts in seconds, comma-separated (e.g. "300" or "60,300"; default: {DEFAULT_TIMEOUT})',
)
```

`_timeouts_callback` is a thin wrapper that calls `_parse_timeouts(value)` — Click runs it during
parameter processing, so `run()` receives `timeouts` already as `List[int]`. `run()`'s signature
becomes `timeouts: List[int]` (not `str`); it assigns the list straight to
`ExperimentConfig.timeouts` and the log lines (`__main__.py:542,606`) display the list. The parse
therefore precedes any experiment setup and, crucially, precedes the `@handle_errors` wrapper that
would otherwise swallow the `BadParameter` (see Decision 1).

## Data Flow

1. Click/argparse resolves `--timeouts` per precedence CLI > `RV_TIMEOUTS` > default (string at
   every step — no premature int coercion).
2. `_parse_timeouts` converts to `list[int]` or aborts with a usage error.
3. The list feeds `ExperimentConfig.timeouts` / `PlatformConfig.timeouts` (Pydantic re-validates
   positivity — INV-EXP-03 / INV-PLT-09 — as the existing boundary check for the JSON/config-file
   path, which bypasses the CLI parser).
4. `Platform._generate_tasks()` expands the matrix; task identity carries each timeout.

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| `click.BadParameter` | non-int token, empty list, value ≤ 0 in rv-experiment | Fail fast before experiment setup; message names the rule and echoes the raw value | User fixes the flag/env value |
| argparse usage error (exit 2) | same conditions in rv-platform | `parser.error()` before `PlatformConfig` construction | Same |
| `ValueError` from Pydantic validators | config-file path with invalid timeouts (unchanged behavior) | Existing `ExperimentConfig.validate()` / `PlatformConfig` field validators | User fixes JSON config |

## Risks / Trade-offs

- [Breaking external scripts that pass `--timeout`] → Intentional (P3). Mitigation: repo-wide
  grep in the same commit updates every in-tree caller (`.env.example`, READMEs,
  `experimento-20260706/` docs, smoke compose comment); the usage error from both CLIs names
  the new flag via help text.
- [Parser duplication drifts between CLIs] → INV-PLT-22 pins identical rules; mirrored unit
  tests in both modules fail if either copy changes alone.
- [Docker entry-point allow-list] → No risk: `RV_TIMEOUTS` stays in the `ENV_*` registry;
  entry point performs no env→flag translation (post-gh55 behavior), so the container path is
  unaffected.

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Unit (rv-experiment) | `_parse_timeouts`: single, list, whitespace, invalid token, empty, ≤ 0 | direct calls | ~6 |
| Integration (rv-experiment) | precedence CLI > env > default with list values; `RV_TIMEOUTS="60,300"` → `[60, 300]`; `--timeout` rejected | `CliRunner` on `run` (update `test_cli_envvar_precedence.py`: captures rename to `timeouts`, assertions become lists) | ~6 updated + ~3 new |
| Unit (rv-platform) | `_parse_timeouts` mirror cases; `_create_platform_config` wiring | direct calls with `Namespace` | ~4 |

CI contract: `pytest --import-mode=importlib -o "addopts="` per module.

## Open Questions

None — the three questions from the investigation doc (value format, helper placement,
dedup policy) are resolved in Decisions 1-3; the OpenSpec-vs-direct question was resolved by
running this change as gh75.
