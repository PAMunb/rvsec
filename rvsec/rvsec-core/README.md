# rvsec-core

Shared domain models and interfaces for the RVSec runtime verification framework.

## Purpose

Provides the foundational types used across all rvsec Java modules: error classification,
violation reporting interfaces, and shared constants. Acts as the common dependency for
`rvsec-agent`, `rvsec-logger-csv`, `rvsec-logger-logcat`, and other modules.

## Key Components

- **Error types**: Classification of runtime verification violations (property violations,
  API misuse patterns)
- **Error collection**: `rvsec-logger-csv` and `rvsec-android/rvsec-logger-logcat` each
  independently define their own `br.unb.cic.mop.eh.ErrorCollector` class under the same
  fully-qualified name; exactly one is selected by the classpath at build/run time (csv or
  logcat, never both) — not a shared interface
- **Shared constants**: Specification set identifiers, error tag formats

## Build

```bash
cd rvsec-core
mvn clean install
```

## Dependencies

None (root of the dependency tree).
