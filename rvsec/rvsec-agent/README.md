# rvsec-agent

Runtime instrumentation agent for the RVSec framework. Provides the JSE `-javaagent`-based
monitoring infrastructure generated from the JCA specs and exercised by the module's
JUnit test suite via Surefire.

## Purpose

rvsec-agent contains the generated runtime monitor classes and support classes that are
loaded into the JVM via `-javaagent` when the module's JUnit tests run under Surefire.
When a test runs, the agent intercepts calls to monitored APIs (e.g.,
JCA cryptographic operations) and logs violations detected by RV-Monitor-generated
monitors.

## Architecture

The agent consists of:

- **Generated monitor** (`MultiSpec_1RuntimeMonitor.java`): Pure `-javaagent` bytecode
  instrumentation (via `rv-monitor-rt`, with `aspectjweaver` explicitly excluded — this
  module does not use AspectJ weaving) that intercepts calls to monitored APIs
- **Monitor runtime**: Generated monitor classes from RV-Monitor that track property
  violations at runtime
- **Logging bridge**: Outputs violation events via `rvsec-logger-csv`, captured in
  `output/summary.csv`

## Integration

```
.mop specs (rvsec-mop, jca set)
    -> mop-maven-plugin (mop-gen + agent-gen)
    -> Generated MultiSpec_1RuntimeMonitor.java + JavaMOPAgent.jar
    -> Surefire runs JUnit tests with -javaagent:JavaMOPAgent.jar
    -> rvsec-core + rvsec-logger-csv
    -> output/summary.csv
```

## Build

Built as part of the rvsec parent Maven project:

```bash
cd rvsec
mvn clean install -DskipTests
```

The agent JAR (`JavaMOPAgent.jar`) is passed to Surefire via `-javaagent` when this
module's JUnit tests run.

## Dependencies

- `rvsec-core`: Shared domain models and interfaces
- `rvsec-logger-csv`: CSV-based violation logging
- `rv-monitor-rt` (AspectJ weaver excluded — pure `-javaagent` instrumentation)
