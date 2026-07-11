# mop-maven-plugin

Maven plugin that compiles JavaMOP `.mop` specification files into RV-Monitor
runtime monitors during the Maven build lifecycle.

## Purpose

This plugin automates the MOP specification compilation pipeline within Maven builds.
It invokes JavaMOP to parse `.mop` files and generate `.rvm` specifications, then
invokes RV-Monitor to produce Java monitoring aspects and runtime classes. The generated
artifacts are used by `rvsec-agent` for runtime verification.

## Build and Install

```bash
mvn clean install
```

## Usage

This plugin exposes two goals: `mop-gen` (bound to the `generate-sources`
phase, runs JavaMOP with `-merge` and RV-Monitor) and `agent-gen` (bound to
the `process-classes` phase, runs `javamopagent` to build `JavaMOPAgent`).
Configured in the rvsec parent POM:

```xml
<plugin>
    <groupId>br.unb.cic</groupId>
    <artifactId>mop-maven-plugin</artifactId>
    <executions>
        <execution>
            <goals>
                <goal>mop-gen</goal>
                <goal>agent-gen</goal>
            </goals>
        </execution>
    </executions>
</plugin>
```

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `mopDir` | `src/main/mop` | Directory containing `.mop` specification files |
| `outputDir` | `target/generated-sources/mop` | Output for generated monitors |
| `merge` | `true` | Merge all specs into a single monitor (RV-Monitor `-merge` flag) |

## Integration

```
.mop files (rvsec-mop/src/main/mop/)
    -> mop-maven-plugin (this plugin)
    -> JavaMOP: .mop -> .rvm
    -> RV-Monitor: .rvm -> Java aspects + monitors
    -> rvsec-agent (woven into APKs)
```

## Known Issues

- JavaMOP's `-d` flag for output directory does not work reliably. The plugin
  generates `.rvm` files in the current directory and moves them to the target
  location explicitly (see INV-INS-04 in the instrumentation spec).
