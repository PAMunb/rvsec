# CLAUDE.md - rv-android-core

## Purpose

Foundational infrastructure for RV-Android: shared domain models, error handling, logging, and utilities used by every other module. Establishes the core abstractions (Pydantic validation, singletons, decorators) the rest of the framework builds on.

## Key Components

| Component | Purpose |
|-----------|---------|
| `ErrorHandler` | Unified error management; type-specific handlers + `@handle_errors()` decorator (singleton) |
| `LoggingManager` | Centralized logging with context injection and structured formatting (singleton) |
| `BaseValidatedModel` | Pydantic base for all validated domain models |
| `Command` | System command execution with timeout and process management |
| `AbstractTool` | Template-method base defining the execution contract for all testing tools |

## Directory map

```
src/rv_android_core/
├── constants.py                 # File extensions + env var names (e.g. EXTENSION_STATIC_ANALYSIS = ".json")
├── analysis/base_analyzer.py    # Base class for analysis tools
├── commands/                    # command.py, command_result.py, command_exception.py, command_not_found_error.py
├── domain/
│   ├── app.py                   # Android app model (APK metadata; package_name vs code_package)
│   ├── classes.py  components.py  widget.py  window.py   # class/method + Android UI/component models
│   ├── coverage.py              # MethodCoverageData + coverage tracking models
│   ├── log.py                   # Coverage and error log models (RvCoverageLog / RvErrorLog / LogcatRepository)
│   ├── static.py  dynamic_wtg.py  wtg.py                 # static-analysis + Window Transition Graph models
│   └── task.py                  # Task, TaskConfiguration, TaskResult
├── tools/                       # abstract_tool.py, tool_spec.py
└── util/
    ├── decorators.py  diagnostics.py  jar_resolver.py  json_helpers.py  utils.py
    ├── android/                 # android.py (ADB), emulator_manager, logcat_manager,
    │                            #   package_detector, signature_normalizer, repository_initializer
    ├── error/                   # error_handler.py, exceptions.py (23 exception types)
    ├── logging/                 # manager.py (LoggingManager), context_adapter, formatters, constants
    └── validation/              # base.py (BaseValidatedModel), config.py, decorators.py (@validated_model)
```

Notable files: `util/android/package_detector.py` (code-package vs manifest-package detection; see below), `util/android/signature_normalizer.py` (normalizes inner-class notation `Outer.Inner` → `Outer$Inner` in Soot signatures), `constants.py` (holds file extensions and env var names, including the device timeout budgets `RV_EMULATOR_BOOT_TIMEOUT` / `RV_ADB_CMD_TIMEOUT` / `RV_APK_INSTALL_TIMEOUT`, resolved at the point of use in `util/android/android.py` with defaults 300 s / 30 s / 600 s; a value that is set but not an integer raises instead of falling back).

## `package_name` vs `code_package`

The `App` model exposes two package properties, answering two different questions:
- **`package_name`** — what the APK calls itself to the device: the applicationId from AndroidManifest.xml, verbatim. Use for device operations (install, launch, force-stop, monkey `-p`).
- **`code_package`** — which package scopes the classes a study treats as the app's own. Use for static-analysis parsing and class filtering.

The second question is about the corpus, not about the APK, so it is an input rather than an inference. By default `code_package` **is** `package_name`, returned verbatim — no suffix stripping, no prefix repair; such rules belong to whoever curates a corpus. Passing `package_detector=True` runs `PackageDetector` over the APK's components instead, which is what a corpus of Godot games wants (manifest `ir.hsn6.trans`, classes under `org.godotengine.godot`); the mismatch is logged at INFO on that path only. `code_package_source` reports which mechanism produced the value (`"manifest"` or `"detector"`), because the analysis artefacts downstream carry no trace of it.

The value arrives as a constructor argument. `domain/app.py` reads no environment variable (INV-CORE-55): `RV_PACKAGE_DETECTOR` and the `--package-detector` / `--no-package-detector` flag are resolved at the entry point the user invoked — `rv-experiment` or the `rv-static-analysis` command — and passed down already decided. The election is lazy and does not run at all on the default path, so an unconfigured run never pays for component enumeration.

## Dependencies

- **Internal**: None (this is the core foundation module).
- **External**: `pydantic` ^2.9.0, `androguard` 3.4.0a1 (APK metadata), `psutil` ^7.0.0 (process mgmt), `networkx` ^3.5 (WTG graphs).
