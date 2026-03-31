<!-- Groups 1 and 2 are independent and can run in parallel (different files/repos).
     Within Group 2, tasks 2.1-2.2 must precede 2.3-2.5 (entry points affect reachability sets used by writeComponents).
     Group 2.4 (writeJson integration) depends on 2.3 (writeComponents exists).
     Group 2.5 (writeReachability) is independent of 2.3-2.4.
     Group 3 depends on Groups 1 and 2.
     Group 4 (Python parser) is independent of Groups 1-3 but must use the same JSON format.
     Critical path: 1 → 2.1 → 2.3 → 2.4 → 3

     Group 1-3 paths relative to:
     /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-android/rvsec-gator/

     Group 4 paths relative to:
     /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/modules/rv-static-analysis/
-->

## 1. XMLParser — all component getters + exported + authorities

- [x] 1.1 Add `getReceivers()` method to `XMLParser` interface (`sootandroid/.../xml/XMLParser.java` L154, after `getServices()`). Return type: `Iterator<String>`.
- [x] 1.2 Add `getReceivers()` implementation in `AbstractXMLParser` inner class (after `getActivities()` at L49): `return receivers.iterator()`.
- [x] 1.3 Move `getServices()` from `DefaultXMLParser` (L169-171) to `AbstractXMLParser` inner class, next to `getActivities()` and `getReceivers()`. Remove the override from `DefaultXMLParser`. All component getters now live in `AbstractXMLParser` alongside their fields.
- [x] 1.4 Add `providers` field (`ArrayList<String>`) to `AbstractXMLParser` inner class. Add `getProviders()` method to `XMLParser` interface with implementation in `AbstractXMLParser`: `return providers.iterator()`.
- [x] 1.5 Add `componentExported` field (`Map<String, Boolean>`) to `AbstractXMLParser` inner class. Add `isComponentExported(String className)` method to `XMLParser` interface with implementation in `AbstractXMLParser`: `return componentExported.getOrDefault(className, false)`.
- [x] 1.6 Add `providerAuthorities` field (`Map<String, String>`) to `AbstractXMLParser` inner class. Add `getProviderAuthorities(String className)` method to `XMLParser` interface with implementation in `AbstractXMLParser`: `return providerAuthorities.get(className)`.
- [x] 1.7 Parse `android:exported` attribute in `DefaultXMLParser.readManifest()` for services (L415-426), receivers (L428-436), and providers. Extract from `NamedNodeMap` via `getNamedItemNS(ANDROID_NS, "exported")`. If attribute absent, default to `true` if component has intent-filters, `false` otherwise. Store in `componentExported` map.
- [x] 1.8 Parse `<provider>` elements in `DefaultXMLParser.readManifest()` (add after receiver handling block). Extract `android:name` → resolve via `Helper.getClassName()`, add to `providers` list. Extract `android:authorities` → store in `providerAuthorities` map. Extract `android:exported` → store in `componentExported` map (default `false` for providers without intent-filters).

## 2. RvsecAnalysisClient — entry points + JSON output

- [x] 2.1 Modify `getEntryPoints()` (`client/.../clients/RvsecAnalysisClient.java` L252-266) to also iterate Services, Receivers, and Providers. Access via `XMLParser.Factory.getXMLParser().getServices()`, `getReceivers()`, and `getProviders()`. Resolve each class name to `SootClass` via `Scene.v().getSootClassUnsafe(className)`. If null, log WARNING and skip. For each resolved class, iterate `getMethods()` and add: (a) lifecycle methods by name (Services: `onCreate`, `onStartCommand`, `onBind`, `onUnbind`, `onRebind`, `onDestroy`, `onHandleIntent`; Receivers: `onReceive`; Providers: `onCreate`, `query`, `insert`, `update`, `delete`, `call`, `openFile`), (b) public/protected methods (same pattern as Activities).
- [x] 2.2 Modify `complementWithCallbacks()` (L351-393) to add Service/Receiver/Provider lifecycle methods to the `callbacks` set. Add a second loop after the existing Activity loop (L362-364): resolve Service/Receiver/Provider classes (same getSootClassUnsafe pattern as 2.1), iterate their methods, add lifecycle methods by name to `callbacks`. These then receive MOP flag propagation via the existing graph traversal code (L383-393).
- [x] 2.3 Add `writeComponents(JsonWriter w, Set<SootMethod> reachesMopSet)` method. Access `XMLParser.Factory.getXMLParser()` for service/receiver/provider names + exported status + provider authorities. Access `IntentFilterManager.v().getAllFilters()` for intent-filters per component (Services/Receivers only). For each component: resolve to `SootClass` via `getSootClassUnsafe()`, find lifecycle methods, check which are in `reachesMopSet`, collect their signatures. Write JSON structure: `"components": {"receivers": [...], "services": [...], "providers": [...]}`. Services/Receivers have fields: `className`, `intentFilters` (array of `{actions, categories}`), `exported`, `reachesMop`, `mopMethods`. Providers have fields: `className`, `authorities` (string), `exported`, `reachesMop`, `mopMethods`.
- [x] 2.4 Call `writeComponents()` from `writeJson()` (L739-782) as Section 4 after transitions (L774-775). Insert before `w.endObject()`: `w.name("components"); writeComponents(w, reachesMopSet); w.flush();`. The `reachesMopSet` parameter must be passed through from `writeJson()` signature (add parameter).
- [x] 2.5 Modify `writeReachability()` (L784-821) to replace `isActivity` (L802) and `isMainActivity` (L803) with `componentType` and `isMain`. Build `Set<String>` of service, receiver, and provider class names from `XMLParser.Factory.getXMLParser()` at the start of the method. For each class, determine `componentType`: `"activity"` if in activities set, `"service"` if in services set, `"receiver"` if in receivers set, `"provider"` if in providers set, `null` otherwise. Write `w.name("componentType").value(componentType)` and `w.name("isMain").value(cls.equals(mainActivity))`. Remove the old `isActivity`/`isMainActivity` writes.

## 3. Build + Verification (rvsec-gator)

- [x] 3.1 `mvn clean package` in rvsec-gator module — verify BUILD SUCCESS.
- [x] 3.2 Run existing integration tests (`RvsecAnalysisClientIT`) — verify no regressions.
- [x] 3.3 Generate JSON for a test APK with known Services/Receivers/Providers. Verify: `components{}` present with `receivers[]`/`services[]`/`providers[]`, intentFilters populated for services/receivers, authorities populated for providers, exported field correct, reachesMop and mopMethods populated, `reachability[]` entries have `componentType`/`isMain` fields (no `isActivity`/`isMainActivity`).
- [x] 3.4 Generate JSON for a test APK WITHOUT non-Activity components. Verify: `"components": {"receivers": [], "services": [], "providers": []}`, `componentType="activity"` for activity classes, `componentType=null` for other classes.

## 4. rv-static-analysis Python parser update

## 5. Activity intent-filters in components{} — complete triggering data for all component types

- [x] 5.1 Parse `android:exported` attribute for Activities in `DefaultXMLParser.readManifest()`. Add after `readIntentFilters(cls, n)` in the activity block. Same pattern as services/receivers: extract from `NamedNodeMap`, default to `true` if has intent-filters. Store in `componentExported` map.
- [x] 5.2 Add `activities[]` array to `writeComponents()` in `RvsecAnalysisClient.java`. Write BEFORE receivers (activities first — most important for triggering). Use `writeComponentEntry()` with Activity lifecycle method names from `output.getLifecycleHandlers()`. Add `isMain` boolean field to Activity entries only (the main launcher activity). For lifecycle methods, use the same names GATOR already tracks for Activities (no change needed — existing `getEntryPoints()` already handles Activities via `output.getActivities()`).
- [x] 5.3 Add `isMain` field to Activity entries in `writeComponentEntry()`. Since only Activities need `isMain`, add an `isMain` parameter to `writeComponentEntry()` (default `false`, pass `true` for the main activity). This avoids a separate method for Activities.
- [x] 5.4 Build: `mvn clean install -DskipTests` in rvsec-gator — verify BUILD SUCCESS.
- [x] 5.5 Update spec scenario "Components section in JSON" to include `activities[]` with `intentFilters`, `exported`, `isMain`, `reachesMop`, `mopMethods`.
- [x] 5.6 Smoke test: re-run GATOR on `com.xmission.trevin.android.todo_1.apk`, verify `activities[]` in JSON with intent-filters for ToDoListActivity (main=true, has MAIN+LAUNCHER intent-filter).

- [x] 4.1 Update `Clazz` domain model: replace `is_activity: bool` and `is_main_activity: bool` with `component_type: str | None` and `is_main: bool`. Move old model file to `backup/`.
- [x] 4.2 Update `StaticAnalysisParser._parse_classes()` to read `componentType` (string or null) and `isMain` (boolean) from JSON instead of `isActivity`/`isMainActivity`. Populate the new `Clazz` fields.
- [x] 4.3 Grep all callers of `Clazz.is_activity` and `Clazz.is_main_activity` across rv-android modules. Update each call site to use `component_type` and `is_main`. Common patterns: `clazz.is_activity` → `clazz.component_type == "activity"`, `clazz.is_main_activity` → `clazz.is_main`.
- [x] 4.4 Update existing tests for `StaticAnalysisParser` to use the new field names and values. Add test for parsing a reachability entry with `componentType="service"`.
- [x] 4.5 Run `uv run pytest modules/rv-static-analysis/tests/ -v` — verify all tests pass.
