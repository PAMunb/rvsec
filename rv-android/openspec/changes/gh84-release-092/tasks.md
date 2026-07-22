<!-- Branch-level order is STRICT: commit gh84 on modules → FF master → master release pass
     → modules dev pass → verify → archive. No git tag (user decision). Within a branch, the
     version-string groups touch disjoint files and are subagent-parallelizable.
     ALL LOCAL — no push (user pushes after review). -->

## 0. Prerequisites (sequential)

- [ ] 0.1 Confirm clean working tree on `modules` (`git status`); stash/commit unrelated WIP
- [ ] 0.2 Commit this change (gh84 artifacts) on `modules` with `refs #84` so the fast-forward carries it into `master`

## 1. Fast-forward master ← modules (Group G0a)

- [ ] 1.1 Create local `master`: `git fetch origin && git switch -c master origin/master`
- [ ] 1.2 `git merge --ff-only modules` (must be a clean fast-forward — abort if it is not)
- [ ] 1.3 Verify: `git diff --quiet master modules` (trees identical); confirm ~585 legacy files gone (`test ! -e rv-android/android.py && test ! -e rv-android/commands`)

## 2. master → release 0.9.2 (only `-SNAPSHOT` carriers + stale docs)

- [ ] 2.1 Group A: from repo root `mvn versions:set -DnewVersion=0.9.2 -DgenerateBackupPoms=true`; `git diff --stat` confirms only the 45 reactor POMs changed (zero in `backup/`, crylogger, docker/mop, rv-monitor docs/installer, teste-sootup)
- [ ] 2.2 Group B: `rv-android/pom.xml` `<parent><version>` (l.10) only — module inherits, has no own `<version>` → `0.9.2`
- [ ] 2.3 Group C: `configure.sh:13`, `rvsec/config.sh:13`, `rv-android/scripts/run_phase5_validators.sh:80` → `0.9.2` (drop `-SNAPSHOT`)
- [ ] 2.4 Group F: test asserts in `test_instrumenter.py:97-99` + `test_dexlib_instrumentation.py:536-538,546-548,580-582,594-596` → `*-0.9.2.jar`
- [ ] 2.5 Group H: `InstrumentationCli.java:27` `version = "0.9.2"`
- [ ] 2.6 Group I: drop `-SNAPSHOT` rows (`architecture.md:34,56`, CLAUDE.md files, `rvsec-mop/CLAUDE.md:26`) → `0.9.2`; refresh stale `0.9.1` doc rows (`subsystem-rv-experiment.md:181,308,1280,1316`, `specs/tools/spec.md:522`, `SKILL.md:53`) → `0.9.2`; confirm/skip the two **Review** rows (`subsystem-rv-experiment.md:550`, `specs/instrumentation/spec.md:1192`)
- [ ] 2.7 Groups D/E: verify NO change needed (Docker chain + Python defaults already `0.9.2`)
- [ ] 2.8 `mvn versions:commit` (remove `*.versionsBackup`)
- [ ] 2.9 `mvn clean install -DskipMopAgent -DskipTests` (root, full reactor build) → EXIT=0
- [ ] 2.10 `cd rv-android && uv run pytest modules/rv-instrumentation-core/tests/test_instrumenter.py modules/rv-instrumentation-dexlib2/tests/test_dexlib_instrumentation.py --import-mode=importlib -o "addopts="` → 0 failed
- [ ] 2.11 `git grep -n "0.9.2-SNAPSHOT"` → residual only in excluded paths (`backup/`, `experimento-*/`, ADRs, plan-docs, `openspec/changes/**`)
- [ ] 2.12 Commit on `master`: `release 0.9.2` (`closes #84`) — no git tag (user decision)

## 3. modules → 0.9.3-SNAPSHOT (all groups)

- [ ] 3.1 `git switch modules`
- [ ] 3.2 Group A: `mvn versions:set -DnewVersion=0.9.3-SNAPSHOT -DgenerateBackupPoms=true`; validate `git diff --stat` (only 45 reactor POMs)
- [ ] 3.3 Group B: `rv-android/pom.xml` → `0.9.3-SNAPSHOT`
- [ ] 3.4 Group C: 3 runtime scripts → `0.9.3-SNAPSHOT`
- [ ] 3.5 Group D: Docker chain (`build_docker_image.sh:12`; `docker/{base,android,tools,rvandroid}/build.sh:5` +comment l.15; `rvandroid_dev/build.sh:3`; 4 Dockerfile `FROM`; 4 run helpers +comments; `docker-compose.yml:20`; `docker-compose.gh80.yml:24` +comments; `docker-compose.dexlib2-validation.template.yml:34,55` +comments) → `0.9.3`
- [ ] 3.6 Group E: Python defaults `baseline_docker.py:252-253`, `preprocess_docker.py:271-272`, `calibration_orchestrator.py:584-585`, `gen_compare.py:202` → `0.9.3`
- [ ] 3.7 Group F: test asserts → `*-0.9.3-SNAPSHOT.jar`
- [ ] 3.8 Group H: `InstrumentationCli.java:27` `version = "0.9.3-SNAPSHOT"`
- [ ] 3.9 Group I: all doc rows → `0.9.3` / `0.9.3-SNAPSHOT` (same Review-row judgment as 2.6)
- [ ] 3.10 `mvn versions:commit`; `mvn clean install -DskipMopAgent -DskipTests` (full reactor build) → EXIT=0
- [ ] 3.11 Pytest (same command as 2.10) → 0 failed
- [ ] 3.12 `git grep -n "0.9.2\b"` outside excluded paths → none (all `0.9.3`); confirm `0.9.0`-pinned experiment compose files intact
- [ ] 3.13 Commit on `modules`: `open 0.9.3-SNAPSHOT dev cycle` (`refs #84`)

## 4. Archive & tracking

- [ ] 4.1 Archive gh84 on `modules` (invoke `openspec-archive-change` / `openspec archive gh84-release-092`)
- [ ] 4.2 Report status to user; **do NOT push** — hand off `git push origin master modules` for user (no tag)
- [ ] 4.3 After user confirms push, move Kanban card #84 → Done

## 5. Verification (acceptance criteria)

- [ ] 5.1 Re-check every acceptance criterion in `plan.md` §5
- [ ] 5.2 Confirm branch divergence is forward-only — `master` +1 (release `0.9.2`), `modules` +2 (dev-bump `0.9.3-SNAPSHOT`, gh84 archive-move): `git rev-list --left-right --count master...modules` → `1  2`, no force-push involved
- [ ] 5.3 Confirm working tree clean on both branches; no `*.versionsBackup` remnants
