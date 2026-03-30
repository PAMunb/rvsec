## Why

`RvsecAnalysisClient.getEntryPoints()` in rvsec-gator iterates only over `output.getActivities()`, ignoring Services, BroadcastReceivers, and ContentProviders as entry points. Methods reachable only through these non-GUI components are excluded from the `reachableSet` and MOP reachability analysis. This was documented as a Known Limitation in phtcosta/ape#9 design but never implemented. Prerequisite for phtcosta/ape#11 (component triggering). GitHub Issue: #45.

## What Changes

- Add `getReceivers()` and `getProviders()` accessors to GATOR's `XMLParser` interface (fields already exist in `AbstractXMLParser`/`DefaultXMLParser`, getters are missing)
- Parse `android:exported` attribute and `android:authorities` (for providers) in `DefaultXMLParser` manifest reading, expose via `isComponentExported()` and `getProviderAuthorities()`
- Extend `RvsecAnalysisClient.getEntryPoints()` to iterate over Services, Receivers, and Providers, adding their lifecycle methods as entry points
- Extend `RvsecAnalysisClient.complementWithCallbacks()` to propagate MOP flags for Service/Receiver/Provider lifecycle methods
- Add rich `components{}` section to the static analysis JSON with intent-filters (or authorities for providers), exported status, MOP reachability, and MOP method signatures per component
- Replace `isActivity`/`isMainActivity` booleans in `reachability[]` with `componentType` string and `isMain` boolean — cleaner representation that scales without adding new booleans per component type
- Update `StaticAnalysisParser` (Python) and `Clazz` domain model to parse the new `componentType`/`isMain` fields

## Capabilities

### New Capabilities

### Modified Capabilities

- `analysis`: Extends the Unified Static Analysis requirement (FR04-FR06) to include Service/BroadcastReceiver/ContentProvider lifecycle methods as entry points, add `components{}` JSON section with intent-filters and MOP data, and replace `isActivity`/`isMainActivity` booleans with `componentType`/`isMain` in `reachability[]` entries

## Impact

- **rvsec-gator** (`XMLParser`, `DefaultXMLParser`, `RvsecAnalysisClient`): Interface change + manifest parsing enrichment + entry point enumeration + new `components{}` JSON section. This is a Java Maven module in the rvsec umbrella repo, not a Python rv-android module.
- **Static analysis JSON**: New `components{}` section. In `reachability[]`, `isActivity`/`isMainActivity` replaced by `componentType`/`isMain`. All consumers must be updated.
- **rv-static-analysis Python parser**: `StaticAnalysisParser` and `Clazz` domain model updated to parse `componentType`/`isMain` instead of `isActivity`/`isMainActivity`. Old fields removed from JSON — no backward compatibility shims.
- **Downstream consumers**: APE-RV `MopData` (phtcosta/ape#11) needs update to parse `components{}` and new reachability format.
- **Experiment reproducibility**: Re-running static analysis produces enriched JSON. Existing JSON files remain valid.
- **Coverage metric impact**: Adding new entry points expands the `reachableSet` denominator, so coverage percentages may decrease even without exploration degradation. This is expected — the denominator now reflects a more complete picture of the app.

## Known Limitations

- **Dynamic BroadcastReceivers**: Only manifest-declared (static) receivers are included. Receivers registered programmatically via `registerReceiver()` are not detectable by static analysis of the manifest.
- **`android:exported` default**: The default inference (`true` if has intent-filters, `false` otherwise) is correct for API 31+ (Android 12). For older `targetSdkVersion`, Android defaulted to `true` for all components with intent-filters. This change does not read `targetSdkVersion` — the API 31+ behavior is applied universally.
- **JobScheduler/WorkManager**: `JobService.onStartJob()` and `Worker.doWork()` are not included as entry points. These are scheduled via APIs, not declared as manifest components with intent-filters.
- **Application class**: `Application.onCreate()` and `attachBaseContext()` are not included.
