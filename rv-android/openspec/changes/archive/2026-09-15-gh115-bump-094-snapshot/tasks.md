<!-- Dependency hints:
     - Group 1 (prerequisite gate) must complete first. Do NOT start before #114 is committed.
     - Group 2 (plugin) runs before the manual groups so its diff is validated in isolation.
     - Groups 3–9 touch disjoint files with one-token edits; run them sequentially in one
       session (no subagents — see plan.md §4).
     - Group 10 (Verification) runs after all other groups; Group 11 last.
     - Line numbers come from plan.md §3, re-measured at 9caaf326 (#114's last commit); task 1.3
       confirms them against the tree at apply time.
     - No push, no work on master. -->

## 1. Prerequisite gate (sequential)

- [x] 1.1 Confirm #114 is committed on `modules` (and #112: `8edf9396`, `30568f09`)
- [x] 1.2 `git status --porcelain -- <every path in plan.md §3>` is empty; if not, stop and ask — uncommitted work in those files belongs to another change
- [x] 1.3 Run the re-measurement grep of plan.md §4 step 1; reconcile every hit with plan.md §3 (shifted line numbers) or §2 (exclusions); add any new version-bearing file to plan.md §3 before editing

## 2. Group A — Reactor POMs (via plugin)

- [x] 2.1 From the repository root, with JDK 21: `mvn versions:set -DnewVersion=0.9.4-SNAPSHOT -DgenerateBackupPoms=true`
- [x] 2.2 `git diff --stat -- '*pom.xml'` lists exactly the 48 reactor POMs of plan.md §3 Group A; nothing under `rv-android/backup/`, `rv-android/docs/handoff/`, crylogger, docker/mop, rv-monitor docs/installer, teste-sootup

## 3. Group B — rv-android/pom.xml

- [x] 3.1 `rv-android/pom.xml` `<parent><version>` → `0.9.4-SNAPSHOT`

## 4. Group C — Runtime config scripts

- [x] 4.1 `configure.sh:13` and `rvsec/config.sh:13` `RV_MONITOR_VERSION` → `0.9.4-SNAPSHOT`
- [x] 4.2 `rv-android/scripts/run_phase5_validators.sh:80` → `validator-0.9.4-SNAPSHOT.jar`

## 5. Group D — Docker chain

- [x] 5.1 Build scripts: `build_docker_image.sh:12`; `rv-android/docker/{base,android,tools}/build.sh:5,15`; `rv-android/docker/rvandroid_dev/build.sh:3` → `0.9.4`
- [x] 5.2 `rv-android/docker/rvandroid/build.sh`: `VERSION` default (l.23) and `TAG_LATEST` comparison (l.28) → `0.9.4`; comments l.10, l.12, l.19 → `0.9.4`; examples l.20–21 → `0.9.4-gh111`
- [x] 5.3 Dockerfile `FROM` (l.1 only): `rv-android/docker/{android,tools,rvandroid,rvandroid_dev}/Dockerfile` → `0.9.4`; leave `tools/Dockerfile:12` untouched
- [x] 5.4 Run helpers: `rv-android/docker/{base,android,rvandroid}/run.sh:3`, `rv-android/docker/tools/run.sh:17,47` → `0.9.4`
- [x] 5.5 Compose: `rv-android/docker/docker-compose.yml:20`; `docker-compose.gh80.yml:7,11,24`; `docker-compose.dexlib2-validation.template.yml:6,21,34,55` → `0.9.4`; `docker-compose.estudo02*.yml` untouched

## 6. Group E — Python image defaults

- [x] 6.1 `rv-android/scripts/baseline_docker.py:252-253`, `preprocess_docker.py:271-272`, `calibration_orchestrator.py:584-585` → `phtcosta/rvandroid:0.9.4`
- [x] 6.2 `rv-android/.claude/skills/rv-experiment-compare/scripts/gen_compare.py:367` → `phtcosta/rvandroid:0.9.4`

## 7. Group F — Test asserts

- [x] 7.1 `rv-android/modules/rv-instrumentation-core/tests/test_instrumenter.py:97-99` → `*-0.9.4-SNAPSHOT.jar`
- [x] 7.2 `rv-android/modules/rv-instrumentation-dexlib2/tests/test_dexlib_instrumentation.py:613-615,623-625,657-659,671-673` → `*-0.9.4-SNAPSHOT.jar`
- [x] 7.3 Run `/rv-test-run rv-instrumentation-core` and `/rv-test-run rv-instrumentation-dexlib2` (`--import-mode=importlib -o "addopts="`) → 0 failed

## 8. Group H — Source version string

- [x] 8.1 `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/cli/src/main/java/br/unb/cic/rv/cli/InstrumentationCli.java:34` → `version = "0.9.4-SNAPSHOT"`

## 9. Group I — Current docs

- [x] 9.1 `CLAUDE.md:4`, `rvsec/rvsec-android/CLAUDE.md:7`, `rvsec/rvsec-mop/CLAUDE.md:26` → `0.9.4-SNAPSHOT`
- [x] 9.2 `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/architecture.md:34,56` → `0.9.4-SNAPSHOT`
- [x] 9.3 `rv-android/docs/architecture/subsystem-rv-experiment.md:181,310,1284,1320` → `0.9.4` (leave l.552)
- [x] 9.4 `rv-android/openspec/specs/tools/spec.md:522` and `rv-android/.claude/skills/rv-experiment-compare/SKILL.md:53` → `0.9.4`

## 10. Verification

- [x] 10.1 `mvn versions:commit` from the repository root; `git ls-files --others | grep versionsBackup` is empty
- [x] 10.2 With `JAVA_HOME=$HOME/.sdkman/candidates/java/21.0.12-tem`: `mvn clean install -DskipMopAgent -DskipTests` from the repository root → EXIT=0, 48 modules
- [x] 10.3 Run `/rv-qa-lint-fix rv-instrumentation-core` and `/rv-qa-lint-fix rv-instrumentation-dexlib2`; any change outside the edited lines is reverted (this change edits strings only)
- [x] 10.4 Run `/rv-verify rv-instrumentation-core` and `/rv-verify rv-instrumentation-dexlib2`
- [x] 10.5 Re-run the plan.md §4 step 1 grep → only §2 exclusions remain; `git grep -n '0\.9\.4'` hits no excluded path
- [x] 10.6 Verify every acceptance criterion in plan.md §5

## 11. Commit and archive

- [x] 11.1 `git commit -- <paths of plan.md §3>` with `closes #115`; `git show --stat HEAD` contains only those paths
- [x] 11.2 Archive via `/opsx:archive gh115-bump-094-snapshot`
- [x] 11.3 Report to the user; do NOT push (the user pushes `modules`), then move Kanban card #115 → Done after the push
