# CLAUDE.md - rv-monitor

## Purpose
Compiles `.rvm` monitor specifications into monitor `.java` classes, and provides `rv-monitor-rt`, the small runtime library those generated monitors depend on.

## Role in the RVSEC pipeline
Monitor generation (pre-processing, the `rv-monitor` CLI/generator submodule) **and** runtime (`rv-monitor-rt`, linked/woven into the final artifacts). `rv-monitor-rt.jar` is woven into Android APKs and used by the JSE `-javaagent`.

## Relationships
- ⟵ consumes from: nothing internal to the reactor (standalone generator + runtime; only external AspectJ).
- ⟶ consumed by: `javamop` (calls into `rv-monitor` as its Java-monitor-generation backend), `rvsec-agent` (depends on `rv-monitor-rt` for the compiled `.java`/`.aj` monitors it weaves via `-javaagent`, and shells to `bin/rv-monitor` through `pathToMonitor`), `rv-android/modules/rv-monitor-generator` (shells to `bin/rv-monitor` for Android monitor generation).

## Sub-reactor
`rv-monitor/pom.xml`, artifact `rv-monitor-parent` (packaging `pom`):
| Module | Role |
|---|---|
| `rv-monitor-rt` | **Runtime** — the only artifact actually consumed at Android/JSE runtime. |
| `logicrepository` | Shared logic-plugin repository infra. |
| `plugins_logicrepository/{cfg,ere,fsm,ltl,pda,po,ptcaret,ptltl,srs,tfsm}` | One logic-plugin module per supported specification formalism (context-free grammar, extended regular expr, finite-state machine, LTL, pushdown automata, past-operator, etc.). |
| `rv-monitor` | CLI/generator (`.rvm` → `.java`/`.aj`). |
| `installer` | **Commented out** in the reactor `<modules>` — present on disk, not built. |

## Key components
| Component | File | Purpose |
|---|---|---|
| Generator entry point | `rv-monitor/src/main/java/com/runtimeverification/rvmonitor/java/rvj/Main.java` | Java-monitor generation CLI main. |
| C generator | `rv-monitor/src/main/java/com/runtimeverification/rvmonitor/c/rvc/Main.java` | Unrelated C-target generator, not used by RVSEC's Java/Android path. |
| Dev entry script | `bin/rv-monitor` | ⚠ Same trap as javamop: delegates to `target/release/rv-monitor/bin/rv-monitor`, only present after `mvn install`. |
| Runtime package | `rv-monitor-rt/src/main/java/com/runtimeverification/rvmonitor/java/rt/` | Runtime classes woven/linked into instrumented apps (`table`, `concurrent`, `tablebase`, `observable`, `ref`, `map` subpackages). |
| `.rvm` grammar | `rv-monitor/src/main/javacc/com/runtimeverification/...` | JavaCC grammar for the `.rvm` intermediate format. |

## Build & invocation
`mvn install` → `rv-monitor-rt-*.jar`, `rv-monitor-*.jar`, one jar per logic plugin, plus `target/release/rv-monitor/` (assembly with `bin/rv-monitor`). Dependency: `org.aspectj:aspectjweaver`. Invoked programmatically by `mop-maven-plugin`'s `mop-gen` mojo (`pathToMonitor` property) or directly via `bin/rv-monitor`.

## Provenance
Root `pom.xml` `<scm>` and `rvsec/docker/base/Dockerfile` (`git clone https://github.com/PAMunb/rv-monitor.git`) record this as a fork by UnB of `github.com/runtimeverification/rv-monitor` (NCSA license). Inside this source tree, however, packages remain `com.runtimeverification.rvmonitor.*` and there is no PAMunb reference — only the Maven `groupId` (`br.unb.cic.rvmonitor`) marks it as the UnB fork. It was internalized (copy, not submodule) in the same `3228f60e` commit as javamop; groupId rebased across `d46cfc36`/`ca086a64` ("changing rvmonitor groupId"). The upstream commit hash is not preserved in the tree; an externally-referenced `statistics-1.4` upstream branch could not be confirmed from the git history available here.

## Gotchas / corrections
- groupId (`br.unb.cic.rvmonitor`) ≠ Java packages (`com.runtimeverification.rvmonitor.*`) — grepping for `br.unb.cic` inside this module's source will find almost nothing; grep `com.runtimeverification` instead.
- `installer` submodule exists on disk but is commented out of `<modules>` — do not expect it to build via the reactor.
- `rv-monitor/rv-monitor/pom.xml` sets `<skipITs>true</skipITs>` — integration tests are known-broken/skipped (no fix tracked in this tree).
- `javacc-maven-plugin` is pinned to `<jdkVersion>1.6</jdkVersion>` in both the module `pluginManagement` and inline config — a landmine if the JavaCC toolchain is ever modernized (root project itself targets Java 21).
