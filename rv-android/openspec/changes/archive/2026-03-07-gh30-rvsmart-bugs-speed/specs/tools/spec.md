# Delta Spec: tools (gh30-rvsmart-bugs-speed)

**Base**: `openspec/specs/tools/spec.md`
**Change**: gh30-rvsmart-bugs-speed
**Affected sections**: RVSmartTool Execution Contract, RVSmartTool Variants

---

## Changed: RVSmartTool Execution Contract

### Addition: `--code-package` parameter

In step 5 of the execution contract, the command construction SHALL additionally include `--code-package <code_package>` after `--package <package_name>`:

```
adb -s <device_serial> shell CLASSPATH=/data/local/tmp/rvsmart.jar /system/bin/app_process
    /data/local/tmp/ br.unb.cic.rvsmart.Main
    --package <package_name> --code-package <code_package> --timeout <timeout>
    [--static-data ...] [--config ...] [--mode ...]
```

Where `<code_package>` comes from `app.code_package` (detected by `PackageDetector` during APK loading). The `--code-package` parameter is used by the Java agent's `StaticMap`/`MopScorer` for activity-based MOP lookup — the static analysis JSON keys use code-package-qualified class names (e.g., `org.godotengine.godot.GodotLib.initialize(...)`) which may differ from the manifest package (e.g., `ir.hsn6.trans`) in ~27.5% of APKs.

`--code-package` is **not** used for out-of-app detection. OOA detection uses `ComponentName.getPackageName()` (manifest package of the foreground activity) compared against `--package` (also manifest package).

When running standalone (no rv-android), `--code-package` is optional. The Java agent falls back to `--package` (manifest package) when `--code-package` is absent.

#### Scenario: Command includes code package
- **WHEN** `_build_main_command(app, device_serial, timeout, has_static_data)` is called
- **THEN** the command SHALL include `--code-package app.code_package` after `--package app.package_name`

#### Scenario: Standalone execution without code package
- **WHEN** the rvsmart JAR is invoked without `--code-package`
- **THEN** the Java agent SHALL use the `--package` value as fallback for `StaticMap` lookups

---

## New: Out-of-App Detection and Recovery

The rvsmart Java agent SHALL detect when the foreground application is not the target app and recover automatically.

### Detection mechanism

After each action execution, the agent calls `AppController.getCurrentActivity()` to obtain the `ComponentName` of the top activity. It compares `cn.getPackageName()` (manifest package of the foreground app) against `Config.getPackage()` (the `--package` CLI arg, manifest package of the target app). If they differ, the agent is out-of-app (OOA).

This approach is reliable because `ComponentName.getPackageName()` always returns the manifest package, and `--package` is also the manifest package. No code-package detection needed for OOA.

### Two-tier recovery

1. **Launcher fast-path**: Known launcher packages (`com.android.launcher3`, `com.google.android.apps.nexuslauncher`, `com.android.launcher`) trigger immediate RESTART bypassing the tolerance counter. The agent has no useful actions on the home screen.

2. **Tolerance for other packages**: Non-launcher OOA packages (e.g., Chrome opened by an in-app link) allow up to 3 iterations (OOA tolerance counter) before forcing RESTART. This gives the agent a chance to return via BACK.

### Consecutive failure fallback

If the agent detects 3 consecutive OOA events immediately after RESTART (the app keeps redirecting to an external intent on startup), fall back to `forceStop` + `startApp` recovery. Reset the counter when the agent successfully returns to the target app.

### Scoring and learning

OOA iterations SHALL be skipped for scoring and learning — they produce no useful exploration data.

### RVTRACK logging

OOA events SHALL be logged via RVTRACK with: trigger action type, destination package, recovery type (`out_of_app_launcher` or `out_of_app_tolerance`).

#### Scenario: Launcher detected
- **WHEN** `AppController.getCurrentActivity().getPackageName()` returns `com.google.android.apps.nexuslauncher`
- **AND** `Config.getPackage()` is `com.example.myapp`
- **THEN** the agent SHALL immediately execute RESTART
- **AND** the OOA tolerance counter SHALL NOT be decremented
- **AND** RVTRACK SHALL log the event as `out_of_app_launcher`

#### Scenario: Non-launcher OOA within tolerance
- **WHEN** `AppController.getCurrentActivity().getPackageName()` returns `org.chromium.chrome`
- **AND** the OOA tolerance counter is > 0
- **THEN** the agent SHALL decrement the tolerance counter
- **AND** the agent SHALL NOT force RESTART (allows BACK recovery)
- **AND** scoring/learning SHALL be skipped for this iteration

#### Scenario: Non-launcher OOA tolerance exhausted
- **WHEN** the foreground package is `org.chromium.chrome`
- **AND** the OOA tolerance counter reaches 0
- **THEN** the agent SHALL execute RESTART
- **AND** the tolerance counter SHALL be reset to 3

#### Scenario: Consecutive RESTART failures
- **WHEN** the agent has executed RESTART 3 times consecutively
- **AND** each time the foreground package is still not the target app
- **THEN** the agent SHALL fall back to `forceStop` + `startApp`

---

## Changed: Default throttle

In the variants table, the default `throttle_ms` for `default` and `mvp` variants changes from 50 to 100. The `fast` variant remains at 30. The `hybrid` variant changes from 50 to 100.

| Variant | mode | throttle_ms | Notes |
|---------|------|-------------|-------|
| `default` | pure_algorithm | 100 | Moderate throttle to avoid UI instability |
| `mvp` | pure_algorithm | 100 | Same as default |
| `fast` | pure_algorithm | 30 | Reduced throttle for maximum throughput |
| `hybrid` | multimode | 100 | LLM hybrid mode, requires SGLang |

Rationale: 50ms risks acting before the screen stabilizes, potentially increasing out-of-app events. 100ms is a safer moderate reduction from the original 200ms default in the Java code.
