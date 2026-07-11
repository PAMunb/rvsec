# aperv-tool - CLAUDE.md

## Overview

rv-platform plugin that wraps the APE-RV binary (`ape-rv.jar`) as an `AbstractTool`. Manages JAR deployment, `ape.properties` injection, and command execution on the Android emulator via `app_process`. (APE-RV internals live in the sibling `../ape` repo, which has its own CLAUDE.md.)

```bash
uv run rv-experiment run --tools aperv:sata_mop --specification-set jca   # MOP-guided run
```

(uv sync / editable install, pytest, and the general `rv-experiment run` form are documented in the top-level module CLAUDE.md.)

## Files

| File | Purpose |
|------|---------|
| `src/aperv_tool/tools/aperv/tool.py` | `ApeRVTool`: JAR resolution, device push, `ape.properties` generation, command building, execution |
| `src/aperv_tool/tools/aperv/ape-rv.jar` | APE-RV binary (gitignored); pushed to `/data/local/tmp/ape-rv.jar` |
| `src/aperv_tool/tools/aperv/system-broadcast.json` | System broadcast intent catalog for component triggering |
| `tests/test_aperv_tool.py` | Tool spec, variants, configure validation, JAR search paths, command building, empty-trace detection, properties generation |
| `docs/architecture.md` | Architecture notes |

Dependencies: internal `rv-android-core` (AbstractTool, ToolSpec, Command, JarResolver, domain models); external `rv-tools` (plugin registration).

## Variants

`get_variants()` returns 17 variants: 11 arm-defining named arms + 6 frozen gh43 prompt-ablation arms. All use `throttle_ms: 200`. The `dfs` strategy is accepted by `configure()` but has no named variant (reach it via override, e.g. `aperv:default@strategy=dfs`).

| Variant | Strategy | MOP | LLM | Notes |
|---------|----------|-----|-----|-------|
| `default` / `sata` | sata | no | no | Adaptive random baseline (`default` aliases `sata`) |
| `bfs` | bfs | no | no | Breadth-first |
| `random` | random | no | no | Pure random |
| `ape_pure` | sata | no | no | Original APE via `apePureMode` kill-switch (all RV flags off) |
| `sata_mop_widget` / `sata_mop` | sata | yes | no | MOP-guided (`sata_mop` aliases `sata_mop_widget`, same object) |
| `sata_mop_activity` | sata | yes | no | + activity source components |
| `sata_mop_act_frontier` | sata | yes | no | + frontier/activity-trigger boost |
| `sata_llm` | sata | no | yes | LLM guidance via SGLang |
| `sata_mop_llm` | sata | yes | yes | MOP + LLM combined |
| `sata_mop_llm_*` | sata | yes | yes | 6 frozen prompt arms (ape_current, ape_reasoning, compact_v1, v13, v17, visual_only) at `llm_percentage 0.7` |

## Configuration Flow

1. `configure(config)` validates strategy eagerly (catches typos before device interaction).
2. `execute_tool_specific_logic(task, app)`:
   - Resolves `ape-rv.jar` by priority: module dir > `$RVSEC_HOME/ape/target/` > `$TOOLS_DIR/aperv/`.
   - Pushes JAR to `/data/local/tmp/ape-rv.jar`; `system-broadcast.json` to `/data/local/tmp/` (optional).
   - MOP variants: pushes static-analysis JSON to `/data/local/tmp/static_analysis.json`.
   - Generates + pushes `ape.properties`, then runs `adb shell CLASSPATH=... app_process`.

`APERV_PROPERTY_MAPPING` translates Python config keys → Java `ape.properties` keys. Keys not in the mapping (e.g. `strategy`, `mop_data`) are Python-only and never written to properties.

## Key Design Decisions

- **Working dir `/system/bin`**: APE-RV needs system-level resource resolution; `/data/local/tmp/` causes `ClassNotFoundException` on some API levels.
- **Shared `process_pattern`** `com.android.commands.monkey`: shared with the builtin `ape` tool — the two must not run concurrently on the same device.
- **Timeout as expected exit**: exploration runs to the time limit; `RVCommandTimeoutError` → `RVToolTimeoutError` (completed run, not failure).
- **Non-zero exit is normal**: APE-RV exits non-zero when it detects app crashes during exploration.
- **LLM URL override**: `APERV_LLM_BASE_URL` overrides `llm_url` for Docker/non-emulator setups (emulator uses `10.0.2.2` host loopback).

## Gotchas

- `ape-rv.jar` is gitignored. The Docker image builds it at image-build time (`docker/rvandroid/Dockerfile` clones `https://github.com/phtcosta/ape.git`, `mvn package`, copies `target/ape-rv.jar` into the module dir = priority-1 path). Standalone runs must build/place it manually, or `_resolve_jar_path()` raises `RVToolExecutionError`.
- The `+15s` grace on the command timeout lets APE-RV flush its WTG model before the process is killed.
- Empty (0-byte) trace file = silent startup crash; logged as a warning, not an error (coverage may still come from logcat).
- Static-analysis JSON for MOP variants must exist at `<task.results_dir>/<apk_name>.json`; if missing the tool degrades gracefully (runs without MOP data).
