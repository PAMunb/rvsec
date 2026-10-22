# APE Tool

CEGAR-based model abstraction testing tool for systematic Android exploration. APE (Android Programmatic Events) uses counterexample-guided abstraction refinement to build and refine a model of the app's UI state space during exploration.

**Upstream:** https://github.com/tjusenchen/ape

## Execution

Runs via ADB shell using `app_process` with a JAR pushed to the device:

1. Push `ape.jar` to `/data/local/tmp/ape.jar` on the device
2. Push `ape.properties` to `/data/local/tmp/ape.properties` (see below)
3. Execute via: `adb shell CLASSPATH=/data/local/tmp/ape.jar app_process / ape.Main -p <package> --ape <strategy> --running-minutes <minutes>`

The JAR is resolved by `JarResolver`, which searches the module directory first, then `TOOLS_DIR` and standard paths.

## Timing, Completion and Capture

The `ape` tool gives APE the same host time and the same completion rule as the `aperv` tool, so the two arms of an APE × APE-RV comparison differ only in the jar.

- **Teardown grace.** The `adb shell` command runs under a timeout of the budget plus `TOOL_TEARDOWN_GRACE_S` (45 s, `rv_android_core.constants`, INV-TOOL-27). APE ends on its own `--running-minutes` timer and finishes its teardown inside that window. If the host timeout fires, the resulting `RVToolTimeoutError` is a normal end of the run.
- **Completion by elapsed time.** The exit code is not consulted: APE exits non-zero when the app under test crashes, which is data the run collects, and a device that went away also exits non-zero. A return earlier than the budget minus `TOOL_TEARDOWN_GRACE_S` (255 s for a 300 s budget) raises `RVToolExecutionError`, naming the elapsed time and the budget, so rv-platform stores the task as `ERROR` and its resume re-executes it (INV-TOOL-28).
- **`ape.properties`.** Before each run the tool pushes `/data/local/tmp/ape.properties` with exactly `ape.takeScreenshotForEveryStep=false`, `ape.saveGUITreeToXmlEveryStep=false` and `ape.takeScreenshotForNewState=true` (INV-TOOL-29). Upstream APE then writes a screenshot and a GUI-tree XML only when a new abstract state appears, rather than on every step, which is the capture policy of the APE-RV jar. This is the only setting that departs from the author's defaults. A failed push raises `RVToolExecutionError` and APE does not start. The file is not removed: each task boots its own emulator with `-read-only` and `-no-snapshot-save`.

## Variants

| Variant | Strategy | Duration | Debug |
|---------|----------|----------|-------|
| `default` | SATA | 5 min | yes |
| `sata` | SATA | 10 min | no |
| `bfs` | Breadth-first | 5 min | no |
| `dfs` | Depth-first | 5 min | no |
| `random` | Random | 5 min | no |

The SATA strategy (State-Action Transition Abstraction) is the primary APE algorithm that iteratively refines the UI model. BFS/DFS/random are simpler exploration strategies.

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `strategy` | sata | Exploration strategy (sata, bfs, dfs, random) |
| `running_minutes` | 5 | Execution duration in minutes |
| `device_serial` | emulator-5554 | Target device serial |
| `debug_mode` | true | Enable debug output |
| `output_dir` | auto | Output directory for results |

## Docker Usage

```bash
# Standalone (Tier 1 - no external dependencies)
docker run --rm --device /dev/kvm \
  -e RV_TOOLS=ape \
  -e RV_TIMEOUTS=60 \
  ...
```

## Dependencies

- Android SDK (adb)
- `ape.jar` (bundled in module directory, resolved by JarResolver)
- Running Android emulator or device

## Process Pattern

`com.android.commands.monkey` — APE uses the monkey process infrastructure internally.

## Output

The tool creates an empty `ape_output/` directory alongside the trace file. APE writes its
state graphs, model refinement logs and the screenshots and GUI-tree XML of each new abstract state
on the device (`/sdcard`), and rv-android does not pull them; the trace file holds APE's stdout and
stderr.

## ICST Study

APE was one of the 8 official tools in the ICST experiment, using the SATA strategy for systematic model-based exploration.
