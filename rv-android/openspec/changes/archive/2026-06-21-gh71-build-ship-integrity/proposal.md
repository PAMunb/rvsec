## Why

The Docker image ships a **stale, committed `ape-rv.jar`** instead of compiling APE-RV from source, and this silently invalidated a whole experiment. In the June 2026 169-APK comparison run, `[APE-RV] MOP boost` reported `maxBoost>0` in **0 of 147,153** evaluations — the MOP guidance never fired once. Root cause: the image baked the git-committed binary (`modules/aperv-tool/src/aperv_tool/tools/aperv/ape-rv.jar`, last bump `c5d76943`), which reads the legacy static-analysis key `reachesMop`, against gh60 static-analysis JSONs that emit `reachesTarget`. The signature index came up empty, so every boost was zero. The correct parser already exists in the `ape` source tree; nothing in the consumer needs changing. The image build is the only broken link: no `Dockerfile` ever compiles the ape — the jar reaches the image purely because it is committed inside the cloned `rvsec` repo, with no freshness gate (unlike the dexlib2 CLI jar, which has one at `Dockerfile:25-26`).

This change is the fix that unblocks any future MOP measurement. GitHub Issue: rvsec#71.

## What Changes

- **`docker/rvandroid/Dockerfile`**: add a single-stage standalone `RUN` step after the existing `rvsec` build step (the compound `RUN` at `Dockerfile:13-17` that clones `rvsec` and ends with `uv sync`) that clones `https://github.com/phtcosta/ape.git` (default branch — always the current tip at build time; no `ARG`, no SHA pin), runs `mvn package`, and copies the freshly built `target/ape-rv.jar` to `modules/aperv-tool/src/aperv_tool/tools/aperv/ape-rv.jar` inside the image. The base image already provides the toolchain (`d8`, Maven, Git, JDK), so no multi-stage builder is needed.
- **BREAKING (build provenance)**: delete the git-tracked committed `ape-rv.jar` (backed up to `backup/` first) and add `ape-rv.jar` to the empty `.gitignore` in that directory. This must land in the **same atomic commit** as the Dockerfile change: today the jar enters the image via the `rvsec` clone, so deleting it without the new build step would produce an image where `aperv:*` runs fail at JAR resolution.
- **No image tag change** — the image is rebuilt in place.

## Capabilities

### New Capabilities
- **tools** → `aperv-image-build`: the image build SHALL compile `ape` from source and ship the freshly built `ape-rv.jar`, with no dependence on a committed binary or a runtime bind-mount.

### Modified Capabilities
- None. (The `ape` MOP parser is already correct in source; this change does not alter the `tools` runtime behavior of `aperv-tool`, only how the jar it consumes is produced.)

## Out of Scope

- `docker/docker-compose.*.yml` and `scripts/calibration_orchestrator.py` are **not** touched. Their `:ro` jar bind-mounts are experiment configuration/execution (the researcher's domain), and several are historical A/B experiments (`final-*`, `revalidate-*`) that mount distinct per-arm jars; removing those would alter what those experiments test.
- The final 169-APK comparison run is executed by the researcher, once, at the end, for result validation and change closure only. Nothing in this change depends on it.

## Impact

- **Modules**: `aperv-tool` (the jar consumer — Python source unchanged; `JarResolver` priority 1 is the module dir the build copies into) and `docker/rvandroid` (the `Dockerfile`).
- **FRs/NFRs**: FR18-FR20 (Tools).
- **External dependency (new, build-time only)**: an HTTPS clone of `phtcosta/ape` (public repo) during image build — mirrors the existing `rvsec` clone pattern; no SSH, no credentials.
- **Build pipeline**: image build gains a network clone + `mvn package` of `ape` (longer build; cached by layers). No CI gate exists on the jar today; `aperv-tool` tests mock the jar and stay green.
- **Reference**: plan `ape/docs/20260621_plano_correcao_aperv_e_modulos_relacionados.md` §B-1.
