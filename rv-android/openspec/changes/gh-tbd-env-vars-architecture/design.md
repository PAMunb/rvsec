# Design — Env-Var Resolution Architecture

> **Status**: draft. This document is created during gh55 implementation as a follow-up tracking artifact. Detailed design will be filled in once a GitHub issue is filed and the change is officially picked up.

## Context

Inherits the entire "Known Limitations (Gambiarra)" section of `openspec/changes/gh55-env-purity-avd-api30/design.md`. Read that first.

The TL;DR: gh55 deleted the OLD `docker-entrypoint.sh` env→flag translator (~100 lines) without compensating Python-side reading. The bug surfaced in the gh55 smoke run on 2026-05-06 — the experiment ran with defaults despite `RV_*` env vars being set. gh55 §9 patched 17 `@click.option(...)` with `envvar=ENV_X` to satisfy INV-EXP-32 inside `rv-experiment` Click. That patch is the gambiarra this change replaces with a real architecture.

## Goals

1. **One mechanism, six entry points**: `rv-experiment`, `rv-platform`, `rv-static-analysis`, `rv-instrumentation-ajc`, `rv-monitor-generator`, `rv-agent` all resolve env vars identically.
2. **Standalone execution honors env**: invoking any L5 module directly (without `rv-experiment`) honors `RV_*` env vars.
3. **No per-flag manual wiring**: adding a new flag should not require remembering to add `envvar=` (Click) or `default=os.environ.get(...)` (argparse).
4. **INV-EXP-30 and INV-EXP-32 hold uniformly**: only L5 reads env; precedence CLI > env > default for every flag with a matching env var.
5. **No new env vars introduced**: the `.env.example` inventory (post-gh55) is the universe.

## Constraints

- Must not break existing `RV_*` env var names or CLI flag names (P3 forbids shims; this is a *replace*, not an *add*).
- Must work for both Click and argparse CLIs without forcing a CLI library migration.
- Must respect Layer Purity (INV-EXP-30): only L5 reads env; lower layers receive resolved config via Pydantic models.
- Must keep `check_env_vars_drift.py` lint operational; ideally extend it.

## Options under evaluation

### Option C: Centralized loader

```python
# modules/rv-android-core/src/rv_android_core/config/env_loader.py
def load_env_config(allow_list: list[str]) -> dict[str, str]:
    """Read env vars matching allow_list (the ENV_* constant values). Return dict
    keyed by the bare var name (without RV_ prefix? Or with? Decide in spike)."""
    return {k: v for k, v in os.environ.items() if k in allow_list}
```

Each L5 entry point:

```python
from rv_android_core.constants import ENV_TOOLS, ENV_TIMEOUTS, ...
from rv_android_core.config.env_loader import load_env_config

ALLOW_LIST = [ENV_TOOLS, ENV_TIMEOUTS, ENV_INSTRUMENTATION_VARIANT, ...]

def main():
    args = parser.parse_args()  # or click.command()
    env_config = load_env_config(ALLOW_LIST)
    config = ExperimentConfig(**{**env_config, **vars(args)})  # CLI wins
```

**Pros**:
- Single, simple utility. Easy to test.
- Works for argparse and Click identically.
- Standalone modules covered by calling `load_env_config` once.

**Cons**:
- Each L5 entry point still needs to declare its allow-list.
- Type coercion (int, bool, list) is the caller's responsibility.
- Drift risk: a new `RV_*` constant might be added but not appended to any allow-list.

### Option D: pydantic-settings BaseSettings

```python
# modules/rv-experiment/src/rv_experiment/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class ExperimentConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="RV_",
        case_sensitive=True,
        extra="forbid",
    )
    tools: list[str] = []
    timeout: int = 60
    instrumentation_variant: str = "ajc"
    ...
```

`pydantic-settings` reads from env automatically using `env_prefix="RV_"`. Each L5 entry point:

```python
def main():
    args = parser.parse_args()
    config = ExperimentConfig(**{k: v for k, v in vars(args).items() if v is not None})
    # Pydantic merges: env + defaults first; explicit kwargs override
```

**Pros**:
- Type coercion is automatic (Pydantic handles `RV_TOOLS=a,b` → `list[str]`, `RV_TIMEOUTS=60` → `int`).
- No allow-list maintenance: declaring a field with the right name *is* the env binding.
- Standalone execution gets env "for free".
- Idiomatic Pydantic v2; aligns with existing `ExperimentConfig` Pydantic adoption.
- Drift detection: a new `ENV_*` constant without a corresponding field surfaces as a missing-field complaint.

**Cons**:
- Forces every L5 config to be a `BaseSettings` subclass (some are plain dataclasses today).
- `env_prefix="RV_"` is module-global — there is no per-flag override. If two flags resolve from the same env var with different semantics, this wouldn't fit (no current case, but worth noting).
- Pydantic precedence: env is consumed *during construction*. CLI override semantics need explicit `**kwargs` merging — must verify `model_validate` vs constructor behavior in the spike.

## Decision criteria for the spike

Run a 2-hour spike that builds **both** a minimal example using `RV_TOOLS=ape,fastbot` (list) and `RV_TIMEOUTS=180` (int). Validate:

1. **List parsing**: `RV_TOOLS=ape,fastbot` arrives as `list[str]` in the resolved config.
2. **Boolean parsing**: `RV_PYDANTIC=true` arrives as `bool`. (Currently parsed manually.)
3. **CLI override**: setting `RV_TIMEOUTS=180` *and* passing `--timeout 60` resolves to 60.
4. **Default fallback**: with neither env nor CLI, the defined default applies.
5. **`extra="forbid"` interaction**: `RV_BOGUS=x` fails loudly under both options.
6. **Standalone**: running `uv run rv-platform run` (no `rv-experiment` wrapper) honors env.

If both options pass, choose D (idiomatic, less code). If D blocks on a real-world config that can't be Pydantic, choose C.

## Migration plan (per-entry-point)

1. **rv-experiment** (gh55 §9 site):
   - Delete the 17 `envvar=ENV_X` declarations in `__main__.py`.
   - Delete the 3 `os.environ.get(ENV_*)` reads in `ExperimentConfig.__post_init__`.
   - Add the chosen mechanism.
   - Re-run gh55 smoke 6.5 to confirm parity.

2. **rv-platform**: argparse main currently has zero env reads. Add the mechanism. Add an integration test: `RV_TOOLS=ape uv run rv-platform run --apks-dir test/fixtures/` resolves `tools=["ape"]`.

3. **rv-static-analysis, rv-instrumentation-ajc, rv-monitor-generator**: same pattern as rv-platform.

4. **rv-agent**: audit existing partial Click `envvar=`, migrate to chosen pattern.

5. **scripts/check_env_vars_drift.py**: extend with a "missing field/binding" check appropriate to the chosen pattern (option D: every `ENV_*` constant has a corresponding field in some `BaseSettings` subclass).

## Testing strategy

- **Unit**: per-entry-point precedence test (CLI > env > default), three reps each → 18 cases.
- **Unit**: `extra="forbid"` rejects unknown env vars.
- **Integration**: `RV_TOOLS=ape RV_TIMEOUTS=180 uv run rv-experiment run --skip-execution` in a clean container, assert resolved config matches.
- **Integration**: same env in `uv run rv-platform run --skip-execution`, assert standalone path works.
- **Smoke**: re-run gh55 smoke 6.5 with the new mechanism replacing the gambiarra; assert tool selection and timeouts match the env vars.

## Risks

- **Pydantic v2 BaseSettings list-parsing edge cases**: `env_parse_none_str`, `env_nested_delimiter` may need tuning for `RV_TOOLS=monkey,ape:dfs` (colon-suffix variants). Mitigated by spike step 1.
- **argparse `Namespace` to Pydantic merge**: `vars(args)` may include keys the config doesn't declare → handle via `extra="ignore"` for the wrapper or filter in the merge step.
- **Existing tests that mock `os.environ.get`**: may need rewriting if option D moves env access into Pydantic internals.
- **Two-week scope creep**: this change is *only* about env resolution. Resist the temptation to also normalize CLI library choice (argparse vs Click), config ergonomics, or logging.

## Open questions

- Should `check_env_vars_drift.py` gain a "missing env binding" check, or stay focused on docs drift? Recommendation: yes, but only after the architecture lands so the lint logic is meaningful.
- Should `rv-agent` config also adopt the same `BaseSettings` pattern for consistency, even if some of its fields are not env-resolvable? Recommendation: yes — uniformity is the point of this change.
- Do we file a single GitHub issue for this change, or split into "infrastructure" + "per-module migration"? Recommendation: single issue; six modules × ~30 minutes each is one PR.
