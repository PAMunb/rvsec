# Proposal: CLI `--timeout` → `--timeouts` accepting a comma-separated list

GitHub Issue: #75

## Why

The env var is named `RV_TIMEOUTS` (plural) and the entire core — `ExperimentConfig.timeouts: List[int]`, `PlatformConfig.timeouts: List[int]`, and task generation in `Platform._generate_tasks()` (cartesian product per FR08) — already treats timeouts as a list that multiplies the execution matrix. But both CLI entry points accept only a single scalar value and force-wrap it in a one-element list. Worse, because the Click option infers `type=INT`, setting `RV_TIMEOUTS="60,300"` crashes with "not a valid integer" instead of producing two timeout arms.

This limitation already forced a production workaround: `experimento-20260706/docker-compose.smoke.yml` documents running the same container twice (`RV_TIMEOUTS=60`, then `120`) with the same experiment name, relying on auto-resume — exactly what a single invocation with a timeout list would do. Full investigation: `docs/20260712_investigacao_rv_timeouts_lista.md`.

## What Changes

- **BREAKING** — `rv-experiment run --timeout <int>` is renamed to `--timeouts <csv>` (hard rename, no alias, per P3). The option becomes a string parsed as comma-separated positive integers (`"300"` or `"60,300,600"`), mirroring the `--tools` pattern (string option + manual split downstream).
- **BREAKING** — `rv-platform run --timeout <int>` is renamed to `--timeouts <csv>` with the same parsing, for CLI parity.
- `RV_TIMEOUTS` gains list semantics end-to-end: `RV_TIMEOUTS="60,300"` now yields `timeouts=[60, 300]` instead of a CLI crash. The env var name, the `ENV_TIMEOUTS` constant, and CLI > env > default precedence (INV-EXP-32) are unchanged.
- Invalid values (empty string, non-integer, `<= 0`) fail fast with a clear CLI error at the entry point, before any experiment setup.
- Tests: `test_cli_envvar_precedence.py` updated for the renamed parameter (assertions become lists); new cases for the list format and for invalid input.
- Docs: `.env.example`, top-level and module READMEs, `rv-experiment/docs/architecture.md`, `experimento-20260706/README.md`, and the smoke-compose workaround comment are updated to the new flag and list format.

**Not changing** (explicitly out of scope):
- The core: config models, `_generate_tasks()`, resume identity `(apk, tool, variant, repetition, timeout)`, result processing — all already list-aware.
- `RV_TIMEOUTS` / `ENV_TIMEOUTS` (already plural and correct); the ~40 `docker-compose.*.yml` files that set `RV_TIMEOUTS=...` keep working and gain list support for free.
- `rv-agent`'s own `--timeout` (agent execution timeout, scalar) and `--analysis-timeout` (static analysis timeout, scalar) — unrelated flags, correct as-is.
- The env-var resolution architecture (`gh-tbd-env-vars-architecture`) — orthogonal; this change keeps the existing Click `envvar=` mechanism.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `experiment`: the CLI ingestion requirement changes — the run command exposes `--timeouts` (comma-separated list of positive integers) instead of scalar `--timeout`; `RV_TIMEOUTS` accepts the same list format; validation of the list happens at the CLI boundary.
- `platform`: the `rv-platform` CLI run command exposes `--timeouts` with identical format and validation, feeding `PlatformConfig.timeouts` directly.

## Impact

- **Modules**: `rv-experiment` (`__main__.py`: Click option, `run()` signature, log lines, `_create_experiment_config_from_cli`, new parse helper; tests), `rv-platform` (`__main__.py`: argparse option and config wiring). No other module touches the flag.
- **Requirements**: FR08 (task generation cartesian product — now reachable with multiple timeouts from a single CLI invocation), FR16 (CLI surface), INV-EXP-32 (precedence preserved), INV-PLT-01/INV-PLT-09 (already list-based, unchanged).
- **Operational**: any script invoking the literal `--timeout` flag on rv-experiment/rv-platform must switch to `--timeouts` (breaking by design). Compose files using `RV_TIMEOUTS` are unaffected.
- **Cross-module**: none beyond the two CLIs; the parse helper is 3 lines and may be duplicated per CLI or centralized in `rv-android-core` (decided in design.md under P1).
