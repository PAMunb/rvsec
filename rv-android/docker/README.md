# Docker Infrastructure

## Image Architecture

The Docker image chain builds incrementally:

| Layer | Image | Base | Purpose |
|-------|-------|------|---------|
| 1 | `phtcosta/rvandroid_base` | Ubuntu 22.04 | Java 8, Python 3.10, Poetry |
| 2 | `phtcosta/rvandroid_android` | rvandroid_base | Android SDK, emulator (API 25 x86), KVM support |
| 3 | `phtcosta/rvandroid_tools` | rvandroid_android | DroidBot, APE, FastBot, Docker CLI |
| 4a | `phtcosta/rvandroid_dev:0.8.0` | rvandroid_tools | Full framework (editable Poetry install) |
| 4b | `phtcosta/rvandroid:0.8.0` | rvandroid_tools | Production image |

## Entry Point

`docker-entrypoint.sh` translates environment variables to `rv-experiment run` CLI arguments:

| Environment Variable | CLI Flag | Description |
|---------------------|----------|-------------|
| `RV_TOOLS` | `--tools` | Tool specification (e.g., `monkey,droidbot:dfs_greedy`) |
| `RV_TIMEOUTS` | `--timeout` | Execution timeout in seconds |
| `RV_REPETITIONS` | `--repetitions` | Number of repetitions |
| `RV_APKS_DIR` | `--apks-dir` | APK directory path |
| `RV_NO_WINDOW` | `--no-window` / `--window` | Emulator headless mode |
| `RV_SPEC_SET` | `--specification-set` | Specification set (jca, generic, custom) |
| `RV_SKIP_MONITORS` | `--skip-monitors` | Skip monitor generation |
| `RV_SKIP_INSTRUMENT` | `--skip-instrument` | Skip APK instrumentation |
| `RV_SKIP_STATIC_ANALYSIS` | `--skip-static` | Skip static analysis |
| `RV_DEVICE_PORT` | `--device-port` | Emulator port for parallel execution |
| `RV_APKS_FILTER` | `--apks-filter` | APK filter file |
| `RV_EXPERIMENT_NAME` | `--name` | Experiment name (enables resume) |
| `RV_RESUME_DIR` | `--resume-dir` | Resume from specific directory |
| `RV_DEBUG` | `--debug` | Debug logging |
| `RV_DELAY` | (sleep before start) | Startup delay for parallel staggering |

Interactive mode: pass `bash` or `shell` as command to drop into a shell.

## Docker Compose

Two deployment patterns:

**Single container** (`docker-compose.yml`): One rvandroid container with Humanoid service and docker.sock mount.

**Parallel containers** (`docker-compose.parallel.yml`): YAML anchors define base service, N concrete services (rv01, rv02, ...) each with own experiment name, device port, delay, and result volume. Shared Humanoid service.

## Resume in Docker

Containers resume via `RV_EXPERIMENT_NAME`. When a container with `RV_EXPERIMENT_NAME=batch_01` is killed and restarted with the same name and result volume, rv-experiment detects `results/batch_01/tasks.json` and auto-skips pre-processing and completed tasks.

## Docker-Based Tools

ARES, QTesting, and Humanoid require additional Docker infrastructure:

- **ARES/QTesting**: Spawn sibling containers via docker.sock mount. Network: `--network container:$(hostname)` inside Docker, `--network host` outside.
- **Humanoid**: Shared inference server (`phtcosta/humanoid:1.0` on port 50405), declared as service in compose files.

## Building

```bash
# Build all images
./build_all.sh

# Build individual layers
cd base && ./build.sh
cd android && ./build.sh
cd tools && ./build.sh
cd rvandroid_dev && ./build.sh
```
