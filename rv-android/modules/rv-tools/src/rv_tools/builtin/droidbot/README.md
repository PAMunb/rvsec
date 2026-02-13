# DroidBot Tool

Lightweight test input generator for Android applications with policy-based UI exploration. DroidBot models the app's UI state as a graph (UTG - UI Transition Graph) and uses configurable policies (DFS, BFS, greedy, naive, random) to guide exploration.

**Upstream:** https://github.com/honeynet/droidbot

## Execution

Runs as a Python process via Poetry:

```
poetry run droidbot -d emulator-5554 -a <apk_path> -policy <policy> -count <events> -timeout <seconds> -ignore_ad -is_emulator
```

DroidBot is installed in the Poetry virtual environment (the local `droidbot/` directory is a path dependency in `pyproject.toml`). The tool connects to the device via ADB and uses Android's accessibility service for UI element discovery.

## Variants

| Variant | Policy | Count | Interval | Notes |
|---------|--------|-------|----------|-------|
| `default` | dfs_naive | 1,000 | 3s | Basic exploration |
| `dfs_greedy` | dfs_greedy | 10^10 | 3s | Deep-first, prioritizes unseen |
| `bfs_greedy` | bfs_greedy | 10^10 | 3s | Breadth-first, prioritizes unseen |
| `dfs_naive` | dfs_naive | 1,000 | 3s | Deep-first, no prioritization |
| `bfs_naive` | bfs_naive | 1,000 | 3s | Breadth-first, no prioritization |
| `random` | random | 1,000 | 3s | Random action selection |

Greedy variants prioritize UI elements that have not been interacted with yet, resulting in broader coverage. Naive variants select actions without coverage awareness. The high event count (10^10) in greedy variants ensures the tool runs until the platform timeout kills it.

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `policy` | dfs_naive | Exploration policy |
| `count` | 1,000 | Maximum event count |
| `interval` | 3 | Seconds between events |
| `timeout` | 3,600 | Execution timeout in seconds |
| `device_serial` | emulator-5554 | Target device serial |
| `ignore_ad` | true | Block ad content |
| `keep_app` | false | Preserve app state between runs |
| `debug_mode` | false | Enable debug output |

## Docker Usage

```bash
# Standalone (Tier 1 - no external dependencies)
docker run --rm --device /dev/kvm \
  -e RV_TOOLS=droidbot:dfs_greedy \
  -e RV_TIMEOUTS=60 \
  ...
```

## Dependencies

- Python, Poetry
- DroidBot Python package (installed via Poetry path dependency from `droidbot/`)
- Android SDK (adb)
- Running Android emulator or device

## Process Pattern

`droidbot` — used by the platform to detect if the tool process is still running.

## ICST Study

DroidBot was used in the ICST experiment with 4 variants (dfs_greedy, bfs_greedy, dfs_naive, bfs_naive), providing the most diverse policy coverage among all tools. The `dfs_greedy` variant is the recommended default for experiments as it provides the best balance of depth and coverage.
