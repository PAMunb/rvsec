## Why

The instrumentation pipeline achieves only 17.5% success rate on modern F-Droid APKs with JCA specs (70/400) and 54% with generic_new specs (216/400). Analysis across 1164 APKs (ASE 2025 + F-Droid 2026) identified three dominant failure families: (1) d8 rejects stack map frames corrupted by ajc weaving (~37-64% of failures), (2) `j$` prefix conflicts from redundant desugaring (~7-15%), and (3) ajc internal crashes on complex classes (~5-25%). Additionally, the fixed `android-29/android.jar` classpath causes ajc type resolution failures on APKs targeting API 30+, and AspectJ 1.9.24 has known bytecode generation bugs fixed in 1.9.25.1. GitHub Issue: #50.

## What Changes

- **d8 `--no-desugaring` flag**: Added to the d8 command in `__d8()`. Since `--min-api 26` already covers Java 8 features natively, desugaring is unnecessary and causes `j$` prefix conflicts (~7-15% of failures).
- **ajc `-proceedOnError` flag**: Added to the ajc command in `__weave_monitors()`. Allows partial weaving instead of total failure on OOM or class-level errors (~5-25% of failures).
- **ajc `-xmlConfigured` + aop.xml**: The `-xmlConfigured` flag enables `aop.xml` in compile-time weaving mode. An `aop.xml` is generated at runtime from configurable YAML exclude patterns, preventing weaving into library packages whose frames are corrupted by the weaver. Exclude patterns aligned with `Coverage.aj` exclusions.
- **ASM COMPUTE_FRAMES post-weaving**: A small Java utility (`rv-frame-computer.jar`) runs after ajc and before d8, recomputing all stack map frames using ASM's `ClassWriter.COMPUTE_FRAMES`. This fixes corrupted frames in classes that WERE weaved (app code), complementing aop.xml which prevents corruption in excluded libraries. Together, these two mechanisms address the full AIOOBE family (~37-64% of failures).
- **Dynamic `android.jar` selection**: `__get_android_jar()` selects the `android.jar` matching the APK's `targetSdkVersion` (via `app.sdk_target`), with fallback to the highest available platform. Resolves ajc type resolution failures on APKs targeting API 30+ (TODO #23).
- **AspectJ 1.9.24 → 1.9.25.1**: Upgrade fixes "Attempt to push null on operand stack" variants (#336, #337) — a bytecode generation correctness improvement in the same area as our stack frame problems.
- **Configurable exclude patterns**: A `weaving_excludes.yaml` file in `rv-instrumentation/assets/` defines which packages to exclude. Default list aligned with `Coverage.aj` exclusions.

## Capabilities

### New Capabilities

(none — all changes modify existing capability)

### Modified Capabilities

- `instrumentation`: Pipeline gains ASM frame recomputation post-weaving, class exclusion via `-xmlConfigured` + `aop.xml`, `--no-desugaring` on d8, `-proceedOnError` on ajc, dynamic `android.jar` by `targetSdkVersion`, and AspectJ 1.9.25.1 upgrade. Configurable exclude patterns via YAML.

## Impact

**Modules affected**:
- rv-instrumentation (`rvandroid.py`, `config.py`, new `assets/weaving_excludes.yaml`, new `assets/rv-frame-computer.jar`) — pipeline changes
- rvsec parent (`pom.xml`) — AspectJ version property
- Docker base image (`docker/base/Dockerfile`) — AspectJ binary download URL
- Docker development environment — local AspectJ binary update

**FRs/NFRs**: FR02 (APK Instrumentation with Monitors), NFR04 (Resilience)

**Expected impact**: Instrumentation success rate estimated from ~17% to ~33% for JCA (2x baseline, conservative) and from ~54% to ~59% for generic_new. The remaining gap is dominated by d8 internal bugs (AIOOBE in crypto/okio classes) that may be partially addressed by COMPUTE_FRAMES.

**MOP coverage trade-off**: Excluding library packages from weaving removes MOP monitoring of calls originating **inside** excluded libraries. All 168 MOP specs use `call()` semantics (caller-site interception), so calls from **app code** to monitored APIs remain 100% monitored. The trade-off is defensible: (1) `Coverage.aj` already excludes the same packages from coverage tracking, (2) the research objective is detecting misuse in developer code, not library internals, (3) `App.code_package` (via `PackageDetector`) validates that exclusions never cover the app's own package. This is a standard scope decision in Android analysis literature (CogniCrypt, CrySL) and should be documented as a threat to validity.
