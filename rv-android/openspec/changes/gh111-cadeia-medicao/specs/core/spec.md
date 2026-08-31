## Purpose

The core capability owns the domain models the whole chain shares: `App`, which answers which package scopes an application's own classes; `LogcatRepository`, where the static denominator meets the runtime numerator; `TaskResult`, which carries a task's outcome to disk; and `LoggingManager`, which is supposed to persist what the run observed.

Three of the four carry a defect this change repairs, and they share a shape: **something is decided or counted, and then does not survive to anywhere a reader can see it.**

`App.code_package` returns the declared applicationId verbatim, which is correct as a rule and wrong for this corpus. The corpus is built with `assembleDebug`, and Gradle's `applicationIdSuffix` appends a segment to the applicationId without touching the namespace of the compiled classes, so the declared value is not a prefix of any class in 75 of the 162 artefacts. The answer is not a curated per-APK map — RV-Android is generic, and a suffixed applicationId is a property of how this corpus was built, not of the APK. The answer is a **run-scalar policy**, resolved at the entry point the user invoked and propagated by value, exactly as `package_detector` already is.

`LogcatRepository.register_method_call` performs two literal-equality lookups — the class name, then the complete method signature — and drops the event at `logger.debug` when either fails, with no counter. `_percentage` returns `0.0` for `0/0`. Between them, an application that measured nothing and an application whose denominator collapsed produce the same row.

`TaskResult.write_errors` is populated and never serialized. `LoggingManager.setup_file_logging` is guarded by `if self.log_path:` where `log_path` is assigned only inside `setup_file_logging` itself — a closed cycle — and its only caller, `configure_output`, has no production caller either. The effective scope key is logged at INFO through that path, which is to say it is never written.

`SignatureNormalizer` also lives here, and this change deletes it. Its only consumer is the analysis parser, and the analysis capability establishes why the transformation is always wrong on the output it is applied to.

## Data Contracts

### Input
- `app_path: str` — absolute path to the APK (unchanged)
- `package_detector: bool` — run-scalar policy, resolved at the entry point (unchanged, INV-CORE-55)
- `strip_build_type_suffix: bool` — new run-scalar policy: neutralize a build-type suffix on the declared applicationId before reporting `code_package`

### Output
- `code_package: str` — the package that scopes app-owned classes
- `code_package_source: str` — `"manifest"`, `"manifest-neutralized"` or `"detector"`
- `unmatched_out_of_scope: int` / `unmatched_in_scope: int` — crossing discard counts, serialized
- `TaskResult.write_errors: Dict[str, int]` — rows not written, keyed by the artefact that lost them (`errors.csv`, `results.json`); serialized by `to_dict()`, read back by `from_dict()`, and persisted after result processing

### Side-Effects
- **[Filesystem]**: `setup_file_logging` acquires a production caller, so the run's INFO log — including the effective scope key — reaches disk

### Error
- `ConfigurationError` — unchanged; APK path validation

## Invariants

- **INV-CORE-58**: `App.code_package` MUST apply build-type-suffix neutralization when, and only when, the run states the policy. The rule MUST be the fixed denylist `{debug, dev, beta, staging, qa, nightly, alpha, snapshot, current, head, indev}` with a floor of two remaining segments, compared **in lowercase** and applied **repeatedly** until the last segment is not a denied one. Lowercase comparison is what handles `.BETA`; repeated application is what handles `.qa.debug` and `.debug.HEAD`; the floor is what prevents a two-segment applicationId from being consumed. `App` MUST NOT read the policy from the environment (INV-CORE-55 unchanged) and MUST receive it as a constructor argument.

- **INV-CORE-59**: The denylist MUST NOT be treated as total: an applicationId whose suffix the denylist does not cover MUST pass through the neutralization unchanged and reach the denominator gate, which refuses the resulting implausible analysis (INV-ANA-69) — the wrong key MUST NOT be silently published. The space of suffixes is open by construction (`com.learntube.app` declares `applicationIdSuffix = ".debug.$branch"`, interpolating a git branch name); the neutralization resolves the common case, the gate carries the guarantee.

- **INV-CORE-60**: `LogcatRepository.register_method_call` MUST count every event it does not register, classifying it as **out-of-scope** when an effective scope key is known and the event's class does not start with it, as **in-scope** when the key is known and the class does start with it, and as **unclassified** when no key is known (`None`, the state of all 162 existing artefacts) — never silently as in-scope. No count MUST be emitted at `logger.debug` alone.

- **INV-CORE-61**: `TaskResult.to_dict()` MUST serialize `write_errors` as the `Dict[str, int]` it is, and `TaskResult.from_dict()` MUST read the key back with its per-artefact counts intact. The resume protocol reads `tasks.json`, so both directions MUST change together and a `tasks.json` without the key MUST still load, defaulting to `{}`. The round trip alone is inert and MUST NOT be taken for the repair: `_count_write_error` is called only from result processing (`result_processor.py:362`, `:397`, `:695`, `:1085`), and no `task_storage.update_task` or save runs after `Platform._process_results()` — `platform.py:181` executes the tasks and saves per task at `:426`/`:461`, `:192` processes the results, `:197` summarises, and nothing writes the store again. The serialization MUST therefore be accompanied by a persistence step performed after result processing, on the live path and on the standalone `--process-results` path (`rv_platform/__main__.py:497-514`) alike, so the counts reach disk instead of dying with the process.

- **INV-CORE-62**: `LoggingManager.setup_file_logging` MUST have a production caller at an entry point. The existing guard is self-referential — `log_path` is assigned only inside the method it guards — so the repair MUST create the call rather than re-enable an existing one.

- **INV-CORE-18**: `App.code_package` MUST return the declared applicationId verbatim when both the `PackageDetector` and the build-type-suffix neutralization policy are off, which is the default; MUST return the neutralized identifier when the neutralization policy is on, the detector is off, and a denied segment was removed; and MUST return the `PackageDetector` election when the detector is on — **the detector takes precedence**: when both policies are on, `code_package` is the detector's election and `code_package_source` is `"detector"`, because the detector answers from the compiled classes themselves and the neutralization is only a repair of the declared id. `code_package_source` MUST report which of the three produced the value — `"manifest"`, `"manifest-neutralized"` or `"detector"` — so that no reader has to re-derive the key from the artefacts it shaped.

## ADDED Requirements

### Requirement: Build-Type Suffix Neutralization as a Run Policy

`App` SHALL accept a run-scalar policy stating that this corpus was built with a build-type suffix, and SHALL neutralize that suffix when reporting `code_package`. The declared applicationId remains the rule; the policy states that this particular corpus departs from it in a mechanical, reversible way.

The policy MUST be a boolean resolved at the entry point the user invoked and passed to the constructor, propagated to every `App(` construction site by value. It MUST NOT be a per-APK map, a curated key channel, or a lookup table: which package scopes app-owned classes is a property of the corpus under study, and a scalar is the aridity that property has.

The rule SHALL be the denylist recorded in the article's `mneut_scope.py`, applied in lowercase and repeatedly, never reducing the applicationId below two segments.

#### Scenario: A single build-type suffix
- **WHEN** `App(path, strip_build_type_suffix=True)` wraps an APK declaring `br.com.colman.petals.debug`
- **THEN** `code_package` MUST be `br.com.colman.petals`
- **AND** `package_name` MUST remain `br.com.colman.petals.debug`, because that is the id the `PackageManager` knows
- **AND** `code_package_source` MUST be `"manifest-neutralized"`

#### Scenario: A stacked suffix
- **WHEN** an APK declares `com.example.app.qa.debug` and the policy is enabled
- **THEN** `code_package` MUST be `com.example.app`
- **AND** the rule MUST have been applied twice

#### Scenario: A capitalized suffix
- **WHEN** an APK declares `com.example.app.BETA` and the policy is enabled
- **THEN** `code_package` MUST be `com.example.app`

#### Scenario: The floor protects a short applicationId
- **WHEN** an APK declares `com.debug` and the policy is enabled
- **THEN** `code_package` MUST be `com.debug`
- **AND** no segment MUST be removed, because two segments is the floor

#### Scenario: The policy is off by default
- **WHEN** `App(path)` is constructed with no policy stated and the APK declares `br.com.colman.petals.debug`
- **THEN** `code_package` MUST be `br.com.colman.petals.debug`
- **AND** `code_package_source` MUST be `"manifest"`

#### Scenario: A suffix the denylist does not cover
- **WHEN** an APK declares `com.learntube.app.debug.feature-x`, produced by `applicationIdSuffix = ".debug.$branch"`, and the policy is enabled
- **THEN** `code_package` MUST be `com.learntube.app.debug.feature-x`
- **AND** the wrong key MUST NOT pass silently — the denominator gate MUST refuse the resulting analysis (INV-ANA-69)

### Requirement: The Coverage Crossing Counts Its Discards

`LogcatRepository` SHALL count every runtime event it declines to register and SHALL classify the discard by scope. An event whose class does not start with the effective scope key is out-of-scope, and the discard is expected — the weavers instrument by a library deny-list, not by the app key, so library events legitimately arrive. An event whose class is under the key but absent from the denominator, or present with a non-matching signature, is in-scope, and that discard is a defect in the chain.

The two counts MUST be kept separate. Summing them would restore exactly the ambiguity the counters exist to remove.

Both `LogcatRepository` and the `ParserDiagnostics` object that carries the parser's own discard counters live in **rv-android-core**, in `modules/rv-android-core/src/rv_android_core/domain/coverage.py` — not in rv-coverage, which increments the object the repository owns rather than constructing one of its own, because rv-android-core cannot import rv-coverage. The counters added here belong beside them, so the live tracker path and the offline `parse_logcat_file` path count onto the same totals.

#### Scenario: An unknown class
- **WHEN** `register_method_call` receives an event for `br.com.colman.petals.settings.SettingsWorker` and no such class is in the repository, with effective key `br.com.colman.petals`
- **THEN** the event MUST NOT be registered
- **AND** the in-scope discard count MUST be incremented

#### Scenario: A known class with an unknown signature
- **WHEN** the repository holds `br.com.colman.petals.MainActivity` but not the signature `<br.com.colman.petals.MainActivity: void onCreate(android.os.Bundle)>`
- **THEN** the event MUST NOT be registered
- **AND** the in-scope discard count MUST be incremented

#### Scenario: A library event
- **WHEN** the event names `kotlin.jvm.internal.Intrinsics` and the effective key is `br.com.colman.petals`
- **THEN** the out-of-scope discard count MUST be incremented
- **AND** the in-scope count MUST be unchanged

### Requirement: What the Run Counts Reaches Disk

`TaskResult` SHALL serialize `write_errors` in `to_dict()` and read it back in `from_dict()`, the task store SHALL be persisted after result processing, and `LoggingManager.setup_file_logging` SHALL have a production caller.

The second is not a matter of re-enabling existing wiring. `setup_file_logging` is called from `manager.py:147` under `if self.log_path:`, and `log_path` is assigned only inside `setup_file_logging` — the guard can never be true unless the method has already run. Its only caller, `configure_output`, has no production caller of its own. The repair MUST create a call at an entry point.

Because `tasks.json` is what the resume protocol reads, the serialization change MUST be verified in both directions, and `write_errors` MUST keep its shape: a `Dict[str, int]` mapping each output artefact to the number of rows it lost. Flattening it to a list of artefact names would discard the per-artefact count INV-PLT-32 exists to preserve.

Serialization is necessary and not sufficient. `write_errors` is populated only during result processing, and the task store is never saved again after it, so a run that counted a loss still ends with a `tasks.json` that shows none. The repair MUST therefore also persist the store after result processing, on the live path and on the standalone `--process-results` path.

#### Scenario: Write errors survive a round trip
- **WHEN** a `TaskResult` accumulates `write_errors == {"errors.csv": 2, "results.json": 1}` and is serialized to `tasks.json`
- **THEN** `to_dict()` MUST include the mapping with both counts
- **AND** `from_dict()` on that file MUST restore `{"errors.csv": 2, "results.json": 1}`
- **AND** the per-artefact counts MUST NOT be flattened into a list of artefact names

#### Scenario: A tasks.json without the write_errors key still loads
- **WHEN** the resume protocol reads a `tasks.json` with no `write_errors` key
- **THEN** `from_dict()` MUST load it
- **AND** `write_errors` MUST be an empty dict `{}`

#### Scenario: A write error counted during result processing is on disk when the run ends
- **WHEN** result processing fails to write two rows of `errors.csv` for a task, so `_count_write_error` leaves `write_errors == {"errors.csv": 2}` on the in-memory `TaskResult`
- **THEN** the task store MUST be persisted after result processing completes, not only inside the per-task execution loop
- **AND** `tasks.json` read after the run ends MUST carry `{"errors.csv": 2}` for that task

#### Scenario: The standalone result-processing path persists the same counts
- **WHEN** `rv-platform --process-results` reprocesses a finished run and counts one lost row of `results.json`
- **THEN** `tasks.json` MUST carry `{"results.json": 1}` for that task after the command returns
- **AND** the persistence MUST happen on that path as it does on the live path

#### Scenario: The effective key reaches the log file
- **WHEN** a run resolves the effective scope key and logs it at INFO
- **THEN** the file handler MUST be installed
- **AND** the line MUST be present in the run's log file on disk

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
  strip_build_type_suffix: bool  # Neutralize a build-type suffix on the declared applicationId (default False)
  # computed fields:
  path: str                      # os.path.abspath(app_path)
  name: str                      # os.path.basename(app_path)
  package_name: str              # From AndroidManifest.xml (for device ops)
  code_package: str              # package_name, or PackageDetector when enabled
  code_package_source: str       # "manifest" | "manifest-neutralized" | "detector"
  sdk_target: int                # Target SDK version
  permissions: List[str]         # Requested permissions
  min_api: int                   # Minimum API level

Command(BaseValidatedModel):
  command: str                   # Executable name (validated non-empty)
  args: List[str]                # Command arguments
  timeout: Optional[float]       # Seconds (None = no timeout)
```

`App.package_detector` carries a decision made by the user, not one derived from the APK. Which package scopes app-owned classes depends on the corpus under study, so `App` reports the package the APK declares and elects one heuristically only on request. The value is resolved at the entry point the user invoked and passed to the constructor; the domain model reads no environment variable (INV-CORE-55).

`App.strip_build_type_suffix` carries a decision of the same kind, for the other normalization. Normalization of the declared identifier — stripping a build-type suffix — is **not** a property this model invents per corpus, and it is not something the model performs on its own initiative: it is a run-scalar **policy the caller states**, resolved at the same entry point and passed to the same constructor, applied when and only when it is stated. The model still decides nothing. It reads no environment variable (INV-CORE-55), consults no per-APK map or curated key table, and leaves the declared identifier untouched when the policy is off, which is the default.

This supersedes the gh98 decision that normalization "is a property of a particular corpus and belongs to whoever curates it, not to this model". That decision named a responsible party without giving it a channel: the corpus curator had no way to state the repair, so the wrong key kept reaching every consumer of `code_package`. The channel is now the constructor argument, and the responsibility is unchanged — the caller still decides, the model still only obeys.

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

- **WHEN** an App is created from `org.fossify.calendar_20.apk`, whose manifest declares `org.fossify.calendar.debug`, without stating a package preference and without stating the neutralization policy
- **THEN** `app.code_package` MUST return `"org.fossify.calendar.debug"`
- **AND** `app.code_package_source` MUST return `"manifest"`
- **AND** no build-type segment MUST be stripped, because the policy is off by default and the model never decides the normalization on its own

#### Scenario: The build-type suffix is neutralized when the policy is on

- **WHEN** an App is created from the same `org.fossify.calendar_20.apk` with `strip_build_type_suffix=True`
- **THEN** `app.package_name` MUST return `"org.fossify.calendar.debug"`, because that is the id the `PackageManager` knows
- **AND** `app.code_package` MUST return `"org.fossify.calendar"`
- **AND** `app.code_package_source` MUST return `"manifest-neutralized"`

#### Scenario: Coverage repository ignores unknown methods

- **WHEN** a LogcatRepository has static analysis data for class "com.example.MyClass" with method signature `<com.example.MyClass: void doSomething()>`, the effective scope key is `com.example`, and `register_method_call()` is called with a RvCoverageLog for class "com.unknown.Other"
- **THEN** the call MUST NOT be registered, because the denominator holds no such method
- **AND** `calculate_metrics().called_methods` MUST remain 0
- **AND** the discard MUST be counted and classified as out-of-scope, because `com.unknown.Other` does not start with the effective scope key
- **AND** the discard MUST NOT be recorded at `logger.debug` alone

#### Scenario: RvErrorLog deduplication

- **WHEN** two RvErrorLog instances are created with the same `class_full_name`, `method`, `spec`, `error_type`, and `message`
- **THEN** both instances MUST have identical `unique_msg` computed properties
- **AND** `error1 == error2` MUST return True
- **AND** `hash(error1) == hash(error2)` MUST return True

### Requirement: Package Key Provenance on the App Model (FR33, NFR06)

`App` MUST expose which mechanism produced `code_package`, as the computed field `code_package_source`, taking the value `"manifest"` when the package was read from the APK manifest verbatim, `"manifest-neutralized"` when it was read from the manifest and had a build-type suffix removed under the run policy, and `"detector"` when it was elected by `PackageDetector`.

The field exists because the choice does not survive in the data it shapes. Two runs over one APK can produce different `code_package` values, and the artefacts downstream carry no trace of which run produced them — measured over the 162 artefacts of the article corpus, zero classes start with the `package` the GATOR JSON records and 162 of 162 start with the key that actually filtered it. Whoever records a run MUST be able to state the key and its origin without re-deriving either. The analysis capability now requires the effective key to be recorded in the artefact (INV-ANA-66); this field is its source.

`App` MUST NOT read an existing analysis artefact to infer a key, and MUST NOT override a caller's choice on the grounds that a stored artefact used a different one. Reconciling stored results with the key they were measured under is data management, outside this model's responsibility.

#### Scenario: Provenance follows the mechanism that ran

- **WHEN** `App(apk_path)` is constructed with no package preference and `code_package` is read
- **THEN** `app.code_package_source` MUST be `"manifest"`

- **WHEN** `App(apk_path, strip_build_type_suffix=True)` is constructed over an APK declaring `org.fossify.paint.debug` and `code_package` is read
- **THEN** `app.code_package_source` MUST be `"manifest-neutralized"`

- **WHEN** `App(apk_path, package_detector=True)` is constructed and `code_package` is read
- **THEN** `app.code_package_source` MUST be `"detector"`

#### Scenario: Provenance is consistent with the returned key

- **WHEN** any `App` instance has been asked for `code_package`
- **THEN** `code_package == package_name` MUST hold whenever `code_package_source == "manifest"`
- **AND** `code_package` MUST be a proper prefix of `package_name` whenever `code_package_source == "manifest-neutralized"`
- **AND** `code_package` MUST equal the `PackageDetector` election whenever `code_package_source == "detector"`

#### Scenario: Neutralization that removes nothing reports the plain origin

- **WHEN** `App(apk_path, strip_build_type_suffix=True)` wraps an APK declaring `org.cry.otp`, which carries no denied suffix
- **THEN** `code_package` MUST be `org.cry.otp`
- **AND** `code_package_source` MUST be `"manifest"`, because no neutralization occurred

#### Scenario: The detector takes precedence when both policies are on

- **WHEN** `App(apk_path, package_detector=True, strip_build_type_suffix=True)` wraps `com.github.cvzi.screenshottile_148`, whose manifest declares `com.github.cvzi.screenshottile` and whose detector election is `com.github.cvzi`
- **THEN** `code_package` MUST be `"com.github.cvzi"`, the detector's election
- **AND** `code_package_source` MUST be `"detector"` — never `"manifest-neutralized"`, even though a neutralization pass over the declared id would also have been possible (INV-CORE-18)

## REMOVED Requirements

(none — no named requirement of the main specification is removed. The deletion of
`modules/rv-android-core/src/rv_android_core/util/android/signature_normalizer.py` and
`modules/rv-android-core/tests/util/android/test_signature_normalizer.py` is a code-level removal
governed by the withdrawal of INV-ANA-02 in the analysis capability, not by a requirement of this
one. The class has exactly one consumer across all of `modules/*/src` — `StaticAnalysisParser` —
and with both call sites removed it is dead. Deletion is complete under P3: no shim, adapter,
deprecation wrapper or `_unused` rename remains, and no re-export is left in any `__init__.py`.)
