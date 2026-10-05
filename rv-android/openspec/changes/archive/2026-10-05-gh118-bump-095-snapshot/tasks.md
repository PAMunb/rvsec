<!-- Dependency hints:
     - Group 1 (prerequisite gate) and Group 2 (plugin) run first, in the main window, in that
       order — the plugin's diff is validated in isolation before anything else is edited.
     - Groups 3–7 touch disjoint files with one-token edits and run IN PARALLEL, one subagent each
       (plan.md §4 step 3: S1–S5). Each subagent edits only its rows of plan.md §3, never builds,
       never runs `git add`/`git commit`, and reports the lines it changed.
     - Group 8 (Verification) runs after every subagent has returned; the reactor build is
       serialized and runs once. Group 9 last.
     - Line numbers come from plan.md §3, measured at df575539; task 1.2 confirms them.
     - No push, no work on master. -->

## 1. Prerequisite gate (sequential — main window)

- [x] 1.1 `git status --porcelain -- <every path in plan.md §3>` is empty; if not, stop and ask — uncommitted work in those files belongs to another session
- [x] 1.2 Run the re-measurement grep of plan.md §4 step 1; reconcile every hit with plan.md §3 or §2; add any new version-bearing file to plan.md §3 before editing

## 2. Group A — Reactor POMs (sequential — main window)

- [x] 2.1 From the repository root, with JDK 21: `mvn -o versions:set -DnewVersion=0.9.5-SNAPSHOT -DgenerateBackupPoms=true`
- [x] 2.2 `git diff --stat -- '*pom.xml'` lists exactly the 48 reactor POMs of plan.md §3 Group A; nothing under `rv-android/backup/`, `rv-android/docs/handoff/`, crylogger, docker/mop, rv-monitor docs/installer, teste-sootup

## 3. S1 — Groups B + C + H (parallel — subagent, 5 files)

- [x] 3.1 `rv-android/pom.xml:10` `<parent><version>` → `0.9.5-SNAPSHOT`
- [x] 3.2 `configure.sh:13` and `rvsec/config.sh:13` `RV_MONITOR_VERSION` → `0.9.5-SNAPSHOT`
- [x] 3.3 `rv-android/scripts/run_phase5_validators.sh:80` → `validator-0.9.5-SNAPSHOT.jar`
- [x] 3.4 `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/cli/src/main/java/br/unb/cic/rv/cli/InstrumentationCli.java:34` → `version = "0.9.5-SNAPSHOT"`

## 4. S2 — Group D, build side (parallel — subagent, 10 files)

- [x] 4.1 `build_docker_image.sh:12`; `rv-android/docker/{base,android,tools}/build.sh:5,15`; `rv-android/docker/rvandroid_dev/build.sh:3` → `0.9.5`
- [x] 4.2 `rv-android/docker/rvandroid/build.sh`: `VERSION` default (l.23) and `TAG_LATEST` comparison (l.28) → `0.9.5`, both in the same edit; comments l.10, l.12, l.19 → `0.9.5`; examples l.20–21 → `0.9.5-gh111`
- [x] 4.3 Dockerfile `FROM` (l.1 only): `rv-android/docker/{android,tools,rvandroid,rvandroid_dev}/Dockerfile` → `0.9.5`; leave `tools/Dockerfile:12` untouched

## 5. S3 — Group D, run side (parallel — subagent, 7 files)

- [x] 5.1 Run helpers: `rv-android/docker/{base,android,rvandroid}/run.sh:3`, `rv-android/docker/tools/run.sh:17,47` → `0.9.5`
- [x] 5.2 Compose: `rv-android/docker/docker-compose.yml:20`; `docker-compose.gh80.yml:7,11,24`; `docker-compose.dexlib2-validation.template.yml:6,21,34,55` → `0.9.5`; `docker-compose.estudo02*.yml` and the untracked `docker-compose.e5*.yml` untouched

## 6. S4 — Groups E + F (parallel — subagent, 6 files)

- [x] 6.1 `rv-android/scripts/baseline_docker.py:252-253`, `preprocess_docker.py:271-272`, `calibration_orchestrator.py:584-585` → `phtcosta/rvandroid:0.9.5`
- [x] 6.2 `rv-android/.claude/skills/rv-experiment-compare/scripts/gen_compare.py:367` → `phtcosta/rvandroid:0.9.5`
- [x] 6.3 `rv-android/modules/rv-instrumentation-core/tests/test_instrumenter.py:97-99` → `*-0.9.5-SNAPSHOT.jar`
- [x] 6.4 `rv-android/modules/rv-instrumentation-dexlib2/tests/test_dexlib_instrumentation.py:613-615,623-625,657-659,671-673` → `*-0.9.5-SNAPSHOT.jar`
- [x] 6.5 Run `/rv-test-run rv-instrumentation-core` and `/rv-test-run rv-instrumentation-dexlib2` (`--import-mode=importlib -o "addopts="`) → 0 failed

## 7. S5 — Group I, current docs (parallel — subagent, 7 files)

- [x] 7.1 `CLAUDE.md:4`, `rvsec/rvsec-android/CLAUDE.md:7`, `rvsec/rvsec-mop/CLAUDE.md:26` → `0.9.5-SNAPSHOT`
- [x] 7.2 `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/architecture.md:34,56` → `0.9.5-SNAPSHOT`
- [x] 7.3 `rv-android/docs/architecture/subsystem-rv-experiment.md:181,310,1284,1320` → `0.9.5` (leave l.552)
- [x] 7.4 `rv-android/openspec/specs/tools/spec.md:522` and `rv-android/.claude/skills/rv-experiment-compare/SKILL.md:53` → `0.9.5`

## 8. Verification (sequential — main window, after Groups 3–7)

- [x] 8.1 `mvn -o versions:commit` from the repository root; `git ls-files --others | grep versionsBackup` is empty
- [x] 8.2 With `JAVA_HOME=$HOME/.sdkman/candidates/java/21.0.12-tem`: `mvn -o clean install -DskipMopAgent -DskipTests` from the repository root → EXIT=0, 48 modules; `rvsec-parent/0.9.5-SNAPSHOT` in the local Maven repository
- [x] 8.3 Run `/rv-qa-lint-fix rv-instrumentation-core` and `/rv-qa-lint-fix rv-instrumentation-dexlib2`; any change outside the edited lines is reverted (this change edits strings only)
- [x] 8.4 Run `/rv-verify rv-instrumentation-core` and `/rv-verify rv-instrumentation-dexlib2` — tests pass (core 11, dexlib2 26); lint flags F401 `import subprocess` and isort order in `test_instrumenter.py`, both present at HEAD before gh118 and outside its lines, left as found
- [x] 8.5 Re-run the plan.md §4 step 1 grep → only §2 exclusions remain; `git grep -nE '0\.9\.5-SNAPSHOT|:0\.9\.5'` hits no excluded path; the untracked `docker/docker-compose.e5*.yml` still read `0.9.4@sha256:…`
- [x] 8.6 Verify every acceptance criterion in plan.md §5

## 9. Commit and archive (sequential — main window)

- [x] 9.1 `git commit -- <paths of plan.md §3>` with `closes #118` (no co-author trailer); `git show --stat HEAD` contains only the 83 §3 paths plus `tasks.md`
- [x] 9.2 Archive via `/opsx:archive gh118-bump-095-snapshot` (`--skip-specs`) and commit the archive by path
- [x] 9.3 Tick the acceptance criteria in issue #118 and close it by hand (`closes` does not act outside `master`); report to the user; do NOT push (the user pushes `modules`)
