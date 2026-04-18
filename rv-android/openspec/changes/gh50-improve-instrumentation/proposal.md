## Why

The instrumentation pipeline achieves only 17.5% success rate on modern F-Droid APKs with JCA specs (70/400) and 54% with generic_new specs (216/400). The ASE journal dataset (2025) had 0% success (0/364). The root cause is the `ajc` weaver processing ALL classes in `-inpath` — including library code (`com.google.*`, `androidx.*`, `kotlin.*`) — and corrupting stack map frames that `d8` subsequently rejects. Three immediate improvements can raise the success rate to an estimated 50-70%: adding `--no-desugaring` to d8, adding `-proceedOnError` to ajc, and using `-xmlConfigured` with `aop.xml` to exclude library packages from weaving. GitHub Issue: #50.

## What Changes

- **d8 `--no-desugaring` flag**: Added to the d8 command in `__d8()`. Since `--min-api 26` already covers Java 8 features natively, desugaring is unnecessary and causes `j$` prefix conflicts (~7% of failures).
- **ajc `-proceedOnError` flag**: Added to the ajc command in `__weave_monitors()`. Allows partial weaving instead of total failure on OOM or class-level errors (~25% of failures).
- **ajc `-xmlConfigured` + aop.xml**: The `-xmlConfigured` flag enables `aop.xml` in compile-time weaving mode. An `aop.xml` is generated at runtime from configurable YAML exclude patterns, preventing weaving into library packages whose frames are corrupted by the weaver (~64% of failures).
- **Configurable exclude patterns**: A `weaving_excludes.yaml` file in `rv-instrumentation/assets/` defines which packages to exclude. Default list covers `com.google..*`, `androidx..*`, `kotlin..*`, `j$..*`, etc.
- **Pre-filtering fallback** (conditional): If `-xmlConfigured` alone doesn't prevent frame corruption (because ajc still reads excluded classes through `-inpath`), implement Python-based pre-filtering that physically moves excluded classes out of `tmp/` before ajc.

## Capabilities

### New Capabilities

(none — all changes modify existing capability)

### Modified Capabilities

- `instrumentation`: Pipeline weaving phase gains class exclusion via `-xmlConfigured` + `aop.xml`, d8 gains `--no-desugaring`, ajc gains `-proceedOnError`. Configurable exclude patterns via YAML.

## Impact

**Modules affected**:
- rv-instrumentation (`rvandroid.py`, `config.py`, new `assets/weaving_excludes.yaml`) — all production changes

**FRs/NFRs**: FR02 (APK Instrumentation with Monitors), NFR04 (Resilience)

**Expected impact**: Instrumentation success rate from ~17% to ~50-70% for JCA specs on modern APKs. Excludes affect only library code — MOP monitoring of app code is fully preserved.
