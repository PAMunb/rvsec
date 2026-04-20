## Why

The instrumentation pipeline achieves only 17.5% success rate on modern F-Droid APKs with JCA specs (70/400) and 54% with generic_new specs (216/400). Analysis across 1164 APKs (ASE 2025 + F-Droid 2026) identified three dominant failure families: (1) d8 rejects stack map frames corrupted by ajc weaving (~37-64% of failures), (2) `j$` prefix conflicts from redundant desugaring (~7-15%), and (3) ajc internal crashes on complex classes (~5-25%). Additionally, the fixed `android-29/android.jar` classpath causes ajc type resolution failures on APKs targeting API 30+, and AspectJ 1.9.24 has known bytecode generation bugs fixed in 1.9.25.1. GitHub Issue: #50.

**Post-landing regression (Apr 2026)**: Empirical validation on `cryptoapp.apk` identified two flags that broke runtime instrumentation while silently producing valid APKs. They were reverted; see Section 8 of `tasks.md` and decision D-REVERT in `design.md`.

## What Changes

- **ajc `-proceedOnError` flag**: Added to the ajc command in `__weave_monitors()`. Allows partial weaving instead of total failure on OOM or class-level errors (~5-25% of failures).
- **ASM COMPUTE_FRAMES post-weaving**: A small Java utility (`rv-frame-computer.jar`) runs after ajc and before d8, recomputing all stack map frames using ASM's `ClassWriter.COMPUTE_FRAMES`. This fixes corrupted frames in classes that WERE weaved. It is the primary mechanism against the AIOOBE family (~37-64% of failures).
- **d8 `skip_stderr=True`**: d8 emits non-fatal "Expected stack map table" warnings to stderr even on success (exit code 0). `skip_stderr=True` is applied to the d8 `execute_command` call so those warnings do not mask success.
- **Dynamic `android.jar` selection**: `__get_android_jar()` selects the `android.jar` matching the APK's `targetSdkVersion` (via `app.sdk_target`), with fallback to the highest available platform. Resolves ajc type resolution failures on APKs targeting API 30+ (TODO #23).
- **AspectJ 1.9.24 → 1.9.25.1**: Upgrade fixes "Attempt to push null on operand stack" variants (#336, #337) — a bytecode generation correctness improvement in the same area as our stack frame problems.

### Reverted during regression investigation (Apr 2026)

- **d8 `--no-desugaring`**: Reverted. It disables synthetic-accessor generation for JDK 11+ nest-mate field access. With `--min-api 26`, Dalvik rejects direct access from an inner class to a private field of its outer class, raising `java.lang.IllegalAccessError` at runtime (observed: `TerminatedMonitorCleaner$Runner` → `TerminatedMonitorCleaner.removedEntries`). Desugaring is required to keep nest-mate semantics valid on Android < 30.
- **ajc `-xmlConfigured` + `aop.xml` + `weaving_excludes.yaml`**: Reverted. With `-xmlConfigured`, ajc switches to XML-driven weaving; aspects not declared under `<aspects>` in the XML are compiled to `.class` but never activated, producing APKs whose bytecode has zero `aspectOf()` calls in app code (observed: 0 woven methods in `br.unb.cic.cryptoapp.*`, empty logcat, zero coverage). Removing the flag restores standard `-sourceroots` weaving. Library exclusion is already achieved by `Coverage.aj`'s `excludedPackages()` pointcut at runtime and by `COMPUTE_FRAMES`' bytecode repair on written classes.

## Capabilities

### New Capabilities

(none — all changes modify existing capability)

### Modified Capabilities

- `instrumentation`: Pipeline gains ASM frame recomputation post-weaving, `-proceedOnError` on ajc, dynamic `android.jar` by `targetSdkVersion`, AspectJ 1.9.25.1 upgrade, and d8 `skip_stderr=True` for non-fatal warnings.

## Impact

**Modules affected**:
- rv-instrumentation (`rvandroid.py`, `config.py`, `pyproject.toml`) — pipeline changes
- rvsec-frame-computer (new Maven module under `rvsec/rvsec-android/`) — ASM COMPUTE_FRAMES utility, fat JAR with `org.ow2.asm:asm:9.7.1`, copied to `rv-android/lib/frame-computer/` via `maven-resources-plugin`
- rvsec parent (`pom.xml`) — AspectJ version property
- Docker base image (`docker/base/Dockerfile`) — AspectJ binary download URL
- Docker development environment — local AspectJ binary update

**FRs/NFRs**: FR02 (APK Instrumentation with Monitors), NFR04 (Resilience)

**Expected impact**: Instrumentation success rate estimated from ~17% to ~33% for JCA (2x baseline, conservative) and from ~54% to ~59% for generic_new. The remaining gap is dominated by d8 internal bugs (AIOOBE in crypto/okio classes) that may be partially addressed by COMPUTE_FRAMES. After the Apr 2026 revert, the achievable rate is expected to be slightly below the original gh50 projection because aop.xml-based library exclusion (which was inactive anyway due to the missing `<aspects>` declaration) was dropped; COMPUTE_FRAMES remains the primary bytecode-repair mechanism.
