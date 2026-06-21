## Purpose

This delta adds the `aperv-image-build` capability to the `tools` domain. It governs **how the `ape-rv.jar` consumed by `aperv-tool` is produced and shipped inside the rvandroid Docker image** — not the runtime behavior of the tool itself, which is unchanged.

`aperv-tool` (rv-platform plugin, Layer 5) wraps the APE-RV binary `ape-rv.jar` and resolves it at runtime via `JarResolver`, whose first search path is the module directory `modules/aperv-tool/src/aperv_tool/tools/aperv/`. Until now that directory contained a **git-committed** `ape-rv.jar`, and the rvandroid image acquired the jar only because it travels inside the cloned `rvsec` repository — no Dockerfile ever compiled the `ape` project. That coupling let a stale binary persist: the committed jar (`c5d76943`) reads the legacy static-analysis key `reachesMop`, while gh60 static-analysis JSONs emit `reachesTarget`, so in the June 2026 169-APK run `[APE-RV] MOP boost` fired in 0 of 147,153 evaluations. The correct parser already exists in the `ape` source; the only broken link is the build/ship chain.

This capability makes the image **build `ape` from source** and ship the freshly compiled jar, eliminating the committed binary as a source of drift. The base image already carries the full toolchain, so a single-stage build suffices. The experiment composes and orchestrator (which historically bind-mounted host jars to work around the stale binary) are out of scope here — they belong to experiment configuration owned by the researcher.

## Data Contracts

### Input
- `phtcosta/ape` (default branch, HTTPS) — the APE-RV source cloned at image-build time (build-time external dependency; public repository)
- base image `phtcosta/rvandroid_tools:0.9.1` — provides the build toolchain (`d8` from build-tools 35.0.1, Maven 3.9.16, Git, JDK 25)

### Output
- `modules/aperv-tool/src/aperv_tool/tools/aperv/ape-rv.jar` (inside the image) — the freshly compiled `target/ape-rv.jar`, at `JarResolver` search-path priority 1

### Side-Effects
- **[Docker image build]**: a network clone of `phtcosta/ape` plus `mvn package` (which runs `d8` to dex the classes) during the build; longer build, amortized by layer caching
- **[Repository]**: the previously committed `ape-rv.jar` is removed from version control and ignored thereafter

### Error
- Build fails (non-zero) if the `ape` clone or `mvn package` does not produce `target/ape-rv.jar` — the build SHALL NOT silently fall back to a committed binary (there is none).

## Invariants

- **INV-TOOL-21**: The rvandroid image build SHALL produce `ape-rv.jar` by compiling `ape` from source (`git clone` + `mvn package`) inside the image; it SHALL NOT depend on a git-committed `ape-rv.jar` nor on a runtime bind-mount.
- **INV-TOOL-22**: The repository SHALL NOT track an `ape-rv.jar` under `modules/aperv-tool/src/aperv_tool/tools/aperv/`; that directory's `.gitignore` SHALL ignore `ape-rv.jar`.
- **INV-TOOL-23**: The `ape` ref compiled SHALL be the repository default branch at build time (always current). There SHALL be no build `ARG` and no pinned SHA for the `ape` ref (P1 — it is never overridden in practice).
- **INV-TOOL-24**: The ape build step SHALL be a new standalone `RUN` placed after the existing `rvsec` build step (the compound `RUN` that clones `rvsec` and ends with `uv sync`, currently `Dockerfile:13-17`), so the destination module directory already exists. It runs within a single image stage (the base image already provides `d8`, Maven, Git, and a JDK; no multi-stage builder is introduced). The jar is consumed at device runtime, not during `uv sync`, so placement after the `rvsec` build step is correct.

## ADDED Requirements

### Requirement: Build ape-rv.jar from source in the image
The rvandroid image build SHALL compile the APE-RV binary from source and place the freshly built jar where `aperv-tool` resolves it, so the shipped jar always matches current `ape` source (and the current static-analysis JSON schema).

#### Scenario: Image built from scratch ships a source-compiled jar
- **WHEN** the rvandroid image is built from `docker/rvandroid/Dockerfile`
- **THEN** the Dockerfile clones `https://github.com/phtcosta/ape.git` (default branch, HTTPS, anonymous) AND runs `mvn package` AND copies `target/ape-rv.jar` to `modules/aperv-tool/src/aperv_tool/tools/aperv/ape-rv.jar` inside the image
- **AND** the resulting `ape-rv.jar` is the compiled artifact, not the legacy committed binary
- **AND** the copied jar exists and is non-empty (build-time verifiable)

#### Scenario: Single-stage build using the base-image toolchain
- **WHEN** the ape build step runs in the image
- **THEN** it uses the toolchain already present in `phtcosta/rvandroid_tools:0.9.1` (`d8`, Maven, Git, JDK)
- **AND** no multi-stage builder is added
- **AND** the image tag is unchanged (the image is rebuilt in place)

### Requirement: No committed or bind-mounted jar dependency
The build and the repository SHALL NOT depend on a pre-committed `ape-rv.jar`, removing the drift that caused the stale-jar failure (legacy `reachesMop` vs gh60 `reachesTarget`).

#### Scenario: Committed jar removed and ignored
- **WHEN** this change is applied
- **THEN** the git-tracked `ape-rv.jar` under `modules/aperv-tool/src/aperv_tool/tools/aperv/` is deleted (backed up to `backup/` first)
- **AND** that directory's `.gitignore` ignores `ape-rv.jar`
- **AND** the deletion and the Dockerfile build step land in a single atomic commit (the jar otherwise enters the image via the `rvsec` clone, so neither half is safe alone)

#### Scenario: ape ref tracks the default branch
- **WHEN** the image is built at any time
- **THEN** the `ape` clone uses the repository default branch (current tip), with no build `ARG` and no pinned SHA
