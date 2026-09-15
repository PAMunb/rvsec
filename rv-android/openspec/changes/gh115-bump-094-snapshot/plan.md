# Change Plan: Bump 0.9.3-SNAPSHOT → 0.9.4-SNAPSHOT (branch `modules`)

**Date**: 2026-09-15
**Track**: Quick Path
**Priority**: Medium
**GitHub Issue**: [#115](https://github.com/PAMunb/rvsec/issues/115)
**PRD Reference**: N/A (maintenance chore; no behavior change)
**Domains**: instrumentation (test asserts, dexlib2 CLI version string), build/infra (reactor POMs, runtime scripts, Docker chain — not mapped to a spec domain)

## 1. Context

The project moves from `0.9.3-SNAPSHOT` to `0.9.4-SNAPSHOT` on the `modules` branch, and the
Docker image chain moves from tag `0.9.3` to `0.9.4`. POMs, runtime jar-path scripts, test
jar-name asserts and the CLI version string carry the `-SNAPSHOT` suffix; Docker tags use the
bare form. **Nothing is done on `master`**: there is no release cut, no branch operation and no
tag.

This repeats two archived changes: **gh76-bump-092-snapshot** (`0.9.1-SNAPSHOT → 0.9.2-SNAPSHOT`)
and the `modules` pass of **gh84-release-092** (`0.9.2-SNAPSHOT → 0.9.3-SNAPSHOT`, commit
`41539390`, 82 files). The group structure (A–I) is kept so the three changes read side by side.
Four facts differ from gh84:

1. **The reactor has 48 POMs, not 45.** The `rvsec-crysl` subtree added four (`rvsec-crysl`,
   `-core`, `-mop`, `-crysl`); `rvsec-mop-defsuses` was retired to
   `rv-android/backup/gh105-retired/`. Every one of the 48 carries exactly one `0.9.3-SNAPSHOT`
   occurrence — its own `<version>` or its `<parent><version>` — and no dependency pins the
   version literally, so `versions:set` covers them completely.
2. **`docker/rvandroid/build.sh` is parametrized.** The version appears as the `VERSION` default
   and again inside the comparison that decides whether `:latest` is also tagged. Changing only
   the default would silently stop the production build from moving `:latest`.
3. **The `0.9.3` image tag is the identity of measurements.** The estudo02 campaign ran on
   `phtcosta/rvandroid:0.9.3` (`89462651fe15`), the calibration spec pins it, and several campaign
   directories reference it. Moving the chain to `0.9.4` is what protects those records: after the
   bump, the production `build.sh` writes `0.9.4` and no longer overwrites `0.9.3`. Campaign pins
   themselves are **not** edited (§2, excluded).
4. **Execution is blocked on #112 and #114.** Both touch files in this inventory
   (`InstrumentationCli.java`, the dexlib2 `architecture.md`, the dexlib2 test file). #112 is
   committed (`8edf9396`, `30568f09`); #114 is at proposal stage. This change is written now and
   applied only after #114 is committed, so the bump neither sweeps uncommitted work into its
   commit nor lands mid-way through a change that is still editing the same lines. Line numbers
   below were measured at `30568f09` and **must be re-measured at apply time** (§4, step 1): #114
   will shift them and may add new version-bearing lines (new tests with jar names, new POMs).

After the bump the local Maven repository still holds the `0.9.3-SNAPSHOT` artifacts. Nothing in
the active tree resolves them by that path once this change is applied; campaign scripts that do
(§2, excluded) keep reading the jar they were written against.

## 2. Scope

**Groups:**
- **Group A — Reactor POMs (via plugin):** `mvn versions:set` from the reactor root reaches 48 POMs.
- **Group B — `rv-android/pom.xml` (explicit):** commented out of the reactor (`pom.xml:73`), so the
  plugin does not reach it. Only `<parent><version>` changes; the module inherits its version.
- **Group C — Runtime config scripts** (`-SNAPSHOT` carriers, Maven jar paths): 3 files.
- **Group D — Docker chain** (bare tag `0.9.3` → `0.9.4`): build scripts, Dockerfile `FROM`, run
  helpers, the canonical compose and the two general-purpose compose files gh84 also bumped.
- **Group E — Python image defaults** (bare tag): 4 files.
- **Group F — Test asserts** (`-SNAPSHOT` jar names): 2 files, then run the suites.
- **Group H — Source version string:** `InstrumentationCli.java` `@Command(version=...)`.
- **Group I — Current docs** that state the project version or the current image tag.

**Excluded (do NOT touch):**
- **Campaign and experiment material**, pinned to the image or jars they ran against:
  `experimento-*/` (among them `experimento-cal`, `-comp162`, `-gh104`, `-estudo02`,
  `-e3-decisiva`, `-20260721`); `docker/docker-compose.estudo02.yml` and
  `docker/docker-compose.estudo02smoke.yml`; every other campaign compose under `docker/` (none of
  them carries `0.9.3` today); `scripts/e3_preflight_instrument.py:36-37` (Estudo 3 Phase B
  preflight, asserts properties of the `rvsec-core-0.9.3-SNAPSHOT.jar` in the local Maven
  repository).
- **Records of what was measured:** dated docs `rv-android/docs/YYYYMMDD_*.md`; ADRs
  (`docs/adr/0006-*.md:38`, "the AVD baked into `rvsec_android:0.9.3`");
  `openspec/specs/calibration-control/spec.md:10` (the fixed campaign image and its ID);
  `openspec/specs/core/spec.md:1110` (the AVD of the `0.9.3` image);
  `docs/architecture/subsystem-rv-experiment.md:552` (historical "bumped to image 0.9.1");
  `docker/tools/Dockerfile:12` (comment naming the `0.9.3-jca-android` image that wove the corpus).
- **Working and archival material:** `rv-android/audit/**`, `rv-android/docs/handoff/**` (includes
  four `v10/rvsec-crysl` POM copies at `0.9.3-SNAPSHOT`), `rv-android/backup/**` (includes
  `gh105-retired/rvsec-mop-defsuses/pom.xml` at `0.9.3-SNAPSHOT` and four POMs at
  `0.9.0-SNAPSHOT`), `openspec/changes/**`.
- **Own-version reactors:** crylogger (`0.3.0`), docker/mop (`1.2.8`), rv-monitor docs/installer
  (`1.4-SNAPSHOT`), teste-sootup (`0.6.0`).
- `rvsec/rvsec-android/rvsmart/dependency-reduced-pom.xml` (shade output, regenerated on build).

## 3. File Inventory

Paths are relative to the `rvsec/` repository root. Line numbers measured at `30568f09`
(2026-09-15); re-measure before applying.

### Group A — Reactor POMs (via `versions-maven-plugin`)

From the repository root:
```
mvn versions:set -DnewVersion=0.9.4-SNAPSHOT -DgenerateBackupPoms=true
```

| File | Action | Detail |
|------|--------|--------|
| `pom.xml` (`rvsec-parent`) | `versions:set` | `0.9.3-SNAPSHOT` → `0.9.4-SNAPSHOT` |
| `rv-monitor/pom.xml`, `rv-monitor/rv-monitor/pom.xml`, `rv-monitor/rv-monitor-rt/pom.xml`, `rv-monitor/logicrepository/pom.xml` | `versions:set` | same |
| `rv-monitor/plugins_logicrepository/pom.xml` + `{cfg,ere,fsm,ltl,pda,po,ptcaret,ptltl,srs,tfsm}/pom.xml` | `versions:set` | same (11 POMs) |
| `javamop/pom.xml`, `mop-maven-plugin/pom.xml` | `versions:set` | same |
| `rvsec/pom.xml`, `rvsec/rvsec-mop/pom.xml`, `rvsec/rvsec-mop-extractor/pom.xml`, `rvsec/rvsec-core/pom.xml`, `rvsec/rvsec-logger-csv/pom.xml`, `rvsec/rvsec-agent/pom.xml` | `versions:set` | same |
| `rvsec/rvsec-crysl/pom.xml` + `rvsec-crysl-{core,mop,crysl}/pom.xml` | `versions:set` | same (4 POMs) |
| `rvsec/rvsec-android/pom.xml`, `rvsec-apk/pom.xml`, `rvsec-logger-logcat/pom.xml`, `rvsec-frame-computer/pom.xml`, `rvsmart/pom.xml` | `versions:set` | same |
| `rvsec/rvsec-android/rvsec-gator/pom.xml` + `{commons,sootandroid,client}/pom.xml` | `versions:set` | same (4 POMs) |
| `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/pom.xml` + `{advice-emitter,cli,coverage-weaver,descriptor-reader,dex-mutator,grammar-tests,monitor-builder,multidex-merger,pointcut-engine,validator}/pom.xml` | `versions:set` | same (11 POMs) |

Total: 48 POMs. `rvsec-crysl` overrides `guava.version` in its own parent; `versions:set` does not
touch properties, so the override is unaffected.

### Group B — `rv-android/pom.xml` (explicit)

| File | Action | Detail |
|------|--------|--------|
| `rv-android/pom.xml` | Edit | `<parent><version>` `0.9.3-SNAPSHOT` → `0.9.4-SNAPSHOT` (module has no own `<version>`) |

### Group C — Runtime config scripts (`-SNAPSHOT` carriers)

| File | Action | Detail |
|------|--------|--------|
| `configure.sh:13` | Edit | `RV_MONITOR_VERSION=0.9.3-SNAPSHOT` → `0.9.4-SNAPSHOT` |
| `rvsec/config.sh:13` | Edit | `RV_MONITOR_VERSION=0.9.3-SNAPSHOT` → `0.9.4-SNAPSHOT` |
| `rv-android/scripts/run_phase5_validators.sh:80` | Edit | `validator-0.9.3-SNAPSHOT.jar` → `validator-0.9.4-SNAPSHOT.jar` |

### Group D — Docker chain (bare tag `0.9.3` → `0.9.4`)

| File | Action | Detail |
|------|--------|--------|
| `build_docker_image.sh:12` | Edit | `IMAGE_TAG="0.9.3"` → `"0.9.4"` |
| `rv-android/docker/base/build.sh:5,15` | Edit | `VERSION=0.9.3` + push comment → `0.9.4` |
| `rv-android/docker/android/build.sh:5,15` | Edit | `VERSION=0.9.3` + push comment → `0.9.4` |
| `rv-android/docker/tools/build.sh:5,15` | Edit | `VERSION=0.9.3` + push comment → `0.9.4` |
| `rv-android/docker/rvandroid/build.sh:10,12,19,20,21,23,28` | Edit | `VERSION` default (l.23) **and** the `TAG_LATEST` comparison (l.28) → `0.9.4`; header comments l.10, l.12, l.19 → `0.9.4`; campaign-tag examples l.20–21 `0.9.3-gh111` → `0.9.4-gh111` |
| `rv-android/docker/rvandroid_dev/build.sh:3` | Edit | `VERSION=0.9.3` → `0.9.4` |
| `rv-android/docker/android/Dockerfile:1` | Edit | `FROM phtcosta/rvsec_base:0.9.3` → `0.9.4` |
| `rv-android/docker/tools/Dockerfile:1` | Edit | `FROM phtcosta/rvsec_android:0.9.3` → `0.9.4` (l.12 comment excluded) |
| `rv-android/docker/rvandroid/Dockerfile:1` | Edit | `FROM phtcosta/rvandroid_tools:0.9.3` → `0.9.4` |
| `rv-android/docker/rvandroid_dev/Dockerfile:1` | Edit | `FROM phtcosta/rvandroid_tools:0.9.3` → `0.9.4` |
| `rv-android/docker/base/run.sh:3` | Edit | `rvsec_base:0.9.3` → `0.9.4` |
| `rv-android/docker/android/run.sh:3` | Edit | `rvsec_android:0.9.3` → `0.9.4` |
| `rv-android/docker/tools/run.sh:17,47` | Edit | `rvandroid_tools:0.9.3` (command + comment) → `0.9.4` |
| `rv-android/docker/rvandroid/run.sh:3` | Edit | `rvandroid:0.9.3` → `0.9.4` |
| `rv-android/docker/docker-compose.yml:20` | Edit | `image: phtcosta/rvandroid:0.9.3` → `0.9.4` |
| `rv-android/docker/docker-compose.gh80.yml:7,11,24` | Edit | `image:` + two comments → `0.9.4` |
| `rv-android/docker/docker-compose.dexlib2-validation.template.yml:6,21,34,55` | Edit | two `image:` + two comments → `0.9.4` |

Because every `FROM` moves, building layer 4 at `0.9.4` requires layers 1–3 (`rvsec_base`,
`rvsec_android`, `rvandroid_tools`) to be built at `0.9.4` first. Building images is not part of
this change.

### Group E — Python image defaults (bare tag)

| File | Action | Detail |
|------|--------|--------|
| `rv-android/scripts/baseline_docker.py:252-253` | Edit | `default` + help → `phtcosta/rvandroid:0.9.4` |
| `rv-android/scripts/preprocess_docker.py:271-272` | Edit | `default` + help → `0.9.4` |
| `rv-android/scripts/calibration_orchestrator.py:584-585` | Edit | `default` + help → `0.9.4` |
| `rv-android/.claude/skills/rv-experiment-compare/scripts/gen_compare.py:346` | Edit | `--image` default → `phtcosta/rvandroid:0.9.4` |

### Group F — Test asserts (`-SNAPSHOT` jar names)

| File | Action | Detail |
|------|--------|--------|
| `rv-android/modules/rv-instrumentation-core/tests/test_instrumenter.py:97-99` | Edit | `rv-monitor-rt`, `rvsec-core`, `rvsec-logger-logcat` `-0.9.3-SNAPSHOT.jar` → `-0.9.4-SNAPSHOT.jar` |
| `rv-android/modules/rv-instrumentation-dexlib2/tests/test_dexlib_instrumentation.py:613-615,623-625,657-659,671-673` | Edit | same trio × 4 blocks → `-0.9.4-SNAPSHOT.jar` |

### Group H — Source version string

| File | Action | Detail |
|------|--------|--------|
| `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/cli/src/main/java/br/unb/cic/rv/cli/InstrumentationCli.java:34` | Edit | `version = "0.9.3-SNAPSHOT"` → `"0.9.4-SNAPSHOT"` |

### Group I — Current docs

| File | Action | Detail |
|------|--------|--------|
| `CLAUDE.md:4` | Edit | `rvsec-parent:0.9.3-SNAPSHOT` → `0.9.4-SNAPSHOT` |
| `rvsec/rvsec-android/CLAUDE.md:7` | Edit | `0.9.3-SNAPSHOT` → `0.9.4-SNAPSHOT` |
| `rvsec/rvsec-mop/CLAUDE.md:26` | Edit | `rvsec-mop-0.9.3-SNAPSHOT.jar` → `rvsec-mop-0.9.4-SNAPSHOT.jar` |
| `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/architecture.md:34,56` | Edit | `0.9.3-SNAPSHOT` → `0.9.4-SNAPSHOT` |
| `rv-android/docs/architecture/subsystem-rv-experiment.md:181,310,1284,1320` | Edit | current image-chain refs `rvandroid:0.9.3` → `0.9.4` (l.552 excluded) |
| `rv-android/openspec/specs/tools/spec.md:522` | Edit | `phtcosta/rvandroid_tools:0.9.3` → `0.9.4` |
| `rv-android/.claude/skills/rv-experiment-compare/SKILL.md:53` | Edit | `(default 0.9.3)` → `0.9.4` |

## 4. Execution Order

1. **Prerequisite gate.** #114 committed (and #112, already committed). Working tree clean for
   every file in §3. Then re-measure the inventory from the repository root:
   ```
   git grep -nE '0\.9\.3' -- ':!**/openspec/changes/**' ':!crylogger/**' \
     | grep -vE '^rv-android/(backup|experimento-[^/]*|audit|docs/handoff)/'
   ```
   Every hit must be either a row of §3 (possibly at a shifted line) or an item of the §2
   exclusion list. A hit that is neither — a new test, a new POM, a new doc — is added to §3
   before any edit.
2. **Group A** (`versions:set`), then `git diff --stat` shows only the 48 reactor POMs.
3. **Groups B, C, D, E, F, H, I** — disjoint files, plain string edits. Around 35 files outside
   the plugin, all single-token substitutions: done sequentially, without subagents (WORKFLOW.md
   §5 — the bulk is one plugin command and the rest are one-line edits).
4. **Verification** — `versions:commit`, full reactor build, pytest, residual grep (§5).
5. **Commit by path** (`git commit -- <paths>`), message `chore(gh115): bump 0.9.3-SNAPSHOT →
   0.9.4-SNAPSHOT (reactor, rv-android, scripts, Docker chain 0.9.4) (closes #115)`. The repository
   is shared with other sessions, so nothing staged by them may enter this commit.
6. **Archive** via `/opsx:archive`. No push: the user pushes.

## 5. Acceptance Criteria

- [ ] 49 POMs at `0.9.4-SNAPSHOT` (48 reactor + `rv-android/pom.xml`); `git diff --stat` shows no change under `backup/`, `docs/handoff/`, crylogger, docker/mop, rv-monitor docs/installer, teste-sootup
- [ ] Group C scripts, Group F asserts, Group H CLI version and Group I docs at `0.9.4-SNAPSHOT` / `0.9.4`
- [ ] Group D Docker chain and Group E Python defaults at `0.9.4`; in `docker/rvandroid/build.sh`, `VERSION` default and the `TAG_LATEST` comparison hold the same value
- [ ] `mvn versions:commit` run; no `*.versionsBackup` file left
- [ ] From the repository root, with JDK 21 (`JAVA_HOME=$HOME/.sdkman/candidates/java/21.0.12-tem`): `mvn clean install -DskipMopAgent -DskipTests` → EXIT=0, 48 modules built
- [ ] `cd rv-android && uv run pytest modules/rv-instrumentation-core/tests/test_instrumenter.py modules/rv-instrumentation-dexlib2/tests/test_dexlib_instrumentation.py --import-mode=importlib -o "addopts="` → 0 failed
- [ ] The §4 step 1 grep, re-run after the edits, returns only §2 exclusions
- [ ] `git grep -n '0\.9\.4'` hits no excluded path (campaign composes, `experimento-*`, dated docs, ADRs, the two measurement-record specs)
- [ ] The commit contains only §3 paths (`git show --stat HEAD`)
