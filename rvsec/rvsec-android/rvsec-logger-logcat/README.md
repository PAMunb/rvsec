# rvsec-logger-logcat

Logcat-based violation logger for runtime verification on Android devices.

## Purpose

Implements the logging interface from `rvsec-core` using Android's logcat system.
When an instrumented APK runs on a device/emulator, this logger outputs violation
events with the `RVSEC` tag to logcat. The Python `rv-platform` module captures
this tag in real-time via `adb logcat` to track specification violations.

## Log Format

Violations are logged as:
```
V/RVSEC: <errorSummary>,<expecting>
```

Coverage events (`RVSEC-COV`) are produced separately by the weaver's `Coverage.aj`,
not by this module.

## Integration

```
Instrumented APK (on device)
    -> rvsec-logger-logcat (this module, runs inside APK)
    -> Android logcat stream
    -> rv-platform (Python, captures via adb logcat)
    -> rv-coverage (Python, parses RVSEC tags)
```

## Build

```bash
mvn clean install
```

## Dependencies

- `rvsec-core`: Logger interface and error types
- Android SDK (logcat API)
