# ADR 0005 — Build `ape-rv.jar` from source inside the rvandroid image (not ship a committed binary)

**Status**: Accepted (gh71, 2026-06-21)

## Context

`aperv-tool` consumes `ape-rv.jar` at runtime. `JarResolver` resolves it with the module directory `modules/aperv-tool/src/aperv_tool/tools/aperv/` as its first search path (priority 1), and the rvandroid Docker image acquired that jar only as a side effect of cloning the `rvsec` repo at build time — the binary travels *inside* the repo. No Dockerfile ever compiled `ape`. Nothing gated the jar's freshness (unlike the dexlib2 CLI jar, which has a freshness gate at `docker/rvandroid/Dockerfile:25-26`).

This let the committed binary drift stale. The committed jar (last bump `c5d76943`) reads the legacy static-analysis key `reachesMop`; the gh60 static-analysis JSONs emit `reachesTarget`. The signature index built by the jar therefore came up empty, and in the June 2026 169-APK comparison run `[APE-RV] MOP boost` reported `maxBoost>0` in **0 of 147,153** evaluations — the MOP guidance never fired once, silently invalidating the run. The MOP parser in the current `ape` source is already correct; the only broken link is build/ship. Without a fix, any future MOP measurement is blocked.

Verified facts (Explore phase): the base image `phtcosta/rvandroid_tools:0.9.1` already provides `d8` (`/opt/android/build-tools/35.0.1/d8`), Maven 3.9.16, Git, and JDK 25, with `ANDROID_HOME=/opt/android`. `ape/pom.xml` sets `maven.compiler.release=11`; `mvn package` runs `d8` (bound to the `package` phase) and yields `target/ape-rv.jar`. The module directory's `.gitignore` exists but is empty (0 B), and the jar is git-tracked (force-added).

PRD references: FR18–FR20 (Tools).

## Decision

**The rvandroid image build SHALL compile `ape` from source and ship the freshly built `ape-rv.jar`; the repository SHALL NOT track a committed binary.** Concretely:

1. `docker/rvandroid/Dockerfile` gains a single-stage `RUN` step, added as a **new standalone `RUN` after** the existing `rvsec` build step (the compound `RUN` at lines 13-17 that clones `rvsec` and ends with `uv sync`), that clones `https://github.com/phtcosta/ape.git` (default branch — the current tip at build time; no `ARG`, no SHA pin), runs `mvn package`, and copies the built `target/ape-rv.jar` into `modules/aperv-tool/src/aperv_tool/tools/aperv/ape-rv.jar` inside the image. The compound `RUN` is NOT split (P1); the jar is consumed at device runtime, not during `uv sync`, so placement after it is correct. The base image already provides the toolchain, so no multi-stage builder is introduced.
2. The git-tracked committed `ape-rv.jar` is deleted (backed up to `backup/` first) and `ape-rv.jar` is added to the module directory's `.gitignore`.
3. Both repository changes and the Dockerfile change land in **one atomic commit**: today the jar enters the image via the `rvsec` clone, so deleting it without the build step would produce an image where `aperv:*` runs fail at JAR resolution.

This makes the image self-consistent with `ape` HEAD and establishes a single source of truth (the build) for the shipped jar.

## Alternatives Considered

**D1 — Build from source inside the image (chosen) vs. keep shipping a committed jar behind a freshness gate.** A freshness gate on a committed binary only *detects* drift; it does not remove the root cause. The cause is human: someone must rebuild `ape` and recommit the jar, which is exactly the step that failed. Building from source at image build makes drift structurally impossible — the shipped jar is always compiled from the `ape` source available at build time. Rejected: the freshness-gate option preserves the manual recommit step that caused the incident.

**D2 — Single-stage (chosen) vs. multi-stage builder.** Multi-stage is only needed when the runtime base lacks build tools. Here the base image already carries `d8`, Maven, Git, and a JDK, so a single `RUN` is simpler (P1) and avoids a second `FROM`. Trade-off: the build tools remain in the image — but they are already present today, so this introduces no size regression. Rejected: multi-stage adds a stage with no payoff on this base.

**D3 — Clone the default branch with no `ARG`/no SHA pin (chosen) vs. a parametrized/pinned ref.** The ref is never overridden in practice, and "always current" is the desired default. An `ARG APE_REF` adds surface with no consumer (P1). If a specific ref is ever required, it is a one-line Dockerfile edit at that time. Rejected: parametrization is speculative configuration.

**D4 — HTTPS anonymous clone (chosen) vs. SSH key / build secret / git submodule.** `phtcosta/ape` is public, so no credentials are needed; an anonymous HTTPS clone mirrors the existing `rvsec` clone and preserves the "no SSH key in build" property. A submodule would re-introduce a tracked pointer in the repo (the thing this ADR removes from the build path) and would still require a clone at build. Pre-condition: `phtcosta/ape` must be public before the first image build. Rejected: SSH/secret add credential surface; submodule re-couples repo state to the build.

**D5 — One atomic commit for jar deletion + Dockerfile build step (chosen) vs. split commits.** One commit = one consistent state (P3). Because the jar currently reaches the image only via the `rvsec` clone, a split that deletes the jar before adding the build step would leave an intermediate commit whose image cannot resolve the jar. Rejected: split commits create a broken intermediate state.

**D6 — `mvn package` (chosen) vs. `mvn install`.** The `d8` step is bound to the `package` phase and already produces `target/ape-rv.jar`. No Maven consumer inside the image needs the artifact installed to the local repository, so `install` does extra work for no benefit. Rejected: `install` is unnecessary.

## Consequences

**Positive.**

- The shipped `ape-rv.jar` is always compiled from current `ape` source at image build, so the schema-drift class of failure (the gh71 incident: jar reads `reachesMop` while JSONs emit `reachesTarget`) cannot recur via a stale committed binary.
- One source of truth: the build replaces the committed binary, so there is no human recommit step to forget.
- Minimal blast radius: build-chain only. `aperv-tool` Python source is unchanged (`JarResolver` priority 1 is still the module dir the build copies into), and the `ape` MOP parser is unchanged (already correct). No image tag bump — the image is rebuilt in place.

**Negative / Trade-offs.**

- Longer image build: an extra clone plus `mvn package` of `ape`. Mitigated by Docker layer caching; the step is small relative to the existing `rvsec` build.
- New build-time network dependency on `phtcosta/ape`. Mitigated: public HTTPS, the same failure surface as the existing `rvsec` clone. If the clone or `mvn package` fails, the build fails loudly — there is no fallback binary, by design.
- Pre-condition: `phtcosta/ape` must be public before the first build. Tracked as an operational task, not a design unknown.
- No bind-mount escape hatch is added in the image itself. Accepted: experiment composes (out of scope here) can still mount a specific jar if a researcher needs one.

**Neutral.**

- `aperv-tool` runtime behavior is unchanged; its tests mock the jar and stay green. No CI gate on the jar exists today and none is added by this change.
- `docker/docker-compose.*.yml` and `scripts/calibration_orchestrator.py` are not touched — their `:ro` jar bind-mounts are experiment configuration (the researcher's domain), and several are historical A/B experiments that mount distinct per-arm jars.

## References

- GitHub Issue: rvsec#71
- Change: `openspec/changes/gh71-build-ship-integrity/` — `proposal.md`, `design.md` (Decisions D1–D6)
- Reference plan: `ape/docs/20260621_plano_correcao_aperv_e_modulos_relacionados.md` §B-1
- Affected build files: `docker/rvandroid/Dockerfile` (new standalone `RUN` after the existing `rvsec` build step, lines 13-17, ending in `uv sync`); `modules/aperv-tool/src/aperv_tool/tools/aperv/.gitignore` (adds `ape-rv.jar`)
- Runtime resolver (unchanged): `aperv-tool` `JarResolver._resolve_jar_path` — module dir is priority 1
- Invariants (gh71 spec deltas): INV-TOOL-21 (build from source, no committed/bind-mount dependency), INV-TOOL-22 (repo does not track the jar; `.gitignore` ignores it), INV-TOOL-23 (default branch, no `ARG`/no pin), INV-TOOL-24 (single-stage, new standalone RUN after the rvsec build step)
- Related ADRs: 0001 (env-var pattern), 0004 (gh60/gh69 `reachesTarget` target matching — the schema this jar must read)
