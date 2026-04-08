# rvsec-logger-csv

CSV-based violation logger for the RVSec runtime verification framework.

## Purpose

Implements the logging interface from `rvsec-core` using CSV file output.
Records runtime verification violations (property failures, API misuse detections)
as structured CSV rows for offline analysis. Used during development and testing;
production Android deployments use `rvsec-logger-logcat` instead.

## Build

```bash
mvn clean install
```

## Dependencies

- `rvsec-core`: Logger interface and error types
