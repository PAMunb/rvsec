## Purpose

The Core domain (`rv-android-core`) provides the foundation library for the entire RV-Android workspace. Every higher-layer module depends on it; it depends on no internal module. Beyond the existing responsibilities (domain models, error handling, logging, validation, command execution, abstract tool contract), this change formalizes Core as the single source of truth for the **environment-variable identifier registry**: every `RV_*` environment variable consumed anywhere in the codebase MUST have a corresponding `ENV_*` constant declared in `rv-android-core/src/rv_android_core/constants.py`. Higher layers (experiment, platform, tools) read environment variables only through these constants, never through string literals.

This restriction is what makes the Layer Purity rule (introduced in the experiment and tools deltas) verifiable by lint: a single grep confirms that all `os.environ` access sites import from the central registry. The registry also bounds what the Docker entry point and Pydantic configurations are allowed to accept — anything not listed is rejected as unknown input.

In addition, this change formalizes strict Pydantic validation for top-level configuration models (`ExperimentConfig`, `PlatformConfig`): unknown fields cause `ValidationError`. This matters because the new entry-point allow-list catches typos in environment-variable names, but the corresponding CLI flags must catch typos in command-line arguments too. Together they form a tight allow-list at every entry point.

## Data Contracts

### Input
- `os.environ` (Python process environment) — read at L5 / L1-cross-layer only

### Output
- `ENV_*` constants — string literals (the canonical environment-variable name) used by callers via `os.environ.get(ENV_X)`

### Side-Effects
- None at the Core level (the registry itself is just a list of `str` constants)

### Error
- `ValidationError` raised by Pydantic when a top-level config model receives unknown fields (see MODIFIED Requirement: Pydantic Validation, Scenario "Top-level config explicitly declares extra='forbid'")

## Invariants

- **INV-CORE-30**: Every `RV_*` environment variable consumed anywhere in the project — Python modules under `modules/`, shell scripts under `docker/`, or scripts under `scripts/` — MUST have a corresponding `ENV_*` constant declared in `rv-android-core/src/rv_android_core/constants.py`. This includes the L1 cross-layer infra family (`RV_PYDANTIC`, `RV_PYDANTIC_STRICT`, `RV_PYDANTIC_LOG`) — they are surfaced in the registry even though only Core (L1) reads them. The Docker entry-point allow-list (see experiment delta INV-EXP-31) mirrors this registry; any `RV_*` not listed is by definition unknown. Verified by lint: `scripts/check_env_vars_drift.py`.
- **INV-CORE-31**: No code under `modules/` (excluding `rv-android-core/constants.py` itself and tests) MAY reference an environment-variable name as a string literal — all reads MUST go through the corresponding `ENV_*` constant. Verified by lint: a single combined regex covers all read forms — `grep -rnE 'os\.environ\.get\("RV_|os\.environ\["RV_|os\.getenv\("RV_' modules/` MUST return 0 hits. The lint additionally rejects environment-leaking patterns `dict\(os\.environ` and `os\.environ\.copy\(` outside the L5 module.
- **INV-CORE-32**: Top-level configuration models (`ExperimentConfig` in `rv-experiment`, `PlatformConfig` in `rv-platform`) MUST set `model_config = ConfigDict(extra="forbid")`. Unknown fields cause `ValidationError` rather than silent acceptance.

## ADDED Requirements

### Requirement: Environment-Variable Identifier Registry (NFR01, NFR03)

The Core module MUST own the canonical registry of environment-variable identifiers used by the RV-Android system. The registry takes the form of `ENV_*` constants in `rv-android-core/src/rv_android_core/constants.py`, where each constant maps a logical identifier (e.g., `ENV_HUMANOID_URL`) to the corresponding environment-variable string (`"RV_HUMANOID_URL"`). The registry MUST cover all environment variables that the system recognizes as input — any variable name not listed in the registry is by definition unknown.

Higher layers consume the registry by importing the constant and passing it to `os.environ.get`. They MUST NOT pass string literals like `"RV_TIMEOUTS"` directly. This indirection serves two purposes: (a) it lets a single grep across `modules/` confirm Layer Purity (only L5 and L1-exceptions read environment variables), and (b) it provides a definitive list against which the Docker entry-point allow-list and the README documentation can be reconciled by the CI lint.

When a new environment variable is added to the system, the developer MUST first add the corresponding `ENV_*` constant to `constants.py`. The CI lint script `scripts/check_env_vars_drift.py` MUST fail if any `os.environ` access uses a string literal that does not correspond to an `ENV_*` constant.

#### Scenario: Tool reads an environment variable via the registry

- **WHEN** the rv-experiment CLI initialization code needs to resolve a value from the environment
- **AND** the value's logical name is `RV_TIMEOUTS`
- **THEN** the code MUST `from rv_android_core.constants import ENV_TIMEOUTS`
- **AND** MUST call `os.environ.get(ENV_TIMEOUTS)` (not `os.environ.get("RV_TIMEOUTS")`)
- **AND** the lint script `scripts/check_env_vars_drift.py` MUST pass

#### Scenario: Lint catches string-literal regression

- **WHEN** a developer commits code containing any of these forms — `os.environ.get("RV_TOOLS")`, `os.environ["RV_TOOLS"]`, `os.getenv("RV_TOOLS")` — instead of going through `ENV_TOOLS`
- **THEN** the CI lint MUST fail with a message naming the offending file, line, and which of the three forms was matched
- **AND** the message MUST point the developer at `rv-android-core/src/rv_android_core/constants.py` for the canonical constant
- **AND** the lint MUST also fail if it sees `dict(os.environ)` or `os.environ.copy()` outside of `modules/rv-experiment/` (these forms leak the entire environment past Layer Purity boundaries)

#### Scenario: New environment variable requires registry update

- **WHEN** a developer adds a new environment variable `RV_NEW_FEATURE` to the system
- **AND** does not add the corresponding `ENV_NEW_FEATURE` constant to `rv-android-core/constants.py`
- **THEN** the CI lint MUST fail with a drift message

## MODIFIED Requirements

### Requirement: Pydantic Validation (FR35, NFR03, NFR05)

The rv-android-core module MUST provide BaseValidatedModel as the foundation for all validated domain models. BaseValidatedModel inherits from Pydantic v2 BaseModel and enforces consistent validation configuration across the framework.

Validation behavior MUST be controlled by the `RV_PYDANTIC` environment variable. When `RV_PYDANTIC=true`, full Pydantic validation is active (development mode). When `RV_PYDANTIC=false` or unset, validation still occurs at the Pydantic level (model_config settings apply) but logging and strict mode checks are suppressed for performance. After this change the env read for `RV_PYDANTIC` (plus the related toggles `RV_PYDANTIC_STRICT` and `RV_PYDANTIC_LOG`) goes through the `ENV_PYDANTIC*` constants from `rv-android-core/constants.py` — string literals are forbidden by INV-CORE-31. These three reads remain the only authorized L1 cross-layer infra reads in `rv-android-core` and are explicitly allow-listed by the lint.

The `@validated_model(positional_fields)` decorator MUST enable Pydantic models to accept both positional and named arguments, maintaining backwards compatibility with pre-Pydantic constructors. The decorator MUST map positional arguments to field names in the declared order.

All configuration classes (PlatformConfig, ExperimentConfig, RVAgentConfig, and others in downstream modules) MUST inherit from BaseValidatedModel. **In addition** (this is the substantive delta from the baseline), the top-level configuration classes that sit at the user-input boundary — `ExperimentConfig` (in `rv-experiment`) and `PlatformConfig` (in `rv-platform`) — MUST explicitly set `model_config = ConfigDict(extra="forbid")` at the class level (not relying solely on the inherited setting). The reason is the change pairs Pydantic strict validation with the new Docker entry-point allow-list (see experiment delta INV-EXP-31) and the `ENV_*` registry (INV-CORE-30): the system has a single, tight allow-list at every entry point — configuration files, environment variables, and command-line flags — and the explicit `model_config` declaration on the boundary classes makes that pairing visible to readers and to Pydantic introspection.

This explicit declaration is what INV-CORE-32 verifies. It does NOT change validation behavior of `BaseValidatedModel` itself (which has always set `extra="forbid"`); it surfaces the constraint at the boundary classes so that the contract is auditable without needing to chase the inheritance chain.

#### Scenario: Positional and named argument equivalence

- **WHEN** `CommandResult(0, b"output", b"error")` and `CommandResult(code=0, stdout=b"output", stderr=b"error")` are both constructed
- **THEN** both instances MUST have identical field values: `code=0`, `stdout=b"output"`, `stderr=b"error"`
- **AND** `instance1 == instance2` MUST return True

#### Scenario: Extra fields are rejected (BaseValidatedModel subclass)

- **WHEN** a BaseValidatedModel subclass is constructed with an unexpected field (e.g., `CommandResult(code=0, stdout=b"", stderr=b"", unexpected_field="value")`)
- **THEN** Pydantic MUST raise a ValidationError because `extra='forbid'` is set in model_config
- **AND** the error message MUST indicate the unexpected field

#### Scenario: Top-level config explicitly declares extra='forbid' (NEW)

- **WHEN** `inspect.getsource(ExperimentConfig)` (or `PlatformConfig`) is read
- **THEN** the source MUST contain `model_config = ConfigDict(extra="forbid")` at the class body level (not just inherited from `BaseValidatedModel`)
- **AND** the test `tests/test_top_level_configs_strict.py` MUST assert the declaration via Python AST or string match
- **AND** instantiating the model with an extra field (e.g., `ExperimentConfig(unknown_field="value", ...)`) MUST raise `ValidationError` naming `unknown_field`

#### Scenario: Top-level config accepts only declared fields

- **WHEN** `ExperimentConfig` is instantiated with all required and declared optional fields
- **THEN** validation MUST succeed
- **AND** the resulting object's attributes MUST match the input

#### Scenario: Positional-keyword conflict detection

- **WHEN** `CommandResult(0, b"output", code=1)` is constructed (field "code" specified both positionally and as keyword)
- **THEN** a `ValueError` MUST be raised with a message indicating the conflict for field "code"

#### Scenario: Validation config from environment (constants only)

- **WHEN** `RV_PYDANTIC` is set to `"true"` in the environment
- **THEN** `ValidationConfig.get_instance().enabled` MUST return True
- **AND** when `RV_PYDANTIC` is set to `"false"`, `enabled` MUST return False
- **AND** when `RV_PYDANTIC` is not set, `enabled` MUST return False (default)
- **AND** the source code reading these values MUST use `os.getenv(ENV_PYDANTIC, ...)` (and analogously `ENV_PYDANTIC_STRICT`, `ENV_PYDANTIC_LOG`); string literals are forbidden by INV-CORE-31

#### Scenario: String whitespace stripping

- **WHEN** a BaseValidatedModel subclass has a `name: str` field and is constructed with `name="  padded  "`
- **THEN** the stored value MUST be `"padded"` (whitespace stripped)
- **AND** this behavior is enforced by `str_strip_whitespace=True` in model_config
