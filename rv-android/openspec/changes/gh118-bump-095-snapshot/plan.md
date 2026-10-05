# Change Plan: Bump 0.9.4-SNAPSHOT → 0.9.5-SNAPSHOT (branch `modules`)

**Date**: 2026-10-05
**Track**: Quick Path
**Priority**: Medium
**GitHub Issue**: [#118](https://github.com/PAMunb/rvsec/issues/118)
**PRD Reference**: N/A (maintenance chore; no behavior change)
**Domains**: instrumentation (test asserts, dexlib2 CLI version string), build/infra (reactor POMs, runtime scripts, Docker chain — not mapped to a spec domain)

## 1. Context

The project moves from `0.9.4-SNAPSHOT` to `0.9.5-SNAPSHOT` on the `modules` branch, opening the
development cycle for the last implementation round. The Docker image chain moves from tag `0.9.4`
to `0.9.5`. POMs, runtime jar-path scripts, test jar-name asserts and the CLI version string carry
the `-SNAPSHOT` suffix; Docker tags use the bare form. **Nothing is done on `master`**: there is no
release cut, no branch operation and no tag.

This repeats three archived changes so they read side by side: **gh76-bump-092-snapshot**
(`0.9.1 → 0.9.2`), the `modules` pass of **gh84-release-092** (`0.9.2 → 0.9.3`) and
**gh115-bump-094-snapshot** (`0.9.3 → 0.9.4`, commit `8cdac0d2`, 84 files: 83 version carriers plus its own `tasks.md`). The group letters
(A–I, no G) are gh115's. The inventory was re-measured at `df575539` (gh117 archive, already on
`origin/modules`), and what it found differs from gh115 in three ways:

1. **Every version-bearing line is where gh115 left it.** gh116 and gh117 added no line carrying
   the version, no POM entered or left the reactor, and every line number in §3 is identical to
   gh115's. The tracked total is again 83 files: 48 reactor POMs, `rv-android/pom.xml` and 34
   single-token files (a bare `git grep` also hits
   `crylogger/scripts/passwords/xato-net-10-million-passwords.txt`, a wordlist inside the excluded
   crylogger).
2. **The `0.9.4` image tag is now the identity of measurements.** The `estudo02-20260916` campaign
   ran on `phtcosta/rvandroid:0.9.4`, and the E5 composes of the Estudo 3
   (`docker/docker-compose.e5*.yml`) pin `phtcosta/rvandroid:0.9.4@sha256:130f127b5b4c…`. Moving the
   chain to `0.9.5` is what protects those records: after the bump, the production
   `docker/rvandroid/build.sh` writes `0.9.5` and no longer overwrites `0.9.4`. In that script the
   `VERSION` default and the comparison that decides whether `:latest` is also tagged must move
   **together** — changing only the default would silently stop the production build from moving
   `:latest`. The campaign records themselves are **not** edited (§2, excluded).
3. **No change is pending on these files.** gh115 had to wait for #112 and #114; here every path
   in §3 is clean in `git status`, so execution can start right after the artifacts. Other sessions
   do have uncommitted work elsewhere in the tree (dated docs, `experimento-cal/`,
   `experimento-gh104/`, `backup/`), which is why the commit is made by path.

After the bump the local Maven repository (`/home/pedro/desenvolvimento/repository`) still holds the
`0.9.3-SNAPSHOT` and `0.9.4-SNAPSHOT` artifacts. Nothing in the active tree resolves them by that
path once this change is applied; campaign scripts that do (§2, excluded) keep reading the jar
they were written against.

One string already contains `0.9.5` and is unrelated: the PyPI package `retry2==0.9.5` in
`rv-android/uv.lock:2504,2510` (and in `backup/**/poetry.lock`). The residual greps of §4 and §5
therefore match `0\.9\.5-SNAPSHOT|:0\.9\.5`, never a bare `0\.9\.5`.

## 2. Scope

**Groups:**
- **Group A — Reactor POMs (via plugin):** `mvn versions:set` from the reactor root reaches 48 POMs.
- **Group B — `rv-android/pom.xml` (explicit):** commented out of the reactor (`pom.xml:73`), so the
  plugin does not reach it. Only `<parent><version>` changes; the module inherits its version.
- **Group C — Runtime config scripts** (`-SNAPSHOT` carriers, Maven jar paths): 3 files.
- **Group D — Docker chain** (bare tag `0.9.4` → `0.9.5`): build scripts, Dockerfile `FROM`, run
  helpers, the canonical compose and the two general-purpose compose files gh84 and gh115 also bumped.
- **Group E — Python image defaults** (bare tag): 4 files.
- **Group F — Test asserts** (`-SNAPSHOT` jar names): 2 files, then run the suites.
- **Group H — Source version string:** `InstrumentationCli.java` `@Command(version=...)`.
- **Group I — Current docs** that state the project version or the current image tag.

**Excluded (do NOT touch):**
- **Campaign and experiment material**, pinned to the image or jars they ran against:
  `experimento-*/` — among them `experimento-estudo02-20260916/` (22 hits in 11 files, including its
  own composes `docker-compose.estudo02-20260916{,-smoke}.yml:15`, `scripts/campanha.env:35,37` and
  `scripts/repair.py:9`), `experimento-cal`, `-comp162`, `-gh104`, `-estudo02`, `-e3-decisiva`,
  `-20260721`; `docker/docker-compose.estudo02.yml` and `docker/docker-compose.estudo02smoke.yml`
  (`0.9.3`); the ten **untracked** E5 composes `docker/docker-compose.{e5m1,e5m5,e5m5smoke,e5smoke,
  e5bm1,e5bm5,e5bsmoke,e5bsmoke5,e5c,e5csmoke}.yml` (digest-pinned `0.9.4`, written by the Estudo 3
  sessions; being untracked, the `git grep` of §4 does not list them, and the commit by path cannot
  take them); the untracked `cal163*`, `cmp163*` and `gh104` composes (`0.9.3-*` tags);
  `scripts/e3_preflight_instrument.py:36-37` (Estudo 3 Phase B preflight, asserts properties of the
  `rvsec-core-0.9.3-SNAPSHOT.jar`).
- **Records of what was measured:** dated docs `rv-android/docs/YYYYMMDD_*.md` (among them the
  untracked `docs/20260924_e5m1.md:5,63` and `docs/20260924_e5m5.md:5,63`, "**Imagem:**
  phtcosta/rvandroid:0.9.4"); `rv-android/data/**` (`data/gh104/README.md:56` quotes the title of
  commit `4153939`; rewriting it would falsify a commit reference); ADRs
  (`docs/adr/0006-*.md:38`, "the AVD baked into `rvsec_android:0.9.3`");
  `openspec/specs/calibration-control/spec.md:10` (the fixed campaign image and its ID);
  `openspec/specs/core/spec.md:1130` (the AVD of the `0.9.3` image — gh115 recorded it at l.1110);
  `docs/architecture/subsystem-rv-experiment.md:552` (historical "bumped to image 0.9.1");
  `docker/tools/Dockerfile:12` (comment naming the `0.9.3-jca-android` image that wove the corpus).
- **Working and archival material:** `rv-android/audit/**`, `rv-android/docs/handoff/**`,
  `rv-android/backup/**`, `openspec/changes/**`.
- **Own-version reactors:** crylogger (`0.3.0`), docker/mop (`1.2.8`), rv-monitor docs/installer
  (`1.4-SNAPSHOT`), teste-sootup (`0.6.0-SNAPSHOT`).
- `rvsec/rvsec-android/rvsmart/dependency-reduced-pom.xml` (shade output, gitignored, regenerated on build).
- `rv-android/uv.lock` and `backup/**/poetry.lock` (`retry2==0.9.5`, a third-party package).

## 3. File Inventory

Paths are relative to the `rvsec/` repository root. Line numbers measured at `df575539`
(2026-10-05); they match gh115's exactly.

### Group A — Reactor POMs (via `versions-maven-plugin`)

From the repository root, with JDK 21 and offline:
```
mvn -o versions:set -DnewVersion=0.9.5-SNAPSHOT -DgenerateBackupPoms=true
```

| File | Action | Detail |
|------|--------|--------|
| `pom.xml` (`rvsec-parent`, own `<version>` at l.8) | `versions:set` | `0.9.4-SNAPSHOT` → `0.9.5-SNAPSHOT` |
| `rv-monitor/pom.xml`, `rv-monitor/rv-monitor/pom.xml`, `rv-monitor/rv-monitor-rt/pom.xml`, `rv-monitor/logicrepository/pom.xml` | `versions:set` | same |
| `rv-monitor/plugins_logicrepository/pom.xml` + `{cfg,ere,fsm,ltl,pda,po,ptcaret,ptltl,srs,tfsm}/pom.xml` | `versions:set` | same (11 POMs) |
| `javamop/pom.xml`, `mop-maven-plugin/pom.xml` | `versions:set` | same |
| `rvsec/pom.xml`, `rvsec/rvsec-mop/pom.xml`, `rvsec/rvsec-mop-extractor/pom.xml`, `rvsec/rvsec-core/pom.xml`, `rvsec/rvsec-logger-csv/pom.xml`, `rvsec/rvsec-agent/pom.xml` | `versions:set` | same |
| `rvsec/rvsec-crysl/pom.xml` + `rvsec-crysl-{core,mop,crysl}/pom.xml` | `versions:set` | same (4 POMs) |
| `rvsec/rvsec-android/pom.xml`, `rvsec-apk/pom.xml`, `rvsec-logger-logcat/pom.xml`, `rvsec-frame-computer/pom.xml`, `rvsmart/pom.xml` | `versions:set` | same |
| `rvsec/rvsec-android/rvsec-gator/pom.xml` + `{commons,sootandroid,client}/pom.xml` | `versions:set` | same (4 POMs) |
| `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/pom.xml` + `{advice-emitter,cli,coverage-weaver,descriptor-reader,dex-mutator,grammar-tests,monitor-builder,multidex-merger,pointcut-engine,validator}/pom.xml` | `versions:set` | same (11 POMs) |

Total: 48 POMs, each with exactly one occurrence (47 `<parent><version>` plus the root's own
`<version>`). No dependency pins the version literally — intra-reactor references use
`${project.version}`. `rvsec-crysl` overrides `guava.version` in its own parent; `versions:set`
does not touch properties, so the override is unaffected.

### Group B — `rv-android/pom.xml` (explicit)

| File | Action | Detail |
|------|--------|--------|
| `rv-android/pom.xml:10` | Edit | `<parent><version>` `0.9.4-SNAPSHOT` → `0.9.5-SNAPSHOT` (module has no own `<version>`) |

### Group C — Runtime config scripts (`-SNAPSHOT` carriers)

| File | Action | Detail |
|------|--------|--------|
| `configure.sh:13` | Edit | `RV_MONITOR_VERSION=0.9.4-SNAPSHOT` → `0.9.5-SNAPSHOT` |
| `rvsec/config.sh:13` | Edit | `RV_MONITOR_VERSION=0.9.4-SNAPSHOT` → `0.9.5-SNAPSHOT` |
| `rv-android/scripts/run_phase5_validators.sh:80` | Edit | `validator-0.9.4-SNAPSHOT.jar` → `validator-0.9.5-SNAPSHOT.jar` |

### Group D — Docker chain (bare tag `0.9.4` → `0.9.5`)

| File | Action | Detail |
|------|--------|--------|
| `build_docker_image.sh:12` | Edit | `IMAGE_TAG="0.9.4"` → `"0.9.5"` |
| `rv-android/docker/base/build.sh:5,15` | Edit | `VERSION=0.9.4` + push comment → `0.9.5` |
| `rv-android/docker/android/build.sh:5,15` | Edit | `VERSION=0.9.4` + push comment → `0.9.5` |
| `rv-android/docker/tools/build.sh:5,15` | Edit | `VERSION=0.9.4` + push comment → `0.9.5` |
| `rv-android/docker/rvandroid/build.sh:10,12,19,20,21,23,28` | Edit | `VERSION="${VERSION:-0.9.4}"` (l.23) **and** `if [ "$VERSION" = "0.9.4" ]; then TAG_LATEST=1` (l.28) → `0.9.5`; header comments l.10, l.12, l.19 → `0.9.5`; campaign-tag examples l.20–21 `0.9.4-gh111` → `0.9.5-gh111` |
| `rv-android/docker/rvandroid_dev/build.sh:3` | Edit | `VERSION=0.9.4` → `0.9.5` |
| `rv-android/docker/android/Dockerfile:1` | Edit | `FROM phtcosta/rvsec_base:0.9.4` → `0.9.5` |
| `rv-android/docker/tools/Dockerfile:1` | Edit | `FROM phtcosta/rvsec_android:0.9.4` → `0.9.5` (l.12 comment excluded) |
| `rv-android/docker/rvandroid/Dockerfile:1` | Edit | `FROM phtcosta/rvandroid_tools:0.9.4` → `0.9.5` |
| `rv-android/docker/rvandroid_dev/Dockerfile:1` | Edit | `FROM phtcosta/rvandroid_tools:0.9.4` → `0.9.5` |
| `rv-android/docker/base/run.sh:3` | Edit | `rvsec_base:0.9.4` → `0.9.5` |
| `rv-android/docker/android/run.sh:3` | Edit | `rvsec_android:0.9.4` → `0.9.5` |
| `rv-android/docker/tools/run.sh:17,47` | Edit | `rvandroid_tools:0.9.4` (command + comment) → `0.9.5` |
| `rv-android/docker/rvandroid/run.sh:3` | Edit | `rvandroid:0.9.4` → `0.9.5` |
| `rv-android/docker/docker-compose.yml:20` | Edit | `image: phtcosta/rvandroid:0.9.4` → `0.9.5` |
| `rv-android/docker/docker-compose.gh80.yml:7,11,24` | Edit | `image:` + two comments → `0.9.5` |
| `rv-android/docker/docker-compose.dexlib2-validation.template.yml:6,21,34,55` | Edit | two `image:` + two comments → `0.9.5` |

Because every `FROM` moves, building layer 4 at `0.9.5` requires layers 1–3 (`rvsec_base`,
`rvsec_android`, `rvandroid_tools`) to be built at `0.9.5` first. Building images is not part of
this change.

### Group E — Python image defaults (bare tag)

| File | Action | Detail |
|------|--------|--------|
| `rv-android/scripts/baseline_docker.py:252-253` | Edit | `default` + help → `phtcosta/rvandroid:0.9.5` |
| `rv-android/scripts/preprocess_docker.py:271-272` | Edit | `default` + help → `0.9.5` |
| `rv-android/scripts/calibration_orchestrator.py:584-585` | Edit | `default` + help → `0.9.5` |
| `rv-android/.claude/skills/rv-experiment-compare/scripts/gen_compare.py:367` | Edit | `--image` default → `phtcosta/rvandroid:0.9.5` |

### Group F — Test asserts (`-SNAPSHOT` jar names)

| File | Action | Detail |
|------|--------|--------|
| `rv-android/modules/rv-instrumentation-core/tests/test_instrumenter.py:97-99` | Edit | `rv-monitor-rt`, `rvsec-core`, `rvsec-logger-logcat` `-0.9.4-SNAPSHOT.jar` → `-0.9.5-SNAPSHOT.jar` |
| `rv-android/modules/rv-instrumentation-dexlib2/tests/test_dexlib_instrumentation.py:613-615,623-625,657-659,671-673` | Edit | same trio × 4 blocks → `-0.9.5-SNAPSHOT.jar` |

### Group H — Source version string

| File | Action | Detail |
|------|--------|--------|
| `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/cli/src/main/java/br/unb/cic/rv/cli/InstrumentationCli.java:34` | Edit | `version = "0.9.4-SNAPSHOT"` → `"0.9.5-SNAPSHOT"` |

### Group I — Current docs

| File | Action | Detail |
|------|--------|--------|
| `CLAUDE.md:4` | Edit | `rvsec-parent:0.9.4-SNAPSHOT` → `0.9.5-SNAPSHOT` |
| `rvsec/rvsec-android/CLAUDE.md:7` | Edit | `0.9.4-SNAPSHOT` → `0.9.5-SNAPSHOT` |
| `rvsec/rvsec-mop/CLAUDE.md:26` | Edit | `rvsec-mop-0.9.4-SNAPSHOT.jar` → `rvsec-mop-0.9.5-SNAPSHOT.jar` |
| `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/architecture.md:34,56` | Edit | `0.9.4-SNAPSHOT` → `0.9.5-SNAPSHOT` |
| `rv-android/docs/architecture/subsystem-rv-experiment.md:181,310,1284,1320` | Edit | current image-chain refs `rvandroid:0.9.4` → `0.9.5` (l.552 excluded) |
| `rv-android/openspec/specs/tools/spec.md:522` | Edit | `phtcosta/rvandroid_tools:0.9.4` → `0.9.5` |
| `rv-android/.claude/skills/rv-experiment-compare/SKILL.md:53` | Edit | `(default 0.9.4)` → `0.9.5` |

## 4. Execution Order

1. **Prerequisite gate (main window).** `git status --porcelain -- <every path in §3>` is empty.
   Then re-measure the tracked inventory from the repository root:
   ```
   git grep -nE '0\.9\.4' -- ':!**/openspec/changes/**' ':!crylogger/**' \
     | grep -vE '^rv-android/(backup|experimento-[^/]*|audit|docs/handoff|data)/'
   ```
   Every hit must be either a row of §3 or an item of the §2 exclusion list. A hit that is
   neither — a new test, a new POM, a new doc — is added to §3 before any edit.
2. **Group A (main window)** — `versions:set`, then `git diff --stat` shows only the 48 reactor
   POMs. It runs alone and first so the plugin's diff is validated in isolation; it also shares no
   file with any later group.
3. **Groups B–I in parallel (subagents).** 35 files — the 34 single-token files plus `rv-android/pom.xml` —, all single-token substitutions on
   disjoint files. Following `docs/WORKFLOW.md` §5 (20+ files, 3+ independent groups, 3–15 files
   per subagent, grouped by locality), five subagents run at once:
   - **S1 — Groups B + C + H** (5 files: `rv-android/pom.xml`, `configure.sh`, `rvsec/config.sh`,
     `run_phase5_validators.sh`, `InstrumentationCli.java`).
   - **S2 — Group D, build side** (10 files: `build_docker_image.sh`, the five `build.sh`, the four
     Dockerfiles). Holds `docker/rvandroid/build.sh`, whose l.23 and l.28 must move together.
   - **S3 — Group D, run side** (7 files: the four `run.sh`, the three general-purpose composes).
     Must not open any `docker-compose.estudo02*.yml` or `docker-compose.e5*.yml`.
   - **S4 — Groups E + F** (6 files), then the pytest of the two Group F files.
   - **S5 — Group I** (7 docs).
   Each subagent receives its rows of §3, the exclusions of §2 that sit next to its files, and the
   rule that it edits only the listed lines. None of them builds, commits or runs `git add`.
4. **Verification (main window)** — `versions:commit`, full reactor build, pytest, residual greps
   (§5). The reactor build is serialized: it runs once, after every subagent has returned.
5. **Commit by path** (`git commit -- <paths>`), message `chore(gh118): bump 0.9.4-SNAPSHOT →
   0.9.5-SNAPSHOT (reactor, rv-android, scripts, cadeia Docker 0.9.5) (closes #118)`. The
   repository is shared with other sessions, so nothing staged by them may enter this commit.
6. **Archive** via `/opsx:archive` (`--skip-specs`). Close #118 by hand after ticking its
   criteria: `closes` does not close issues outside the default branch (`master`). No push: the
   user pushes.

## 5. Acceptance Criteria

- [ ] 49 POMs at `0.9.5-SNAPSHOT` (48 reactor + `rv-android/pom.xml`); `git diff --stat` shows no change under `backup/`, `docs/handoff/`, crylogger, docker/mop, rv-monitor docs/installer, teste-sootup
- [ ] Group C scripts, Group F asserts, Group H CLI version and Group I docs at `0.9.5-SNAPSHOT` / `0.9.5`
- [ ] Group D Docker chain and Group E Python defaults at `0.9.5`; in `docker/rvandroid/build.sh`, the `VERSION` default (l.23) and the `TAG_LATEST` comparison (l.28) hold the same value
- [ ] `mvn -o versions:commit` run; no `*.versionsBackup` file left
- [ ] From the repository root, with JDK 21 (`JAVA_HOME=$HOME/.sdkman/candidates/java/21.0.12-tem`): `mvn -o clean install -DskipMopAgent -DskipTests` → EXIT=0, 48 modules built, and `rvsec-parent/0.9.5-SNAPSHOT` present in the local Maven repository
- [ ] `cd rv-android && uv run pytest modules/rv-instrumentation-core/tests/test_instrumenter.py modules/rv-instrumentation-dexlib2/tests/test_dexlib_instrumentation.py --import-mode=importlib -o "addopts="` → 0 failed
- [ ] The §4 step 1 grep, re-run after the edits, returns only §2 exclusions
- [ ] `git grep -nE '0\.9\.5-SNAPSHOT|:0\.9\.5'` hits no excluded path (campaign composes, `experimento-*`, `data/**`, dated docs, ADRs, the two measurement-record specs), and the ten untracked `docker/docker-compose.e5*.yml` still read `0.9.4@sha256:130f127b5b4c…`
- [ ] The commit contains only §3 paths (`git show --stat HEAD` lists 84 files: the 83 §3 paths plus this change's `tasks.md`)
