## Context

APE-RV's MOP-guided scoring relies on static analysis JSON produced by rvsec-gator (`RvsecAnalysisClient`). The JSON contains `reachability[]`, `windows[]`, and `transitions[]` sections. Currently, only Activity classes serve as entry points for the call graph traversal (`getEntryPoints()` at L252-266 of `RvsecAnalysisClient.java`). Services, BroadcastReceivers, and ContentProviders declared in AndroidManifest.xml are ignored, causing methods reachable only through these components to be absent from the reachability analysis.

This was documented as a Known Limitation in phtcosta/ape#9 design and analyzed in `rv-android/docs/analise_broadcast_service_integration.md`. The ape repo has comprehensive change artifacts at `ape/openspec/changes/gh11-enrich-static-analysis-entrypoints/` covering both rvsec-gator and APE-RV sides. This design covers the rvsec-gator side only. Refs #45, prerequisite for phtcosta/ape#11.

All four Android component types are covered: Activity (existing), Service (new), BroadcastReceiver (new), ContentProvider (new). Each component type can be triggered via ADB for testing: `am start` (Activity), `am startservice` (Service), `am broadcast` (Receiver), `content query/insert/update/delete` (Provider).

### Current state in GATOR (verified via code analysis)

- `XMLParser` interface: `getActivities()` (L152), `getServices()` (L154). No `getReceivers()`.
- `AbstractXMLParser` (inner class of `XMLParser`): fields `activities` (L35), `services` (L36), `receivers` (L37). Has `getActivities()` implementation (L46-49). No `getServices()` or `getReceivers()` implementation.
- `DefaultXMLParser`: `getServices()` (L169-171) returns `services.iterator()`. Parses services at L415-426 and receivers at L428-436, calling `readIntentFilters(cls, n)` for both.
- `IntentFilterManager` (singleton): stores `Map<String, Set<IntentFilter>>` keyed by component class name. `IntentFilter` has `getActions()` → `Set<String>`, `getCategories()` → `Set<String>`.
- `android:exported` attribute is NOT parsed by GATOR anywhere in the codebase.
- `RvsecAnalysisClient.getEntryPoints()` (L252-266): iterates only `output.getActivities()`.
- `RvsecAnalysisClient.complementWithCallbacks()` (L351-393): lifecycle + event handlers for activities only.
- `RvsecAnalysisClient.writeJson()` (L739-782): 3 sections (reachability, windows, transitions) with `w.flush()` after each.
- `RvsecAnalysisClient.writeReachability()` (L784-821): writes `isActivity` (L802), `isMainActivity` (L803) per class — to be replaced by `componentType`/`isMain`.
- `run()` method (L70-145): no direct XMLParser access, but `XMLParser.Factory.getXMLParser()` available as singleton.

## Architecture

4 files in rvsec-gator (2 Maven modules: sootandroid, client) + 2 files in rv-static-analysis (Python).

### Key Components

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| `XMLParser.getReceivers()` | Expose parsed receiver class names | AndroidManifest.xml | `Iterator<String>` |
| `XMLParser.getProviders()` | Expose parsed provider class names | AndroidManifest.xml | `Iterator<String>` |
| `XMLParser.isComponentExported()` | Expose exported attribute per component | AndroidManifest.xml | `boolean` |
| `XMLParser.getProviderAuthorities()` | Expose provider authorities | AndroidManifest.xml | `String` |
| `DefaultXMLParser.readManifest()` | Parse exported/authorities during component handling | DOM NamedNodeMap | `componentExported` Map, `providerAuthorities` Map |
| `RvsecAnalysisClient.getEntryPoints()` | Add Service/Receiver/Provider lifecycle methods as entry points | `XMLParser` + `Scene` | `Set<SootMethod>` |
| `RvsecAnalysisClient.complementWithCallbacks()` | MOP flag propagation for Service/Receiver/Provider callbacks | Components + graph | Updated reachability sets |
| `RvsecAnalysisClient.writeComponents()` | Write `components{}` JSON with intent-filters/authorities | `XMLParser` + `IntentFilterManager` + reachability sets | JSON section |
| `RvsecAnalysisClient.writeReachability()` | Write componentType/isMain instead of isActivity/isMainActivity | Component name sets | Updated JSON entries |
| `StaticAnalysisParser._parse_classes()` | Parse componentType/isMain fields | JSON reachability[] | Updated `Clazz` model |

## Mapping: Spec → Implementation → Test

| Requirement | Implementation | Test |
|-------------|---------------|------|
| INV-EP-01: Service lifecycle entry points | `getEntryPoints()` Service loop | Integration: JSON output for APK with Service |
| INV-EP-02: Receiver onReceive entry point | `getEntryPoints()` Receiver loop | Integration: JSON output for APK with Receiver |
| INV-EP-03: Provider lifecycle entry points | `getEntryPoints()` Provider loop | Integration: JSON output for APK with Provider |
| INV-EP-04: components{} in JSON | `writeComponents()` | Integration: verify JSON structure |
| INV-EP-05: Existing data unchanged | No change to existing code paths | Integration: diff JSON before/after |
| INV-EP-06: Intent-filters in components | `writeComponents()` reads IntentFilterManager | Integration: verify intentFilters |
| INV-EP-07: Authorities in providers | `writeComponents()` reads providerAuthorities | Integration: verify authorities field |
| INV-EP-08: MOP flag propagation | `complementWithCallbacks()` | Integration: verify reachesMop for component lifecycle |
| INV-EP-09: componentType/isMain in reachability | `writeReachability()` + `StaticAnalysisParser` + `Clazz` | Integration: verify JSON fields + Python parsing |
| INV-EP-10: exported attribute | `DefaultXMLParser` + `isComponentExported()` | Integration: verify exported field |

## Goals / Non-Goals

**Goals:**
- Service/BroadcastReceiver/ContentProvider lifecycle methods included as entry points in the call graph traversal
- Rich `components{}` JSON section with intentFilters (or authorities for providers), exported, reachesMop, mopMethods
- MOP flag propagation for Service/Receiver/Provider callbacks
- Replace `isActivity`/`isMainActivity` booleans with `componentType` string + `isMain` boolean in `reachability[]`
- Update `StaticAnalysisParser` and `Clazz` model to parse the new format — no legacy fields preserved

**Non-Goals:**
- APE-RV MopData parser changes (phtcosta/ape#11)
- Runtime component triggering (phtcosta/ape#11)
- Modifying `windows[]` structure (non-Activity components have no GUI windows)
- Dynamic BroadcastReceivers (registered via `registerReceiver()`, not in manifest)
- JobScheduler/WorkManager entry points
- Application class entry points (`Application.onCreate()`, `attachBaseContext()`)

## Decisions

**D1: Resolve class names via `Scene.v().getSootClassUnsafe()`**

`output.getActivities()` returns `Set<SootClass>` from the flowgraph, but there is no equivalent for Services/Receivers. `XMLParser.getServices()/getReceivers()` return `Iterator<String>`. We resolve to `SootClass` using `Scene.v().getSootClassUnsafe(className)`, which returns `null` for unresolvable classes.

Note: The ape design cited `ServiceTestingClient` (L54) as using this pattern. Code analysis revealed `ServiceTestingClient` actually uses `getSootClass()` (which can throw). We use `getSootClassUnsafe()` for safety, following the pattern in `rvsec-taint/TesteLayout.java` (L59) and `rvsec-gesda/SootAnalyze.java` (L222).

**D2: Lifecycle methods found by iterating `getMethods()` + filtering by name**

The ape design suggested `getMethodByNameUnsafe()`. Soot's `getMethodByName()` throws `AmbiguousMethodException` for overloaded methods (e.g., `onBind` with different signatures). Instead, iterate `SootClass.getMethods()` and filter by name. This matches the existing pattern in `getEntryPoints()` which iterates `activity.getMethods()`.

**D3: Structured `components{}` with `receivers[]`/`services[]`/`providers[]`**

Type-specific arrays enable different lifecycle method sets and triggering construction per component type. From `analise_broadcast_service_integration.md` analysis. Each type has its own ADB triggering mechanism: `am startservice` (Service), `am broadcast` (Receiver), `content query/insert/update/delete` (Provider).

**D4: Parse `android:exported` in `DefaultXMLParser.readManifest()`**

GATOR does not parse `android:exported`. We add extraction during service/receiver/provider element handling (L415-436+), where we already have the `NamedNodeMap`. Store in `Map<String, Boolean> componentExported` in `AbstractXMLParser`. Expose via `isComponentExported(String className)` in `XMLParser` interface. Default: `true` if component has intent-filters, `false` otherwise. Note: this default is correct for API 31+ (Android 12). For older `targetSdkVersion` (API < 31), Android defaulted `exported` to `true` for any component — even those without intent-filters. We apply the API 31+ behavior universally — this is a known simplification documented in the proposal's Known Limitations.

**D5: All component getters in `AbstractXMLParser`**

All component fields (`activities`, `services`, `receivers`) live in `AbstractXMLParser` (L35-37). `getActivities()` is already implemented there (L46-49). We add `getReceivers()`, `getProviders()`, and move `getServices()` from `DefaultXMLParser` (L169) to `AbstractXMLParser` — fixing the existing inconsistency where `getServices()` was the only getter not co-located with its field. Remove the `getServices()` override from `DefaultXMLParser`. All four getters follow the same pattern: `return <field>.iterator()`.

**D6: `components{}` is the last JSON section (Section 4)**

`writeJson()` writes sections in priority order: reachability (most critical) → windows → transitions → components (least critical). If a timeout interrupts, critical sections are already flushed. The `w.flush()` pattern is maintained.

**D7: ContentProvider lifecycle methods and `authorities` attribute**

ContentProviders are the 4th Android component type, declared via `<provider>` in the manifest. Unlike Services/Receivers that use intent-filters for triggering, Providers are addressed by `content://` URIs derived from the `android:authorities` attribute. Lifecycle methods included as entry points: `onCreate`, `query`, `insert`, `update`, `delete`, `call`, `openFile`. These are the methods that can contain application logic (including cryptographic operations). The `authorities` field replaces `intentFilters` in the provider's JSON structure, since providers use content URIs for ADB triggering (`adb shell content query --uri content://<authority>/<path>`). Parsing: extract `android:authorities` from `NamedNodeMap` during `<provider>` element handling in `readManifest()`. Store in `Map<String, String> providerAuthorities` in `AbstractXMLParser`.

**D8: Service lifecycle methods — complete set**

Service lifecycle methods included as entry points: `onCreate`, `onStartCommand`, `onBind`, `onUnbind`, `onRebind`, `onDestroy`, `onHandleIntent`. Note: `onRebind` was missing from the original design — it is called when a previously unbound client re-binds to a service, and may contain application logic. `onTaskRemoved` and `onTrimMemory` are excluded: they are system callbacks for resource management, unlikely to contain application logic relevant to MOP.

**D9: `componentType` string replaces boolean flags in `reachability[]`**

The current JSON uses `isActivity` (boolean) and `isMainActivity` (boolean) per reachability entry. Adding `isService`, `isReceiver`, `isProvider` would mean 5 booleans where only one can be true (a class is exactly one Android component type, or none). This is replaced by: `componentType` (string: `"activity"`, `"service"`, `"receiver"`, `"provider"`, or `null` for non-component classes) and `isMain` (boolean: `true` only for the main launcher activity). The old `isActivity`/`isMainActivity` fields are removed from the JSON — no backward compatibility. The `Clazz` domain model in rv-static-analysis is updated accordingly: `is_activity: bool` and `is_main_activity: bool` become `component_type: str | None` and `is_main: bool`. `StaticAnalysisParser._parse_classes()` is updated to read the new fields.

## API Design

### `XMLParser.getReceivers() -> Iterator<String>`
- **Pre**: Manifest has been parsed
- **Post**: Returns iterator over fully qualified receiver class names
- **Error**: Never throws; returns empty iterator if no receivers

### `XMLParser.getProviders() -> Iterator<String>`
- **Pre**: Manifest has been parsed
- **Post**: Returns iterator over fully qualified provider class names
- **Error**: Never throws; returns empty iterator if no providers

### `XMLParser.isComponentExported(String className) -> boolean`
- **Pre**: Manifest has been parsed
- **Post**: Returns exported status for the given component class name
- **Error**: Returns `false` for unknown class names

### `XMLParser.getProviderAuthorities(String className) -> String`
- **Pre**: Manifest has been parsed
- **Post**: Returns the `android:authorities` value for the given provider class name
- **Error**: Returns `null` for unknown class names or non-provider classes

### `RvsecAnalysisClient.getEntryPoints(GUIAnalysisOutput output) -> Set<SootMethod>`
- **Pre**: output non-null, Soot Scene initialized, XMLParser singleton available
- **Post**: Set contains lifecycle methods + public/protected methods of Activities, Services, Receivers, and Providers
- **Error**: Unresolvable classes logged as WARNING and skipped

### `RvsecAnalysisClient.writeComponents(JsonWriter w, Set<SootMethod> reachesMopSet) -> void`
- **Pre**: JsonWriter in object context, XMLParser and IntentFilterManager singletons available
- **Post**: Writes `"components": {"receivers": [...], "services": [...], "providers": [...]}` with full enrichment data
- **Error**: IOException propagated to caller (same as other write methods)

## Data Flow

```
AndroidManifest.xml
    │
    ▼
DefaultXMLParser.readManifest()
    ├── activities[]       → (existing) → GUIAnalysisOutput.getActivities()
    ├── services[]         → getServices() ────────────────────┐
    ├── receivers[]        → getReceivers() ───────────────────┤
    ├── providers[]        → getProviders() ───────────────────┤
    ├── intentFilters      → IntentFilterManager ──────────────┤
    ├── componentExported  → isComponentExported() ────────────┤
    └── providerAuthorities → getProviderAuthorities() ───────┤
                                                                │
                                                                ▼
                                              RvsecAnalysisClient
                                              ├── getEntryPoints(): resolves via getSootClassUnsafe()
                                              │   → adds lifecycle + public/protected methods
                                              ├── multiSourceBfs(): expanded reachable/reachesMop sets
                                              ├── complementWithCallbacks(): MOP propagation
                                              ├── writeReachability(): componentType, isMain
                                              └── writeComponents(): intentFilters/authorities, exported, reachesMop, mopMethods
                                                                │
                                                                ▼
                                              Static Analysis JSON
                                              ├── reachability[] (expanded)
                                              ├── windows[], transitions[] (unchanged)
                                              └── components{} (NEW: receivers[], services[], providers[])
```

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| Class not in Soot Scene | Manifest declares class not in APK | Log WARNING, skip class | Continue with remaining classes |
| Lifecycle method not found | Method not overridden in class | Skip silently (expected) | No recovery needed |
| `android:exported` attr absent | Manifest element lacks attribute | Default: true with intent-filter, false without | API 31+ behavior (see Known Limitations) |
| `android:authorities` attr absent | Provider without authorities | Log WARNING, use empty string | Provider still included in components |
| No non-Activity components | App has only Activities | Write empty `components{}` | `{"receivers": [], "services": [], "providers": []}` |

## Risks / Trade-offs

- **[Risk: Increased analysis time]** More entry points mean larger call graphs. Mitigation: Services/Receivers/Providers are typically few (1-5 per app) vs activities (5-20). Marginal impact.
- **[Risk: `exported` default inference]** The `true-if-has-intent-filter` default is correct for API 31+. For older targets, it may differ. Mitigation: documented as Known Limitation. This is the standard Android documentation behavior and matches what build tools enforce for modern apps.
- **[Risk: Coverage % decrease]** Adding new entry points expands `reachableSet`, increasing the denominator of coverage metrics. Coverage percentages may decrease even without exploration degradation. Mitigation: this is expected and correct — the previous metric was artificially inflated by excluding reachable methods.
- **[Trade-off: No MopScorer changes]** Component MOP data is produced but not used for priority scoring in this change. It feeds APE-RV's stagnation escape hatch (phtcosta/ape#11).

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Build | Java compilation | `mvn clean package` in rvsec-gator | 1 |
| Build | Python tests | `uv run pytest modules/rv-static-analysis/tests/ -v` | existing + new |
| Integration | Existing Java tests pass | `RvsecAnalysisClientIT` | existing |
| Integration | JSON with Services/Receivers/Providers | Generate JSON for test APK, verify structure | manual |
| Integration | JSON without non-Activity components | Generate JSON for simple APK, verify empty components | manual |
| Integration | Provider authorities in JSON | Generate JSON for APK with ContentProvider, verify authorities | manual |
| Unit | Python parser: componentType/isMain | `StaticAnalysisParser` parses new fields into `Clazz` | new |
| Unit | Python parser: old fields absent | Verify no `isActivity`/`isMainActivity` in JSON or model | new |

## Lifecycle Methods Reference

| Component Type | Lifecycle Methods (entry points) | ADB Triggering |
|---------------|----------------------------------|----------------|
| Activity | (existing — via GATOR `getLifecycleHandlers`) | `am start -n pkg/.Activity` |
| Service | `onCreate`, `onStartCommand`, `onBind`, `onUnbind`, `onRebind`, `onDestroy`, `onHandleIntent` | `am startservice -n pkg/.Service` |
| BroadcastReceiver | `onReceive` | `am broadcast -a action.NAME` |
| ContentProvider | `onCreate`, `query`, `insert`, `update`, `delete`, `call`, `openFile` | `content query/insert/update/delete --uri content://authority/path` |

## Open Questions

None — all design questions resolved through code analysis and multi-LLM review (Claude, Codex, Gemini, Minimax, Qwen).
