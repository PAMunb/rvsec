## MODIFIED Requirements

### Requirement: Docker Execution Mode (FR15, FR16, NFR01)

rv-experiment runs inside Docker containers via `docker/rvandroid/docker-entrypoint.sh`, which translates environment variables (`RV_TOOLS`, `RV_TIMEOUTS`, `RV_REPETITIONS`, etc.) into CLI arguments and executes the experiment command. The entrypoint uses `exec` to replace the shell process, ensuring proper signal handling. A startup delay (`RV_DELAY`) supports staggered parallel container launches. Interactive mode (`bash` or `shell` as first argument) drops into a shell instead of running the experiment.

The Docker base image installs uv as a single binary via `curl -LsSf https://astral.sh/uv/install.sh | sh`. The entrypoint uses `uv run rv-experiment run` to execute experiments, and `uv sync` for dependency installation during image build.

#### Scenario: Docker Entry Point Translates Environment Variables to CLI

- **WHEN** a Docker container starts with `RV_TOOLS=monkey,droidbot`, `RV_TIMEOUTS=300`, `RV_EXPERIMENT_NAME=batch_01`, `RV_NO_WINDOW=true`
- **THEN** the entry point MUST generate: `uv run rv-experiment run --tools monkey,droidbot --timeout 300 --name batch_01 --no-window`
- **AND** MUST echo the generated command to stdout for debugging
- **AND** MUST use `exec` to replace the shell process with the Python process (proper signal handling)

#### Scenario: Docker Entry Point Supports Interactive Mode

- **WHEN** the user runs `docker run ... phtcosta/rvandroid:0.8.0 bash`
- **THEN** the entry point MUST detect the `bash` or `shell` argument
- **AND** MUST drop into an interactive bash shell instead of running the experiment
- **AND** the user MUST be able to run `rv-experiment` commands manually inside the container

#### Scenario: Docker Entry Point Applies Startup Delay

- **WHEN** a Docker container starts with `RV_DELAY=30`
- **THEN** the entry point MUST `sleep 30` before executing the experiment command
- **AND** MUST log the delay duration

#### Scenario: Docker Resume on Container Restart

- **WHEN** a Docker container with `RV_EXPERIMENT_NAME=batch_01` completes 3 out of 10 tasks and is killed
- **AND** a new container starts with the same `RV_EXPERIMENT_NAME=batch_01` and the same result volume mount
- **THEN** the platform MUST detect the existing `tasks.json` in the result volume
- **AND** MUST skip the 3 completed tasks
- **AND** MUST execute only the remaining 7 tasks
- **AND** MUST consolidate results from both sessions into unified CSV/JSON output
