# CLAUDE.md - rvsec (aggregator)

## Purpose
2nd-level Maven aggregator (`br.unb.cic:rvsec`, `packaging=pom`). Groups the Java side of the RVSEC monitored-operations infrastructure under the top-level `rvsec-parent`.

## Module order (verified `pom.xml`)
```xml
<modules>
  <module>rvsec-mop</module>
  <module>rvsec-mop-extractor</module>
  <module>rvsec-mop-defsuses</module>
  <module>rvsec-core</module>
  <module>rvsec-logger-csv</module>
  <module>rvsec-agent</module>
  <module>rvsec-android</module>
</modules>
```

| Module | Purpose |
|---|---|
| `rvsec-mop` | Repository of 168 JavaMOP `.mop` specs (jca/generic/generic_new) + `Coverage.aj`; resources only, no Java. |
| `rvsec-mop-extractor` | CLI extracting the class/method API surface of a spec set; feeds `rv-android/lib/mop-extractor` and GATOR reachability. |
| `rvsec-mop-defsuses` | Dev-only, orphan def/use → PlantUML utility; no consumers, hardcoded path. |
| `rvsec-core` | Shared runtime types (`ExecutionContext`, `Property`, `eh.*`, `org.aspectj.lang` shim); zero dependencies. |
| `rvsec-logger-csv` | JSE-side `ErrorCollector` writing `output/summary.csv`. |
| `rvsec-agent` | JSE `-javaagent` generated from the jca spec set + CogniCrypt-derived JUnit suite (18 classes / 213 `@Test`). |
| `rvsec-android` | Android-side aggregator (APK build, logcat logger, GATOR reachability, dexlib2 instrumentation) — out of scope for this map; has its own module tree. |

## Properties / profiles
Declares `skipMopAgent` and `skipTests` properties (both default `false`). The `check` profile flips both to `true`, sets `defaultGoal=verify`, and adds `spotbugs-maven-plugin` + `dependency-check-maven` plugins — used for static-analysis-only CI passes that skip MOP code generation and tests.

## Build
```bash
cd rvsec
mvn clean install            # full build, generates monitors, runs tests
mvn -Pcheck verify           # static analysis only, no codegen, no tests
```

## Gotchas
- Module build order matters: `rvsec-core` must build before `rvsec-logger-csv`/`rvsec-agent`; `rvsec-mop` (resources) must exist before `rvsec-agent`'s `mop-maven-plugin` codegen reads `rvsec-mop/src/main/resources/jca`.
- `rvsec-android` is a separate Maven aggregator (its own `pom.xml`, own module list) rooted under this same `rvsec` parent — treat it as a distinct subtree when reasoning about Android vs JSE build paths.
