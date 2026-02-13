# Humanoid Tool

DroidBot with Humanoid inference server for human-like UI exploration. Humanoid is an external deep learning model that predicts which UI elements a human user would interact with, replacing DroidBot's standard action selection with neural network inference.

**Upstream:** https://github.com/yzygitzh/Humanoid

## Execution

Runs DroidBot with the `-humanoid` flag pointing to an inference HTTP server:

```
poetry run droidbot -d emulator-5554 -a <apk_path> \
  -humanoid <server_url> -policy dfs_greedy \
  -count 10000000000 -timeout <seconds> -ignore_ad -is_emulator
```

The Humanoid inference server (`phtcosta/humanoid:1.0`) runs as a separate Docker container on port 50405. The tool connects to this server to get human-like action predictions during DroidBot's exploration loop.

## Variants

| Variant | Policy | Count | Notes |
|---------|--------|-------|-------|
| `default` | dfs_greedy | 10^10 | DFS greedy with humanoid inference |

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `policy` | dfs_greedy | DroidBot exploration policy |
| `count` | 10,000,000,000 | Maximum event count |
| `timeout` | 3,600 | Execution timeout in seconds |
| `device_serial` | emulator-5554 | Target device serial |
| `humanoid_url` | 127.0.0.1:50405 | Inference server URL |
| `ignore_ad` | true | Block ad content |

The `humanoid_url` is resolved in this priority order:
1. Value from `configure()` config dict
2. `RV_HUMANOID_URL` environment variable
3. Default: `127.0.0.1:50405`

## Docker Usage

Humanoid requires a Docker network to connect the rvandroid container to the humanoid inference server:

```bash
# Create network
docker network create rv-test

# Start humanoid inference server
docker run -d --name rv-humanoid --network rv-test phtcosta/humanoid:1.0

# Run rvandroid with humanoid tool
docker run --rm --device /dev/kvm --network rv-test \
  -e RV_TOOLS=humanoid \
  -e RV_HUMANOID_URL=rv-humanoid:50405 \
  -e RV_TIMEOUTS=60 \
  ...

# Cleanup
docker stop rv-humanoid && docker rm rv-humanoid
docker network rm rv-test
```

## Dependencies

- Python, Poetry
- DroidBot Python package (installed via Poetry)
- Humanoid inference server (`phtcosta/humanoid:1.0` Docker image, port 50405)
- Android SDK (adb)
- Running Android emulator or device

## Process Pattern

`droidbot` — same as the DroidBot tool (Humanoid extends DroidBot's functionality).

## ICST Study

Humanoid was one of the 8 official tools in the ICST experiment (Tier 2 - external service dependency). It provides neural network-guided exploration as an alternative to DroidBot's algorithmic policies.
