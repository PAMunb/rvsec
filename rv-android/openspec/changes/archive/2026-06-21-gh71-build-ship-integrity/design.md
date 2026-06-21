## Context

`aperv-tool` consumes `ape-rv.jar` at runtime, resolved by `JarResolver` whose first search path is the module directory `modules/aperv-tool/src/aperv_tool/tools/aperv/`. That directory has carried a **git-committed** `ape-rv.jar`, and the rvandroid image acquired it only because the binary travels inside the cloned `rvsec` repo — no Dockerfile compiles `ape`. This let a stale jar persist: the committed binary (`c5d76943`) reads the legacy static-analysis key `reachesMop`; gh60 JSONs emit `reachesTarget`. In the June 2026 169-APK run, `[APE-RV] MOP boost` fired in 0/147,153 evaluations. The MOP parser in current `ape` source is already correct — the only broken link is build/ship. See proposal.md and plan §B-1 (`ape/docs/20260621_plano_correcao_aperv_e_modulos_relacionados.md`). GitHub Issue: rvsec#71. FRs: FR18-FR20 (Tools).

Verified facts (Explore phase): the base image `phtcosta/rvandroid_tools:0.9.1` already provides `d8` (`/opt/android/build-tools/35.0.1/d8`), Maven 3.9.16, Git, and JDK 25, with `ANDROID_HOME=/opt/android`. `ape/pom.xml` sets `maven.compiler.release=11`; `mvn package` runs `d8` (bound to the `package` phase) and yields `target/ape-rv.jar`. The directory `.gitignore` exists but is empty (0 B), and the jar is git-tracked (force-added).

## Architecture

```
docker/rvandroid/Dockerfile  (single stage, base = rvandroid_tools:0.9.1)
  ├─ RUN git clone rvsec && mvn install && mvn compile && uv sync   (lines 13-17, existing compound RUN)
  ├─ RUN git clone phtcosta/ape  ┐
  │   && mvn package             │  NEW standalone RUN (single-stage), placed AFTER the rvsec RUN
  │   && cp target/ape-rv.jar →  ┘  modules/aperv-tool/.../ape-rv.jar   (overwrites the now-deleted committed path)
  └─ (existing dexlib2 freshness gate / LABEL / ENV / ENTRYPOINT ...)

Repository (branch `modules`):
  ├─ modules/aperv-tool/.../ape-rv.jar         → DELETED (backup/ first)
  └─ modules/aperv-tool/.../.gitignore         → add `ape-rv.jar`
```

### Key Components

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| `docker/rvandroid/Dockerfile` (new RUN) | Clone `ape`, `mvn package`, copy fresh jar | `phtcosta/ape` default branch | `ape-rv.jar` in module dir (in image) |
| `aperv-tool` `_resolve_jar_path` (unchanged) | Resolve jar at runtime, module dir = priority 1 | jar in module dir | path pushed to device |
| `.gitignore` (module dir) | Keep the built jar out of version control | — | `ape-rv.jar` ignored |

## Mapping: Spec → Implementation → Test

| Requirement | Implementation | Test |
|-------------|---------------|------|
| INV-TOOL-21 (build from source, no committed/bind-mount dep) | new `RUN` in `Dockerfile`; `git rm` committed jar | Image build smoke: jar present + non-empty; `git ls-files` shows no tracked jar |
| INV-TOOL-22 (repo does not track jar; `.gitignore` ignores it) | `git rm` + `.gitignore` line | `git check-ignore ape-rv.jar`; `git ls-files` empty for the path |
| INV-TOOL-23 (default branch, no ARG/no pin) | `git clone https://github.com/phtcosta/ape.git` (no `ARG`) | Dockerfile review; `grep -c APE_REF` == 0 |
| INV-TOOL-24 (single-stage, new RUN after the rvsec build step) | new standalone `RUN` after the existing compound RUN (lines 13-17); single `FROM` | Dockerfile review; build succeeds on base image |
| ADDED: Build ape-rv.jar from source | the new RUN | `aperv-tool` tests stay green (mock the jar) |

## Goals / Non-Goals

**Goals:**
- The shipped `ape-rv.jar` is always compiled from current `ape` source at image build.
- Eliminate the committed binary as a drift source; one source of truth (the build).
- Keep the change minimal: build-chain only, single atomic commit.

**Non-Goals:**
- No edits to `docker-compose.*.yml` or `scripts/calibration_orchestrator.py` (experiment config; historical A/B files).
- No image tag bump.
- No `ARG`/SHA pin for the `ape` ref.
- No change to `aperv-tool` Python source or to the `ape` MOP parser (already correct).
- The final 169-APK validation run (researcher-owned) is not part of this change.

## Decisions

**D1 — Build from source inside the image (vs. keep shipping a committed jar with a freshness gate).** Chosen: build from source. A freshness gate on a committed binary only detects drift; it does not remove the root cause (a human must rebuild and recommit the jar, which is exactly what failed). Building from source makes the image self-consistent with `ape` HEAD. This is the architectural decision recorded in the ADR.

**D2 — Single-stage (vs. multi-stage builder).** Chosen: single-stage. Multi-stage is only needed when the runtime base lacks build tools; here the base already has `d8`, Maven, Git, and a JDK. A single `RUN` is simpler (P1) and avoids a second `FROM`. Trade-off: the build tools remain in the image (already true today), so no size regression is introduced by this change.

**D3 — No `ARG APE_REF`, clone the default branch (vs. parametrized/pinned ref).** Chosen: clone the default branch, no `ARG`. The ref is never overridden in practice; an `ARG` adds surface with no consumer (P1). "Always current" is the desired default. If a specific ref is ever required, it is a one-line Dockerfile edit at that time.

**D4 — HTTPS anonymous clone (vs. SSH / build secret / submodule).** Chosen: HTTPS, mirroring the existing `rvsec` clone. `phtcosta/ape` is public, so no credentials are needed; this preserves the "no SSH key in build" property. Pre-condition: the repo must be public before the first image build.

**D5 — Atomic commit for jar deletion + Dockerfile build (vs. separate commits).** Chosen: atomic. Today the jar enters the image via the `rvsec` clone; deleting it without the build step would yield an image where `aperv:*` runs fail at JAR resolution. One commit = one consistent state (P3).

**D6 — `mvn package` (vs. `mvn install`).** Chosen: `package`. The `d8` step is bound to the `package` phase and yields `target/ape-rv.jar`; `install` is unnecessary because no Maven consumer inside the image needs the artifact installed.

## API Design

No code API changes. The contract is the Dockerfile build step and the repository state. Sketch of the new `RUN` (illustrative; exact form finalized in implementation):

```dockerfile
# Build APE-RV from source so the shipped jar matches current ape (and the
# current static-analysis JSON schema). Base image already has d8/mvn/git/JDK.
RUN git clone https://github.com/phtcosta/ape.git /tmp/ape \
    && mvn -f /tmp/ape/pom.xml package -DskipTests \
    && cp /tmp/ape/target/ape-rv.jar \
       /opt/rvsec/rv-android/modules/aperv-tool/src/aperv_tool/tools/aperv/ape-rv.jar \
    && rm -rf /tmp/ape
```

## Data Flow

Build time: `phtcosta/ape` source → `mvn package` (`javac --release 11` → `d8`) → `target/ape-rv.jar` → copied into the aperv-tool module dir in the image. Run time (unchanged): `JarResolver` finds the jar in the module dir (priority 1) → `aperv-tool` pushes it to `/data/local/tmp/ape-rv.jar` on the device.

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| Clone fails (network / repo not public) | image build | Build fails loudly | Ensure `phtcosta/ape` public + network at build |
| `mvn package` fails / no `target/ape-rv.jar` | image build | Build fails loudly (no fallback binary exists) | Fix the ape build; rebuild |
| `ape-rv.jar` missing at runtime | `_resolve_jar_path` | `RVToolExecutionError` (existing behavior) | Indicates the build step did not run — rebuild image |

## Risks / Trade-offs

- [Longer image build: extra clone + `mvn package`] → Mitigation: Docker layer caching; the step is small relative to the existing rvsec build.
- [Build-time network dependency on `phtcosta/ape`] → Mitigation: public HTTPS, same failure surface as the existing `rvsec` clone.
- [Pre-condition: `phtcosta/ape` must be public before first build] → Mitigation: verify before building; documented in tasks.
- [No bind-mount escape hatch in the image] → Accepted: experiment composes (out of scope) can still mount a jar if a researcher needs a specific build.

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Repo state | jar untracked + ignored | `git ls-files`, `git check-ignore` | 2 checks |
| Dockerfile review | no `ARG APE_REF`; RUN placement (new standalone RUN after the rvsec build step, lines 13-17); single `FROM` | static inspection / grep | 3 checks |
| Image build (smoke, manual) | `docker build` succeeds; `/opt/rvsec/.../ape-rv.jar` exists + non-empty | `docker build` + `test -s` | 1 build |
| Unit (existing) | `aperv-tool` jar-resolution tests still pass | `uv run pytest modules/aperv-tool/tests/` (mocks the jar) | unchanged |

## Open Questions

- None blocking. (Pre-condition to confirm operationally: `phtcosta/ape` is public before the first image build — tracked as a task, not a design unknown.)
