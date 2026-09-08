# CLAUDE.md - rvsec (root aggregator)

## Purpose
Root Maven reactor (`br.unb.cic:rvsec-parent:0.9.3-SNAPSHOT`, packaging `pom`) that builds RVSEC's Java side end to end: monitor generation tooling, the MOP build-time plugin, and the JSE/Android agent modules.

## Role in the RVSEC pipeline
Aggregator / build orchestration for pre-processing (monitor generation) and runtime (agent/weaving) modules. Not itself part of the runtime path.

## Reactor build order
```
rv-monitor  →  javamop  →  mop-maven-plugin  →  rvsec
                                                  (rvsec-mop, rvsec-mop-extractor, rvsec-crysl,
                                                   rvsec-core, rvsec-logger-csv, rvsec-agent,
                                                   rvsec-android)

                                                  rvsec-crysl is itself an aggregator:
                                                  (rvsec-crysl-core → rvsec-crysl-mop
                                                                    → rvsec-crysl-crysl)
```
`rvsec-crysl` sits after `rvsec-mop-extractor` and before `rvsec-core` because `rvsec-crysl-mop`
links against `javamop` (already built by then) and against no other reactor module.

`rv-android` is commented out of `<modules>` — it is a sibling Python/Android project, not part of this Java reactor. See `rv-android/modules/*/CLAUDE.md` for its docs.

## Module map
| Module | CLAUDE.md | One-line role |
|---|---|---|
| `rv-monitor` | `rv-monitor/CLAUDE.md` | `.rvm` → Java monitors; `rv-monitor-rt` runtime lib. |
| `javamop` | `javamop/CLAUDE.md` | `.mop` → `.rvm`/`.aj` (+ local JSON descriptor patch). |
| `mop-maven-plugin` | `mop-maven-plugin/CLAUDE.md` | Maven glue: `mop-gen`/`agent-gen` mojos drive javamop + rv-monitor. |
| `rvsec/*` | (out of scope here; see `rvsec-android` module docs where present) | JSE agent, Android instrumentation, MOP specs. |
| `rvsec/rvsec-crysl` | `rvsec/rvsec-crysl/CLAUDE.md` | MOP/CrySL conformance component: lifts `.mop` and `.crysl` into one model and reports M0–M4. |

`rvsec-crysl` (packaging `pom`) is the only subtree that overrides a reactor-wide dependency
property, and the asymmetry is deliberate:
- **`guava.version` is overridden to `33.5.0-jre`.** The root pins 19.0 for Soot; this component
  does not use Soot, and `CrySLParser 4.0.6` calls `ImmutableMap.Builder#buildOrThrow`, which 19.0
  does not have — the inherited pin compiles clean and dies at runtime with `NoSuchMethodError`.
  The root `dependencyManagement` is property-driven, so redefining the property in the subtree
  parent is enough to move the managed version.
- **`scala.version` is deliberately NOT overridden.** It looks like the same fix and is not:
  raising it to 2.13.x breaks `ptltl` (reached transitively via `javamop` → `rv-monitor`) with
  `NoClassDefFoundError: scala/Serializable`, and `ptltl` may not be excluded. The reactor's
  2.11.12 is inherited unchanged.
- **`rvsec-crysl-core` publishes a `test-jar`** (`maven-jar-plugin`, `test-jar` goal) that carries
  `CiTags` — the single holder of the JUnit tag name the CI step excludes by name. `-mop` and
  `-crysl` consume that test-jar in `test` scope so the tag name lives in one place instead of
  three.

## Shared build properties (root `pom.xml`)
- `java.version` = **21** (compiler source/target).
- `aspectj.version` = **1.9.25.1** — comment in the pom flags this as a **TODO: "bater com a versao do docker"** (must match the Docker image's AspectJ version; not verified in sync here).
- `soot.version` = **4.7.1**, `scala.version` = 2.11.12, `guava.version` = 19.0 (overridden to 33.5.0-jre inside the `rvsec-crysl` subtree — see Module map), `javaparser.version` = 3.25.0, `android.version` = 4.1.1.4 (scope `provided`).
- Profile **`-Pcheck`**: sets `skipMopAgent=true`/`skipTests=true`, `defaultGoal=verify`, and runs `spotbugs-maven-plugin` + `org.owasp:dependency-check-maven` — the CI/static-analysis profile, not a normal build.

## `main.basedir` mechanism
`org.commonjava.maven.plugins:directory-maven-plugin` (bound to the `initialize` phase) resolves `main.basedir` to this reactor's root directory by looking up the `br.unb.cic:rvsec-parent` project. This property is what lets downstream modules drop build artifacts straight into the **sibling** `rv-android` tree, e.g.:
- `rvsec/rvsec-android/rvsec-apk/pom.xml` → `${main.basedir}/rv-android/lib/apktool`
- `rvsec/rvsec-android/rvsec-frame-computer/pom.xml` → `${main.basedir}/rv-android/lib/frame-computer`
- `rvsec/rvsec-android/rvsec-gator/pom.xml` → `${main.basedir}/rv-android/lib/gator`
- `rvsec/rvsec-android/rvsec-reachability/pom.xml`, `rvsec-gesda/pom.xml`, `rvsec-instrumentation-dexlib2/cli/pom.xml`, `rvsec-mop-extractor/pom.xml`, `rvsmart/pom.xml` — same pattern into other `rv-android/lib/...` or `rv-android/modules/...` subpaths.
- `rvsec/rvsec-agent/pom.xml` uses it for `pathToJavaMop`/`pathToMonitor`/`pathToMopFiles`/`destinationFolder` (the `mop-maven-plugin` execution).

This mechanism **only resolves correctly when building from the root reactor** (`mvn` invoked at `GR`, or a module built with the full reactor on the classpath) — building an inner module standalone (e.g. `cd rvsec/rvsec-agent && mvn package`) will fail to resolve `main.basedir` unless the parent has been `install`ed and the property is otherwise supplied.

## Gotchas / corrections
- The `aspectj.version` TODO is real and unresolved in the tree — do not assume the pinned version matches whatever Docker image is currently used to build/run.
- `rv-android` being commented out of `<modules>` means `mvn install` at the root never touches it; the two projects are integrated only via the `main.basedir` jar hand-off described above, not via the Maven reactor.
