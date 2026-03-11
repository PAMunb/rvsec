<!-- Change touches ~10 files across 2 modules + 1 test file.
     No subagent orchestration needed (< 20 files, sequential groups). -->

## 1. Module Scaffold

- [ ] 1.1 Create `modules/aperv-tool/pyproject.toml` with `name="aperv-tool"`, `requires-python = ">=3.12"`, dependencies `["rv-android-core", "rv-tools"]`, hatchling build backend, `packages = ["src/aperv_tool"]`
- [ ] 1.2 Create `modules/aperv-tool/src/aperv_tool/__init__.py` (empty)
- [ ] 1.3 Create `modules/aperv-tool/src/aperv_tool/tools/__init__.py` (empty)
- [ ] 1.4 Create `modules/aperv-tool/src/aperv_tool/tools/aperv/__init__.py` (empty)
- [ ] 1.5 Create `modules/aperv-tool/src/aperv_tool/tools/aperv/.gitignore` containing `/ape-rv.jar`
- [ ] 1.6 Add `"aperv-tool"` to `dependencies` list in root `pyproject.toml` (after `"rvsmart-tool"`)
- [ ] 1.7 Add `aperv-tool = { workspace = true }` to `[tool.uv.sources]` in root `pyproject.toml` (after `rvsmart-tool`)
- [ ] 1.8 Run `uv sync` and verify `aperv-tool` appears in installed packages

## 2. ApeRVTool Implementation

- [ ] 2.1 Create `modules/aperv-tool/src/aperv_tool/tools/aperv/tool.py` with module-level constants: `APERV_TOOL_NAME`, `APERV_JAR_NAME`, `APERV_DEVICE_JAR_PATH`, `APERV_DEVICE_PROPERTIES_PATH`, `APERV_MAIN_CLASS`, `APERV_AVAILABLE_STRATEGIES`; import `ConfigurationError` at module level alongside other rv-android-core exception imports
- [ ] 2.2 Add `TOOL_SPEC = ToolSpec.create_builtin_spec(name="aperv", ..., process_pattern="com.android.commands.monkey")` — see design.md D8 for process_pattern note
- [ ] 2.3 Implement `ApeRVTool.__init__()`: call `super().__init__` via `get_tool_spec()`, init `LoggingManager` logger, init `JarResolver`, init `self._tool_config: Dict[str, Any] = {}`
- [ ] 2.4 Implement `ApeRVTool.get_variants()`: 5 variants (`default`, `sata`, `bfs`, `random` all with throttle_ms=200; `sata_mop` adds `mop_data=None`)
- [ ] 2.5 Implement `ApeRVTool.configure(config)`: store copy in `self._tool_config`; validate `config["strategy"]` against `APERV_AVAILABLE_STRATEGIES`; raise `ConfigurationError` if strategy absent or invalid (empty config `{}` also raises — per INV-APV-02)
- [ ] 2.6 Implement `ApeRVTool._resolve_jar_path()`: search_paths = [`os.path.dirname(__file__)`, `$RVSEC_HOME/ape/target/` if set, `$TOOLS_DIR/aperv/` if set]; catch exception from JarResolver and re-raise as `RVToolExecutionError` listing all searched paths
- [ ] 2.7 Implement `ApeRVTool._push_file_to_device(local_path, device_path, device_serial, trace_file_path)`: open trace in `"ab"` mode; run `adb -s <serial> push -a -p <local> <device>` timeout=60; raise `RVToolExecutionError` on failure
- [ ] 2.8 Implement `ApeRVTool._push_properties(device_serial, trace_file_path)`: write `ape.defaultGUIThrottle=<throttle_ms>` to `NamedTemporaryFile`; push to `APERV_DEVICE_PROPERTIES_PATH`; cleanup in `finally`
- [ ] 2.9 Implement `ApeRVTool._build_main_command(app, device_serial, timeout_seconds) -> Command`: `adb -s <serial> shell CLASSPATH=/data/local/tmp/ape-rv.jar /system/bin/app_process /system/bin com.android.commands.monkey.Monkey -p <pkg> --running-minutes <max(1, t//60)> --ape <strategy>`; command timeout = timeout_seconds + 15; working dir MUST be `/system/bin` (per INV-APV-04)
- [ ] 2.10 Implement `ApeRVTool._check_empty_trace(trace_file_path)`: log warning `"aperv produced empty trace file — possible silent hang or startup crash"` if file exists and size == 0; wrap in `try/except OSError: pass`
- [ ] 2.11 Implement `ApeRVTool.execute_tool_specific_logic(task, app)` with `@ErrorHandler.handle_errors(component="ApeRVTool", phase="execute_tool_specific_logic", reraise=True)`: extract `device_serial` from `task.config.device_id` (default `"emulator-5554"`) and `timeout_seconds` from `task.config.timeout` (default 300) via `getattr` guards; orchestrate: resolve JAR → push JAR → push properties (if `self._tool_config`) → build command → `open(trace, "wb")` + `_execute_and_check_command` → catch `RVToolTimeoutError` (log + reraise) → `_check_empty_trace`
- [ ] 2.12 Run `/rv-doc-code modules/aperv-tool/src/aperv_tool/tools/aperv/tool.py`

## 3. rv-platform Registration

- [ ] 3.1 In `modules/rv-platform/src/rv_platform/__init__.py`, add idempotent `ApeRVTool` registration block after the `RVSmartTool` block (same pattern: `is_tool_registered("aperv")` check, `ImportError` → warning, other exceptions → error)
- [ ] 3.2 Smoke-test: `uv run python3 -c "import rv_platform; from rv_tools import ToolRegistry; t = ToolRegistry.get_instance().list_tools(); assert 'aperv' in t; print('OK')"`
- [ ] 3.3 Run `/rv-verify rv-platform`

## 4. Unit Tests

- [ ] 4.1 Create `modules/aperv-tool/tests/__init__.py` and `modules/aperv-tool/tests/test_aperv_tool.py`
- [ ] 4.2 Add `TestToolSpec`: verify `name="aperv"`, `process_pattern="com.android.commands.monkey"`, `version="1.0.0"`
- [ ] 4.3 Add `TestVariants`: verify 5 keys exist; `default["strategy"] == "sata"`; `sata_mop["mop_data"] is None`; non-sata_mop variants lack `mop_data` key
- [ ] 4.4 Add `TestConfigure`: valid strategy stores config; invalid strategy raises `ConfigurationError`; absent strategy raises `ConfigurationError`; empty config `{}` raises `ConfigurationError` (per INV-APV-02); `dfs` is accepted (in APERV_AVAILABLE_STRATEGIES even without a named variant)
- [ ] 4.5 Add `TestJarSearchPaths`: no env → only `dirname(__file__)`; `RVSEC_HOME` set → includes path; empty string `RVSEC_HOME=""` → NOT appended
- [ ] 4.6 Add `TestBuildCommand`: verify `--ape sata`, `--running-minutes 1` for 60s, `CLASSPATH=/data/local/tmp/ape-rv.jar`, `/system/bin/app_process`, working dir `/system/bin`; command timeout = timeout_seconds + 15
- [ ] 4.7 Add `TestConstants`: `APERV_DEVICE_JAR_PATH == "/data/local/tmp/ape-rv.jar"`; `APERV_DEVICE_PROPERTIES_PATH == "/data/local/tmp/ape.properties"`
- [ ] 4.8 Add `TestCheckEmptyTrace`: empty file → warning with exact string `"aperv produced empty trace file"`; non-empty file → no warning; non-existent file → no exception
- [ ] 4.9 Run `/rv-test-run aperv-tool`

## 5. E2E Verification

- [ ] 5.1 Verify JAR: `unzip -p modules/aperv-tool/src/aperv_tool/tools/aperv/ape-rv.jar classes.dex | file -` → "Dalvik dex file version 035"
- [ ] 5.2 Verify variants: `uv run python3 -c "from aperv_tool.tools.aperv.tool import ApeRVTool; v = ApeRVTool.get_variants(); assert 'sata' in v and 'sata_mop' in v; print(list(v))"`
- [ ] 5.3 Run e2e with cryptoapp (rv-experiment manages emulator lifecycle — do NOT start emulator manually):
  ```
  source /etc/profile && uv run rv-experiment run \
    --tools aperv:sata \
    --apks-dir ./apks_examples \
    --timeout 60 \
    --no-window \
    --repetitions 1
  ```
  Expected: exits via timeout (normal), trace non-empty, no Python exception
- [ ] 5.4 Check results: `results/*/summary.csv` has aperv entry; `results/*/coverage.csv` has rows (coverage > 0%)

## 6. Final QA

- [ ] 6.1 Run `/rv-qa-lint-fix aperv-tool`
- [ ] 6.2 Run `/rv-verify aperv-tool`
- [ ] 6.3 Run `/rv-docs-sync rv-platform`
- [ ] 6.4 Invoke `/rv-code-reviewer` via Skill tool
