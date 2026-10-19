# Change Plan: Bump 0.9.5-SNAPSHOT → 0.9.6-SNAPSHOT (branch `modules`)

**Date**: 2026-10-19
**Track**: Quick Path
**Priority**: Medium
**GitHub Issue**: none — the author chose to run this change without an issue (2026-10-19); the
change name carries `gh-tbd` and commits reference the change name instead of `#N`
**PRD Reference**: N/A (maintenance chore; no behavior change)
**Domains**: instrumentation (test asserts, dexlib2 CLI version string), build/infra (reactor POMs, runtime scripts, Docker chain — not mapped to a spec domain)

## 1. Context

The project moves from `0.9.5-SNAPSHOT` to `0.9.6-SNAPSHOT` on the `modules` branch, and the
Docker image chain moves from tag `0.9.5` to `0.9.6`. POMs, runtime jar-path scripts, test
jar-name asserts and the CLI version string carry the `-SNAPSHOT` suffix; Docker tags use the bare
form. **Nothing is done on `master`**: there is no release cut, no branch operation and no tag.

This repeats four archived changes so they read side by side: **gh76-bump-092-snapshot**
(`0.9.1 → 0.9.2`), the `modules` pass of **gh84-release-092** (`0.9.2 → 0.9.3`),
**gh115-bump-094-snapshot** (`0.9.3 → 0.9.4`, commit `8cdac0d2`) and
**gh118-bump-095-snapshot** (`0.9.4 → 0.9.5`, commit `347d1ceb`, 84 files: 83 version carriers
plus its own `tasks.md`). The group letters (A–I, no G) and the subagent split S1–S5 are gh118's.
The inventory was re-measured at `3dfd9668` (archive of gh-tbd-gator-distance-paths, two commits
ahead of `origin/modules`), and what it found differs from gh118 in five ways:

1. **One architecture document was renamed and rewritten.** `docs/architecture/subsystem-rv-experiment.md`
   is now `docs/architecture/rv-experiment.md` (commit `ab74a3a8`). It carries seven current
   image-chain references (l.187, 312, 1007, 1010, 1408, 1412, 1478) instead of gh118's four, and
   the historical "bumped to image 0.9.1" line that gh118 excluded (old l.552) no longer exists.
2. **One document entered the inventory.** `docs/architecture/instrumentation-java.md` entered git
   in `daae6c73`; its l.35 states the current dexlib2 reactor version. The tracked total is
   therefore **84 files**: 48 reactor POMs, `rv-android/pom.xml` and 35 single-token files.
3. **Two files shifted lines.** In `test_dexlib_instrumentation.py` the four jar-name blocks moved
   from l.613–673 to l.730–790; in `openspec/specs/tools/spec.md` the toolchain reference moved
   from l.522 to l.539. Every other line number is identical to gh118's.
4. **The `0.9.5` image tag is now the identity of measurements.** The e03mini campaign
   (`docker/docker-compose.e03mini{,-a2,-smoke}.yml`, tracked), the e03igg campaigns (seven
   untracked `docker/docker-compose.e03igg*.yml`), the smokes `experimento-smk119/` and
   `experimento-smk124/`, and the dated docs of October (`docs/202610*_*.md`) ran on or cite
   `phtcosta/rvandroid:0.9.5` — the image rebuilt with the Android Emulator pinned to 37.1.11
   (`37efe5ed`). Moving the chain to `0.9.6` is what protects those records: after the bump, the
   production `docker/rvandroid/build.sh` writes `0.9.6` and no longer overwrites `0.9.5`. In that
   script the `VERSION` default and the comparison that decides whether `:latest` is also tagged
   must move **together** — changing only the default would silently stop the production build
   from moving `:latest`. The campaign records themselves are **not** edited (§2, excluded).
5. **Two parallel branches touch three inventory files, on other lines.** The worktree branches
   `isolate-guidance-groups` and `wip/stamp-callback` (both from `modules` @ `37efe5ed`) edit
   `.claude/skills/rv-experiment-compare/SKILL.md`, `.../scripts/gen_compare.py` and
   `docs/architecture/rv-experiment.md`, but none of their hunks touches a version line of §3
   (measured with `git diff -U0` against the merge base). This change edits only `modules`; it
   does not touch those branches or their worktrees, and their later merge is expected to apply
   without a conflict on these lines.

No path of §3 has uncommitted changes (`git status --porcelain` empty at `3dfd9668`). Other
sessions do have uncommitted work elsewhere in the tree (`docker/docker-compose.e03mini.yml`,
`scripts/*`, `experimento-*`, `backup/`, `data/`), which is why the commit is made by path.

After the bump the local Maven repository (`/home/pedro/desenvolvimento/repository`) still holds
the `0.9.3`, `0.9.4` and `0.9.5-SNAPSHOT` artifacts. Nothing in the active tree resolves
`0.9.5-SNAPSHOT` by path once this change is applied; campaign material that does (§2, excluded)
keeps reading the jar it was written against.

One string contains `0.9.5` and is unrelated: the PyPI package `retry2==0.9.5` in
`rv-android/uv.lock:2506,2512` (and in `backup/**/poetry.lock`). No tracked file contains `0.9.6`
today (`git grep -nE '0\.9\.6'`, crylogger excluded, returns nothing), so after the edits a plain
`0\.9\.6` grep lists exactly what this change wrote.

## 2. Scope

**Groups:**
- **Group A — Reactor POMs (via plugin):** `mvn versions:set` from the reactor root reaches 48 POMs.
- **Group B — `rv-android/pom.xml` (explicit):** commented out of the reactor (`pom.xml:73`), so
  the plugin does not reach it. Only `<parent><version>` changes; the module inherits its version.
- **Group C — Runtime config scripts** (`-SNAPSHOT` carriers, Maven jar paths): 3 files.
- **Group D — Docker chain** (bare tag `0.9.5` → `0.9.6`): build scripts, Dockerfile `FROM`, run
  helpers, the canonical compose and the two general-purpose compose files gh84, gh115 and gh118
  also bumped. 17 files.
- **Group E — Python image defaults** (bare tag): 4 files.
- **Group F — Test asserts** (`-SNAPSHOT` jar names): 2 files, then run the suites.
- **Group H — Source version string:** `InstrumentationCli.java` `@Command(version=...)`.
- **Group I — Current docs** that state the project version or the current image tag: 8 files.

**Excluded (do NOT touch):**
- **Campaign and experiment material**, pinned to the image or jars they ran against:
  `experimento-*/` (among them `experimento-smk119/RELATORIO.md`, `experimento-smk124/{README,RELATORIO}.md`
  and `experimento-smk124/docker-compose.yml`, the four tracked files under `experimento-*` that
  cite `0.9.5`); the tracked e03mini composes `docker/docker-compose.e03mini.yml:8-9` (also
  modified by another session), `docker/docker-compose.e03mini-a2.yml:7` and
  `docker/docker-compose.e03mini-smoke.yml:12`; the seven **untracked** e03igg composes
  `docker/docker-compose.{e03igg,e03iggsmk,e03igg2,e03igg2smk,e03igg3,e03igg3smk,e03igg3smk2}.yml`
  (being untracked, the `git grep` of §4 does not list them and the commit by path cannot take
  them); every earlier campaign compose gh118 already excluded (`docker-compose.estudo02*.yml`,
  `docker-compose.e5*.yml`, `cal163*`, `cmp163*`, `gh104`).
- **Records of what was measured:** dated docs `rv-android/docs/YYYYMMDD_*.md` (among them the
  untracked `docs/20261008_gh120_medicoes_pos_corpus.md`, `docs/20261009_e03mini{,-smoke}.md`,
  `docs/20261017_e03igg{,smk}.md`, `docs/20261018_e03igg{,2smk}.md`, `docs/20261019_e03igg{2,3smk}.md`);
  `rv-android/data/**`; ADRs (`docs/adr/**`); the measurement-record lines gh118 excluded
  (`openspec/specs/calibration-control/spec.md`, `openspec/specs/core/spec.md` AVD line,
  `docker/tools/Dockerfile:12` comment, `scripts/e3_preflight_instrument.py`) — none of them carries
  `0.9.5`, so they stay out by not matching.
- **Working and archival material:** `rv-android/audit/**`, `rv-android/docs/handoff/**`,
  `rv-android/backup/**`, `openspec/changes/**`.
- **Own-version reactors:** crylogger (`0.3.0`), docker/mop (`1.2.8`), rv-monitor docs/installer
  (`1.4-SNAPSHOT`), teste-sootup (`0.6.0-SNAPSHOT`).
- `rvsec/rvsec-android/rvsmart/dependency-reduced-pom.xml` (shade output, gitignored, regenerated on build).
- `rv-android/uv.lock` and `backup/**/poetry.lock` (`retry2==0.9.5`, a third-party package).
- The worktrees under `workspace-rv/worktrees-*` and their branches (`isolate-guidance-groups`,
  `wip/stamp-callback`, `wip/gator-*`, `wip/gh120-int`, `wip/instr-stamp`).

## 3. File Inventory

Paths are relative to the `rvsec/` repository root. Line numbers measured at `3dfd9668`
(2026-10-19).

### Group A — Reactor POMs (via `versions-maven-plugin`)

From the repository root, with JDK 21 and offline:
```
mvn -o versions:set -DnewVersion=0.9.6-SNAPSHOT -DgenerateBackupPoms=true
```

| File | Action | Detail |
|------|--------|--------|
| `pom.xml` (`rvsec-parent`, own `<version>` at l.8) | `versions:set` | `0.9.5-SNAPSHOT` → `0.9.6-SNAPSHOT` |
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
| `rv-android/pom.xml:10` | Edit | `<parent><version>` `0.9.5-SNAPSHOT` → `0.9.6-SNAPSHOT` (module has no own `<version>`) |

### Group C — Runtime config scripts (`-SNAPSHOT` carriers)

| File | Action | Detail |
|------|--------|--------|
| `configure.sh:13` | Edit | `RV_MONITOR_VERSION=0.9.5-SNAPSHOT` → `0.9.6-SNAPSHOT` |
| `rvsec/config.sh:13` | Edit | `RV_MONITOR_VERSION=0.9.5-SNAPSHOT` → `0.9.6-SNAPSHOT` |
| `rv-android/scripts/run_phase5_validators.sh:80` | Edit | `validator-0.9.5-SNAPSHOT.jar` → `validator-0.9.6-SNAPSHOT.jar` |

### Group D — Docker chain (bare tag `0.9.5` → `0.9.6`)

| File | Action | Detail |
|------|--------|--------|
| `build_docker_image.sh:12` | Edit | `IMAGE_TAG="0.9.5"` → `"0.9.6"` |
| `rv-android/docker/base/build.sh:5,15` | Edit | `VERSION=0.9.5` + push comment → `0.9.6` |
| `rv-android/docker/android/build.sh:5,15` | Edit | `VERSION=0.9.5` + push comment → `0.9.6` |
| `rv-android/docker/tools/build.sh:5,15` | Edit | `VERSION=0.9.5` + push comment → `0.9.6` |
| `rv-android/docker/rvandroid/build.sh:10,12,19,20,21,23,28` | Edit | `VERSION="${VERSION:-0.9.5}"` (l.23) **and** `if [ "$VERSION" = "0.9.5" ]; then TAG_LATEST=1` (l.28) → `0.9.6`; header comments l.10, l.12, l.19 → `0.9.6`; campaign-tag examples l.20–21 `0.9.5-gh111` → `0.9.6-gh111` |
| `rv-android/docker/rvandroid_dev/build.sh:3` | Edit | `VERSION=0.9.5` → `0.9.6` |
| `rv-android/docker/android/Dockerfile:1` | Edit | `FROM phtcosta/rvsec_base:0.9.5` → `0.9.6` |
| `rv-android/docker/tools/Dockerfile:1` | Edit | `FROM phtcosta/rvsec_android:0.9.5` → `0.9.6` (l.12 comment excluded) |
| `rv-android/docker/rvandroid/Dockerfile:1` | Edit | `FROM phtcosta/rvandroid_tools:0.9.5` → `0.9.6` |
| `rv-android/docker/rvandroid_dev/Dockerfile:1` | Edit | `FROM phtcosta/rvandroid_tools:0.9.5` → `0.9.6` |
| `rv-android/docker/base/run.sh:3` | Edit | `rvsec_base:0.9.5` → `0.9.6` |
| `rv-android/docker/android/run.sh:3` | Edit | `rvsec_android:0.9.5` → `0.9.6` |
| `rv-android/docker/tools/run.sh:17,47` | Edit | `rvandroid_tools:0.9.5` (command + comment) → `0.9.6` |
| `rv-android/docker/rvandroid/run.sh:3` | Edit | `rvandroid:0.9.5` → `0.9.6` |
| `rv-android/docker/docker-compose.yml:20` | Edit | `image: phtcosta/rvandroid:0.9.5` → `0.9.6` |
| `rv-android/docker/docker-compose.gh80.yml:7,11,24` | Edit | two comments + `image:` → `0.9.6` |
| `rv-android/docker/docker-compose.dexlib2-validation.template.yml:6,21,34,55` | Edit | two comments + two `image:` → `0.9.6` |

Because every `FROM` moves, building layer 4 at `0.9.6` requires layers 1–3 (`rvsec_base`,
`rvsec_android`, `rvandroid_tools`) to be built at `0.9.6` first. Building images is not part of
this change; the emulator pin of `37efe5ed` lives in the Dockerfiles and is untouched.

### Group E — Python image defaults (bare tag)

| File | Action | Detail |
|------|--------|--------|
| `rv-android/scripts/baseline_docker.py:252-253` | Edit | `default` + help → `phtcosta/rvandroid:0.9.6` |
| `rv-android/scripts/preprocess_docker.py:271-272` | Edit | `default` + help → `0.9.6` |
| `rv-android/scripts/calibration_orchestrator.py:584-585` | Edit | `default` + help → `0.9.6` |
| `rv-android/.claude/skills/rv-experiment-compare/scripts/gen_compare.py:367` | Edit | `--image` default → `phtcosta/rvandroid:0.9.6` |

### Group F — Test asserts (`-SNAPSHOT` jar names)

| File | Action | Detail |
|------|--------|--------|
| `rv-android/modules/rv-instrumentation-core/tests/test_instrumenter.py:97-99` | Edit | `rv-monitor-rt`, `rvsec-core`, `rvsec-logger-logcat` `-0.9.5-SNAPSHOT.jar` → `-0.9.6-SNAPSHOT.jar` |
| `rv-android/modules/rv-instrumentation-dexlib2/tests/test_dexlib_instrumentation.py:730-732,740-742,774-776,788-790` | Edit | same trio × 4 blocks → `-0.9.6-SNAPSHOT.jar` |

### Group H — Source version string

| File | Action | Detail |
|------|--------|--------|
| `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/cli/src/main/java/br/unb/cic/rv/cli/InstrumentationCli.java:34` | Edit | `version = "0.9.5-SNAPSHOT"` → `"0.9.6-SNAPSHOT"` |

### Group I — Current docs

| File | Action | Detail |
|------|--------|--------|
| `CLAUDE.md:4` | Edit | `rvsec-parent:0.9.5-SNAPSHOT` → `0.9.6-SNAPSHOT` |
| `rvsec/rvsec-android/CLAUDE.md:7` | Edit | `0.9.5-SNAPSHOT` → `0.9.6-SNAPSHOT` |
| `rvsec/rvsec-mop/CLAUDE.md:26` | Edit | `rvsec-mop-0.9.5-SNAPSHOT.jar` → `rvsec-mop-0.9.6-SNAPSHOT.jar` |
| `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/architecture.md:34,56` | Edit | `0.9.5-SNAPSHOT` → `0.9.6-SNAPSHOT` |
| `rv-android/docs/architecture/instrumentation-java.md:35` | Edit | `0.9.5-SNAPSHOT` → `0.9.6-SNAPSHOT` |
| `rv-android/docs/architecture/rv-experiment.md:187,312,1007,1010,1408,1412,1478` | Edit | current image-chain refs `0.9.5` → `0.9.6` (l.1010 states that `build.sh` tags `0.9.5` and `latest`, which after Group D is `0.9.6`; l.1408/1412 are inside a Mermaid diagram — change only the token) |
| `rv-android/openspec/specs/tools/spec.md:539` | Edit | `phtcosta/rvandroid_tools:0.9.5` → `0.9.6` |
| `rv-android/.claude/skills/rv-experiment-compare/SKILL.md:53` | Edit | `(default 0.9.5)` → `0.9.6` |

## 4. Execution Order

1. **Prerequisite gate (main window).** `git status --porcelain -- <every path in §3>` is empty.
   Then re-measure the tracked inventory from the repository root:
   ```
   git grep -nE '0\.9\.5' -- ':!**/openspec/changes/**' ':!crylogger/**' \
     | grep -vE '^rv-android/(backup|experimento-[^/]*|audit|docs/handoff|data)/'
   ```
   At `3dfd9668` it returns 128 lines in 88 files: the 84 files of §3 plus four §2 exclusions
   (the three e03mini composes and `uv.lock`). Every hit must be a row of §3 or an item of §2. A
   hit that is neither — a new test, a new POM, a new doc — is added to §3 before any edit.
2. **Group A (main window)** — `versions:set`, then `git diff --stat` shows only the 48 reactor
   POMs. It runs alone and first so the plugin's diff is validated in isolation; it also shares no
   file with any later group.
3. **Groups B–I in parallel (subagents).** 36 files — the 35 single-token files plus
   `rv-android/pom.xml` —, all single-token substitutions on disjoint files. Following
   `docs/WORKFLOW.md` §5 (20+ files, 3+ independent groups, 3–15 files per subagent, grouped by
   locality), five subagents run at once:
   - **S1 — Groups B + C + H** (5 files: `rv-android/pom.xml`, `configure.sh`, `rvsec/config.sh`,
     `run_phase5_validators.sh`, `InstrumentationCli.java`).
   - **S2 — Group D, build side** (10 files: `build_docker_image.sh`, the five `build.sh`, the four
     Dockerfiles). Holds `docker/rvandroid/build.sh`, whose l.23 and l.28 must move together.
   - **S3 — Group D, run side** (7 files: the four `run.sh`, the three general-purpose composes).
     Must not open any `docker-compose.e03*.yml`, `docker-compose.estudo02*.yml` or
     `docker-compose.e5*.yml`.
   - **S4 — Groups E + F** (6 files), then the pytest of the two Group F files.
   - **S5 — Group I** (8 docs).
   Each subagent receives its rows of §3, the exclusions of §2 that sit next to its files, and the
   rule that it edits only the listed lines. None of them builds, commits, runs `git add` or any
   git command that changes state (`stash`, `checkout`, `reset`, `branch`): the working tree is
   shared with other sessions.
4. **Verification (main window)** — `versions:commit`, full reactor build, pytest, residual greps
   (§5). The reactor build is serialized: it runs once, after every subagent has returned.
5. **Commit by path** (`git commit -- <paths>`), message `chore(gh-tbd-bump-096-snapshot): bump
   0.9.5-SNAPSHOT → 0.9.6-SNAPSHOT (reactor, rv-android, scripts, cadeia Docker 0.9.6)`, no
   co-author trailer. The repository is shared with other sessions, so nothing staged by them may
   enter this commit.
6. **Archive** via `/opsx:archive` (`--skip-specs`) and commit the archive by path. There is no
   issue to close and no Kanban card to move. No push: the user pushes.

## 5. Acceptance Criteria

- [x] 49 POMs at `0.9.6-SNAPSHOT` (48 reactor + `rv-android/pom.xml`); `git diff --stat` shows no change under `backup/`, `docs/handoff/`, crylogger, docker/mop, rv-monitor docs/installer, teste-sootup
- [x] Group C scripts, Group F asserts, Group H CLI version and Group I docs at `0.9.6-SNAPSHOT` / `0.9.6`
- [x] Group D Docker chain and Group E Python defaults at `0.9.6`; in `docker/rvandroid/build.sh`, the `VERSION` default (l.23) and the `TAG_LATEST` comparison (l.28) hold the same value
- [x] `mvn -o versions:commit` run; no `*.versionsBackup` file left
- [x] From the repository root, with JDK 21 (`JAVA_HOME=$HOME/.sdkman/candidates/java/21.0.12-tem`): `mvn -o clean install -DskipMopAgent -DskipTests` → EXIT=0, 48 modules built, and `rvsec-parent/0.9.6-SNAPSHOT` present in the local Maven repository
- [x] `cd rv-android && uv run pytest modules/rv-instrumentation-core/tests/test_instrumenter.py modules/rv-instrumentation-dexlib2/tests/test_dexlib_instrumentation.py --import-mode=importlib -o "addopts="` → 0 failed
- [x] The §4 step 1 grep, re-run after the edits, returns only the four §2 exclusions (three e03mini composes, `uv.lock`)
- [x] `git grep -nE '0\.9\.6'` (crylogger excluded) lists only §3 paths, and the untracked `docker/docker-compose.e03igg*.yml` still read `0.9.5`
- [x] The commit contains only §3 paths (`git show --stat HEAD` lists 85 files: the 84 §3 paths plus this change's `tasks.md`)
