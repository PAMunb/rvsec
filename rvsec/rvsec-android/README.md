# rvsec-android

Parent Maven module aggregating Android-specific submodules for the RVSec framework.

## Active Submodules

| Module | Purpose | Status |
|--------|---------|--------|
| **rvsec-apk** | APK metadata extraction (manifest, components) | Active |
| **rvsec-logger-logcat** | Logcat-based violation logging on device | Active |
| **rvsec-gator** | GATOR static analysis (client + server) | Active |
| rvsmart | RVSmart exploration engine (Java side) | Archived on Python side |

## Deprecated/Inactive Submodules

| Module | Reason |
|--------|--------|
| rvsec-gesda | Replaced by unified GATOR client (commented out in POM) |
| rvsec-reachability | Replaced by unified GATOR client (commented out in POM) |
| rvsec-taint | For testing only (deprecated) |
| rvsec-methods-extractor | Deprecated |

## Build

```bash
cd rvsec-android
mvn clean install -DskipTests
```

Builds all active submodules. The GATOR module includes the external sootandroid
framework (178 Java files) alongside our client code (6 src files).

## Integration with rv-android

The Python `rv-static-analysis` module invokes the GATOR JAR (built here) to perform
static analysis on Android APKs. The `rv-instrumentation` module uses the logcat logger
(woven into instrumented APKs) to capture runtime events.
