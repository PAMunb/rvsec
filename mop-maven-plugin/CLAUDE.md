# CLAUDE.md - mop-maven-plugin

## Purpose
Maven plugin that orchestrates `javamop` + `rv-monitor` to generate the JavaMOP runtime-verification agent at build time, wired into a consuming project's Maven lifecycle.

## Role in the RVSEC pipeline
Build glue (monitor generation, invoked from within `mvn`). Pipeline: `.mop` files → mojo `mop-gen` (shells out to javamop `-merge` then rv-monitor) → `.java`/`.aj` monitor sources → mojo `agent-gen` (shells out to `javamopagent`) → the compiled `JavaMOPAgent` used as a `-javaagent`.

## Relationships
- ⟵ shells out to: `javamop` (`bin/javamop`, via property `pathToJavaMop`), `rv-monitor` (`bin/rv-monitor`, via property `pathToMonitor`), `javamopagent` (via property `path-to-java-mop`) — no compile-time dependency on either, just external process invocation with configured paths.
- ⟶ used by: `rvsec-agent` (`rvsec/rvsec-agent/pom.xml` binds `mop-gen`/`agent-gen` executions, e.g. `pathToMopFiles=${main.basedir}/rvsec/rvsec-mop/src/main/resources/jca`, `pathToJavaMop=${main.basedir}/javamop/bin`, `pathToMonitor=${main.basedir}/rv-monitor/bin`).

## Key components
| Component | File | Purpose |
|---|---|---|
| `mop-gen` mojo | `src/main/java/br/unb/cic/mop/MOPGen.java` | `@Mojo(name="mop-gen", defaultPhase=GENERATE_SOURCES)`. Params: `pathToJavaMop`, `pathToMonitor`, `pathToMopFiles` (all `required=true`), `destinationFolder`, `skipMopAgent`, `generateMopStatistics`. |
| `agent-gen` mojo | `src/main/java/br/unb/cic/mop/AgentGen.java` | `@Mojo(name="agent-gen", defaultPhase=PROCESS_CLASSES)`. Params: `path-to-java-mop`, `path-to-mop-files`, `skipMopAgent`. |
| Process runner | `src/main/java/br/unb/cic/mop/ProcessUtil.java` | `executeExternalProgram()` — wraps `ProcessBuilder`, logs stdout, and **treats any non-empty stderr as a build failure** (throws `MojoExecutionException`). |

## Build & invocation
Packaging `maven-plugin`. Compile deps (all `provided`): `maven-plugin-api:3.8.5`, `maven-core:3.8.5`, `maven-plugin-annotations:3.6.4`. Built with `mvn install`; consumed by declaring the two executions (`mop-gen`, `agent-gen`) in a downstream module's `pom.xml`.

## Gotchas / corrections
- ⚠ `README.md` documents a single goal `mop` — **that goal does not exist in the code.** The real, only goals are `mop-gen` (GENERATE_SOURCES) and `agent-gen` (PROCESS_CLASSES); each must be bound explicitly.
- `ProcessUtil.executeExternalProgram()` fails the build on **any** non-empty stderr output from the shelled-out `javamop`/`rv-monitor`/`javamopagent` process — a benign warning printed to stderr by those tools is indistinguishable from a real failure and will break the Maven build.
- `AgentGen.java` **hardcodes** a `~/.m2/repository/...` path (`String.format("~/.m2/repository/%s/%s/%s/%s-%s.jar", ...)`) to locate a dependency jar — this is not portable to non-default local-repository locations (e.g. custom `settings.xml` or `-Dmaven.repo.local`).
- README's "Known Issues" note (`-d` flag for JavaMOP output dir unreliable, forcing generation into cwd + explicit move) is corroborated by the mojo doing exactly that via `destinationFolder`/`ProcessUtil`; treat as accurate, unlike the goal-name claim.
