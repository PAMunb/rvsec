# QTesting Tool

Q-learning based Android UI exploration tool. QTesting uses a Siamese LSTM neural network for UI state similarity and Q-learning for action selection. It runs as a Docker sibling container that connects to the emulator via the parent container's network namespace.

**Upstream:** https://github.com/nicetester/QTesting

## Execution

Uses a three-step Docker sibling container pattern:

1. **Create** container: `docker create --name qtesting_<uuid> ...`
2. **Copy** APK and config into container:
   - `docker cp <apk_path> qtesting_<uuid>:/qtesting/apks/app.apk`
   - `docker cp <conf.txt> qtesting_<uuid>:/qtesting/apks/conf.txt`
3. **Start** container and wait: `docker start -a qtesting_<uuid>`
4. **Cleanup** in finally block: `docker rm -f qtesting_<uuid>`

The tool generates a `conf.txt` INI configuration file dynamically with the APK name, device ID, and time limit, then copies it into the container alongside the APK.

### Configuration File Format

```ini
[Path]
APK_NAME = app.apk

[Setting]
DEVICE_ID = emulator-5554
TIME_LIMIT = 60
```

## Variants

| Variant | Docker Image | Notes |
|---------|-------------|-------|
| `default` | phtcosta/qtesting:latest | Q-learning with Siamese LSTM |

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `docker_image` | phtcosta/qtesting:latest | QTesting Docker image |
| `device_serial` | emulator-5554 | Target device serial |
| `timeout` | 3,600 | Execution timeout in seconds |

Note: `TIME_LIMIT` in `conf.txt` is in **seconds** (unlike ARES which uses minutes).

## Docker Usage

QTesting requires Docker socket access to spawn sibling containers:

```bash
docker run --rm --device /dev/kvm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -e RV_TOOLS=qtesting \
  -e RV_TIMEOUTS=60 \
  ...
```

### Network Behavior

- **Inside Docker** (`/.dockerenv` exists): Uses `--network container:$(hostname)` to share the parent container's network namespace. The QTesting container reaches the emulator at `localhost:5554`.
- **Outside Docker**: Uses `--network host` for direct host network access.

## Dependencies

- Docker daemon (accessed via `/var/run/docker.sock`)
- Pre-built Docker image: `phtcosta/qtesting:latest` (built from `modules/rv-tools/src/rv_tools/builtin/qtesting/Dockerfile`)
- Running Android emulator (inside the parent container or on the host)

## Process Pattern

`qtesting` — used by the platform to detect if the tool process is still running.

## ICST Study

QTesting was one of the 8 official tools in the ICST experiment (Tier 3 - Docker sibling container). It provides Q-learning-based exploration with neural network state similarity as an alternative to random and model-based approaches.
