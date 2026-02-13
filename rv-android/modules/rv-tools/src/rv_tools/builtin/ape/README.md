# APE Tool

CEGAR-based model abstraction testing tool for systematic Android exploration. APE (Android Programmatic Events) uses counterexample-guided abstraction refinement to build and refine a model of the app's UI state space during exploration.

**Upstream:** https://github.com/tjusenchen/ape

## Execution

Runs via ADB shell using `app_process` with a JAR pushed to the device:

1. Push `ape.jar` to `/data/local/tmp/ape.jar` on the device
2. Execute via: `adb shell CLASSPATH=/data/local/tmp/ape.jar app_process / ape.Main -p <package> --ape <strategy> --running-minutes <minutes>`

The JAR is resolved by `JarResolver`, which searches the module directory first, then `TOOLS_DIR` and standard paths.

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

APE creates an `ape_output/` directory alongside the trace file containing:
- State graphs and transition data
- Screenshots of explored states
- Model abstraction refinement logs

## ICST Study

APE was one of the 8 official tools in the ICST experiment, using the SATA strategy for systematic model-based exploration.
