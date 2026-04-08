# rvsec-agent

Runtime instrumentation agent for the RVSec framework. Provides the AspectJ-based
monitoring infrastructure that gets woven into Android APKs during instrumentation.

## Purpose

rvsec-agent contains the runtime monitoring aspects and support classes that are
injected into Android applications by the `rv-instrumentation` Python module. When
an instrumented APK runs, these aspects intercept calls to monitored APIs (e.g.,
JCA cryptographic operations) and log violations detected by RV-Monitor-generated
monitors.

## Architecture

The agent consists of:

- **AspectJ aspects**: Pointcuts and advice that intercept method calls to monitored APIs
- **Monitor runtime**: Generated monitor classes from RV-Monitor that track property
  violations at runtime
- **Logging bridge**: Outputs violation events via Android logcat using RVSEC error tags,
  which are captured by rv-platform's logcat infrastructure
- **Coverage aspect** (`Coverage.aj`): Tracks method execution coverage by logging
  method entry events to logcat

## Integration

```
.mop specs (rvsec-mop)
    -> JavaMOP + RV-Monitor (rv-monitor-generator)
    -> Generated monitors + aspects
    -> Woven into APK (rv-instrumentation)
    -> rvsec-agent runtime classes execute inside APK
    -> Logcat output -> rv-platform captures coverage + violations
```

## Build

Built as part of the rvsec parent Maven project:

```bash
cd rvsec
mvn clean install -DskipTests
```

The agent JAR is used by `rv-instrumentation` during the AspectJ weaving phase.

## Dependencies

- `rvsec-core`: Shared domain models and interfaces
- `rvsec-logger-csv`: CSV-based violation logging
- AspectJ runtime (provided by the weaving process)
