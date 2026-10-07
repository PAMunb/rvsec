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
│   ├── coverage.py              # MethodCoverageData, ClassCoverageData, CoverageMetrics,
│   │                            #   ParserDiagnostics, LogcatRepository
│   ├── log.py                   # Parsed logcat records (RvCoverageLog / RvErrorLog / RvDiagnosticEvent)
│   ├── static.py  dynamic_wtg.py  wtg.py                 # static-analysis + Window Transition Graph models
│   └── task.py                  # Task, TaskConfiguration, TaskResult
├── tools/                       # abstract_tool.py, tool_spec.py
└── util/
    ├── decorators.py  diagnostics.py  jar_resolver.py  json_helpers.py  utils.py
    ├── android/                 # android.py (ADB), emulator_manager, logcat_manager,
    │                            #   package_detector, repository_initializer
    ├── error/                   # error_handler.py, exceptions.py (23 exception types)
    ├── logging/                 # manager.py (LoggingManager), context_adapter, formatters, constants
    └── validation/              # base.py (BaseValidatedModel), config.py, decorators.py (@validated_model)
```

Notable files: `util/android/package_detector.py` (code-package vs manifest-package detection; see below), `util/android/build_type_suffix.py` (neutralizes the Gradle build-type suffix of a declared applicationId — a run policy, off by default, INV-CORE-58), `constants.py` (holds file extensions and env var names, including the device timeout budgets `RV_EMULATOR_BOOT_TIMEOUT` / `RV_ADB_CMD_TIMEOUT` / `RV_APK_INSTALL_TIMEOUT`, resolved at the point of use in `util/android/android.py` with defaults 300 s / 30 s / 600 s; a value that is set but not an integer raises instead of falling back).

## Capture tags and emulator launch

`util/android/logcat_manager.py` (`LogcatManager`) captures a live stream filtered on the device: `adb logcat -s <tags>` drops every line whose tag is not in the list before it leaves the emulator, so a stream exists in the captured file only if its tag is admitted when capture starts. The baseline is five tags, `RVSEC:V RVSEC-COV:V ApeRvHb:V RVSEC-OCC:V RVSEC-BIND:V` (`adb -s <serial> logcat -v threadtime -s RVSEC:V RVSEC-COV:V ApeRvHb:V RVSEC-OCC:V RVSEC-BIND:V`, INV-CORE-37). `default_tags` is built from the five constants `TAG_RVSEC`, `TAG_RVSEC_COV`, `TAG_APERV_HEARTBEAT`, `TAG_RVSEC_OCC` and `TAG_RVSEC_BIND` in `util/logging/constants.py`, in that order, and each tag string appears only there (INV-CORE-53). A misspelt tag fails silently, as an empty stream, which is why the string lives in one place. `RVSEC` is the monitor runtime's first-occurrence violation line, `RVSEC-COV` the coverage line, `ApeRvHb` the APE-RV step heartbeat, `RVSEC-OCC` the monitor runtime's occurrence line (every occurrence of a violation identity, at most one line per identity per 100 ms), and `RVSEC-BIND` the handler-stamp verification line the `dexlib2` instrumenter's `mop.RvsecStamp` helper writes each time a View or Compose node's stamp changes (`RvsecStamp.TAG`). `RV_LOGCAT_DIAGNOSTICS` appends `AndroidRuntime:E art:E dalvikvm:E ActivityManager:W` after the five, without reordering them (INV-CORE-38). Before capture, `start_capture` sizes the device ring buffers to `LOGCAT_BUFFER_SIZE` (16 MiB) with a separate `logcat -G` command (INV-CORE-64). `rv-coverage`'s parser dispatches on the exact tag, so `ApeRvHb`, `RVSEC-OCC` and `RVSEC-BIND` lines are counted as `lines_other_tag` and change no parsed value (INV-CORE-65, INV-CORE-67).

`util/android/android.py` (`Android.start_emulator`) launches `emulator -avd <name> -port <port> -read-only -no-cache -no-boot-anim -noaudio -no-snapshot-save -delay-adb -memory 4096 -partition-size 8192 [-no-window]`. The memory and the `/data` partition come from `EMULATOR_MEMORY_MB = 4096` and `EMULATOR_PARTITION_SIZE_MB = 8192` in `constants.py`, passed as `-memory` and `-partition-size` on every launch (INV-CORE-66). The flags take precedence over the AVD's `config.ini` for that launch; the campaign image's AVD carries the `pixel` profile defaults `hw.ramSize=1536M` and `disk.dataPartition.size=800M`, under which the guest's low-memory killer can terminate the app under test and a large APK can fail to install. The values are constants rather than environment variables so every container of one campaign runs under the same condition. `-cores` is not passed: the core count is left to the AVD (`hw.cpu.ncore=4`).

## `package_name` vs `code_package`

The `App` model exposes two package properties, answering two different questions:
- **`package_name`** — what the APK calls itself to the device: the applicationId from AndroidManifest.xml, verbatim. Use for device operations (install, launch, force-stop, monkey `-p`).
- **`code_package`** — which package scopes the classes a study treats as the app's own. Use when *running* a static analysis: it becomes GATOR's `-clientParam codePackage=`, and the run records it in the artefact. Parsing an artefact resolves no key of its own — GATOR already applied the scope before writing (INV-ANA-59/61); reading the key the artefact recorded is a different act, and it classifies rather than filters (see below).

The second question is about the corpus, not about the APK, so it is an input rather than an inference. By default `code_package` **is** `package_name`, returned verbatim. Two opt-in policies can change that, both off by default, both stated by the caller through a channel of their own:

- **`package_detector=True`** runs `PackageDetector` over the APK's components, which is what a corpus of Godot games wants (manifest `ir.hsn6.trans`, classes under `org.godotengine.godot`); the mismatch is logged at INFO on that path only.
- **`strip_build_type_suffix=True`** neutralizes the Gradle build-type suffix (`util/android/build_type_suffix.py`, INV-CORE-58), so the debug variant of `com.example.app` is scoped by the package its classes were compiled under rather than by `com.example.app.debug`, under which nothing was compiled at all. The rule is a fixed denylist compared in lowercase (`.BETA` is caught), applied repeatedly (`.qa.debug` is one Gradle variant, not two), with a floor of two segments (stripping to `com` would match every library in the Scene).

**The detector takes precedence** when both are on (INV-CORE-18), because it answers from the compiled classes themselves while the neutralization only repairs the declared id. Prefix repair is neither policy and stays out: no string rule resolves it (`de.grobox.liberario` ships as `de.grobox.transportr`), and the denylist is deliberately not total either (INV-CORE-59) — an uncovered suffix passes through unchanged, and the backstop is the downstream denominator gate, which refuses an implausible universe loudly rather than a longer list that fails silently.

`code_package_source` reports which mechanism produced the value — `"manifest"`, `"manifest-neutralized"` or `"detector"` — because the analysis artefacts downstream carry no trace of it unless it is carried there deliberately. It names what *produced* the key, not what was requested: neutralization that removed nothing still reports `"manifest"`.

Both values arrive as constructor arguments. `domain/app.py` reads no environment variable (INV-CORE-55): `RV_PACKAGE_DETECTOR` / `--package-detector` and `RV_STRIP_BUILD_TYPE_SUFFIX` / `--strip-build-type-suffix` are resolved at the entry point the user invoked — `rv-experiment` or the `rv-static-analysis` command — and passed down already decided (precedence: CLI flag > env var > default `False`). `util/utils.py:get_apks()` forwards both to every `App` it builds and reads no environment of its own. The election is lazy and does not run at all on the default path, so an unconfigured run never pays for component enumeration.

## The scope key at the crossing

`LogcatRepository(scope_key=...)` takes the effective scope key the static analysis artefact recorded, and uses it for exactly one thing: classifying the events `register_method_call()` does **not** register. It filters nothing. `_count_unmatched()` splits those discards three ways in `ParserDiagnostics` (INV-CORE-60, INV-ANA-68):

| Counter | Meaning |
|---|---|
| `unmatched_out_of_scope` | The executed class sits outside the key — the app called a library. Expected. |
| `unmatched_in_scope` | The class sits *inside* the key and the artefact still lacks it. This is the one that indicts the denominator. |
| `unmatched_unclassified` | No key was available, so neither claim can be made. |

The key is read from the artefact's own record and never re-derived from a package name (INV-ANA-58). `None` is legitimate — every artefact written before the key reached disk, and the resume path, which loads no artefact at all — and is counted unclassified rather than silently attributed to either side. A missing key costs a row its two `unmatched_*` cells and nothing else; coverage still comes from the artefact's own denominator. The three counters stay **out** of `ParserDiagnostics.discarded_lines`, for the same reason the sentinel and grammar counters do: these lines *did* become records, so the INV-ANA-62 identity (records registered plus counted lines equals lines read) holds unchanged.

`StaticAnalysisData` is where the key comes from. Three optional members carry the producer's record (INV-ANA-66): `code_package` (the key GATOR actually filtered by — the `package` member is the MANIFEST package whatever key was used, so it cannot stand in), `code_package_source`, and `class_defs_under_key` (the **net** count of compiled classes under the key that survive the client's own `isAppClass` filter — what the denominator gate divides by). All three are `None` on artefacts written before the key reached disk; the producer writes `-1` for the count and the parser maps it to `None`, so "not recorded" stays distinguishable from a genuine zero universe.

## `TaskResult` serialization

`to_dict()` / `from_dict()` round-trip `write_errors` as the `Dict[str, int]` it is — a per-artefact count of rows lost while writing, not a list of messages (INV-CORE-61). The count is the whole point: without it, a task whose violations were lost during writing reads exactly like a task that had none. `from_dict()` defaults the key to `{}`, so a `tasks.json` written before the field was serialized still loads on the resume path — no loss was recorded there because nothing was recording.

## Dependencies

- **Internal**: None (this is the core foundation module).
- **External**: `pydantic` ^2.9.0, `androguard` 3.4.0a1 (APK metadata), `psutil` ^7.0.0 (process mgmt), `networkx` ^3.5 (WTG graphs).
