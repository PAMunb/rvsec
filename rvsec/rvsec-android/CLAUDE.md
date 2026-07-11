# CLAUDE.md - rvsec-android

## Purpose

3rd-level Maven aggregator (`br.unb.cic:rvsec-android`, `packaging=pom`) grouping all
Android-facing Java modules of RVSEC, under the `rvsec` parent (`br.unb.cic:rvsec`,
`0.9.1-SNAPSHOT`).

## Role in pipeline

Pure dependency/version glue for the Android side of RVSEC: no code of its own, only
`<modules>`, shared `<properties>`, and a `<dependencyManagement>` block inherited by children.

## Children (verify against `pom.xml`)

| Module | Status | CLAUDE.md |
|---|---|---|
| `rvsec-apk` | active | `rvsec-apk/CLAUDE.md` |
| `rvsec-logger-logcat` | active | `rvsec-logger-logcat/CLAUDE.md` |
| `rvsec-gator` | active | out of scope for this pass |
| `rvsmart` | **DISCONTINUED** (still listed in `<modules>`, builds, but not documented here) | none |
| `rvsec-frame-computer` | active | `rvsec-frame-computer/CLAUDE.md` |
| `rvsec-instrumentation-dexlib2` | active (multi-module aggregator itself: `coverage-weaver`, `cli`, `dex-mutator`, `grammar-tests`, `descriptor-reader`, `advice-emitter`, `monitor-builder`, `multidex-merger`, `pointcut-engine`, `validator`) | out of scope for this pass |

## Shared versions (`<properties>`)

| Property | Version |
|---|---|
| `apktool.version` | 2.10.0 |
| `flowdroid.version` | 2.10.0 |
| `gson.version` | 2.10.1 |
| `jgrapht.version` | 1.5.2 |
| `logback.version` | 1.2.6 |

## History: GESDA / REACH absorbed into GATOR

GESDA and the standalone reachability module were absorbed into GATOR
(`rvsec-gator-commons` / `-sootandroid` / `-client`). Their orphaned source trees were
archived to `backup/rvsec-gesda/` and `backup/rvsec-reachability/`, and the matching stale
`rvsec-gesda-common` / `rvsec-gesda-core` / `rvsec-reachability` `dependencyManagement`
entries were removed from `pom.xml`. Use `rvsec-gator-*` for any new analysis-backend
dependency.

## Gotchas

- `rvsmart` is present in `<modules>` and will build with the reactor, but it is
  discontinued and intentionally undocumented (per scope of this documentation pass).
