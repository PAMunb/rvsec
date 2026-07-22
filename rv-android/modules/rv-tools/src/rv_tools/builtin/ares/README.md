# ARES Tool

Docker-based systematic UI exploration tool using SAC (Soft Actor-Critic) reinforcement learning. ARES runs as a Docker sibling container that connects to the emulator via the parent container's network namespace.

**Upstream:** https://github.com/H2SO4T/ARES

## Execution

Uses a three-step Docker sibling container pattern:

1. **Create** container with env vars: `docker create --name ares_<uuid> -e EMUNAME=emulator-5554 -e TIMEOUT_IN_MINUTES=1 ...`
2. **Copy** APK into container: `docker cp <apk_path> ares_<uuid>:/ares/apks/app.apk`
3. **Start** container and wait: `docker start -a ares_<uuid>`
4. **Cleanup** in finally block: `docker rm -f ares_<uuid>`

The ARES container runs its own Python process with Appium for device interaction and SAC for action selection.

## Variants

| Variant | Docker Image | Notes |
|---------|-------------|-------|
| `default` | phtcosta/ares:latest | SAC-based exploration |

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `docker_image` | phtcosta/ares:latest | ARES Docker image |
| `device_serial` | emulator-5554 | Emulator name (passed as EMUNAME) |
| `timeout` | 600 | Execution timeout in seconds |

Timeout conversion: the tool converts seconds to minutes via `max(1, int(seconds / 60))` for the ARES container's `TIMEOUT_IN_MINUTES` env var.

## Docker Usage

ARES requires Docker socket access to spawn sibling containers:

```bash
docker run --rm --device /dev/kvm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -e RV_TOOLS=ares \
  -e RV_TIMEOUTS=60 \
  ...
```

### Network Behavior

- **Inside Docker** (`/.dockerenv` exists): Uses `--network container:$(hostname)` to share the parent container's network namespace. The ARES container reaches the emulator at `localhost:5554`.
- **Outside Docker**: Uses `--network host` for direct host network access.

In parallel execution (multiple rvandroid containers), each container spawns its own ARES sibling with `--network container:<its-own-container-id>`. Each sibling reaches only its parent's emulator.

## Dependencies

- Docker daemon (accessed via `/var/run/docker.sock`)
- Pre-built Docker image: `phtcosta/ares:latest` (built from `modules/rv-tools/src/rv_tools/builtin/ares/Dockerfile`)
- Running Android emulator (inside the parent container or on the host)

## Process Pattern

`ares` — used by the platform to detect if the tool process is still running.

## ICST Study

ARES was one of the 8 official tools in the ICST experiment (Tier 3 - Docker sibling container). It provides reinforcement learning-based exploration using the Soft Actor-Critic algorithm.
