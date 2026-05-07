## Why

GitHub Issue: # *(TBD — directory name will be renamed to `gh<N>-env-vars-architecture` once the issue is filed)*

This change exists because **gh55 left the env-var → CLI bridge as a gambiarra**. See `openspec/changes/gh55-env-purity-avd-api30/design.md` → "Known Limitations (Gambiarra)" for the historical reasoning. In short, gh55 patched 17 `@click.option(...)` decorators in `rv-experiment/__main__.py` with `envvar=ENV_X` so Click itself performs env→flag fallback. That made INV-EXP-32 hold for *one* CLI surface — `rv-experiment` Click — and *only* when the module is invoked through that exact path.

Four problems remain after gh55:

1. **Other module CLIs are argparse, not Click.** `rv-platform.__main__`, `rv-static-analysis.__main__`, `rv-instrumentation-ajc.__main__`, `rv-monitor-generator.__main__` all use `argparse`. argparse has no `envvar=` equivalent; manual `default=os.environ.get(...)` per-arg would be required.
2. **Standalone module execution ignores env vars entirely.** Every L5 module above can be invoked directly (`uv run rv-platform run ...`, `uv run rv-static-analysis ...`, etc.). When invoked outside `rv-experiment`, env vars set on the shell are silently ignored — the user explicitly flagged this during gh55 investigation: *"boa parte dos modulos pode ser executada standalone!!!! esta tudo muito errado"*.
3. **Two sources of truth in `rv-experiment` itself.** Some `RV_*` are read in `ExperimentConfig.__post_init__` (Python `os.environ.get`), others are handled via Click `envvar=`. New developers must memorize which path applies to which var; lint cannot enforce a single pattern.
4. **Per-flag manual maintenance.** Each new CLI option requires remembering to wire `envvar=` (Click) or `default=os.environ.get(...)` (argparse). There is no compile-time check that `ENV_X` ↔ `--flag` stays paired. `check_env_vars_drift.py` (gh55) detects undocumented vars but cannot detect a missing `envvar=` declaration.

The architectural decision was deferred during gh55 because gh55's primary goals (constant centralization, Layer Purity, AVD bump) were validated and ready to ship. Reopening the architecture would have blocked ~3 weeks of completed work. This change finishes the job.

## What Changes

### Goal

Establish **one** mechanism for env-var resolution across **every** L5 entry point in the workspace, so:

- Every documented `RV_*` env var is consumed identically whether the user runs `rv-experiment`, `rv-platform`, `rv-static-analysis`, `rv-instrumentation-ajc`, `rv-monitor-generator`, or `rv-agent`.
- Standalone module execution (no `rv-experiment` wrapper) honors env vars.
- INV-EXP-30 (only L5 reads env) and INV-EXP-32 (every CLI flag has matching env var, precedence CLI > env > default) hold across all CLIs, not just Click.
- Adding a new flag does not require remembering to wire env reading manually.

### Two design options under evaluation

| Option | Approach | Where it lives |
|---|---|---|
| **C: Centralized loader** | New `rv-android-core/config/env_loader.py` with `load_env_config(allow_list: list[str]) -> dict[str, str]`. Each L5 entry point calls it at startup, merges result with CLI args (CLI wins). | One module, called from each L5 main. |
| **D: pydantic-settings** | Each L5 config (`ExperimentConfig`, `PlatformConfig`, `StaticAnalysisConfig`, ...) inherits `pydantic_settings.BaseSettings` with `env_prefix="RV_"` and `model_config = SettingsConfigDict(case_sensitive=True, extra="forbid")`. Pydantic resolves env automatically; CLI args override via constructor kwargs. | Each L5 config class. |

Both options eliminate per-flag `envvar=` and per-arg `default=os.environ.get()` boilerplate. Both work for Click *and* argparse (argparse merge logic stays trivial: `Config(**{**env_dict, **vars(args)})`). The follow-up design phase compares them with a small spike before committing.

**Expected choice**: D, because pydantic-settings is the idiomatic Pydantic v2 pattern, gives type-safe env coercion (int/bool/list parsing), and makes standalone modules "free" (no extra glue). The spike's job is to confirm there's no blocker (e.g. a config that genuinely cannot be Pydantic).

### Scope (all L5 entry points)

| Entry point | CLI lib today | Has `RV_*` reads? | Change |
|---|---|---|---|
| `rv-experiment.__main__` | Click | Yes (gh55 §9 gambiarra: 17 envvar= + 3 in `__post_init__`) | Replace gambiarra with chosen option |
| `rv-platform.__main__` | argparse | No (silent gap) | Add env via chosen option |
| `rv-static-analysis.__main__` | argparse | No (silent gap; `RV_SA_TIMEOUT` only honored when called from rv-experiment) | Add env via chosen option |
| `rv-instrumentation-ajc.__main__` | argparse | No (silent gap; `RV_JVM_MEMORY` only honored when called from rv-experiment) | Add env via chosen option |
| `rv-monitor-generator.__main__` | argparse | No (silent gap) | Add env via chosen option |
| `rv-agent.cli.main` | Click | Partial (one or two envvar= today) | Audit + migrate |

### Out of scope

- Adding *new* env vars. The 28 vars in `.env.example` (post-gh55) are the universe; this change only normalizes how they are read.
- Changing INV-EXP-30 / INV-EXP-32 semantics. They stand. This change makes them hold uniformly.
- Removing the `check_env_vars_drift.py` lint. It stays; if the chosen pattern allows it, the lint may gain a "missing env binding" check.

### Backward compat (P3 — no shims)

- **gh55 §9 envvar= entries are deleted in this change** (replaced by the chosen option). No alias, no warning, no `_legacy` suffix.
- **`ExperimentConfig.__post_init__` env reads** (the 3 surviving Python `os.environ.get` calls for `RV_HUMANOID_URL`, `RV_SA_TIMEOUT`, `RV_JVM_MEMORY`) are replaced by the chosen mechanism.
- **Old files** (`rv-experiment/__main__.py` pre-change, `__post_init__` env block) are moved to `backup/<date>_env_vars_architecture/` before being overwritten, per project P3 convention.
- One commit = one consistent state. CI lint, smoke compose, and the integration test suite must pass per commit.

## Capabilities

### New Capabilities

None. This change refactors existing capabilities; the public surface (`RV_*` names, CLI flags, config fields) is preserved.

### Modified Capabilities

- `core`: gains either an `env_loader` utility (option C) or pydantic-settings base classes (option D). Either way, this is a single new internal abstraction in `rv-android-core`.
- `experiment`: `ExperimentConfig` adopts the chosen mechanism; `__main__.py` drops the gh55 §9 envvar= per-flag wiring; `__post_init__` env reads removed.
- `platform`: `PlatformConfig` adopts the chosen mechanism; `rv-platform.__main__` reads env via the same path as `rv-experiment`.
- `analysis`: `rv-static-analysis.__main__` and config gain env support, closing the silent-gap on standalone runs.
- `instrumentation`: `rv-instrumentation-ajc.__main__` and `rv-monitor-generator.__main__` gain env support similarly.
- `agent`: audit + migrate any partial Click `envvar=` entries to the chosen mechanism.

## Impact

**Modules touched:**

| Module | Change |
|--------|--------|
| `rv-android-core` | New `env_loader.py` (option C) OR `BaseRVSettings` shared base class (option D); +unit tests. |
| `rv-experiment` | Drop gh55 §9 envvar= block; drop `__post_init__` env reads; adopt chosen mechanism. |
| `rv-platform` | argparse main gains env reading via chosen mechanism. |
| `rv-static-analysis` | argparse main + config gain env reading. |
| `rv-instrumentation-ajc` | argparse main + config gain env reading. |
| `rv-monitor-generator` | argparse main gains env reading. |
| `rv-agent` | Click main audited; partial envvar= entries migrated. |
| `scripts/check_env_vars_drift.py` | Optionally extended with "missing env binding" check, depending on chosen pattern. |
| `tests/integration/` | Add per-module standalone-execution env precedence tests (CLI > env > default × 6 modules × 2 reps). |

**FRs/NFRs:**

- NFR01 Maintainability — single mechanism replaces per-flag manual wiring; new flags get env support automatically (option D) or with one call (option C).
- NFR03 Testability — single mechanism is a single test surface; no per-flag matrix.
- NFR05 Reproducibility — every CLI honors documented env vars uniformly, eliminating the standalone-execution silent-gap.

**Breaking changes for consumers:**

- None at the user level. The `RV_*` env vars and CLI flags keep the same names and semantics. Only the internal resolution path changes.
- Internal consumers (callers passing pre-built config objects) may need to update construction syntax if option D is chosen and configs become Pydantic `BaseSettings` (positional vs keyword args).

**Cross-module dependencies:**

- `rv-android-core` becomes the canonical home of the env-resolution mechanism (option C: utility module; option D: shared `BaseSettings` base).
- All L5 entry points depend on `rv-android-core` for env resolution, replacing today's heterogeneous mix (Click `envvar=`, argparse `default=os.environ.get`, raw `os.environ.get` in `__post_init__`).

## Estimated effort

- Spike to choose between C and D: ~2 hours (write minimal example for each, verify pydantic-settings handles list-typed flags like `RV_TOOLS=ape,fastbot`).
- Implementation: ~1 day (touch 6 entry points + tests).
- Smoke run inside container: 1 run × 3 min.

## References

- `openspec/changes/gh55-env-purity-avd-api30/design.md` — "Known Limitations (Gambiarra)" section. Required reading before starting this change.
- `openspec/changes/gh55-env-purity-avd-api30/tasks.md §9` — the gambiarra being replaced.
- `modules/rv-android-core/src/rv_android_core/constants.py` — canonical `ENV_*` constants (post-gh55).
- `.env.example` — canonical `RV_*` inventory (post-gh55).
- `pydantic-settings` docs: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
