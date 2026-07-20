# Change Plan: Release 0.9.2 — fast-forward modules→master, open 0.9.3-SNAPSHOT on modules

**Date**: 2026-07-20
**Track**: Quick Path
**Priority**: Medium
**GitHub Issue**: [#84](https://github.com/PAMunb/rvsec/issues/84)
**PRD Reference**: N/A (release/maintenance chore; no behavior change)
**Domains**: build/infra (reactor POMs + Docker chain + runtime scripts), instrumentation (dexlib2 CLI version string + test asserts)

## 1. Context

Cut the **0.9.2 release** on `master` and open the next development cycle (`0.9.3-SNAPSHOT`)
on `modules`. This mirrors the archived change **gh76-bump-092-snapshot**
(`0.9.1-SNAPSHOT → 0.9.2-SNAPSHOT`), reusing the same Group structure, exclusion list, and
verification steps, but adds three dimensions gh76 did not have:

1. **A git branch operation.** `origin/master` is a **strict ancestor** of `modules`
   (`git merge-base --is-ancestor origin/master modules` → true; `modules` is 1223 commits
   ahead, `origin/master` is 0 ahead). So promoting `master` to the `modules` tree is a clean
   **fast-forward** — no force-push. The fast-forward also *removes* ~585 legacy pre-modular
   files (e.g. `rv-android/android.py`, `rv-android/commands/*`, `rv-android/examples/osmtracker-android/*`)
   that still exist in `master`'s tree but were deleted across the 1223 `modules` commits. No
   manual deletion is needed — those deletions are already recorded in `modules`' history.

2. **Two target versions on two branches.** After the fast-forward, `master` and `modules`
   both sit at `0.9.2-SNAPSHOT`. `master` then becomes the release `0.9.2` (drop `-SNAPSHOT`);
   `modules` moves to `0.9.3-SNAPSHOT`. After the fast-forward the branches diverge forward-only:
   `master` gains **one** commit (release `0.9.2`), `modules` gains **two** (dev-bump `0.9.3-SNAPSHOT`,
   then the gh84 archive-move) — textbook release/develop divergence, no force-push ever.

3. **A slightly larger active file set than gh76**: the dexlib2 CLI version annotation
   (`InstrumentationCli.java`), the dexlib2 `architecture.md`, an additional compose file
   (`docker-compose.gh80.yml`), and several current docs still pointing at stale `0.9.1`/`0.9.0`.

The change is **mechanical** (Quick Path — WORKFLOW.md §3): version-string substitution via
`versions-maven-plugin` + targeted edits, plus deterministic git branch/tag commands. No design
decisions. POMs and runtime jar-path scripts carry `-SNAPSHOT`; Docker image tags use the release
form (no `-SNAPSHOT`).

### Version-form matrix

Every in-scope reference falls into one of two buckets:

| Bucket | Current | On `master` (release) | On `modules` (dev) |
|---|---|---|---|
| **`-SNAPSHOT` carriers** (POMs, runtime config scripts, test jar asserts, CLI version, dexlib2 `architecture.md`) | `0.9.2-SNAPSHOT` | `0.9.2` (drop suffix) | `0.9.3-SNAPSHOT` |
| **bare tag carriers** (Docker build scripts, Dockerfile `FROM`, run helpers, compose `image:`, Python image defaults) | `0.9.2` | `0.9.2` (**no change** — release tag already matches) | `0.9.3` |

Consequence: on `master`, the Docker chain and Python defaults need **no edit** (already `0.9.2`);
only the `-SNAPSHOT` carriers change. On `modules`, both buckets change.

## 2. Scope

**Groups (execution units):**
- **Group G0 — Git branch op** *(new vs gh76)*: fast-forward `master` ← `modules`. No tag (user
  decision 2026-07-20), no push (stop before push — user decision 2026-07-20).
- **Group A — Reactor POMs (via plugin)**: `mvn versions:set` from root reaches 45 reactor POMs.
- **Group B — `rv-android/pom.xml` (explicit)**: commented out of the reactor (`pom.xml:73`), not
  reached by the plugin — manual `<version>` + `<parent><version>`.
- **Group C — Runtime config scripts** (`-SNAPSHOT` carriers, Maven jar paths).
- **Group D — Docker chain** (bare tag; `master` unchanged, `modules` → `0.9.3`).
- **Group E — Python image defaults** (bare tag; `master` unchanged, `modules` → `0.9.3`).
- **Group F — Test asserts** (`-SNAPSHOT` jar-name assertions) + run suites green.
- **Group H — Source version string** *(new)*: `InstrumentationCli.java` `@Command(version=...)`.
- **Group I — Current docs** *(new)*: current CLAUDE.md / architecture / spec docs carrying a
  version string (stale `0.9.1`/`0.9.0` included). ADRs and plan-docs excluded (historical).

**Excluded (do NOT touch — same rationale as gh76, decision confirmed 2026-07-20):**
- `backup/*` (4 POMs at `0.9.0-SNAPSHOT` — gesda/reachability), all `experimento-*/`, `para05/`, `data/`.
- Own-version reactors: crylogger (`0.3.0`), docker/mop (`1.2.8`), rv-monitor docs/installer
  (`1.4-SNAPSHOT`), teste-sootup (`0.6.0`).
- `rvsec/rvsec-android/rvsmart/dependency-reduced-pom.xml` (shade-generated — regenerated on build).
- `rv-android/tools/qtesting/src` submodule (third-party; pointer untouched).
- **ADRs** `rv-android/docs/adr/0001-*.md` (`0.9.0`), `0005-*.md` (`0.9.1`): historical decision
  records — P4/P3, do not rewrite history.
- `rvsec/.../rvsec-instrumentation-dexlib2/javadoc-improvement-plan.md`: a plan doc (historical).
- **`0.9.0`-pinned experiment compose files**: `docker-compose.exp-ape-gh59.yml:34`,
  `docker-compose.instrument-jca190.yml` (l.4,20,32), `instrument-jca226.yml:16`,
  `instrument-jca-ajc.yml:16`. These pin a *specific published image* for experiment
  reproducibility — leave at `0.9.0` (analogous to gh76 leaving `experimento-*` pins).
- Everything under `openspec/changes/**` (incl. archived gh76) — historical artifacts.
- Dated experiment/methodology docs (`rv-android/docs/YYYYMMDD_*.md`), notably
  `rv-android/docs/20260619_comparacao_aperv.md` (~20 `phtcosta/rvandroid:0.9.1` refs): experiment
  records pinned to the image they ran against — leave at `0.9.1` (same rationale as the `0.9.0`-pinned
  experiment compose files).

## 3. File Inventory

Line numbers verified on `modules` @ `0.9.2-SNAPSHOT` (2026-07-20). "→R" = value on `master`
release; "→M" = value on `modules` dev cycle.

### Group A — Reactor POMs (via `versions-maven-plugin`)

From repo root `rvsec/`:
```
# master (release):
mvn versions:set -DnewVersion=0.9.2 -DgenerateBackupPoms=true
# modules (dev):
mvn versions:set -DnewVersion=0.9.3-SNAPSHOT -DgenerateBackupPoms=true
```
Reaches the 45 reactor POMs (confirmed by Maven: reactor builds `[1/45]…[45/45]`): root
`rvsec-parent`; `rv-monitor` (+rt, logicrepository, 10 plugins,
rv-monitor); `javamop`; `mop-maven-plugin`; `rvsec` (+rvsec-mop, -mop-extractor, -mop-defsuses,
-core, -logger-csv, -agent, -android); `rvsec-android` (+rvsec-apk, -logger-logcat, rvsec-gator
+commons/sootandroid/client, rvsmart, -frame-computer, -instrumentation-dexlib2 +10 children).

| File | Action | Detail |
|------|--------|--------|
| 45 reactor POMs | `versions:set` | `0.9.2-SNAPSHOT` → **R** `0.9.2` / **M** `0.9.3-SNAPSHOT` (via plugin) |

### Group B — `rv-android/pom.xml` (explicit; commented out of reactor)

| File | Action | Detail |
|------|--------|--------|
| `rv-android/pom.xml` | Edit | `<parent><version>` (l.10) **only** — module inherits from parent, has no own `<version>` → **R** `0.9.2` / **M** `0.9.3-SNAPSHOT` |

### Group C — Runtime config scripts (`-SNAPSHOT` carriers, Maven jar paths)

| File | Action | Detail |
|------|--------|--------|
| `configure.sh:13` | Edit | `RV_MONITOR_VERSION=0.9.2-SNAPSHOT` → **R** `0.9.2` / **M** `0.9.3-SNAPSHOT` |
| `rvsec/config.sh:13` | Edit | `RV_MONITOR_VERSION=0.9.2-SNAPSHOT` → **R** `0.9.2` / **M** `0.9.3-SNAPSHOT` |
| `rv-android/scripts/run_phase5_validators.sh:80` | Edit | `validator-0.9.2-SNAPSHOT.jar` → **R** `validator-0.9.2.jar` / **M** `validator-0.9.3-SNAPSHOT.jar` |

### Group D — Docker chain (bare tag; **R** = no change, **M** → `0.9.3`)

Active tags:

| File | Action (modules only) | Detail |
|------|------|--------|
| `build_docker_image.sh:12` | Edit (M) | `IMAGE_TAG="0.9.2"` → `0.9.3` |
| `rv-android/docker/base/build.sh:5` (+comment l.15) | Edit (M) | `VERSION=0.9.2` → `0.9.3` |
| `rv-android/docker/android/build.sh:5` (+comment l.15) | Edit (M) | `VERSION=0.9.2` → `0.9.3` |
| `rv-android/docker/tools/build.sh:5` (+comment l.15) | Edit (M) | `VERSION=0.9.2` → `0.9.3` |
| `rv-android/docker/rvandroid/build.sh:5` (+comment l.15) | Edit (M) | `VERSION=0.9.2` → `0.9.3` |
| `rv-android/docker/rvandroid_dev/build.sh:3` | Edit (M) | `VERSION=0.9.2` → `0.9.3` |
| `rv-android/docker/android/Dockerfile:1` | Edit (M) | `FROM phtcosta/rvsec_base:0.9.2` → `0.9.3` |
| `rv-android/docker/tools/Dockerfile:1` | Edit (M) | `FROM phtcosta/rvsec_android:0.9.2` → `0.9.3` |
| `rv-android/docker/rvandroid/Dockerfile:1` | Edit (M) | `FROM phtcosta/rvandroid_tools:0.9.2` → `0.9.3` |
| `rv-android/docker/rvandroid_dev/Dockerfile:1` | Edit (M) | `FROM phtcosta/rvandroid_tools:0.9.2` → `0.9.3` |
| `rv-android/docker/base/run.sh:3` | Edit (M) | `rvsec_base:0.9.2` → `0.9.3` |
| `rv-android/docker/android/run.sh:3` | Edit (M) | `rvsec_android:0.9.2` → `0.9.3` |
| `rv-android/docker/tools/run.sh:17` (+comment l.47) | Edit (M) | `rvandroid_tools:0.9.2` → `0.9.3` |
| `rv-android/docker/rvandroid/run.sh:3` | Edit (M) | `rvandroid:0.9.2` → `0.9.3` |
| `rv-android/docker/docker-compose.yml:20` | Edit (M) | `image: phtcosta/rvandroid:0.9.2` → `0.9.3` |
| `rv-android/docker/docker-compose.gh80.yml:24` (+comments l.7,11) | Edit (M) | `image: phtcosta/rvandroid:0.9.2` → `0.9.3` |
| `rv-android/docker/docker-compose.dexlib2-validation.template.yml:34,55` (+comments l.6,21) | Edit (M) | `image:` `0.9.2` → `0.9.3` |

### Group E — Python image defaults (bare tag; **R** = no change, **M** → `0.9.3`)

| File | Action (modules only) | Detail |
|------|------|--------|
| `rv-android/scripts/baseline_docker.py:252-253` | Edit (M) | `default="phtcosta/rvandroid:0.9.2"` + help → `0.9.3` |
| `rv-android/scripts/preprocess_docker.py:271-272` | Edit (M) | `default=...:0.9.2` + help → `0.9.3` |
| `rv-android/scripts/calibration_orchestrator.py:584-585` | Edit (M) | `default=...:0.9.2` + help → `0.9.3` |
| `rv-android/.claude/skills/rv-experiment-compare/scripts/gen_compare.py:202` | Edit (M) | `default="phtcosta/rvandroid:0.9.2"` → `0.9.3` |

### Group F — Test asserts (`-SNAPSHOT` jar-name assertions)

| File | Action | Detail |
|------|--------|--------|
| `rv-android/modules/rv-instrumentation-core/tests/test_instrumenter.py:97-99` | Edit | rv-monitor-rt / rvsec-core / rvsec-logger-logcat `-0.9.2-SNAPSHOT.jar` → **R** `-0.9.2.jar` / **M** `-0.9.3-SNAPSHOT.jar` |
| `rv-android/modules/rv-instrumentation-dexlib2/tests/test_dexlib_instrumentation.py:536-538,546-548,580-582,594-596` | Edit | same trio ×4 blocks `-0.9.2-SNAPSHOT.jar` → **R** `-0.9.2.jar` / **M** `-0.9.3-SNAPSHOT.jar` |

### Group H — Source version string (`-SNAPSHOT` carrier)

| File | Action | Detail |
|------|--------|--------|
| `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/cli/src/main/java/br/unb/cic/rv/cli/InstrumentationCli.java:27` | Edit | `@Command(... version = "0.9.2-SNAPSHOT")` → **R** `0.9.2` / **M** `0.9.3-SNAPSHOT` |

### Group I — Current docs (version strings)

| File | Action | Detail |
|------|--------|--------|
| `CLAUDE.md:4` (root) | Edit | `rvsec-parent:0.9.1-SNAPSHOT` (stale) → **R** `0.9.2` / **M** `0.9.3-SNAPSHOT` |
| `rvsec/rvsec-android/CLAUDE.md:7` | Edit | `0.9.1-SNAPSHOT` (stale) → **R** `0.9.2` / **M** `0.9.3-SNAPSHOT` |
| `rvsec/rvsec-mop/CLAUDE.md:26` | Edit | `rvsec-mop-0.9.1-SNAPSHOT.jar` (stale) → **R** `-0.9.2.jar` / **M** `-0.9.3-SNAPSHOT.jar` |
| `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/architecture.md:34,56` | Edit | `0.9.2-SNAPSHOT` → **R** `0.9.2` / **M** `0.9.3-SNAPSHOT` |
| `rv-android/docs/architecture/subsystem-rv-experiment.md:181,308,1280,1316` | Edit | current image-tag refs `rvandroid:0.9.1` (stale) → **R** `0.9.2` / **M** `0.9.3` |
| `rv-android/docs/architecture/subsystem-rv-experiment.md:550` | **Review** | historical narrative ("bumped to image 0.9.1") — likely leave (P4 historical statement); confirm at apply |
| `rv-android/openspec/specs/tools/spec.md:522` | Edit | `phtcosta/rvandroid_tools:0.9.1` (stale) → **R** `0.9.2` / **M** `0.9.3` |
| `rv-android/openspec/specs/instrumentation/spec.md:1192` | **Review** | `rvandroid:0.9.0` describes a rebuilt-image fact — confirm whether to refresh or leave (historical) at apply |
| `rv-android/.claude/skills/rv-experiment-compare/SKILL.md:53` | Edit | default image `(default 0.9.1)` (stale) → **R** `0.9.2` / **M** `0.9.3` |

## 4. Execution Order

The version bumps are two disjoint passes on two branches; git ops bracket them. Suggested order
(all local; **stop before push** per user decision):

1. **Commit this change (gh84) on `modules`** first, so the fast-forward carries it into `master`.
2. **Group G0a — Fast-forward**: create local `master` from `origin/master`, `git merge --ff-only modules`.
   Verify `master` tree == `modules` tree and the ~585 legacy files are gone.
3. **On `master` (release 0.9.2)** — apply `-SNAPSHOT`-carrier groups only:
   - Group A (`versions:set -DnewVersion=0.9.2`) → validate `git diff --stat` touches only reactor POMs
   - Group B (`rv-android/pom.xml`), C, F, H, and the `-SNAPSHOT`→`0.9.2` doc rows of Group I
   - Group D/E: **no change** (already `0.9.2`); still refresh the stale-`0.9.1` doc rows of Group I to `0.9.2`
   - `mvn versions:commit`; run `mvn clean install -DskipMopAgent -DskipTests` (full reactor build) + pytest green
   - Commit `release 0.9.2 (closes #84)` (no git tag — user decision)
4. **On `modules` (0.9.3-SNAPSHOT)** — `git checkout modules`, apply all groups:
   - Group A (`versions:set -DnewVersion=0.9.3-SNAPSHOT`), B, C, D, E, F, H, and all Group I rows → `0.9.3`/`0.9.3-SNAPSHOT`
   - `mvn versions:commit`; `mvn clean install -DskipMopAgent -DskipTests` (full reactor build) + pytest green
   - Commit `open 0.9.3-SNAPSHOT dev cycle (refs #84)`
5. **Archive** gh84 on `modules` (`openspec archive`); move Kanban card #84 → Done (after user pushes).

Groups within a branch touch disjoint files and are parallelizable via subagents (WORKFLOW.md §5),
but the branch-level ordering (FF → master pass → modules pass) is strict. **No push** — the user
pushes `master` and `modules` after review.

## 5. Acceptance Criteria

- [ ] `git merge --ff-only modules` on `master` succeeds (clean fast-forward, no force); `git diff --quiet master modules` before the bumps
- [ ] ~585 legacy files (`rv-android/android.py`, `rv-android/commands/*`, `examples/osmtracker-android/*`) absent from `master` after FF
- [ ] **master**: 46 active POMs (45 reactor + `rv-android/pom.xml`) at `0.9.2` (no `-SNAPSHOT`); `git diff --stat` shows zero change in `backup/`, crylogger, docker/mop, rv-monitor docs/installer, teste-sootup
- [ ] **master**: config scripts (C), test asserts (F), `InstrumentationCli.java` (H), and stale-doc rows (I) at `0.9.2`; Docker chain (D) + Python defaults (E) unchanged at `0.9.2`
- [ ] **modules**: 46 active POMs at `0.9.3-SNAPSHOT`; scripts/tests/CLI/docs at `0.9.3-SNAPSHOT`; Docker chain (D) + Python defaults (E) + gh80 compose at `0.9.3`
- [ ] `experimento-*/`, `backup/`, ADRs, plan-docs, and `0.9.0`-pinned experiment compose files **intact**
- [ ] Both branches: `mvn clean install -DskipMopAgent -DskipTests` (from root, full reactor build) → EXIT=0
- [ ] Both branches: `cd rv-android && uv run pytest modules/rv-instrumentation-core/tests/test_instrumenter.py modules/rv-instrumentation-dexlib2/tests/test_dexlib_instrumentation.py --import-mode=importlib -o "addopts="` → 0 failed
- [ ] `mvn versions:commit` run on both branches (no `*.versionsBackup` left)
- [ ] **master**: `git grep -n "0.9.2-SNAPSHOT"` → residual only in excluded paths; **modules**: `git grep -n "0.9.2\b"` outside excluded paths → none (all `0.9.3`)
- [ ] gh84 change archived on `modules`
- [ ] **No push performed** — left for user to `git push origin master modules` (no tag)
