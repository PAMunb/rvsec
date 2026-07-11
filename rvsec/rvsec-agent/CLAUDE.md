# CLAUDE.md - rvsec-agent

## Purpose
The **JSE agent** (`-javaagent`), generated from the JCA specs, plus a JUnit suite (ported from CogniCrypt) that validates the specs during JSE test runs via Surefire. This is the **JSE/E1 side** of RVSEC (vs. the Android instrumentation side in `rvsec-android`).

## Pipeline (verified)
`rvsec-mop/src/main/resources/jca` → `mop-maven-plugin` (goals `mop-gen` + `agent-gen`, configured in `pom.xml` with `pathToMopFiles`/`pathToJavaMop`/`pathToMonitor`) → `src/main/java/mop/MultiSpec_1RuntimeMonitor.java` (**generated**, 18031 lines) + `JavaMOPAgent.jar` (checked in at module root) → Surefire runs tests with `-javaagent:${basedir}/JavaMOPAgent.jar` → generated monitor calls `rvsec-core` (`ExecutionContext`) + `rvsec-logger-csv` (`ErrorCollector`) → `output/summary.csv`.

## Relationships
- ⟵ `mop-maven-plugin`, `rvsec-mop` (jca set only — `pathToMopFiles` points at `rvsec-mop/.../jca`), `rvsec-core`, `rvsec-logger-csv`.
- ⟵ `rv-monitor-rt` (`br.unb.cic.rvmonitor:rv-monitor-rt`), with `aspectjweaver` **excluded** — this module is pure `-javaagent`, **no AspectJ weaving** (the commented-out `aspectjrt` dependency in `pom.xml` is only needed for `generic_new` specs, not the default `jca` set).

## Test suite (verified counts)
`src/test/java/br/unb/cic/mop/bench01/` — **18 test classes**, **213 `@Test` methods** total (one file per JCA API area, e.g. `CipherTest.java` alone has 72, `KeyGeneratorTest.java` 18, `MessageDigestTest.java` 13). Also `src/test/java/br/unb/cic/mop/{drivers,simple}/` (`Bench01-03`, `ReflectionBased`, `BrokenMacBBCase1`, `StaticInitializationVectorABHCase1`) and a standalone `util/CipherTransformationUtilTest.java`.

## Build
`mvn test` / `mvn install` (regenerates `src/main/java/mop/*` via `mop-maven-plugin` unless skipped). Profile `-Pcheck` (defined in the parent `rvsec/pom.xml`) sets `skipMopAgent=true skipTests=true`.

## Gotchas
- ⚠ This module's `README.md` **describes the Android/AspectJ flow** (aspects woven into APKs, logcat bridge) — that is the `rvsec-android` architecture, **not** this module's actual JSE `-javaagent` flow. Disregard it.
- `src/main/java/mop/` is **generated** and `.gitignore`d (`src/main/java/mop/.gitignore` excludes `MultiSpec_1RuntimeMonitor.java`), but a stale generated copy currently sits on disk (18031 lines) — do not hand-edit it; regenerate via `mvn` with `mop-maven-plugin` instead.
- Do not assert a "209" or "23-classes" test count from any external doc — the verified figures are **18 classes / 213 `@Test`**; recount from `src/test/java/br/unb/cic/mop/bench01/*.java` if this drifts.
