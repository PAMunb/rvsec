## ADDED Requirements

### Invariant: INV-TOOL-15 (Docker Network for Sibling Containers)

When ARES or QTesting tools build their Docker `run` command inside a Docker container (detected by the presence of `/.dockerenv`), the command MUST include `--network container:<hostname>` where `<hostname>` is the current container's ID obtained via `socket.gethostname()`. This flag makes the sibling container (ARES/QTesting) share the parent container's network namespace, allowing it to reach the emulator at `localhost:5554` without any network configuration changes in the ARES/QTesting code or Dockerfiles.

When running outside Docker (`/.dockerenv` does not exist), no `--network` flag MUST be added. ARES/QTesting use their default Docker networking behavior in standalone mode, which connects to the emulator via the default Docker bridge or via `adb connect`.

This invariant exists because ARES and QTesting are Docker-based tools: `AresTool._build_ares_command()` and `QTestingTool._build_qtesting_command()` invoke `docker run` to start the tool in a separate container. When the rvandroid container itself runs inside Docker (the typical production deployment), the sibling container gets its own isolated network namespace by default and cannot reach the emulator running inside the parent container. The `--network container:` flag solves this by making the sibling share the parent's network stack.

In parallel experiment execution (e.g., 7 rvandroid containers in `docker-compose.parallel.yml`), each rvandroid container (rv01..rv07) can independently spawn its own ARES/QTesting sibling. Each sibling uses `--network container:<its-parent-id>`, so it connects to the correct emulator instance. Up to 7 ARES containers may run simultaneously without conflict because each is isolated to its parent's network namespace.

The `docker.sock` mount (`/var/run/docker.sock:/var/run/docker.sock`) in the compose files is a prerequisite for this invariant: without it, the rvandroid container cannot invoke `docker run` at all.

#### Scenario: ARES Command Includes Network Flag Inside Docker

- **WHEN** `AresTool._build_ares_command()` is called
- **AND** the code is running inside a Docker container (`/.dockerenv` exists)
- **THEN** the generated `docker run` command MUST include `--network container:<hostname>` where `<hostname>` is `socket.gethostname()` (which returns the container ID inside Docker)
- **AND** the `--network` flag MUST appear before the Docker image name in the argument list
- **AND** all other command arguments (volumes, environment variables, ARES-specific flags) MUST remain unchanged

#### Scenario: QTesting Command Includes Network Flag Inside Docker

- **WHEN** `QTestingTool._build_qtesting_command()` is called
- **AND** the code is running inside a Docker container (`/.dockerenv` exists)
- **THEN** the generated `docker run` command MUST include `--network container:<hostname>` where `<hostname>` is `socket.gethostname()`
- **AND** the `--network` flag MUST appear before the Docker image name in the argument list
- **AND** all other command arguments MUST remain unchanged

#### Scenario: No Network Flag Outside Docker

- **WHEN** `AresTool._build_ares_command()` or `QTestingTool._build_qtesting_command()` is called
- **AND** the code is NOT running inside a Docker container (`/.dockerenv` does not exist)
- **THEN** the generated `docker run` command MUST NOT include any `--network` flag
- **AND** the command MUST be identical to the current (pre-change) behavior

## MODIFIED Requirements

### Requirement: External Tool Support (FR19, NFR02) — Docker-Based Tool Execution

ARES and QTesting are Docker-based tools that execute via `docker run` commands built by `_build_ares_command()` and `_build_qtesting_command()` respectively. Unlike other tools (Monkey, DroidBot, APE) that run via ADB shell commands or local scripts, these tools spawn a separate Docker container for each execution.

In standalone mode (developer workstation), the spawned container connects to the emulator via the default Docker bridge network. In production Docker deployment (rvandroid container), the spawned container MUST share the parent container's network namespace via `--network container:$(hostname)` (INV-TOOL-15) to reach the emulator at `localhost:5554`.

The Docker socket (`/var/run/docker.sock`) MUST be mounted into the rvandroid container for Docker-based tools to function. Without this mount, `docker run` commands fail because there is no Docker daemon available inside the container. The Docker CLI binary is installed in the tools Docker image layer (`docker/tools/Dockerfile`).

ARES and QTesting images (`phtcosta/ares:latest`, `phtcosta/qtesting:latest`) MUST be pre-built on the Docker host before running experiments that use these tools. They are NOT declared as services in `docker-compose.yml` — they are spawned on-demand at runtime by each rvandroid container. Only Humanoid is declared as a shared service in the compose files because it operates as a REST server that multiple rvandroid containers connect to over the network.
