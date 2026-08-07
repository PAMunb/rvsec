# Delta Spec: core — gh98-manifest-package-default

## Purpose

The `App` domain model is where an APK becomes a set of named facts for the rest of the system: a path, a package identifier, a target SDK, a permission list. Two of those facts are package identifiers, and they answer different questions. `package_name` answers *"what does this APK call itself to the device?"* — it is the applicationId from the manifest, the string `adb install`, `am start` and `am force-stop` operate on. `code_package` answers *"which package scopes the classes this study considers to be the app's own?"* — it is the prefix that decides, downstream, whether a class belongs to the application or to a library it bundles.

The second question has no answer the tool can derive on its own, because it is not a question about the APK. It is a question about the study: a corpus of single-module apps, a corpus of Godot games, and a corpus built with `applicationIdSuffix` each want a different answer from the same bytes. rv-android runs all of them. This capability therefore makes the answer an input rather than an inference: `App` reports the package the APK declares unless the user asked for something else, and `PackageDetector` — whose heuristics are unchanged — runs only when the user turns it on.

The choice arrives as a constructor parameter. `App` sits in `rv-android-core`, and Layer Purity (INV-EXP-30, `docs/adr/0001-env-var-pattern.md` decision 2) reserves environment reading for the entry points and for three named L1 utility files, of which `domain/app.py` is not one. The environment variable that carries the user's choice therefore exists — `RV_PACKAGE_DETECTOR`, in the `ENV_*` registry this module owns — but is read at whichever command the user actually invoked and passed down already resolved. The domain model never inspects the process environment; it receives a decision someone else made explicitly.

Because the choice is invisible in the resulting data, `App` also reports where its answer came from. Two runs over the same APK can legitimately produce different `code_package` values, and nothing in the analysis artefacts distinguishes them after the fact. `code_package_source` makes the distinction available to whoever records the run.

## Data Contracts

### Input
- `app_path: str` — absolute path to the APK file (caller; unchanged)
- `package_detector: bool` — whether to elect the implementation package heuristically instead of reporting the declared one. Default `False`. Resolved at the invoked entry point from the CLI flag, `RV_PACKAGE_DETECTOR`, or the default, and passed in already decided.

### Output
- `package_name: str` — the applicationId declared in `AndroidManifest.xml`, verbatim (consumers: device operations — install, launch, force-stop)
- `code_package: str` — the package that scopes app-owned classes (consumers: `StaticAnalysisParser`, the GATOR `codePackage` client parameter, the AJC quarantine safety check)
- `code_package_source: str` — `"manifest"` or `"detector"`, naming which mechanism produced `code_package` (consumer: the run's provenance record)

### Side-Effects
- **[Logging]**: when `package_detector` is enabled and the elected package differs from the declared one, one INFO record carrying both values, the detection method and the confidence.

### Error
- `ConfigurationError` — the APK is missing, unreadable, or declares no package (unchanged; raised during load and validation).

## Invariants

- **INV-CORE-18**: `App.package_name` MUST return the manifest package name (from `APK.get_package()`), verbatim, with no normalization of any kind. `App.code_package` MUST return that same value when `package_detector` is disabled, and the package elected by `PackageDetector` when it is enabled. `App.code_package_source` MUST report which of the two produced the returned value. The default MUST be the manifest package: constructing `App` without stating a preference MUST NOT run `PackageDetector`.

- **INV-CORE-55**: `modules/rv-android-core/src/rv_android_core/domain/app.py` MUST NOT read the process environment. The `package_detector` value MUST reach `App` as a constructor argument. The three L1 canonical reader locations (`util/validation/config.py`, `util/jar_resolver.py`, `util/android/android.py`) MUST remain the complete set of environment readers inside `rv-android-core`, and `scripts/check_env_vars_drift.py` MUST keep enforcing it.

## MODIFIED Requirements

### Requirement: Domain Models (FR33)

The core domain layer MUST provide validated data models used across all modules. These models use `BaseValidatedModel` (with `@validated_model` decorator) for field validation when `RV_PYDANTIC=true`.

The central data models are:

```
TaskConfiguration(BaseValidatedModel):
  apk_name: str                  # APK filename
  repetition: int                # Repetition number (1-based)
  timeout: int                   # Seconds for tool execution
  tool_config: ToolConfig        # Tool name + variant + params
  no_window: bool                # Headless mode flag
  device_id: str                 # Default "emulator-5554"

ToolConfig(BaseValidatedModel):
  name: str                      # e.g. "droidbot", "rvagent"
  variant: str                   # e.g. "dfs_greedy", "default"
  parameters: Dict               # Parameter overrides

App(BaseValidatedModel):
  app_path: str                  # Absolute path to APK file
  package_detector: bool         # Elect the package heuristically (default False)
  # computed fields:
  path: str                      # os.path.abspath(app_path)
  name: str                      # os.path.basename(app_path)
  package_name: str              # From AndroidManifest.xml (for device ops)
  code_package: str              # package_name, or PackageDetector when enabled
  code_package_source: str       # "manifest" | "detector"
  sdk_target: int                # Target SDK version
  permissions: List[str]         # Requested permissions
  min_api: int                   # Minimum API level

Command(BaseValidatedModel):
  command: str                   # Executable name (validated non-empty)
  args: List[str]                # Command arguments
  timeout: Optional[float]       # Seconds (None = no timeout)
```

`App.package_detector` carries a decision made by the user, not one derived from the APK. Which package scopes app-owned classes depends on the corpus under study, so `App` reports the package the APK declares and elects one heuristically only on request. The value is resolved at the entry point the user invoked and passed to the constructor; the domain model reads no environment variable (INV-CORE-55). Any normalization of the declared identifier — stripping build-type suffixes, repairing prefixes — is a property of a particular corpus and belongs to whoever curates it, not to this model.

ToolConfig is the single source of truth for tool configuration across all modules. It represents exactly one (tool, variant, parameters) combination. For experiments with multiple variants of the same tool, multiple ToolConfig instances are created — one per variant. All modules import ToolConfig from rv-android-core; no other module defines its own ToolConfig class.

ToolConfig provides `from_dict()` for deserialization from JSON. It accepts only the current field names (`name`, `variant`, `parameters`). Per P3 (No Backward Compatibility), old `tasks.json` files using previous field names (`tool_name`, `additional_params`) are not supported — experiments must be re-run.

#### Scenario: ToolConfig creation with unified field names

- **WHEN** `ToolConfig(name="droidbot", variant="dfs_greedy", parameters={"count": 5000})` is created
- **THEN** the instance MUST have `name == "droidbot"`, `variant == "dfs_greedy"`, `parameters == {"count": 5000}`

#### Scenario: ToolConfig default variant

- **WHEN** `ToolConfig(name="monkey")` is created without specifying a variant
- **THEN** the instance MUST have `variant == "default"` and `parameters == {}`

#### Scenario: ToolConfig from_dict with current field names

- **WHEN** `ToolConfig.from_dict({"name": "droidbot", "variant": "dfs_greedy", "parameters": {"count": 5000}})` is called
- **THEN** the result MUST have `name == "droidbot"`, `variant == "dfs_greedy"`, `parameters == {"count": 5000}`

#### Scenario: ToolConfig get_full_tool_name

- **WHEN** `tool_config.get_full_tool_name()` is called on a ToolConfig with `name="droidbot"`, `variant="dfs_greedy"`
- **THEN** the result MUST be `"droidbot:dfs_greedy"`

- **WHEN** `tool_config.get_full_tool_name()` is called on a ToolConfig with `name="monkey"`, `variant="default"`
- **THEN** the result MUST be `"monkey"`

#### Scenario: ToolConfig serialization via to_dict

- **WHEN** `tool_config.to_dict()` is called on a ToolConfig with `name="rvagent"`, `variant="multimode"`, `parameters={"mop_direct_score": 500}`
- **THEN** the result MUST be `{"name": "rvagent", "variant": "multimode", "parameters": {"mop_direct_score": 500}}`
- **AND** the keys MUST use the unified field names (not legacy names)

#### Scenario: Task UUID generation

- **WHEN** `Task(config=valid_config)` is constructed without a `task_id` parameter
- **THEN** `task.id` MUST be a valid UUID string (36 characters, 8-4-4-4-12 format)
- **AND** two tasks created without explicit IDs MUST have different IDs

#### Scenario: Task state lifecycle

- **WHEN** a Task is created and then `task.update_state(TaskState.RUNNING)` is called
- **THEN** `task.result.state` MUST be `TaskState.RUNNING`
- **AND** `task.result.start_time` MUST be set to approximately the current time
- **AND** `task.result.state_transitions` MUST contain entries for both CREATED and RUNNING

#### Scenario: App reports the declared package by default

- **WHEN** an App is created from the Godot game whose manifest declares `ir.hsn6.trans` and whose implementation classes live under `org.godotengine.godot`, without stating a package preference
- **THEN** `app.package_name` MUST return `"ir.hsn6.trans"`
- **AND** `app.code_package` MUST return `"ir.hsn6.trans"`
- **AND** `app.code_package_source` MUST return `"manifest"`
- **AND** `PackageDetector` MUST NOT be invoked

#### Scenario: App elects the implementation package when the detector is enabled

- **WHEN** an App is created from the same APK with `package_detector=True`
- **THEN** `app.package_name` MUST return `"ir.hsn6.trans"`
- **AND** `app.code_package` MUST return `"org.godotengine.godot"`
- **AND** `app.code_package_source` MUST return `"detector"`
- **AND** a log message MUST be emitted at INFO level indicating the mismatch

#### Scenario: The declared package is reported verbatim, suffix included

- **WHEN** an App is created from `org.fossify.calendar_20.apk`, whose manifest declares `org.fossify.calendar.debug`, without stating a package preference
- **THEN** `app.code_package` MUST return `"org.fossify.calendar.debug"`
- **AND** no build-type segment MUST be stripped, because normalization is a property of the corpus and not of this model

#### Scenario: Coverage repository ignores unknown methods

- **WHEN** a LogcatRepository has static analysis data for class "com.example.MyClass" with method signature `<com.example.MyClass: void doSomething()>`, and `register_method_call()` is called with a RvCoverageLog for class "com.unknown.Other"
- **THEN** the call MUST be silently ignored (debug log only)
- **AND** `calculate_metrics().called_methods` MUST remain 0

#### Scenario: RvErrorLog deduplication

- **WHEN** two RvErrorLog instances are created with the same `class_full_name`, `method`, `spec`, `error_type`, and `message`
- **THEN** both instances MUST have identical `unique_msg` computed properties
- **AND** `error1 == error2` MUST return True
- **AND** `hash(error1) == hash(error2)` MUST return True

## ADDED Requirements

### Requirement: Package Key Provenance on the App Model (FR33, NFR06)

`App` MUST expose which mechanism produced `code_package`, as the computed field `code_package_source`, taking the value `"manifest"` when the package was read from the APK manifest and `"detector"` when it was elected by `PackageDetector`.

The field exists because the choice does not survive in the data it shapes. Two runs over one APK can produce different `code_package` values, and the artefacts downstream — including the GATOR analysis JSON, which records the manifest package rather than the key that filtered it — carry no trace of which run produced them. Whoever records a run MUST be able to state the key and its origin without re-deriving either.

`App` MUST NOT read an existing analysis artefact to infer a key, and MUST NOT override a caller's choice on the grounds that a stored artefact used a different one. Reconciling stored results with the key they were measured under is data management, outside this model's responsibility.

#### Scenario: Provenance follows the mechanism that ran

- **WHEN** `App(apk_path)` is constructed with no package preference and `code_package` is read
- **THEN** `app.code_package_source` MUST be `"manifest"`

- **WHEN** `App(apk_path, package_detector=True)` is constructed and `code_package` is read
- **THEN** `app.code_package_source` MUST be `"detector"`

#### Scenario: Provenance is consistent with the returned key

- **WHEN** any `App` instance has been asked for `code_package`
- **THEN** `code_package == package_name` MUST hold whenever `code_package_source == "manifest"`
- **AND** `code_package` MUST equal the `PackageDetector` election whenever `code_package_source == "detector"`
