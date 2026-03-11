## Context

Phase 4 of the APE-RV project integrates the enhanced `ape-rv.jar` binary into the rv-android experiment framework. The `ape` builtin tool already exists in `rv-tools` and invokes APE via `adb shell monkey`. However, the enhanced APE binary (`ape-rv.jar`) uses the `app_process` execution model — the same approach used by rvsmart-tool — to gain direct access to Android internal APIs at runtime. This is incompatible with the existing builtin `ape` tool's ADB monkey invocation.

The `aperv-tool` module implements `ApeRVTool(AbstractTool)` following the exact pattern of `rvsmart-tool`. It locates `ape-rv.jar` (placed in the module directory by `mvn install` in the ape repo), pushes it to the device, optionally writes an `ape.properties` configuration file, and executes via `app_process`. The tool is registered in rv-platform's `_register_external_tools()` as an optional external tool.

**Relevant FRs**: FR18 (tool registration and factory), FR19 (external tool support), FR20 (per-tool variant system)
**NFRs**: NFR02 (modularity — graceful ImportError if aperv-tool not installed)

## Architecture

```
rv-platform/__init__.py
    _register_external_tools()
        └── ApeRVTool  ←  aperv_tool.tools.aperv.tool
                            ├── JarResolver (rv-android-core)
                            ├── Command / adb push (rv-android-core)
                            └── Command / adb shell app_process (rv-android-core)
```

### Key Components

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| `ApeRVTool.configure(config)` | Store variant config, validate strategy | `Dict[str, Any]` | None (side-effect) |
| `ApeRVTool.execute_tool_specific_logic(task, app)` | Orchestrate JAR push, properties push, execution | `Task`, `App` | None (writes trace file) |
| `ApeRVTool._resolve_jar_path()` | Locate `ape-rv.jar` on host | — | `str` (absolute path) |
| `ApeRVTool._push_file_to_device(...)` | ADB push a file to device | local path, device path, serial | None |
| `ApeRVTool._push_properties(...)` | Write and push `ape.properties` | device serial, trace path | None |
| `ApeRVTool._build_main_command(...)` | Construct `app_process` command | `App`, serial, timeout | `Command` |
| `ApeRVTool._check_empty_trace(...)` | Warn if trace file is empty | trace path | None (side-effect) |
| `JarResolver.resolve_jar_path(...)` | First-match search across paths | jar name, path list | `str` or raises |

## Mapping: Spec → Implementation → Test

| Requirement | Implementation | Test |
|-------------|---------------|------|
| FR18: Tool registration | `rv_platform/__init__.py: _register_external_tools()` | `test_aperv_registration` |
| FR19: External tool | `aperv_tool/tools/aperv/tool.py: ApeRVTool` | `test_aperv_tool_spec` |
| FR20: Variant system | `ApeRVTool.get_variants()` | `test_aperv_variants` |
| INV-TOOL-02: default variant | `get_variants()` returns `"default"` key | `test_default_variant_exists` |
| INV-APV-01: JAR resolution | `_resolve_jar_path()` + JarResolver | `test_jar_search_paths` |
| INV-APV-02: strategy validation | `configure()` validates against `APERV_AVAILABLE_STRATEGIES` | `test_configure_invalid_strategy` |
| INV-APV-03: device path collision | `APERV_DEVICE_JAR_PATH = "/data/local/tmp/ape-rv.jar"` | `test_device_jar_path_constant` |
| INV-APV-04: app_process working dir | `_build_main_command()` uses `/system/bin` | `test_build_command_working_dir` |
| Registration idempotency | `is_tool_registered("aperv")` check in rv-platform | `test_idempotent_registration` |

## Goals / Non-Goals

**Goals:**
- Wrap `ape-rv.jar` as an rv-platform tool with 5 variants
- Register `ApeRVTool` as an optional external tool in rv-platform
- Support all existing rv-experiment lifecycle hooks (timeout, trace file, coverage)
- Provide a `sata_mop` placeholder variant that is spec-documented as Phase 3 work

**Non-Goals:**
- MOP-guided scoring implementation (Phase 3 — `sata_mop` behaves identically to `sata`)
- Metrics extraction from APE stdout (APE does not emit structured metrics; coverage is handled by rv-android logcat infrastructure)
- Health check command (APE does not support `--health-check`)
- Any changes to the existing builtin `ape` tool

## Decisions

**D1: `app_process` over `adb shell am instrument`**
APE requires direct access to internal Android APIs (`android.app.UiAutomationConnection`, `DisplayManagerGlobal`) that are only available via `app_process`. The `am instrument` execution model does not grant these permissions. `rvsmart-tool` uses the same approach for the same reason.

**D2: `ape-rv.jar` filename (not `ape.jar`)**
The device may already have `ape.jar` pushed by the builtin `ape` tool if both tools run in the same session. Using `ape-rv.jar` as both the host filename and the device path `/data/local/tmp/ape-rv.jar` avoids collision.

**D3: No health check**
The original APE codebase does not support a `--health-check` flag. Adding one would require modifying the Java source (out of scope for Phase 4). The risk of a silent startup failure is low given that `app_process` returns a non-zero exit code on crash.

**D4: `sata_mop` as a placeholder**
The `sata_mop` variant is defined now so that Phase 5 experiment configurations can reference it without code changes. Until Phase 3 delivers MOP-guided scoring, `sata_mop` behaves identically to `sata`. The `mop_data: None` entry in the variant dict signals to future implementers where MOP data injection hooks.

**D5: Strategy validation in `configure()`**
`configure()` raises `ConfigurationError` for unknown strategy strings. This catches typos in experiment YAML before the device is touched, saving a multi-minute setup cycle.

**D6: `dfs` in `APERV_AVAILABLE_STRATEGIES` without a named variant**
The builtin `ape` tool exposes `dfs` as a named variant (`"dfs": {"strategy": "dfs", ...}`). `aperv` intentionally omits a `dfs` variant because the SATA and BFS strategies are the primary research comparison targets. `dfs` is nonetheless listed in `APERV_AVAILABLE_STRATEGIES` so it can be used via parameter override (`aperv:default@strategy=dfs`) without a code change. The strategy list is the authoritative gate; variant names are presets.

**D7: `app_process` working directory `/system/bin` instead of `/data/local/tmp/`**
The builtin `ape` tool uses `/data/local/tmp/` as the app_process working directory. `aperv` uses `/system/bin` because the enhanced APE binary references system-level resources relative to its working directory during startup. Using `/data/local/tmp/` as working dir causes startup failures for the enhanced binary. This difference is captured in INV-APV-04 and confirmed during Phase 1 build validation.

**D8: Shared `process_pattern` with builtin `ape` — known limitation**
Both `ape` (builtin) and `aperv` use `process_pattern="com.android.commands.monkey"`. `AbstractTool.kill_related_processes()` kills all ADB processes matching this string via `adb shell ps | grep`. Consequence: if `ape` and `aperv` run concurrently or overlap during cleanup, each tool's cleanup will kill the other's process. Mitigation: `ape` and `aperv` are never assigned to the same task in the same experiment run. Experiments use one or the other, not both simultaneously. A more specific process_pattern would require patching the Java main class — out of scope.

## API Design

### `ApeRVTool.configure(config: Dict[str, Any]) -> None`

Stores configuration in `self._tool_config`. Validates `config["strategy"]` against `APERV_AVAILABLE_STRATEGIES = ["sata", "random", "bfs", "dfs"]`.

- **Precondition**: `config` is a dict (may be empty)
- **Postcondition**: `self._tool_config` is set; strategy is valid or exception raised
- **Error**: `ConfigurationError` if `strategy` key is absent or not in allowed list

### `ApeRVTool._resolve_jar_path() -> str`

Searches `search_paths` in order using `JarResolver.resolve_jar_path("ape-rv.jar", paths)`:
1. `os.path.dirname(__file__)` — module directory (populated by `mvn install`)
2. `$RVSEC_HOME/ape/target/` — development Maven build
3. `$TOOLS_DIR/aperv/` — manual placement

- **Error**: `RVToolExecutionError` if JAR not found in any path, listing all paths searched

### `ApeRVTool._push_file_to_device(local_path, device_path, device_serial, trace_file_path) -> None`

Runs `adb -s <serial> push -a -p <local> <device>` with 60-second timeout. ADB push stdout is appended to `trace_file_path` in `"ab"` (append binary) mode — same pattern as `rvsmart-tool`. Note: the subsequent `execute_tool_specific_logic` opens the trace file in `"wb"` mode, which overwrites it; push output is therefore not preserved in the final trace file.

- **Error**: `RVToolExecutionError` with exit code and stderr if push fails

### `ApeRVTool._build_main_command(app, device_serial, timeout_seconds) -> Command`

Returns `Command("adb", [...])` with:
```
adb -s <serial> shell
  CLASSPATH=/data/local/tmp/ape-rv.jar
  /system/bin/app_process /system/bin
  com.android.commands.monkey.Monkey
  -p <package>
  --running-minutes <max(1, timeout // 60)>
  --ape <strategy>
```
Command timeout = `timeout_seconds + 15`.

## Data Flow

```
rv-experiment run --tools aperv:sata --apks-dir ./apks_examples
    → ToolExecutionComponent.execute(task, app)
        → ApeRVTool.execute_tool_specific_logic(task, app)
            1. _resolve_jar_path() → "/path/to/ape-rv.jar"
            2. _push_file_to_device(jar, "/data/local/tmp/ape-rv.jar", serial, trace)
            3. _push_properties(serial, trace)  # if self._tool_config
            4. _build_main_command(app, serial, timeout) → Command
            5. open(task.result.trace_file, "wb") → execute_and_check_command(cmd, trace_fh)
            6. _check_empty_trace(task.result.trace_file)
        ← raises RVToolTimeoutError on timeout (expected normal exit)
    → CoverageComponent reads logcat RVSEC-COV lines (unchanged)
    → ResultProcessorComponent writes results (unchanged)
```

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| `ConfigurationError` | `configure()` — bad strategy | Raise immediately | Fix variant config |
| `RVToolExecutionError` | JAR not found | Raise with search paths | Run `mvn install` in ape repo |
| `RVToolExecutionError` | ADB push failure | Raise with exit code + stderr | Check ADB connection |
| `RVToolTimeoutError` | Execution timeout | Log + reraise (expected) | Normal termination |

## Risks / Trade-offs

- **Risk: `ape-rv.jar` absent if `mvn install` not run** → Mitigated by `_resolve_jar_path()` raising a clear error listing all searched paths.
- **Risk: device path collision if both `ape` builtin and `aperv` run in same session** → Mitigated by using `ape-rv.jar` (not `ape.jar`) on device.
- **Risk: `sata_mop` semantics unclear to future implementers** → Mitigated by `mop_data: None` in variant dict and spec documentation.
- **Trade-off: no health check** → Accepted. APE startup failures produce non-zero exit codes, which are caught by `_execute_and_check_command`.
- **Risk: `process_pattern` collision with builtin `ape`** → `kill_related_processes()` uses `adb shell ps | grep com.android.commands.monkey` and will match both tools. Accepted because the two tools are never run simultaneously. See D8.
- **Risk: `_push_file_to_device` appends push output to trace file ("ab" mode)** → ADB push stdout is appended to `task.result.trace_file` before the main execution writes to it in "wb" mode, which overwrites. Net result: push output is NOT preserved in the final trace. Accepted — push output is low-value and the trace captures the exploration output that matters.

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Unit | `get_variants()` structure | Direct call | ~5 tests |
| Unit | `configure()` valid/invalid strategy | Mock nothing | ~4 tests |
| Unit | `_resolve_jar_path()` with env vars | Set env in test | ~3 tests |
| Unit | `_build_main_command()` output | Assert command args | ~3 tests |
| Unit | `_check_empty_trace()` warning | Mock logger | ~2 tests |
| Integration | Registration via rv-platform import | Import rv_platform | ~2 tests |

## Open Questions

- None: Phase 3 MOP integration is deferred by design; `sata_mop` is an explicit placeholder.
