# CLAUDE.md - javamop

## Purpose
MOP→AspectJ compiler: parses `.mop` specification files and emits `.rvm` (rv-monitor input) + `MonitorAspect.aj` (AspectJ source), plus (local patch) a `MonitorAspect.json` descriptor.

## Role in the RVSEC pipeline
Monitor generation (pre-processing). Runs before compilation/weaving; its `.aj`/`.rvm` outputs feed rv-monitor and, ultimately, the JSE agent and the Android weavers.

## Relationships
- ⟵ consumes from: `rv-monitor` (sibling reactor module, groupId `br.unb.cic.rvmonitor`, artifact `rv-monitor`) — invoked as a backend to turn `.rvm` into Java monitor classes.
- ⟶ consumed by: `mop-maven-plugin` (`MOPGen` mojo, via `pathToJavaMop`), which is configured from `rvsec-agent/pom.xml`; and by `rv-android/modules/rv-monitor-generator`, whose shell layer calls `bin/javamop`. The emitted JSON descriptor (`--emit-descriptor`) is consumed by the dexlib2-based Android instrumentation prototype (rvsec-android / dexlib2 weaver work, refs #52).

## Dependencies
- Internal: `br.unb.cic.rvmonitor:rv-monitor` (runtime dependency of the CLI).
- External: `org.aspectj:aspectjtools`/`aspectjweaver`/`aspectjrt` (version from root `aspectj.version`, currently 1.9.25.1), `commons-lang3`, `commons-io`, `com.beust:jcommander:1.35` (pinned, older than root's managed 1.82), `com.fasterxml.jackson.core:jackson-databind:2.18.2` (added specifically for descriptor emission), test-only `system-rules:1.16.0`.

## Key components
| Component | File | Purpose |
|---|---|---|
| Dev entry script | `bin/javamop` | ⚠ Trap: just `exec`s `target/release/javamop/javamop/bin/javamop`, which only exists after `mvn package` (assembly output). |
| Real launcher script | `src/main/scripts/bin/javamop` | The actual script packaged into the assembly; sets classpath and calls `javamop.JavaMOPMain`. |
| Main class | `src/main/java/javamop/JavaMOPMain.java` | CLI entry point; drives parsing → `MOPProcessor` → `.rvm`/`.aj`/`.json` output. |
| CLI options | `src/main/java/javamop/JavaMOPOptions.java` | Flags incl. `-merge` (combine all specs into one `.aj`, must be paired with `-n`), `--emit-descriptor`/`-emit-descriptor`. |
| Grammar | `src/main/javacc/javamop/parser/` | `.mop` file grammar (JavaCC, generates the parser at build time). |
| Descriptor emission | `src/main/java/javamop/output/descriptor/DescriptorWriter.java`, `src/main/java/javamop/output/AspectJDescriptor.java` | Local patch: mirrors the `.aj` output (`AdviceAndPointCut.toString()`) as a Jackson-serializable JSON tree for DEX-native weaving. |

## Build & invocation
`mvn package` → `target/release/javamop/` (dir + tar.gz + zip via `maven-assembly-plugin`, descriptor `src/main/assembly/assembly.xml`). Invoked programmatically by `mop-maven-plugin`'s `mop-gen` mojo (`pathToJavaMop` property), or directly via `bin/javamop <specs> -merge -n <name> [--emit-descriptor]`.

## Provenance
Root `pom.xml` `<scm>` and `rvsec/docker/base/Dockerfile` (`git clone https://github.com/PAMunb/javamop.git`) record this as a fork by UnB (org `github.com/PAMunb`) of `github.com/runtimeverification/javamop`. Inside this source tree there are zero references to PAMunb — only `com.runtimeverification.*`/upstream copyright headers remain. It was internalized into the monorepo (copied, not a submodule) at commit `3228f60e` ("initial skeleton", 2022-07-22); groupId rebased to `br.unb.cic.javamop` in `ca086a64` ("changing rvmonitor groupId"). The upstream commit hash is not preserved anywhere in the tree, so the exact fork point is not reconstructible from git history alone.

## Gotchas / corrections
- The `--emit-descriptor` JSON output (`DescriptorWriter`/`AspectJDescriptor`) is a **local, UnB-only patch** (refs #52, added for the dexlib2 instrumentation prototype) — it does not exist upstream and will not survive a re-sync from `runtimeverification/javamop`.
- `-merge` should always be paired with `-n <name>` (per `JavaMOPOptions` javadoc) or the merged monitor has no usable name.
- `bin/javamop` at the module root is dev/test convenience only; it silently no-ops (fails) until `mvn package` has produced `target/release/`.
