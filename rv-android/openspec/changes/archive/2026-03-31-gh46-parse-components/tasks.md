## 1. Domain models (rv-android-core)

- [x] 1.1 Create `modules/rv-android-core/src/rv_android_core/domain/components.py` with `IntentFilter` model: `actions: list[str]`, `categories: list[str]`. Use `@validated_model`, `Field(default_factory=list)`.
- [x] 1.2 Add `ComponentInfo` model to same file: `class_name: str`, `component_type: str` ("activity"/"service"/"receiver"/"provider"), `is_main: bool`, `intent_filters: list[IntentFilter]`, `authorities: str | None`, `exported: bool`, `reaches_mop: bool`, `mop_methods: list[str]`.
- [x] 1.3 Add `Components` container model: `activities`, `receivers`, `services`, `providers` (lists of ComponentInfo). Add methods: `get_by_type(component_type) -> list`, `get_all() -> list`, `get_mop_components() -> list`, `get_exported_components() -> list`, `get_by_class_name(name) -> ComponentInfo | None`, `get_analysis_summary() -> dict`.
- [x] 1.4 Modify `modules/rv-android-core/src/rv_android_core/domain/static.py`: add `components: Components = Field(default_factory=Components)` to `StaticAnalysisData`. Import `Components`. Do NOT change `@validated_model` positional list.

## 2. Parser (rv-static-analysis)

- [x] 2.1 Add `_parse_intent_filters(filters_data: list) -> list[IntentFilter]` to `StaticAnalysisParser`.
- [x] 2.2 Add `_parse_component_list(entries: list, component_type: str) -> list[ComponentInfo]` for activities/receivers/services (shared shape with intentFilters).
- [x] 2.3 Add `_parse_provider_list(entries: list) -> list[ComponentInfo]` for providers (authorities instead of intentFilters). Note: `is_main` defaults to `False` for providers since the JSON does not include this field for providers.
- [x] 2.4 Add `_parse_components(data: dict) -> Components` that calls the above helpers. Wrap in try/except returning empty `Components()` on error (same pattern as other sections).
- [x] 2.5 Wire `_parse_components()` into `parse_file()`: call after transitions, pass result as `components=` kwarg to `StaticAnalysisData`. Update log message with component counts.

- [x] 2.6 Update `modules/rv-android-core/src/rv_android_core/domain/__init__.py` if it exports domain models — add `Components`, `ComponentInfo`, `IntentFilter` to public exports. Skip if `__init__.py` does not re-export domain models.

## 3. Spec update (analysis/spec.md)

- [x] 3.1 Add `Components`, `ComponentInfo`, `IntentFilter` models to the Data Models section of `openspec/specs/analysis/spec.md` (after `WindowTransition` model, before `RvCoverageLog`).
- [x] 3.2 Update `StaticAnalysisData` model in Data Models: add `components: Components` field.
- [x] 3.3 Update line that says "StaticAnalysisData domain model (Classes, Windows, WindowTransitionGraph)" to include Components.
- [x] 3.4 Add scenario "Static analysis JSON parsing — components section" describing how `StaticAnalysisParser._parse_components()` processes the `components{}` section, with graceful degradation for missing data.

## 4. Tests

- [x] 4.1 Create `modules/rv-android-core/tests/domain/test_components.py`: TestIntentFilter (init, defaults), TestComponentInfo (activity with intent-filters, provider with authorities, defaults, validation), TestComponents (get_by_type, get_all, get_mop_components, get_exported_components, get_by_class_name, empty, analysis_summary).
- [x] 4.2 Add `TestComponentsParsing` to `modules/rv-static-analysis/tests/parser/static/test_static_analysis_parser.py`: parse activities, providers with authorities, all 4 types, MOP methods, exported flag, missing section, empty section, malformed data.
- [x] 4.3 Run `uv run pytest modules/rv-android-core/tests/ modules/rv-static-analysis/tests/ -v` — all tests pass.

## 5. Verification

- [x] 5.1 Smoke test: parse `/tmp/gh45_smoke/todo/com.xmission.trevin.android.todo_1.apk.json` e verificar: 7 activities, 5 services, 1 receiver, 1 provider, ToDoListActivity.is_main=True.
